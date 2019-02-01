import time

class Serial():
    def __init__(self, device, baud_rate):
        pass
    def write(self,cmd):
        # Do nothing with the text
        pass

    def readline(self):
        # Simulate waiting for a response
        time.sleep(5)
        return "ok\n"


def get_ports():
    return ["/dev/ttyACM0"]
