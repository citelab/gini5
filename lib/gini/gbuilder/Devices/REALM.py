from Core.Connection import *
from Core.Interfaceable import *
from Core.globals import environ
from PyQt4.QtCore import QPoint

class REALM(Interfaceable):
    device_type="REALM"


    def __init__(self):

        Interfaceable.__init__(self)

        self.setProperty("ipv4", "")
        self.setProperty("port", "")
        self.setProperty("mac", "")
        self.setProperty("filetype", "cow")
        self.setProperty("filesystem", "root_fs_beta2")
        self.hostIndex = 0
        # self.properties["Hosts"] = ["default","change"]
        # self.hostsproperty={"default":ConnectM("1","2","3","4"),"change":ConnectM("name","ip","mac","port")}
        self.lightPoint = QPoint(-10,3)

        # name = []
        # ip = []
        # port = []
        
        # datarev = "aaa"
        # data = datarev.split('end')  # ??????????
   
        # for i in data[:-1]:
        #     i = i.split(',')
        #     name.append(i[1])
        #     ip.append(i[2])
        #     port.append(i[3])
        # print name
        # for i, item in enumerate(name):
        #     # self.properties["Hosts"] = [item]
        #     self.hostsproperty={item:ConnectM(item,ip[i],"",port[i])}


class ConnectM():
    def __init__ (self,name,ip,mac,port):
	self.name=name
	self.ip=ip
	self.mac=mac
	self.port=port
