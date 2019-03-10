from Core.Interfaceable import *
from PyQt4.QtCore import QPoint


class Cloud(Interfaceable):
    device_type = "Cloud"

    def __init__(self):
        super(Cloud, self).__init__()

        self.setProperty("ipv4", "")
        self.setProperty("mac", "")
        self.lightPoint = QPoint(0, 0)
