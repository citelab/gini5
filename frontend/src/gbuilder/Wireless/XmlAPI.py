# Functions for parsing the TSF 

import xml.etree.ElementTree as etree
from yrouterAPI import wlan_iface, rentry

class XML_tuniface:
    def __init__(self, num, DestID, vIP, vHW):
        self.num = num
        self.DestID = DestID
        self.vIP = vIP
        self.vHW = vHW
        self.routes = []

    def AddRoute(self, route):
        self.routes.append(route)

class XML_BBiface:
    def __init__(self, num, DestIface, vIP, vHW):
        self.num = num
        self.DestIface = DestIface
        self.vIP = vIP
        self.vHW = vHW
        self.routes = []

    def AddRoute(self, route):
        self.routes.append(route)

class XML_Station:
    def __init__(self, ID):
        self.ID = ID
        self.TunIfaces = []
        self.WlanIfaces = []
        self.BBIfaces = []

    def AddTunIface(self, TunIface):
        self.TunIfaces.append(TunIface)

    def AddWlanIface(self, WlanIface):
        self.WlanIfaces.append(WlanIface)

    def AddBBIface(self, BBIface):
        self.BBIfaces.append(BBIface)

class XML_Top:
    def __init__(self, name):
        self.root = etree.fromstring(name)
        self.Stations = []

    def Parse(self):
        for Station in self.root.findall('Station'):
            ID = int(Station.find('ID').text)
            nStation = XML_Station(ID)
            index = 0

            for BBInterface in Station.findall('BBInterface'):
                #InterfaceNo = int(BBInterface.find('InterfaceNo').text)
                InterfaceNo = index
                index = index + 1
                DestIface = int(BBInterface.find('DestIface').text)
                IPAddress = BBInterface.find('IPAddress').text
                HWAddress = BBInterface.find('HWAddress').text
                BBIface = XML_BBiface(InterfaceNo, DestIface, IPAddress, HWAddress)
                for REntry in BBInterface.findall('REntry'):
                    Net = REntry.find('Net').text
                    NetMask = REntry.find('NetMask').text
                    NextHop = REntry.find('NextHop').text
                    route = rentry(Net, NetMask, NextHop)
                    BBIface.AddRoute(route)

                nStation.AddBBIface(BBIface)

            for Interface in Station.findall('Interface'):
                #InterfaceNo = int(Interface.find('InterfaceNo').text)
                InterfaceNo = index
                index = index + 1
                DestStationID = int(Interface.find('DestStationID').text)
                IPAddress = Interface.find('IPAddress').text
                HWAddress = Interface.find('HWAddress').text
                TunIface = XML_tuniface(InterfaceNo, DestStationID, IPAddress, HWAddress)
                for REntry in Interface.findall('REntry'):
                    Net = REntry.find('Net').text
                    NetMask = REntry.find('NetMask').text
                    if(NetMask == None):
                        NetMask = "255.255.255.0"
                    NextHop = REntry.find('NextHop').text
                    route = rentry(Net, NetMask, NextHop)
                    TunIface.AddRoute(route)

                nStation.AddTunIface(TunIface)

            for WlanInterface in Station.findall('WlanInterface'):
                #InterfaceNo = int(WlanInterface.find('InterfaceNo').text)
                InterfaceNo = index
                index = index + 1
                IPAddress = WlanInterface.find('IPAddress').text
                WlanIface = wlan_iface(InterfaceNo, IPAddress)
                for REntry in WlanInterface.findall('REntry'):
                    Net = REntry.find('Net').text
                    NetMask = REntry.find('NetMask').text
                    NextHop = REntry.find('NextHop').text
                    route = rentry(Net, NetMask, NextHop)
                    WlanIface.AddRoute(route)

                nStation.AddWlanIface(WlanIface)

            self.AddStation(nStation)

    def AddStation(self, Station):
        self.Stations.append(Station)

    def print_me(self):

        for Station in self.Stations:
            print "Station%d" %Station.ID
            for TunIface in Station.TunIfaces:
                print "tun%d Dest=Station%d vIP=%s vHw=%s" %(TunIface.num, TunIface.DestID, TunIface.vIP, TunIface.vHW)
                for route in TunIface.routes:
                    print "route net=%s netmask=%s gw=%s" %(route.net, route.netmask, route.nexthop)

            for WlanIface in Station.WlanIfaces:
                print "wlan%d vIP=%s" %(WlanIface.num, WlanIface.vIP)
                for route in WlanIface.routes:
                    print "route net=%s netmask=%s gw=%s" %(route.net, route.netmask, route.nexthop)
