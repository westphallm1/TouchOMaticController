import time

class Serial():
    def __init__(self, device, baud_rate):
        print("Connecting to serial device {} at baudrate {}".format(
              device, baud_rate))

    def write(self,cmd):
        print("Sending: {}".format(cmd))

    def readline(self):
        # Simulate waiting for a response
        time.sleep(10)
        print("Recieved: ok")
        return "ok\n"


def get_ports():
    return ["/dev/ttyACM0"]
