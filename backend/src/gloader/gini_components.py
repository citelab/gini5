# file: gini_components.py

# this file contains the class definitions of
# the GINI components and sub-components
# the printMe() methods can be used for debug purposes
# the attributes for each class matches the DTD specification

class Switch:
    name = ""
    targets = None
    port = ""
    remote = "localhost"
    hub = False
    isOVS = False

    def __init__(self, sName):
        "Initialize the Switch class"
        self.name = sName
        self.targets = []
        self.priority = ""
        self.mac = ""

    def addTarget(self, newTarget):
        self.targets.append(newTarget)


    def printMe(self):
        print "[Name: " + self.name + "]",
        print "[Port: " + self.port + "]",
        print "[Remote: " + self.remote + "]",
        print "[Hub: " + str(self.hub) + "]"
        print "[IsOVS " + str(self.isOVS) + "]"


class VM:
    name = ""
    fileSystem = None
    mem = ""
    kernel = ""
    boot = ""
    interfaces = None

    def __init__(self, vmName):
        "Initialize the VM class"
        self.name = vmName
        self.interfaces = []

    def addInterface(self, newIF):
        self.interfaces.append(newIF)

    def printMe(self):
        print "[Name: " + self.name + "]",
        if (self.fileSystem):
            print "[fileSystem: ",
            self.fileSystem.printMe()
            print "]",
        if (self.mem):
            print "[Mem: " + self.mem + "]",
        if (self.kernel):
            print "[Kernel: " + self.kernel + "]",
        print ""
        print "[Interfaces: %d" % len(self.interfaces),
        for item in self.interfaces:
            item.printMe()
        print "end if]"

class VRM(VM):
    def __init__(self, vmName):
        "Initialize the VRM class"
        VM.__init__(self, vmName)

class VMB(VM):
    location = None
    map = None

    def __init__(self, vmName):
        "Initialize the VMB class"
        VM.__init__(self, vmName)

class FileSystem:
    name = ""
    type = ""

    def __init__(self):
        "Initialize the FileSystem class"

    def printMe(self):
        print "[Name: " + self.name + " ]",
        print "[Type: " + self.type + " ]",

class VMInterface:
    name = ""
    target = ""
    network = ""
    mac = ""
    ip = ""
    routes = None

    def __init__(self, ifName):
        "Initialize the VMInterface class"
        self.name = ifName
        self.routes = []

    def addRoute(self, newRoute):
        self.routes.append(newRoute)

    def printMe(self):
        print "[Name: " + self.name + "]",
        print "[Target: " + self.target + "]",
        print "[MAC: " + self.mac + "]",
        print "[IP: " + self.ip + "]"
        print "[Routes: "
        for item in self.routes:
            item.printMe()
        print "end routes]"
        return True

class VMRoute:
    dest = ""
    type = ""
    netmask = ""
    gw = ""

    def __init__(self):
        "Initialize the VMRoute class"

    def printMe(self):
        print "[Dest: " + self.dest + "]",
        print "[Type: " + self.type + "]",
        print "[NetMask: " + self.netmask + "]",
        print "[GW: " + self.gw + "]"

class Location:
    x = ""
    y = ""

    def __init__(self):
        "Initialize the Location class"


class Map:
    map_x = ""
    map_y = ""
    map_z = ""

    def __init__(self):
        "Initialize the MAP class"

class MacLayer:
    macType = ""
    trans = ""

    def __init__(self):
        "Initialize the MacLayer class"

    def printMe(self):
        print "[macType: " + self.macType + "]",
        print "[trans: " + self.trans + "]",

class Antenna:
    aType = ""
    ant_h = ""
    ant_g = ""
    ant_l = ""
    jam = ""

    def __init__(self):
        "Initialize the Antenna class"

    def printMe(self):
        print "[aType: " + self.aType + "]",
        print "[ant_h: " + self.ant_h + "]",
        print "[ant_g: " + self.ant_g + "]",
        print "[ant_l: " + self.ant_l + "]",
        print "[jam: " + self.jam + "]"

class Mobility:
    mType = ""
    ranMax = ""
    ranMin = ""

    def __init__(self):
        "Initialize the Mobility class"

    def printMe(self):
        print "[mType: " + self.mType + "]",
        print "[ranMax: " + self.ranMax + "]",
        print "[ranMin: " + self.ranMin + "]"

