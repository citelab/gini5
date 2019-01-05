from Core.Connection import *
from Core.Interfaceable import *
from Core.globals import environ
from PyQt4.QtCore import QPoint

class Mach(Interfaceable):
    device_type="Mach"

    def __init__(self):
        Interfaceable.__init__(self)

        self.setProperty("ipv4", "")
        self.setProperty("port", "")
        self.setProperty("mac", "")
        self.lightPoint = QPoint(-10,3)
