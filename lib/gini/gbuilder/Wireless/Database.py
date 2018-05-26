# Local Database APIs used by the WGINI server

import sqlite3, os

class WGINI_DB:

	def __init__(self, name):
		# delete database if already exists
		if (os.access(name, os.F_OK)):
			os.remove(name)

		self.conn = sqlite3.connect(name)
		self.c = self.conn.cursor()

		self.conn.execute('pragma foreign_keys=ON')
		self.conn.execute('pragma foreign_keys')

		self.CreateTables()

		# Add Station info into the new database
		self.AddStation("192.168.0.1", 3, 1)
		self.AddStation("192.168.0.2", 3, 0)


	def CreateTables(self):
		self.c.execute("CREATE TABLE Station(ID INTEGER PRIMARY KEY AUTOINCREMENT, IPAddress TEXT, MaxWlanInterfaces INT, IsPortal INT)")
		self.c.execute("CREATE TABLE Topology(ID INTEGER PRIMARY KEY AUTOINCREMENT, HostIP TEXT)")
		self.c.execute('''CREATE TABLE Interface(ID INTEGER PRIMARY KEY AUTOINCREMENT, Type TEXT, InterfaceNo INTEGER, TopologyID INTEGER, StationID INTEGER, DestStaID INTEGER, FOREIGN KEY (TopologyID) REFERENCES Topology(ID), FOREIGN KEY(StationID) REFERENCES Station(ID), FOREIGN KEY(DestStaID) REFERENCES Station(ID))''')

	def AddStation(self, IPAddress, MaxWlanInterfaces, IsPortal):
		self.c.execute("INSERT INTO Station (IPAddress, MaxWlanInterfaces, IsPortal) VALUES (?,?,?)",
			   (IPAddress, MaxWlanInterfaces, IsPortal))
		self.conn.commit()

	def AddTopology(self,HostIP):
		self.c.execute("INSERT INTO Topology (HostIP) VALUES (?)",
			   (HostIP,))
		self.conn.commit()

	def AddInterface(self, Type, InterfaceNo, TopologyID, StationID, DestStaID):
		self.c.execute("INSERT INTO Interface (Type, InterfaceNo, TopologyID, StationID, DestStaID) VALUES (?,?,?,?,?)",
			   (Type, InterfaceNo, TopologyID, StationID, DestStaID))
		self.conn.commit()

	def GetAllStations(self):
		Stations = []
		for Station in self.c.execute("SELECT ID FROM Station"):
			Stations.append(Station[0])
		return Stations

	# Returns the number of wlan interfaces on each Station (Station, no. of wlan interfaces)
	def GetWlanInfo(self):
		Stations = []
		for Station in self.c.execute("SELECT Station.ID, COUNT(Interface.ID) FROM Interface LEFT JOIN Station ON Station.ID = Interface.StationID WHERE Interface.Type = 'wlan' GROUP BY Station.ID"):
			Stations.append(Station)
		return Stations

	# Returns TopologyID of HostIP
	def GetTopologyID(self, HostIP):
		self.c.execute("SELECT ID FROM Topology WHERE HostIP =?", [(HostIP)])
		return 	self.c.fetchone()[0]

	# Returns the Stations that have a wlan interface for the topology of HostIP
	def GetStationsWithWlan(self, HostIP):
		StationsWithWlan = []
		for StationWithWlan in self.c.execute("SELECT StationID FROM Interface INNER JOIN Topology ON \
		Interface.TopologyID = Topology.ID WHERE Interface.Type=? AND Topology.HostIP=?", ["wlan", (HostIP)]):
			StationsWithWlan.append(StationWithWlan[0])
		return StationsWithWlan

	def GetStationIP(self, StationID):
		self.c.execute("SELECT IPAddress FROM Station WHERE ID = %d" %StationID)
		return self.c.fetchone()[0]

	def GetMaxWlan(self, StationID):
		self.c.execute("SELECT MaxWlanInterfaces FROM Station WHERE ID = %d" %StationID)
		return self.c.fetchone()[0]

	def IsPortal(self, StationID):
		self.c.execute("SELECT IsPortal FROM Station WHERE ID = %d" %StationID)
		return self.c.fetchone()[0]

	def GetDestInterface(self, StationID, DestStaID, TopID):
		self.c.execute("SELECT InterfaceNo FROM Interface WHERE StationID =? AND DestStaID =? AND TopologyID =? AND Type =?", [(DestStaID), (StationID), (TopID), "tun"])
		return self.c.fetchone()[0]

	# Return all Stations used by HostIP
	def GetStationsUsed(self, HostIP):
		StationsUsed = []
		for Station in self.c.execute("SELECT StationID FROM Interface INNER JOIN Topology ON Interface.TopologyID = Topology.ID \
		WHERE Topology.HostIP=? GROUP BY Interface.StationID", [(HostIP)]):
			StationsUsed.append(Station[0])
		return StationsUsed

	# Deletes all interfaces for HostIP
	def DeleteInterfaces(self, HostIP):
		 TopologyID = self.GetTopologyID(HostIP)
		 self.c.execute("DELETE FROM Interface WHERE TopologyID=%s" %TopologyID)
		 self.conn.commit()

	# Deletes HostIP's entry from the topology table
	def DeleteTopology(self, HostIP):
		 self.c.execute("DELETE FROM Topology WHERE HostIP =?", [(HostIP)])
		 self.conn.commit()
