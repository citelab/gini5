from Router import *
from PyQt4 import QtCore

##
# Class: the wireless router class
class Wireless_access_point(Router):
    device_type="Wireless_access_point" 

    ##
    # Constructor: Initial a router device
    # @param x the x axis of the device on the canvas
    # @param y the y axis of the device on the canvas
    # @param r_num the serial number of the router
    # @param t_num the serial number of the name tag
    def __init__(self):
        Device.__init__(self)

        self.interface = []
        self.num_interface=0
        self.connection=[]
        self.con_int={}                         # the connection and interface pair
        self.wireless_con_list=[]                # the list of wireless devices that share this wireless connection
        self.next_interface_number=0

        # by default, auto compute routing table is off
        self.auto=0

        #wireless properties
        self.properties[QtCore.QString("w_type")]="Sample Card"
        self.properties[QtCore.QString("freq")]="2400000000"
        self.properties[QtCore.QString("bandwidth")]="2000000.0"
        self.properties[QtCore.QString("Pt")]="0.2818"
        self.properties[QtCore.QString("Pt_c")]="0.660"
        self.properties[QtCore.QString("Pr_c")]="0.395"
        self.properties[QtCore.QString("P_idle")]="0.0"
        self.properties[QtCore.QString("P_sleep")]="0.130"
        self.properties[QtCore.QString("P_off")]="0.043"
        self.properties[QtCore.QString("RX")]="2.818e-9"
        self.properties[QtCore.QString("CS")]="1.409e-9"
        self.properties[QtCore.QString("CP")]="10"
        self.properties[QtCore.QString("module")]="DSSS"
        self.properties[QtCore.QString("a_type")]="Omni Directional Antenna"
        self.properties[QtCore.QString("ant_h")]="1"
        self.properties[QtCore.QString("ant_g")]="1"
        self.properties[QtCore.QString("ant_l")]="1"
        self.properties[QtCore.QString("JAM")]="off"
        self.properties[QtCore.QString("power")]="ON"
        self.properties[QtCore.QString("PSM")]="OFF"
        self.properties[QtCore.QString("energy_amount")]="100"
        self.properties[QtCore.QString("m_type")]="Random Waypoint"
        self.properties[QtCore.QString("ran_max")]="15"
        self.properties[QtCore.QString("ran_min")]="5"
        self.properties[QtCore.QString("mac_type")]="MAC 802.11 DCF"
        self.properties[QtCore.QString("trans")]="0.1"

        self.interfaces.append({
            QtCore.QString("subnet"):QtCore.QString(""),
            QtCore.QString("mask"):QtCore.QString(""),
            QtCore.QString("ipv4"):QtCore.QString(""),
            QtCore.QString("mac"):QtCore.QString(""),
            QtCore.QString("routing"):[]})

        self.lightPoint = QPoint(-14,15)

    def generateToolTip(self):
        """
        Add subnet IP address to the tool tip for easier lookup.
        """
        tooltip = self.getName()
        interface = self.getInterface()
        tooltip += "\n\nSubnet: " + interface[QtCore.QString("subnet")] + "\n"
        tooltip += "IP: " + interface[QtCore.QString("ipv4")]          
        self.setToolTip(tooltip)