class WirelessCard:
    wType = ""
    freq = ""
    bandwidth = ""
    pt = ""
    ptC = ""
    prC = ""
    pIdle = ""
    pSleep = ""
    pOff = ""
    rx = ""
    cs = ""
    cp = ""
    module = ""

    def __init__(self):
        "Initialize the WirelessCard class"

    def printMe(self):
        print "[wType: " + self.wType + "]",
        print "[freq: " + self.freq + "]",
        print "[bandwidth: " + self.bandwidth + "]",
        print "[pt: " + self.pt + "]",
        print "[ptC: " + self.ptC + "]",
        print "[prC: " + self.prC + "]"
        print "[pIdle: " + self.pIdle + "]",
        print "[pSleep: " + self.pSleep + "]",
        print "[pOff: " + self.pOff + "]",
        print "[rx: " + self.rx + "]",
        print "[cs: " + self.cs + "]",
        print "[cp: " + self.cp + "]",
        print "[module: " + self.module + "]"

class Energy:
    power = ""
    psm = ""
    energyAmount = ""

    def __init__(self):
        "Initialize the Energy class"

    def printMe(self):
        print "[power: " + self.power + "]",
        print "[psm: " + self.psm + "]",
        print "[energyAmount: " + self.energyAmount + "]",

class VR:
    name = ""
    netIF = None
    tunIF = None
    cli = False
    openFlowController = None

    def __init__(self, vrName):
        "Initialize the VR class"
        self.name = vrName
        self.netIF = []
        self.tunIF= []

    def addNetIF(self, newIF):
        self.netIF.append(newIF)
    def addTunIF(self, tunIF):
        self.tunIF.append(tunIF)

    def printMe(self):
        print "[Name: " + self.name + "]",
        print "[CLI: " + str(self.cli) + "]",
        if self.openFlowController:
            print "[OpenFlow Controller: " + self.openFlowController + "]",
        print "[NetIF: "
        for item in self.netIF:
            item.printMe()
        print "]"


class VOFC:
    def __init__(self, vofcName):
        "Initialize the VOFC class"
        self.name = vofcName
        self.routers = []

    def addRouter(self, newRouter):
        self.routers.append(newRouter)

    def printMe(self):
        print "[Name: " + self.name + "]",
        print ""
        print "[Routers: "
        for item in self.routers:
            print "[Name: " + item + "]"
        print "]"

class VWR(VR):
    netIFWireless = []

    def __init__(self, vwrName):
        "Initialize the VWR class"
        self.name = vwrName
        self.netIFWireless = []
        self.netIF = []

    def addWirelessIF(self, newIF):
        self.netIFWireless.append(newIF)

class VRInterface:
    name = ""
    target = ""
    nic = ""
    ip = ""
    network = ""
    gw = ""
    mtu = ""
    routes = None

    def __init__(self, ifName):
        "Initialize the VRInterface class"
        self.name = ifName
        self.routes = []

    def addRoute(self, newRoute):
        self.routes.append(newRoute)

    def printMe(self):
        print "[Name: " + self.name + "]",
        print "[target: " + self.target + "]",
        print "[nic: " + self.nic + "]",
        print "[IP: " + self.ip + "]",
        if (self.mtu):
            print "[MTU: " + self.mtu + "]",
        print ""
        print "[Routes: "
        for item in self.routes:
            item.printMe()
        print "]"

class VWRInterface(VRInterface):

    wirelessChannel = None
    mac_layer = None
    antenna = None
    mobility = None
    wireless_card = None
    energy = None

    def __init__(self, ifName):
        "Initialize the VWRInterface class"
        VRInterface.__init__(self, ifName)

    def printMe(self):
        print "[name: " + self.name + "]",
        print "[wirelessChannel: ",
        print self.wirelessChannel,
        print "]",
        print "[routes: ",
        for route in self.routes:
            route.printMe()
        print "]",
        print "[mac_layer: ",
        self.mac_layer.printMe(),
        print "]",
        print "[antenna: ",
        self.antenna.printMe(),
        print "]",
        print "[mobility: ",
        self.mobility.printMe(),
        print "]",
        print "[wireless_card: ",
        self.wireless_card.printMe(),
        print "]",
        print "[energy: ",
        self.energy.printMe(),
        print "]"

class VRRoute:
    dest = ""
    netmask = ""
    nexthop = ""

    def __init__(self):
        "Initialize the VRRoute class"

    def printMe(self):
        print "[Dest: " + self.dest + "]",
        print "[netmask: " + self.netmask + "]",
        if (self.nexthop):
            print "[nexthop: " + self.nexthop + "]",
        print ""

class WirelessChannel:
    pathloss = ""
    deviation = ""
    noise = ""
    distance = ""
    channelType = ""
    propagation = ""

    def __init__(self):
        "Initialize the WirelessChannel class"

    def printMe(self):
        print "[pathloss: " + self.pathloss + "]",
        print "[deviation: " + self.deviation + "]",
        print "[noise: " + self.noise + "]",
        print "[distance: " + self.distance + "]",
        print "[channelType: " + self.channelType + "]",
        print "[propagation: " + self.propagation + "]"
