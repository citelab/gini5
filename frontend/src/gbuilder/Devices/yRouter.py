from Router import *
from PyQt4 import QtCore

class yRouter(Router):
    device_type="yRouter"

    def __init__(self):
        Interfaceable.__init__(self)
        self.setProperty("WLAN", "False")
        self.setProperty("mac_type", "MAC 802.11 DCF")
        self.lightPoint = QPoint(-14,15)
