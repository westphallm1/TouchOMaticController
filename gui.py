import sys
import os
import threading
import time
from PyQt5 import QtCore, QtGui, QtWidgets
import yaml
import logging
import codecs
import serial
import touch_o_matic
import clickanddraw


class SerialTeeThread(QtCore.QThread):
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
        for message in self.messages:
            if self._stopped:
                self._stopped = False
                return
            self.updated.emit('> ' + message)
            self.ser.write(bytes(message+'\r\n','ascii'))
            result = self.ser.readline()
            self.updated.emit(result.strip().decode('ascii'))

    def stop(self):
        self._stopped = True



def stringdecoder(function):
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
        self.serialPort.addItems(['/dev/ttyACM0'])
        self.serialConnect.clicked.connect(self.connect)

        # Controls Menu
        self.startScan.clicked.connect(self.startScanning)
        self.stopScan.clicked.connect(self.stopScanning)
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

    @property
    def machine(self):
        return self.machines[self.cncSelect.currentText()]

    @property
    @stringdecoder
    def instructions(self):
        return self.machine['instructions']

    @property
    @stringdecoder
    def absolute(self):
        return self.machine['instructions']['absolute']

    @property
    @stringdecoder
    def relative(self):
        return self.machine['instructions']['relative']

    @property
    @stringdecoder
    def dimensions(self):
        return self.machine['dimensions']

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
        # Todo: Better names
        self.freeDrawView = clickanddraw.QClickAndDraw(self.customTab)
        self.freeDrawView.setObjectName("freeDrawView")
        self.horizontalLayout_11.addWidget(self.freeDrawView)
        self.zoomInButton.clicked.connect(self.freeDrawView.zoomIn)
        self.zoomOutButton.clicked.connect(self.freeDrawView.zoomOut)
        self.rotateL.clicked.connect(self.freeDrawView.rotateL)
        self.rotateR.clicked.connect(self.freeDrawView.rotateR)
        self.startCustom.clicked.connect(self.startScanningCustom)

    def connect(self):
        self.ser = serial.Serial(self.serialPort.currentText(),
                self.baudRateValue.value())

        self.ser_tee = SerialTeeThread(self,self.ser)
        self.ser_tee.updated.connect(self.commandLog.appendPlainText)

        self.commandLog.appendPlainText(
                "Connected to {} at baudrate {}"
                .format(self.serialPort.currentText(), self.baudRateValue.value()))

        self.ser.write(bytes(self.instructions['connect']+'\r\n','ascii'))
        for button in self.cmdButtons:
             button.setEnabled(True)


    def stepxPlus(self):
        self.ser_tee.start([self.relative['x'].format(x=self.manualStepValue.value())])

    def stepxMinus(self):
        self.ser_tee.start([self.relative['x'].format(x=-self.manualStepValue.value())])
    def stepyPlus(self):
        self.ser_tee.start([self.relative['y'].format(y=self.manualStepValue.value())])
    def stepyMinus(self):
        self.ser_tee.start([self.relative['y'].format(y=-self.manualStepValue.value())])


    def _getTimeInfo(self):
        time_multiplier = {"Seconds":1,"Minutes":60,"Hours":3600}[
                self.yIntervalUnits.currentText()]
        time_interval = self.yIntervalValue.value() * time_multiplier
        return {
            "units":self.yIntervalUnits.currentText(),
            "interval":self.yIntervalValue.value(),
            "interval_s":time_interval
        }
    def startScanning(self):
        time_info = self._getTimeInfo()
        self.commandLog.appendPlainText("Starting scan on {} {} interval."
                .format(time_info["interval"],time_info["units"]))
        self.sendScanCommand()
        for button in self.cmdButtons[3:]:
             button.setEnabled(False)
        self.scanTimer.start(time_info["interval_s"]*1000)

    def startScanningCustom(self):
        time_info = self._getTimeInfo()
        self.commandLog.appendPlainText("Starting custom scan on {} {} interval."
                .format(time_info["interval"],time_info["units"]))
        waypoints = self.freeDrawView.dumpWaypointsInfo()
        commands = [self.instructions['absolute']['xy'].format(**point)
                for point in waypoints]
        self.sendScanCommand(commands)

    def stopScanning(self):
        self.commandLog.appendPlainText("Stopping scan.")
        self.scanTimer.stop()
        self.ser_tee.stop()
        self.ser_tee.quit()
        for button in self.cmdButtons[2:-1]:
             button.setEnabled(True)

    def emergencyStopScanning(self):
        self.stopScanning()
        self.ser_tee.terminate()
        time.sleep(0.1)
        self.ser_tee.start([self.instructions['stop']])

    def sendScanCommand(self,commands=None):
        if not commands:
            GO_CMD = self.instructions['absolute']['y'].format(
                    y=self.yLengthValue.value())
            BACK_CMD = self.instructions['absolute']['y'].format(
                    y=0)
            commands = [GO_CMD,BACK_CMD]
        self.ser_tee.start(commands)

def run():
    app = QtWidgets.QApplication(sys.argv)
    viewer = TouchOMaticApp()
    viewer.show()
    app.exec_()

if __name__ == '__main__':
    run()
