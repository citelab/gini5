from UML import *
from PyQt4.QtCore import QPoint
from UI.StatsWindow import *

class Mobile(UML):
    device_type="Mobile"
 
    def __init__(self):
        UML.__init__(self)
        
        self.next_interface_number=0
        
        self.lightPoint = QPoint(-4,16)

        self.wstatsWindow = StatsWindow(self.getName(), mainWidgets["canvas"])
        self.setAcceptsHoverEvents(True)

    def addEdge(self, edge):
        Device.addEdge(self, edge)

        node = edge.getOtherDevice(self)
        self.addInterface(node)

    def removeEdge(self, edge):
        Device.removeEdge(self, edge)

        node = edge.getOtherDevice(self)
        self.removeInterface(node)

