import xmlrpclib

class WGINI_Client:
	def __init__(self, ServerIP, ServerPort, ClientIP):
		self.conn = xmlrpclib.ServerProxy("http://" + ServerIP + ":" + str(ServerPort))
		self.ClientIP = ClientIP

	def Check(self):
		return self.conn.Check()

	def Create(self, XMLstring):
		return self.conn.Create(XMLstring, self.ClientIP)

	def Delete(self):
		return self.conn.Delete(self.ClientIP)
