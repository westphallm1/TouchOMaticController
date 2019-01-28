import sys
import os
import threading
from PyQt5 import QtCore, QtGui, QtWidgets

import dummySerial as serial
import touch_o_matic


class SerialTee():
    """Write to both a serial device and something else"""
    def __init__(self, serial_device, print_fn):
        self.ser = serial_device
        self.print_fn = print_fn
    
    def write(self,text,*args,**kwargs):
        self.ser.write(text,*args,**kwargs)
        self.print_fn('> '+text)

    def readline(self):
        result = self.ser.readline()
        self.print_fn(result)


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
        def write_to_log(text):
            assert isinstance(text,str)
            self.commandLog.appendPlainText(text)

        ser = serial.Serial(self.serialPort.currentText(),
                self.baudRateValue.value())

        self.ser = SerialTee(ser,write_to_log)
        self.commandLog.appendPlainText(
                "Connected to {} at baudrate {}"
                .format(self.serialPort.currentText(), self.baudRateValue.value()))

        # enable buttons
        self.cmdButtons = [self.startScan, self.stopScan, self.goHome, 
                self.setHome, self.yPlus, self.yMinus, self.xPlus, 
                self.xMinus, self.emergencyStop]

        for button in self.cmdButtons:
             button.setEnabled(True)


    def startScanning(self):
        time_multiplier = {"Seconds":1,"Minutes":60,"Hours":3600}[
                self.yIntervalUnits.currentText()]
        time_interval = self.yIntervalValue.value() * time_multiplier
        print("Starting scan for every {} seconds".format(time_interval))
        self.sendScanCommand()
        self.scanTimer.start(time_interval*1000)

    def stopScanning(self):
        print("Stopping scan.")
        self.scanTimer.stop()

    def sendScanCommand(self):
        def send_scan():
            self.ser.write("Scan.")
            # Make sure command goes through
            self.ser.readline()
        threading.Thread(target=send_scan, daemon=True).start()


def run():
    app = QtWidgets.QApplication(sys.argv)
    viewer = TouchOMaticApp()
    viewer.show()
    app.exec_()

if __name__ == '__main__':
    run()
