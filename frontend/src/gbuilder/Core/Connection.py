"""The logical connection object that links two devices together"""

from Devices.Bridge import *
from Devices.Firewall import *
from Devices.Hub import *
from Devices.Mobile import *
from Devices.Router import *
from Devices.Subnet import *
from Devices.Switch import *
from Devices.Mach import *
from Devices.Wireless_access_point import *
from Devices.yRouter import *
from UI.Edge import *
from Devices.REALM import *
from Devices.OpenFlow_Controller import *

# The connection rules for building topologies
connection_rule={}
connection_rule[Mach.device_type]=(Switch.device_type, Subnet.device_type, Bridge.device_type, Hub.device_type)
connection_rule[Router.device_type]=(Subnet.device_type, OpenFlow_Controller.device_type, Switch.device_type)
connection_rule[Switch.device_type]=(Mach.device_type, Subnet.device_type, Switch.device_type, Router.device_type)
connection_rule[Bridge.device_type]=(Mach.device_type, Subnet.device_type, REALM.device_type)
connection_rule[Hub.device_type]=(Mach.device_type, Subnet.device_type, REALM.device_type)
connection_rule[Wireless_access_point.device_type]=(Mobile.device_type)
connection_rule[Subnet.device_type]=(Mach.device_type, Switch.device_type, Router.device_type, yRouter.device_type, Bridge.device_type, Hub.device_type, Firewall.device_type, REALM.device_type)
connection_rule[Mobile.device_type]=(Wireless_access_point.device_type)
connection_rule[Firewall.device_type]=(Subnet.device_type)
connection_rule[REALM.device_type]=(Switch.device_type, Subnet.device_type, Bridge.device_type, Hub.device_type)
connection_rule[yRouter.device_type]=(Subnet.device_type)
connection_rule[OpenFlow_Controller.device_type]=(Router.device_type)

class Connection(Edge):
    device_type = "Connection"

    def __init__(self, source, dest):
        """
        Create a connection to link devices together.
        """
        Edge.__init__(self, source, dest)

    def getOtherDevice(self, node):
        """
        Retrieve the device opposite to node from this connection.
        """
        if self.source == node:
            return self.dest
        return self.source
