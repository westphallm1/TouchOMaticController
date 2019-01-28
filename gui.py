import sys
import os
from PyQt5 import QtCore, QtGui, QtWidgets

import dummySerial as serial
import touch_o_matic


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

        # Scan timer initial value
        self.scanTimer = QtCore.QTimer(self)
        self.scanTimer.timeout.connect(self.sendScanCommand)
        self.scanTimer.setSingleShot(False)

    def connect(self):
        self.ser = serial.Serial(self.serialPort.currentText(),
                self.baudRateValue.value())


    def startScanning(self):
        time_multiplier = {"Seconds":1,"Minutes":60,"Hours":3600}[
                self.yIntervalUnits.currentText()]
        time_interval = self.yIntervalValue.value() * time_multiplier
        print("Starting scan for every {} seconds".format(time_interval))
        self.scanTimer.start(time_interval*1000)

    def stopScanning(self):
        print("Stopping scan.")
        self.scanTimer.stop()

    def sendScanCommand(self):
        self.ser.write("Scan.")
        # Make sure command goes through
        self.ser.readline()


def run():
    app = QtWidgets.QApplication(sys.argv)
    viewer = TouchOMaticApp()
    viewer.show()
    app.exec_()

if __name__ == '__main__':
    run()
