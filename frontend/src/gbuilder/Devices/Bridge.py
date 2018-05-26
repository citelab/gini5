from Core.Connection import *
from Core.Device import *

##
# Class: the bridge device. Not fully implemented yet
class Bridge(Device):
    device_type="Bridge"

    def __init__(self):
        Device.__init__(self)

        self.setProperty("port", "")
        self.setProperty("monitor", "")
        self.setProperty("hub", True)   # use hub mode by default 
