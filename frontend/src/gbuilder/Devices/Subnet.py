from Core.Connection import *
from Core.Device import *
from Core.Interfaceable import Interfaceable

##
# Class: the Subnet
class Subnet(Device):
    device_type="Subnet"    

    def __init__(self):
        Device.__init__(self)
                
        self.num_interface=0
        self.setProperty("subnet", "")
        self.setProperty("mask", "")
#        self.setProperty("bits", "")

    def addEdge(self, edge):
        Device.addEdge(self, edge)

        if len(self.edgeList) == 2:
            node1 = self.edgeList[0].getOtherDevice(self)
            node2 = self.edgeList[1].getOtherDevice(self)
            if isinstance(node1, Interfaceable):
                node1.addInterface(node2)
            if isinstance(node2, Interfaceable):
                node2.addInterface(node1)

    def removeEdge(self, edge):
        if len(self.edgeList) == 2:
            node1 = self.edgeList[0].getOtherDevice(self)
            node2 = self.edgeList[1].getOtherDevice(self)
            if isinstance(node1, Interfaceable):
                node1.removeInterface(node2)
            if isinstance(node2, Interfaceable):
                node2.removeInterface(node1)
            
        Device.removeEdge(self, edge)

    # Return the other node to which the subnet is connected, if any
    def getTarget(self, node):
        for con in self.edges():
            other = con.getOtherDevice(self)
            if other != node:
                return other

    def setProperty(self, prop, value):
        Device.setProperty(self, prop, value)
        if prop == "subnet":
            self.setToolTip(self.getName() + "\nSubnet: " + value)

