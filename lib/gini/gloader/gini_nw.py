# file: gini_nw.py

import os
import xml.dom.minidom
from gini_components import *

class GINI_NW:
    switches = []
    vm = []
    vrm = []
    vmb = []
    vr = []
    vwr = []
    vofc = []

    def __init__(self, docDOM):
        "Initialize the GINI_NW class"
        self.getSwitches(docDOM.getElementsByTagName("vs"))
        self.getVMs(docDOM.getElementsByTagName('vm'))
        self.getVRMs(docDOM.getElementsByTagName('vrm'))
        self.getVMBs(docDOM.getElementsByTagName("vmb"))
        self.getVRs(docDOM.getElementsByTagName("vr"))
        self.getVWRs(docDOM.getElementsByTagName("vwr"))
        self.getVOFCs(docDOM.getElementsByTagName("vofc"))

    def getSwitches(self, elements):
        "get the switch configuration"
        for switch in elements:
            newSwitch = Switch(switch.getAttribute("name"))
            for para in switch.childNodes:
                if (para.nodeType == para.ELEMENT_NODE):
                    if (para.tagName.lower() == "priority"):
                        newSwitch.priority = self.getTextPart(para)
                    if (para.tagName.lower() == "mac"):
                        newSwitch.mac = self.getTextPart(para)
                    if (para.tagName.lower() == "target"):
                        newSwitch.targets.append(self.getTextPart(para))
                    if (para.tagName.lower() == "port"):
                        newSwitch.port = self.getTextPart(para)
                    if (para.tagName.lower() == "remote"):
                        newSwitch.remote = self.getTextPart(para)
                    if (para.tagName.lower() == "hub"):
                        newSwitch.hub = True
            self.switches.append(newSwitch)
        return True

    def getVMs(self, elements):
        "get virtual machine configurations"
        for vm in elements:
            newVM = VM(vm.getAttribute("name"))
            for para in vm.childNodes:
                if (para.nodeType == para.ELEMENT_NODE):
                    if (para.tagName.lower() == "filesystem"):
                        newVM.fileSystem = FileSystem()
                        newVM.fileSystem.type = para.getAttribute("type")
                        newVM.fileSystem.name = os.environ["GINI_SHARE"] + "/filesystem/" + self.getTextPart(para)
                    if (para.tagName.lower() == "mem"):
                        newVM.mem = self.getTextPart(para)
                    if (para.tagName.lower() == "kernel"):
                        newVM.kernel = self.getTextPart(para)
                    if (para.tagName.lower() == "boot"):
                        newVM.boot = self.getBoot(para)
                    if (para.tagName.lower() == "if"):
                        newIF = self.getVMIF(para, len(newVM.interfaces))
                        newVM.addInterface(newIF)
            self.vm.append(newVM)
        return True

    def getVOFCs(self, elements):
        "get OpenFlow controller configurations"
        for vofc in elements:
            newVOFC = VOFC(vofc.getAttribute("name"))
            for para in vofc.childNodes:
                if (para.nodeType == para.ELEMENT_NODE):
                    if (para.tagName.lower() == "router"):
                        newVOFC.addRouter(self.getTextPart(para))
            self.vofc.append(newVOFC)
        return True

    def getVRMs(self, elements):
        "get remote machine configurations"
        for vrm in elements:
            newVRM = VRM(vrm.getAttribute("name"))
            for para in vrm.childNodes:
                if (para.nodeType == para.ELEMENT_NODE):
                    if (para.tagName.lower() == "filesystem"):
                        newVRM.fileSystem = FileSystem()
                        newVRM.fileSystem.type = para.getAttribute("type")
                        newVRM.fileSystem.name = os.environ["GINI_HOME"] + "/" + self.getTextPart(para)
                    if (para.tagName.lower() == "mem"):
                        newVRM.mem = self.getTextPart(para)
                    if (para.tagName.lower() == "kernel"):
                        newVRM.kernel = self.getTextPart(para)
                    if (para.tagName.lower() == "boot"):
                        newVRM.boot = self.getBoot(para)
                    if (para.tagName.lower() == "if"):
                        newIF = self.getVMIF(para, len(newVRM.interfaces))
                        newVRM.addInterface(newIF)
            self.vrm.append(newVRM)
        return True

    def getVMBs(self, elements):
        "get wireless virtual machine configurations"
        for vmb in elements:
            newVMB = VMB(vmb.getAttribute("name"))
            for para in vmb.childNodes:
                if (para.nodeType == para.ELEMENT_NODE):
                    if (para.tagName.lower() == "filesystem"):
                        newVMB.fileSystem = FileSystem()
                        newVMB.fileSystem.type = para.getAttribute("type")
                        newVMB.fileSystem.name = os.environ["GINI_SHARE"] + "/filesystem/" + self.getTextPart(para)
                    if (para.tagName.lower() == "mem"):
                        newVMB.mem = self.getTextPart(para)
                    if (para.tagName.lower() == "kernel"):
                        newVMB.kernel = self.getTextPart(para)
                    if (para.tagName.lower() == "boot"):
                        newVMB.boot = self.getBoot(para)
                    if (para.tagName.lower() == "if"):
                        newIF = self.getVMIF(para, len(newVMB.interfaces))
                        newVMB.addInterface(newIF)
            self.vmb.append(newVMB)
        return True


    def getVRs(self, elements):
        "Get router specification"
        for router in elements:
            newVR = VR(router.getAttribute("name"))
            numberOfTun=0
            for para in router.childNodes:
                if (para.nodeType == para.ELEMENT_NODE):
                    if (para.tagName.lower() == "cli"):
                        newVR.cli = True
                    if (para.tagName.lower() == "netif"):
                        newIF = self.getVRIF(para, len(newVR.netIF)+1)
                        newVR.addNetIF(newIF)
                    if (para.tagName.lower() == "controller"):
                        newVR.openFlowController = self.getTextPart(para)
                    if (para.tagName.lower() == "loctun"):
                        newIF = self.getTUNIF(para, numberOfTun)
                        numberOfTun+=1
                        newVR.addTunIF(newIF)
            self.vr.append(newVR)
        return True


    def getVWRs(self, elements):
        "Get wireless router specification"
        for router in elements:
            newVWR = VWR(router.getAttribute("name"))
            for para in router.childNodes:
                if (para.nodeType == para.ELEMENT_NODE):
                    if (para.tagName.lower() == "cli"):
                        newVWR.cli = True
                    if (para.tagName.lower() == "netif"):
                        newIF = self.getVRIF(para, len(newVWR.netIF))
                        newVWR.addNetIF(newIF)
                    if (para.tagName.lower() == "netif_wireless"):
                        newWIF = self.getVWRIF(para, len(newVWR.netIFWireless))
                        newVWR.addWirelessIF(newWIF)
            self.vwr.append(newVWR)
        return True


    def getTextPart(self,elem):
        "Extract the text within the element"
        for textPart in elem.childNodes:
            if (textPart.nodeType == textPart.TEXT_NODE):
                remoteName = textPart.nodeValue.strip()
                if (remoteName):
                    return remoteName
        return ""


    def getBoot(self, elem):
        "get boot elememnt in VM specification"
        for part in elem.childNodes:
            if (part.nodeType == part.ELEMENT_NODE and
                part.tagName.lower() == "con0"):
                return self.getTextPart(part)
        return ""


    def getVMIF(self, elem, count):
        "get VM network interface specification"
        ifName =  "eth%d" % count
        myIF = VMInterface(ifName)
        for para in elem.childNodes:
            if (para.nodeType == para.ELEMENT_NODE):
                if (para.tagName.lower() == "target"):
                    myIF.target = self.getTextPart(para)
                if (para.tagName.lower() == "network"):
                    myIF.network = self.getTextPart(para)                
                if (para.tagName.lower() == "mac"):
                    myIF.mac = self.getTextPart(para)
                if (para.tagName.lower() == "ip"):
                    myIF.ip = self.getTextPart(para)
                if (para.tagName.lower() == "route"):
                    newRoute = self.getVMRoute(para)
                    myIF.addRoute(newRoute)
        return myIF


    def getVMRoute(self, elem):
        "Extract VM route entries"
        newRoute = VMRoute()
        newRoute.type = elem.getAttribute("type")
        newRoute.netmask = elem.getAttribute("netmask")
        newRoute.gw = elem.getAttribute("gw")
        newRoute.dest = self.getTextPart(elem)
        return newRoute


    def getVRIF(self, elem, index):
        "get virtual router network interface"
        ifName =  "eth%d" % index
        myIF = VRInterface(ifName)
        for para in elem.childNodes:
            if (para.nodeType == para.ELEMENT_NODE):
                if (para.tagName.lower() == "target"):
                    myIF.target = self.getTextPart(para)
                if (para.tagName.lower() == "nic"):
                    myIF.nic = self.getTextPart(para)
                if (para.tagName.lower() == "ip"):
                    myIF.ip = self.getTextPart(para)
                if (para.tagName.lower() == "network"):
                    myIF.network = self.getTextPart(para)
                if (para.tagName.lower() == "gw"):
                    myIF.gw = self.getTextPart(para)
                if (para.tagName.lower() == "mtu"):
                    myIF.mtu = self.getTextPart(para)
                if (para.tagName.lower() == "rtentry"):
                    newRoute = self.getVRRoute(para)
                    myIF.addRoute(newRoute)
        return myIF


    def getTUNIF(self, elem, index):
        "get virtual router network interface"
        ifName =  "tun%d" % index
        myIF = VRInterface(ifName)
        for para in elem.childNodes:
            if (para.nodeType == para.ELEMENT_NODE):
                if (para.tagName.lower() == "target"):
                    myIF.target = self.getTextPart(para)
                if (para.tagName.lower() == "nic"):
                    myIF.nic = self.getTextPart(para)
                if (para.tagName.lower() == "ip"):
                    myIF.ip = self.getTextPart(para)
                if (para.tagName.lower() == "network"):
                    myIF.network = self.getTextPart(para)
                if (para.tagName.lower() == "gw"):
                    myIF.gw = self.getTextPart(para)
                if (para.tagName.lower() == "mtu"):
                    myIF.mtu = self.getTextPart(para)
                if (para.tagName.lower() == "rtentry"):
                    newRoute = self.getVRRoute(para)
                    myIF.addRoute(newRoute)
        return myIF


    def getVWRIF(self, elem, index):
        "get virtual wireless router network interface"
        ifName =  "eth%d" % index
        myWIF = VWRInterface(ifName)
        for para in elem.childNodes:
            if (para.nodeType == para.ELEMENT_NODE):
                if (para.tagName.lower() == "nic"):
                    myWIF.nic = self.getTextPart(para)
                if (para.tagName.lower() == "ip"):
                    myWIF.ip = self.getTextPart(para)
                if (para.tagName.lower() == "network"):
                    myWIF.network = self.getTextPart(para)
                if (para.tagName.lower() == "rtentry"):
                    newRoute = self.getVRRoute(para)
                    myWIF.addRoute(newRoute)
                if (para.tagName.lower() == "wireless_card"):
                    newWcard = self.getWcard(para)
                    myWIF.wireless_card = newWcard
                if (para.tagName.lower() == "energy"):
                    newEnergy = self.getEnergy(para)
                    myWIF.energy = newEnergy
                if (para.tagName.lower() == "mac_layer"):
                    newMlayer = self.getMlayer(para)
                    myWIF.mac_layer = newMlayer
                if (para.tagName.lower() == "antenna"):
                    newAntenna = self.getAntenna(para)
                    myWIF.antenna = newAntenna
                if (para.tagName.lower() == "mobility"):
                    newMobility = self.getMobility(para)
                    myWIF.mobility = newMobility
        return myWIF

    def getWcard(self, elem):
        newWcard = WirelessCard()
        for para in elem.childNodes:
            if (para.nodeType == para.ELEMENT_NODE):
                if (para.tagName.lower() == "w_type"):
                    newWcard.wType = self.getTextPart(para)
                if (para.tagName.lower() == "freq"):
                    newWcard.freq = self.getTextPart(para)
                if (para.tagName.lower() == "bandwidth"):
                    newWcard.bandwidth = self.getTextPart(para)
                if (para.tagName.lower() == "pt"):
                    newWcard.pt = self.getTextPart(para)
                if (para.tagName.lower() == "pt_c"):
                    newWcard.ptC = self.getTextPart(para)
                if (para.tagName.lower() == "pr_c"):
                    newWcard.prC = self.getTextPart(para)
                if (para.tagName.lower() == "p_idle"):
                    newWcard.pIdle = self.getTextPart(para)
                if (para.tagName.lower() == "p_sleep"):
                    newWcard.pSleep = self.getTextPart(para)
                if (para.tagName.lower() == "p_off"):
                    newWcard.pOff = self.getTextPart(para)
                if (para.tagName.lower() == "rx"):
                    newWcard.rx = self.getTextPart(para)
                if (para.tagName.lower() == "cs"):
                    newWcard.cs = self.getTextPart(para)
                if (para.tagName.lower() == "cp"):
                    newWcard.cp = self.getTextPart(para)
                if (para.tagName.lower() == "module"):
                    newWcard.module = self.getTextPart(para)
        return newWcard

    def getEnergy(self, elem):
        newEnergy = Energy()
        for para in elem.childNodes:
            if (para.nodeType == para.ELEMENT_NODE):
                if (para.tagName.lower() == "power"):
                    newEnergy.power = self.getTextPart(para)
                if (para.tagName.lower() == "psm"):
                    newEnergy.psm = self.getTextPart(para)
                if (para.tagName.lower() == "energy_amount"):
                    newEnergy.energyAmount = self.getTextPart(para)
        return newEnergy

    def getMlayer(self, elem):
        newMlayer = MacLayer()
        for para in elem.childNodes:
            if (para.nodeType == para.ELEMENT_NODE):
                if (para.tagName.lower() == "mac_type"):
                    newMlayer.macType = self.getTextPart(para)
                if (para.tagName.lower() == "trans"):
                    newMlayer.trans = self.getTextPart(para)
        return newMlayer

    def getAntenna(self, elem):
        newAntenna = Antenna()
        for para in elem.childNodes:
            if (para.nodeType == para.ELEMENT_NODE):
                if (para.tagName.lower() == "a_type"):
                    newAntenna.aType = self.getTextPart(para)
                if (para.tagName.lower() == "ant_h"):
                    newAntenna.ant_h = self.getTextPart(para)
                if (para.tagName.lower() == "ant_g"):
                    newAntenna.ant_g = self.getTextPart(para)
                if (para.tagName.lower() == "ant_l"):
                    newAntenna.ant_l = self.getTextPart(para)
                if (para.tagName.lower() == "jam"):
                    newAntenna.jam = self.getTextPart(para)
        return newAntenna

    def getMobility(self, elem):
        newMobility = Mobility()
        for para in elem.childNodes:
            if (para.nodeType == para.ELEMENT_NODE):
                if (para.tagName.lower() == "m_type"):
                    newMobility.mType = self.getTextPart(para)
                if (para.tagName.lower() == "ran_max"):
                    newMobility.ranMax = self.getTextPart(para)
                if (para.tagName.lower() == "ran_min"):
                    newMobility.ranMin = self.getTextPart(para)
        return newMobility

    def getVRRoute(self, elem):
        "Extract VR route entries"
        newRoute = VRRoute()
        newRoute.netmask = elem.getAttribute("netmask")
        newRoute.nexthop = elem.getAttribute("nexthop")
        newRoute.dest = self.getTextPart(elem)
        return newRoute
