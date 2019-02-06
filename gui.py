import sys
import os
import threading
import time
from PyQt5 import QtCore, QtGui, QtWidgets
import yaml
import logging

import dummySerial as serial
import touch_o_matic
import clickanddraw


class SerialTeeThread(QtCore.QThread):
    updated = QtCore.pyqtSignal(str)

    def __init__(self,parent,ser_dev):
        super(QtCore.QThread,self).__init__(parent)
        self.ser = ser_dev

    def set_serial(self,ser_dev):
        self.ser = ser

    def start(self,messages):
        self.messages = messages
        QtCore.QThread.start(self)

    def run(self):
        for message in self.messages:
            self.updated.emit('> ' + message)
            self.ser.write(message)
            result = self.ser.readline()
            self.updated.emit(result.strip())



class TouchOMaticApp(QtWidgets.QMainWindow, touch_o_matic.Ui_MainWindow):
    def __init__(self,parent = None):
        super(TouchOMaticApp,self).__init__(parent)
        self.setupUi(self)
        
        # Connection Menu
        self.ser = None
        self.serialPort.addItems(serial.get_ports())
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
        self.cmdButtons = [self.startScan, self.stopScan, self.goHome, 
                self.setHome, self.yPlus, self.yMinus, self.xPlus, 
                self.xMinus, self.emergencyStop]

        # Widgets for free draw
        self._setupGraphics()

        # List of known CNC machines
        self._readMachineInfo()

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


    def _setupGraphics(self):
        # Todo: Better names
        self.freeDrawView = clickanddraw.QClickAndDraw(self.tab_2)
        self.freeDrawView.setObjectName("freeDrawView")
        self.horizontalLayout_11.addWidget(self.freeDrawView)
        self.zoomInButton.clicked.connect(self.freeDrawView.zoomIn)
        self.zoomOutButton.clicked.connect(self.freeDrawView.zoomOut)
        self.rotateL.clicked.connect(self.freeDrawView.rotateL)
        self.rotateR.clicked.connect(self.freeDrawView.rotateR)
        #self.panButton.clicked.connect(self.freeDrawView.pan)
        #self.drawButton.clicked.connect(self.freeDrawView.draw)

    def connect(self):
        self.ser = serial.Serial(self.serialPort.currentText(),
                self.baudRateValue.value())

        self.ser_tee = SerialTeeThread(self,self.ser)
        self.ser_tee.updated.connect(self.commandLog.appendPlainText)

        self.commandLog.appendPlainText(
                "Connected to {} at baudrate {}"
                .format(self.serialPort.currentText(), self.baudRateValue.value()))

        for button in self.cmdButtons:
             button.setEnabled(True)


    def stepxPlus(self):
        self.ser_tee.start(["G90 GO X{}".format(self.manualStepValue.value())])
    def stepxMinus(self):
        self.ser_tee.start(["G90 GO X-{}".format(self.manualStepValue.value())])
    def stepyPlus(self):
        self.ser_tee.start(["G90 GO Y{}".format(self.manualStepValue.value())])
    def stepyMinus(self):
        self.ser_tee.start(["G90 GO Y-{}".format(self.manualStepValue.value())])

    def startScanning(self):
        time_multiplier = {"Seconds":1,"Minutes":60,"Hours":3600}[
                self.yIntervalUnits.currentText()]
        time_interval = self.yIntervalValue.value() * time_multiplier
        self.commandLog.appendPlainText("Starting scan on {} {} interval."
                .format(self.yIntervalValue.value(),
                        self.yIntervalUnits.currentText().lower()[:-1]))
        self.sendScanCommand()
        for button in self.cmdButtons[2:-1]:
             button.setEnabled(False)
        self.scanTimer.start(time_interval*1000)

    def stopScanning(self):
        self.commandLog.appendPlainText("Stopping scan.")
        self.scanTimer.stop()
        self.ser_tee.quit()
        for button in self.cmdButtons[2:-1]:
             button.setEnabled(True)

    def emergencyStopScanning(self):
        self.ser_tee.terminate()
        # Hack to increase likelihood that thread can start again
        time.sleep(0.1)
        self.ser_tee.start(["!"])
        for button in self.cmdButtons[2:-1]:
             button.setEnabled(True)


    def sendScanCommand(self):
        GO_CMD = "G90 GO Y-{}".format(self.yLengthValue.value())
        BACK_CMD = "G90 GO Y{}".format(self.yLengthValue.value())
        self.ser_tee.start([GO_CMD,BACK_CMD])

def run():
    app = QtWidgets.QApplication(sys.argv)
    viewer = TouchOMaticApp()
    viewer.show()
    app.exec_()

if __name__ == '__main__':
    run()
