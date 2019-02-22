import sys
import os
import threading
import time
import re
import queue
from PyQt5 import QtCore, QtGui, QtWidgets
import yaml
import logging
import codecs
import serial
import serial.tools.list_ports
import dummySerial
import touch_o_matic
import clickanddraw
serial_lock = QtCore.QMutex()

class SerialTeeThread(QtCore.QThread):
    """ Write commands to the serial port and wait for a result without
    blocking the main thread, and emit messages sent/recieved as a signal
    """
    updated = QtCore.pyqtSignal(str)

    def __init__(self,parent,ser_dev):
        super(QtCore.QThread,self).__init__(parent)
        self.ser = ser_dev
        self._stopped = False

    def set_serial(self,ser_dev):
        self.ser = ser

    def start(self,messages):
        self.messages = messages
        QtCore.QThread.start(self)

    def run(self):
        #self.setPriority(self.LowPriority)
        for message in self.messages:
            if self._stopped:
                self._stopped = False
                return
            self.updated.emit('> ' + message)
            serial_lock.lock()
            self.ser.flushInput()
            self.ser.flushOutput()
            self.ser.write(bytes(message+'\r\n','ascii'))
            result = self.ser.readline()
            serial_lock.unlock()
            self.updated.emit(result.strip().decode('ascii'))

    def stop(self):
        self._stopped = True

class SerialInfoThread(QtCore.QThread):
    """ Poll the info command repeatedly, and emit its result as a signal """
    commandSent = QtCore.pyqtSignal(str)
    updated = QtCore.pyqtSignal(dict)

    def __init__(self, parent, ser_dev, info, interval=100):
        super(QtCore.QThread,self).__init__(parent)
        self.ser = ser_dev
        self.info_cmd = bytes(info['command'],'ascii')
        self.regex = re.compile(info['regex'])
        self.order = info['order']
        self.interval = interval #interval to poll in ms
        self.tQ = queue.Queue()
        self._delta = 0
        self._last_pos = {'x':0,'y':0,'z':0}
        

    def run(self):
        #self.setPriority(self.HighPriority)
        while True:
            # ping the machine's position
            self.ping()
            # send a command if we have one in the pipeline
            self.send_command()
            time.sleep(self.interval/1000.)

    def send_command(self):
        if self.tQ.empty() or self._delta > 1e-5:
            return
        print(self._delta)
        message = self.tQ.get()
        self.commandSent.emit('> ' + message)
        self.ser.write(bytes(message+'\r\n','ascii'))
        #result = self.ser.readline()
        #self.updated.emit(result.strip().decode('ascii'))

    def ping(self):
        self.ser.flushInput()
        self.ser.flushOutput()
        self.ser.write(self.info_cmd)
        result = self.ser.readline().strip().decode('ascii')
        self.parse_position(result)

    def parse_position(self,position):
        match = re.search(self.regex,position)
        out = {'x':None, 'y':None, 'z':None}
        if match:
            self._delta = 0
            for coord in 'xyz':
                out[coord] = float(match.groups()[self.order.index(coord)])
                # compute the squared distance travelled since the last ping
                self._delta += (out[coord]-self._last_pos[coord])**2
            self._last_pos = out
            self.updated.emit(out)
            return True

    def enqueue(self,items):
        if isinstance(items,str):
            self.tQ.put(items)
        else:
            [self.tQ.put(item) for item in items]
			 

def stringdecoder(function):
    """Wrapper for functions that return a dictionary. Converts the dictionary
    returned by the function into a dictionary-like object that has all the
    unicode escape sequences (eg. '\\n') in its string values converted into the 
    appropriate ascii bytes, and all its other keys unchanged
    """
    class __stringdecoder():
        def __init__(self,dic):
            self._dict = dic
        def __getitem__(self,item):
            if isinstance(self._dict[item],str):
                return codecs.decode(self._dict[item],'unicode_escape')
            return self._dict[item]

    def wrapper(self,*args,**kwargs):
        return __stringdecoder(function(self,*args,**kwargs))

    return wrapper

