#!/usr/bin/python2

from SimpleXMLRPCServer import SimpleXMLRPCServer
from SimpleXMLRPCServer import SimpleXMLRPCRequestHandler
from yrouterAPI import *
from XmlAPI import *
from Database import *
import socket
import fcntl
import struct

class StationEntity:
	def __init__(self, ID, CurrWlan, MaxWlan, IsPortal):
		self.ID = ID
		self.CurrWlan = CurrWlan
		self.MaxWlan = MaxWlan
		self.IsPortal = IsPortal

	def print_me(self):
		print "Station ID = %d" %self.ID
		print "Current Wlan Interfaces = %d" %self.CurrWlan
		print "Max Wlan Interfaces = %d" %self.MaxWlan
		print "IsPortal = %d" %self.IsPortal

# Restrict to a particular path.
class RequestHandler(SimpleXMLRPCRequestHandler):
    rpc_paths = ('/RPC2',)

class WGINI_Server:

	def __init__(self, ServerIP, ServerPort):
		# Create database instance
		self.database = WGINI_DB("WGINI.db")
		# Create XMLRPC server
		self.server = SimpleXMLRPCServer((ServerIP, ServerPort),
		                            requestHandler=RequestHandler)
		self.server.register_introspection_functions()
		# Register functions
		self.server.register_instance(self)

	def StartServer(self):
		self.server.serve_forever()

	# Returns an array of all Stations available
	def Check(self):
		StationIDs = self.database.GetAllStations()
		StationsWithWlan = self.database.GetWlanInfo()
		Stations = []
		for StationID in StationIDs:
			Stations.append(StationEntity(StationID, 0, self.database.GetMaxWlan(StationID), self.database.IsPortal(StationID)))
			# Get the current number of used wlan interfaces for the last appended Station
			for AvailStation in StationsWithWlan:
				if(StationID == AvailStation[0]):
					Stations[-1].CurrWlan = AvailStation[1]
					break

		return Stations

    # Kills all instances of the topology from the Stations and updates the database
	def Delete(self, HostIP):
		StationsWithWlan = self.database.GetStationsWithWlan(HostIP)
		TopID = self.database.GetTopologyID(HostIP)
		for Station in StationsWithWlan:
			StationIP = self.database.GetStationIP(Station)
			print "Delete: Deleting wlan Interface on Station%d with IP address %s" %(Station, StationIP)
			delete_Wlan_iface(TopID, StationIP)

		StationsUsed = self.database.GetStationsUsed(HostIP)

		for Station in StationsUsed:
			StationIP = self.database.GetStationIP(Station)
			print "Delete: Killing yRouter on Station%d with IP address %s" %(Station, StationIP)
			kill_yrouter(TopID, StationIP)

		self.database.DeleteInterfaces(HostIP)
		self.database.DeleteTopology(HostIP)
		return "Delete: Topology %d deleted"%TopID

    # Deploys the topology on the platform and Updates the database
	def Create(self, XMLstring, HostIP):

		XML = XML_Top(XMLstring)
		XML.Parse()

		# Validation
		Stations = self.Check()
		for XML_Station in XML.Stations:
			# Find Station object from the Stations array
			Station = None
			for CurrStation in Stations:
				if(XML_Station.ID == CurrStation.ID):
					Station = CurrStation
					break

			if( (len(XML_Station.BBIfaces) > 0) and (Station.IsPortal != 1)):
				return "Create: Only Mesh Portals can have BBiface"

			WlanIfacesLen = len(XML_Station.WlanIfaces)
			if(WlanIfacesLen > 1):
				return "Cannot have more than 1 wlan interfaces on a given Station"

			if(Station.CurrWlan + WlanIfacesLen > Station.MaxWlan):
				return "Create: Not enough wlan interfaces on Station %d"%Station.ID

		# Make sure the user doesn't have an existing topology deployed
		#if(self.database.GetTopologyID(HostIP) != None):
			#return "Create: Please delete the exising topology before creating a new one"

		self.database.AddTopology(HostIP)
		TopID = self.database.GetTopologyID(HostIP)

		for Station in XML.Stations:

			# TODO Fix this: currently expects DestIface to be a key and returns an error when its zero
			#for Interface in Station.BBIfaces:
			#	self.database.AddInterface("BB", Interface.num, TopID, Station.ID, Interface.DestIface)

			for Interface in Station.TunIfaces:
				self.database.AddInterface("tun", Interface.num, TopID, Station.ID, Interface.DestID)

			for Interface in Station.WlanIfaces:
				self.database.AddInterface("wlan", Interface.num, TopID, Station.ID, None)

		# Run yRouters
		for Station in XML.Stations:
			interfaces = ifaces(TopID, self.database.GetStationIP(Station.ID))

			for BBiface in Station.BBIfaces:
				dst_ip = HostIP
				dst_iface = BBiface.DestIface
				interfaces.AddTunIface(tun_iface(BBiface.num, dst_ip, dst_iface, BBiface.vIP, BBiface.vHW, BBiface.routes))

			for tuniface in Station.TunIfaces:
				dst_ip = self.database.GetStationIP(tuniface.DestID)
				dst_iface = self.database.GetDestInterface(Station.ID, tuniface.DestID, TopID)
				if(dst_iface == None):
					print "Error: Dst Iface not found"
					return "Create: No interface on Station%d for interface on Station%d"%(tuniface.DestID, Station.ID)

				interfaces.AddTunIface(tun_iface(tuniface.num, dst_ip, dst_iface, tuniface.vIP, tuniface.vHW, tuniface.routes))

			for WlanIF in Station.WlanIfaces:
				interfaces.AddWlanIface(WlanIF)

			run_yrouter(interfaces, Station.ID)

		return "Create: Topology %d deployed" %TopID

def get_ip_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915,  # SIOCGIFADDR
        struct.pack('256s', ifname[:15])
    )[20:24])


if __name__== "__main__":
	wgini_server = WGINI_Server(get_ip_address('eth1'), 60000)
	wgini_server.StartServer()
