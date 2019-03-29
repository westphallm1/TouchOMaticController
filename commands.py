from enum import Enum
class Action(Enum):
    NO_ACTION = 0
    TAKE_PHOTO = 1
    START_RECORDING = 2
    STOP_RECORDING = 3

    def __str__(self):
        return {
            Action.NO_ACTION: "No Action",
            Action.TAKE_PHOTO: "Take Photo",
            Action.START_RECORDING: "Start Recording",
            Action.STOP_RECORDING: "Stop Recording",
        }.get(self,"--")


class Command():
    """ Container object for commands sent over serial and their metadata """
    def __init__(self,text, sequence=None, action=None,instant=False,pos=None,
            response=False):
        # text to send over serial
        self.text = text
        # position in sequence of commands
        self.sequence = sequence
        # action to be called once the command completes
        self.action = action
        # Can it be sent before the previous command completes?
        self.instant = instant
        # Where the machine is at when the command is sent
        self.pos = None
        # Do we care about the response from the command?
        self.response = response