class TouchOMaticApp(QtWidgets.QMainWindow, touch_o_matic.Ui_MainWindow):
    def __init__(self,parent = None):
        super(TouchOMaticApp,self).__init__(parent)
        self.setupUi(self)
        
        # Connection Menu
        self.ser = None
        self._add_serial_devices()
        self.serialConnect.clicked.connect(self.connect)

        # Controls Menu
        self.startScan.clicked.connect(self.startScanning)
        self.stopScan.clicked.connect(self.stopScanning)
        self.stopCustom.clicked.connect(self.stopScanning)
        self.setHome.clicked.connect(self.setNewHome)
        self.goHome.clicked.connect(self.moveToHome)
        self.emergencyStop.clicked.connect(self.emergencyStopScanning)


        # Manual control
        self.yPlus.clicked.connect(self.stepyPlus)
        self.yMinus.clicked.connect(self.stepyMinus)
        self.xPlus.clicked.connect(self.stepxPlus)
        self.xMinus.clicked.connect(self.stepxMinus)

        # Scan timer initial value
        self.scanTimer = QtCore.QTimer(self)
        self.scanTimer.timeout.connect(self.sendScanCommand)
        self.scanTimer.setSingleShot(False)

        # Buttons that can only be used while connected
        self.cmdButtons = [self.startScan, self.stopScan, self.emergencyStop,
                self.goHome, self.setHome, self.yPlus, self.yMinus, self.xPlus, 
                self.xMinus, self.startCustom, self.stopCustom]

        # Widgets for free draw
        self._setupGraphics()

        # List of known CNC machines
        self._readMachineInfo()

    def _add_serial_devices(self):
        ports = serial.tools.list_ports.comports()
        good_ports = [p[0] for p in ports if p[2] != 'n/a']
        if good_ports:
            self.serialPort.addItems(good_ports)
        else:
            self.serialPort.addItems(["Test Port (software only)"])

    @property
    def machine(self):
        return self.machines[self.cncSelect.currentText()]

    @property
    @stringdecoder
    def instructions(self):
        return self.machine['instructions']

    @property
    @stringdecoder
    def dimensions(self):
        return self.machine['dimensions']

 
    def _scaled_key(self,dic,key):
        """Another awful meta class that replaces the string formatting
        function with one that multiplies numeric values by a scale factor
        """
        try:
            scale = self.machine['scale-factor']
        except:
            scale = dict(x=1,y=1,z=1)
        
        string = dic[key]
        class _keyscaler():
            def __init__(self,string,scale):
                self._st = string
                self._sc = scale
            def format(self,*args,**kwargs):
                for dim in 'x','y','z':
                    if dim in kwargs:
                        kwargs[dim]*=self._sc[dim]
                return self._st.format(*args,**kwargs)

        return _keyscaler(string,scale)

    def scaled(self,key1,key2):
        return self._scaled_key(self.instructions[key1],key2)

    def _readMachineInfo(self):
        config_dir = os.path.join(os.path.split(__file__)[0],"config")
        yamls = [y for y in os.listdir(config_dir) if y.endswith('.yaml')]
        self.machines = {}
        for yam in yamls:
            yam = os.path.join(config_dir,yam)
            with open(yam) as y:
                try:
                    data = yaml.safe_load(y)
                    self.machines[data['name']] = data
                except:
                    logging.warning("Failed to parse config file {}".format(yam))

        for i,name in enumerate(sorted(self.machines.keys())):
            self.cncSelect.addItem(name)
            if self.machines[name].get('default'):
                self.cncSelect.setCurrentIndex(i)

        self.freeDrawView.setMachine(self.machines[self.cncSelect.currentText()])
        self.setMachine()

    def setMachine(self):
        self.primary_units.setText(self.machine['units'])
        self.secondary_units.setText(self.machine['units'])
        self.manual_units.setText(self.machine['units'])
        self.yLengthValue.setValue(self.machine['dimensions']['y-axis'])

    def _setupGraphics(self):
        # Add View to GUI
        self.freeDrawView = clickanddraw.QClickAndDraw(self.customTab)
        self.freeDrawView.setObjectName("freeDrawView")
        self.horizontalLayout_11.addWidget(self.freeDrawView)
        # Bind actions to buttons
        self.zoomInButton.clicked.connect(self.freeDrawView.zoomIn)
        self.zoomOutButton.clicked.connect(self.freeDrawView.zoomOut)
        self.rotateL.clicked.connect(self.freeDrawView.rotateL)
        self.rotateR.clicked.connect(self.freeDrawView.rotateR)
        self.startCustom.clicked.connect(self.startScanningCustom)
        # File I/O buttons
        self.saveCustom.clicked.connect(self.saveCustomFile)
        self.loadCustom.clicked.connect(self.loadCustomFile)
        # Selection signal
        self.freeDrawView.scene.selectionChanged.connect(self.showWaypointInfo)

    def showWaypointInfo(self):
        if len(self.freeDrawView.scene.selectedItems()) == 1:
            # find the index of the added item (inefficient)
            selected, = self.freeDrawView.scene.selectedItems()
            idx = (self.freeDrawView.waypointIndex(selected))
            self.waypointLabel.setText("Waypoint {}".format(idx))
            self._waypoint = selected
        else:
            self.waypointLabel.setText("Waypoint --")
            self._waypoint = None

    def saveCustomFile(self):
        to_save = QtWidgets.QFileDialog.getSaveFileName(self,"Save Scan Path",
                filter="YAML files (*.yaml)")
        if to_save:
            waypoints = self.freeDrawView.dumpWaypointsInfo()
            with open(to_save[0],'w') as ts:
                ts.write(yaml.dump(waypoints))
         
    def loadCustomFile(self):
        to_load = QtWidgets.QFileDialog.getOpenFileName(self,"Load Scan Path",
                filter="YAML files (*.yaml)")
        if to_load:
            with open(to_load[0]) as tl:
                info = yaml.load(tl.read())
                self.freeDrawView.loadWaypointsInfo(info)

    def connect(self):
        try:
            self.ser = serial.Serial(self.serialPort.currentText(),
                    self.baudRateValue.value())
        except:
            self.ser = dummySerial.Serial(self.serialPort.currentText(),
                    self.baudRateValue.value())

        #self.ser_tee = SerialTeeThread(self,self.ser)
        #self.ser_tee.updated.connect(self.commandLog.appendPlainText)

        self.ser_info = SerialInfoThread(self,self.ser,
                self.instructions['info'])

        self.ser_info.updated.connect(self.moveMachineMarker)
        self.ser_info.commandSent.connect(self.commandLog.appendPlainText)
        self.ser_info.start()

        self.commandLog.appendPlainText(
                "Connected to {} at baudrate {}"
                .format(self.serialPort.currentText(), self.baudRateValue.value()))

        self.ser.write(bytes(self.instructions['connect'],'ascii'))
        for button in self.cmdButtons:
             button.setEnabled(True)


    def _close_enough(self, v1, v2, threshold=.25):
        return abs(v1 - v2) < threshold
		
    def moveMachineMarker(self,event):
        try:
            scale = self.machine['scale-factor']
        except:
            scale = dict(x=1,y=1,z=1)
        x = event['x']/scale['x']
        y = event['y']/scale['y']
        waypoints = self.freeDrawView.dumpWaypointsInfo()
        self.freeDrawView.moveMachineMarker(x,y)
        
    def stepxPlus(self):
        self.ser_info.enqueue([self.scaled('relative','x')
            .format(x=self.manualStepValue.value())])

    def stepxMinus(self):
        self.ser_info.enqueue([self.scaled('relative','x')
            .format(x=-self.manualStepValue.value())])
    def stepyPlus(self):
        self.ser_info.enqueue([self.scaled('relative','y')
            .format(y=self.manualStepValue.value())])
    def stepyMinus(self):
        self.ser_info.enqueue([self.scaled('relative','y')
            .format(y=-self.manualStepValue.value())])


    def _getTimeInfo(self,custom = False):
        if custom:
            y_interval = self.customIntervalValue.value()
            y_units = self.customIntervalUnits.currentText()
        else:
            y_interval = self.yIntervalValue.value()
            y_units = self.yIntervalUnits.currentText()
        time_multiplier = {"Seconds":1,"Minutes":60,"Hours":3600}[y_units]
        time_interval = y_interval * time_multiplier
        return {
            "units":y_units,
            "interval":y_interval,
            "interval_s":time_interval
        }

    def moveToHome(self):
        cmd = self.scaled('absolute','xy').format(x=0,y=0)
        self.sendScanCommand(commands=[cmd])
        
    def setNewHome(self):
        cmd = self.instructions['set-home']
        self.sendScanCommand(commands=[cmd])
        self.freeDrawView.moveMachineMarker(0,0)
        
    def _startScanning(self,custom=False):
        time_info = self._getTimeInfo(custom=custom)
        self.commandLog.appendPlainText("Starting scan on {} {} interval."
                .format(time_info["interval"],time_info["units"]))
        if custom:
            waypoints = self.freeDrawView.dumpWaypointsInfo()
            move_commands = [self.scaled('absolute','xy').format(**p)
                        for p in waypoints]
            commands = []
            for command in move_commands:
                commands.append(command)
                #commands.append("G4 P0.1")
				
        else:
            there = self.scaled('absolute','y').format(
                    y=self.yLengthValue.value())
            back = self.scaled('absolute','y').format(
                    y=0)
            commands = [there,back]
        self.sendScanCommand(commands=commands)
        self.scanTimer.start(time_info["interval_s"]*1000)

    def startScanning(self):
        self._startScanning(custom=False)

    def startScanningCustom(self):
        self._startScanning(custom=True)

    def stopScanning(self):
        self.commandLog.appendPlainText("Stopping scan.")
        self.scanTimer.stop()
        #self.ser_tee.stop()
        #self.ser_tee.quit()

    def emergencyStopScanning(self):
        self.stopScanning()
        self.ser_tee.terminate()
        time.sleep(0.1)
        self.ser_tee.start([self.instructions['stop']])

    def sendScanCommand(self,commands=None):
        if commands:
            self._commands = commands
        self.ser_info.enqueue(self._commands)

def run():
    app = QtWidgets.QApplication(sys.argv)
    viewer = TouchOMaticApp()
    viewer.show()
    app.exec_()

if __name__ == '__main__':
    run()
