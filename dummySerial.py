import time

class Serial():
    def __init__(self, device, baud_rate):
        pass
    def write(self,cmd):
        # Do nothing with the text
        pass

    def readline(self):
        # It's always OK
        return bytes("ok\n","ascii")


def get_ports():
    return ["/dev/ttyACM0"]
