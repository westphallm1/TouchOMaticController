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

    def __getattr__(self,attr):
        if attr in self.__dict__:
            return self.__dict__[attr]
        else:
            return lambda *args, **kwargs:None


def get_ports():
    return ["/dev/ttyACM0"]
