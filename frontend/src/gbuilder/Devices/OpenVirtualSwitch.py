from Core.Attachable import *
from .Switch import Switch
from PyQt4.QtCore import QPoint

class OpenVirtualSwitch(Switch, Attachable):
    """
    Class definition for Open Virtual Switch devices
    """
    device_type = "OVSwitch"

    def __init__(self):
        Switch.__init__(self)
        Attachable.__init__(self)
        self.setProperty("OVS mode", "True")

        self.lightPoint = QPoint(-10,-5)
