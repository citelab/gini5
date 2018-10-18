"""The compiler that turns topologies into xml network definitions"""

from Core.Item import nodeTypes
from Core.Device import Device
from Core.globals import options, environ, mainWidgets
from PyQt4 import QtCore
import os, re

class Compiler:
    def __init__(self, device_list, filename):
        """
        Create a compile instance with a list of devices and the filename.
        """
        self.warnings = 0
        self.errors = 0

        self.device_list = device_list
        self.filename = filename.replace(".gsav", ".xml")
        self.output = open(self.filename, "w")
        self.log = mainWidgets["log"]

        self.compile_list = {}
        for nodeType in nodeTypes:
            self.compile_list[nodeType] = []
        for device in device_list:
            if isinstance(device, Device):
                self.compile_list[device.device_type].append(device)

    def compile(self):
        """
        Compile the topology into xml.
        """
        if options["autogen"]:
            self.log.append("Auto-generate IP/MAC Addresses is ON.")
        else:
            self.log.append("Auto-generate IP/MAC Addresses is OFF.")
        if options["autorouting"]:
            self.log.append("Auto-routing is ON.")
        else:
            self.log.append("Auto-routing is OFF.")

        self.output.write("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n")
        self.output.write("<!DOCTYPE gloader SYSTEM \"" + os.environ["GINI_SHARE"] + "/gloader/gloader.dtd"+"\">\n")
        self.output.write("<gloader>\n\n")

        if options["autogen"]:
            self.autogen_subnet()
            self.autogen_switch()

        self.compile_subnet()
        self.compile_switch()
        self.switch_pass_mask()

        if options["autogen"]:
            self.autogen_wireless_access_point()
        self.compile_wireless_access_point()

        if options["autogen"]:
            self.autogen_router()
            self.autogen_yRouter()
            self.autogen_UML()
            self.autogen_REALM()
            self.autogen_mobile()

        self.routing_table_clear()
        if options["autorouting"]:
            self.routing_table_router()
            #self.routing_table_wireless_access_point()
            self.routing_table_yRouter()
            self.routing_table_entry()
            self.routing_table_uml()
            #self.routing_table_mobile()

        self.compile_router()
        self.compile_yRouter()
        self.compile_UML()
        self.compile_REALM()
        self.compile_mobile()
        self.compile_OpenFlow_Controller()

        self.output.write("</gloader>\n")
        self.output.close()

        self.log.append("Compile finished with " + str(self.errors) + \
                        " error(s) and " + str(self.warnings) + " warning(s).\n")

        if self.errors:
            os.remove(self.filename)
            return ""

        return self.filename

    def autogen_subnet(self):
        """
        Auto-generate properties for Subnets.
        """
        for subnet in self.compile_list["Subnet"]:
            subnet.setProperty("mask", "255.255.255.0")
            if subnet.getProperty("subnet"):
                continue
            subnet.setProperty("subnet", "192.168.%d.0" % subnet.getID())

    def writeProperty(self, prop, value):
        """
        Write a property and value in xml format to file.
        """
        self.output.write("\t\t<" + prop + ">")
        self.output.write(value)
        self.output.write("</" + prop + ">\n")

    def generateREALMError(self):
        self.errors += 1
        self.log.append("Error: there is more than one REALM")

    def generateError(self, device, prop, errorType, interface = None):
        """
        Generate a compile error.
        """
        self.errors += 1
        message = "Error: " + device.getName() + "'s " + prop
        if not errorType == "missing":
            message += " value"
        if interface:
            message += " of interface " + str(device.getInterfaces().index(interface) + 1)
        message += " is " + errorType + "."
        self.log.append(message)

    def generateConnectionError(self, device, numCons):
        """
        Generate a compile error.
        """
        self.errors += 1
        message = ' '.join(("Error:", device.getName(), "has less than", str(numCons), "connection(s)."))
        self.log.append(message)

    def generateConnectionWarning(self, device, numCons):
        """
        Generate a compile warning.
        """
        self.warnings += 1
        message = ' '.join(("Warning:", device.getName(), "has less than", str(numCons), "connection(s)."))
        self.log.append(message)

    def compile_subnet(self):
        """
        Compile all the Subnets.
        """
        for subnet in self.compile_list["Subnet"]:

            edges = subnet.edges()
            if len(edges) < 1:
                self.generateConnectionWarning(subnet, 1)

            for prop in ["subnet", "mask"]:
                value = subnet.getProperty(prop)
                if not value:
                    self.generateError(subnet, prop, "empty")
                elif not self.validate(prop, value):
                    self.generateError(subnet, prop, "invalid")

            self.pass_mask(subnet)

    def autogen_router(self):
        """
        Auto-generate properties for Routers.
        """
        for router in self.compile_list["Router"]:
            i = 0
            for con in router.edges():
                i += 1
                node = con.getOtherDevice(router)
                if node.device_type == "OpenFlow_Controller":
                    continue
                node = node.getTarget(router)

                if options["autogen"]:
                    subnet = str(router.getInterfaceProperty("subnet", node)).rsplit(".", 1)[0]
                    router.setInterfaceProperty("ipv4", "%s.%d" % (subnet, 127 + router.getID()), node)
                    router.setInterfaceProperty("mac", "fe:fd:03:%02x:00:%02x" % (router.getID(), i), node)

    def compile_router(self):
        """
        Compile all the Routers.
        """
        for router in self.compile_list["Router"]:
            self.output.write("<vr name=\"" + router.getName() + "\">\n")

            controllerFound = False
            for con in router.edges():
                node = con.getOtherDevice(router)
                if node.device_type == "OpenFlow_Controller":
                    if controllerFound:
                        self.generateGenericError(router, " is connected to multiple OpenFlow controllers")
                        return
                    controllerFound = True
                    self.output.write("\t<controller>" + node.getName() + "</controller>\n")

            edges = router.edges()
            if len(edges) < 2:
                self.generateConnectionWarning(router, 2)

            for con in edges:
                node = con.getOtherDevice(router)
                if node.device_type == "OpenFlow_Controller":
                    continue
                node = node.getTarget(router)

                self.output.write("\t<netif>\n")

                interface = router.getInterface(node)
                mapping = {"subnet":"network", "mac":"nic", "ipv4":"ip"}

                self.writeInterface(router, interface, mapping)

                self.output.write("\t</netif>\n")

            self.output.write("</vr>\n\n")

    def autogen_wireless_access_point(self):
        """
        Auto-generate properties for Wireless_access_points.
        """
        for router in self.compile_list["Wireless_access_point"]:
            if options["autogen"]:
                subnet = router.getInterfaceProperty("subnet")
                if not subnet:
                    subnet = "192.168.%d.0" % (256 - router.getID())
                    router.setInterfaceProperty("subnet", subnet)
                subnet = str(subnet).rsplit(".", 1)[0]
                router.setInterfaceProperty("mask", "255.255.255.0")
                router.setInterfaceProperty("ipv4", "%s.%d" % (subnet, router.getID()))
                router.setInterfaceProperty("mac", "fe:fd:01:%02x:00:00" % router.getID())

    def compile_wireless_access_point(self):
        """
        Compile all the Wireless_access_points.
        """
        for router in self.compile_list["Wireless_access_point"]:
            self.output.write("<vwr name=\"" + router.getName() + "\">\n")

            edges = router.edges()
            if len(edges) < 1:
                self.errors += 1
                message = "Error: " + router.getName() + " needs at least one connected Mobile to start."
                self.log.append(message)

            self.output.write("\t<netif_wireless>\n")

            interface = router.getInterface()
            mapping = {"subnet":"network", "mac":"nic", "ipv4":"ip"}

            self.writeInterface(router, interface, mapping)

            #properties=router.getProperties()
            p_types={}
            p_types["wireless_card"]=("w_type", "freq", "bandwidth", "Pt", "Pt_c", "Pr_c", "P_idle", "P_sleep", "P_off", "RX", "CS", "CP", "module")
            p_types["antenna"]=("a_type", "ant_h", "ant_g", "ant_l", "JAM")
            p_types["energy"]=("power", "PSM", "energy_amount")
            p_types["mobility"]=("m_type", "ran_max", "ran_min")
            p_types["mac_layer"]=("mac_type", "trans")

            for item in p_types:
                self.output.write("\t<"+item+">\n")
                for p in p_types[item]:
                    self.output.write("\t\t<"+p+">"+router.getProperty(p)+"</"+p+">\n")
                self.output.write("\t</"+item+">\n")

            self.output.write("\t</netif_wireless>\n")

            self.output.write("</vwr>\n\n")

            subnet = router.getInterfaceProperty("subnet")
            mask = router.getInterfaceProperty("mask")
            for edge in edges:
                target = edge.getOtherDevice(router)
                target.setInterfaceProperty("subnet", subnet, router)
                target.setInterfaceProperty("mask", mask, router)

    def autogen_yRouter(self):
        """
        Auto-generate properties for yRouter.
        """
        for yRouter in self.compile_list["yRouter"]:
            i = 0
            for con in yRouter.edges():
                i += 1
                node = con.getOtherDevice(yRouter)
                node = node.getTarget(yRouter)

                if options["autogen"]:
                    subnet = str(yRouter.getInterfaceProperty("subnet", node)).rsplit(".", 1)[0]
                    yRouter.setInterfaceProperty("ipv4", "%s.%d" %(subnet, yRouter.getID()), node)
                    yRouter.setInterfaceProperty("mac", "fe:fd:05:%02x:00:%02x" %(yRouter.getID(), i), node)

    def compile_yRouter(self):
        """
        Compile all the yRouters.
        """
        if not self.compile_list["yRouter"]:
            return

        if not mainWidgets["wgini_client"]:
            self.log.append("Error: Please run WGINI client first!")
            return


        for yRouter in self.compile_list["yRouter"]:
            self.output.write("<vr name=\"" + yRouter.getName() + "\">\n")

            controllerFound = False
            for con in yRouter.edges():
                node = con.getOtherDevice(yRouter)
                if node.device_type == "OpenFlow_Controller":
                    if controllerFound:
                        self.generateGenericError(router, " is connected to multiple OpenFlow controllers")
                        return
                    controllerFound = True
                    self.output.write("\t<controller>" + node.getName() + "</controller>\n")

            edges = yRouter.edges()
            if len(edges) < 2:
                self.generateConnectionWarning(yRouter, 2)

            for tun in edges:
                subnet = tun.getOtherDevice(yRouter)
                node = subnet.getTarget(yRouter)
                if subnet.device_type == "OpenFlow_Controller":
                    continue
                self.output.write("\t<netif>\n")

                interface = yRouter.getInterface(node)
                mapping = {"subnet":"network", "mac":"nic", "ipv4":"ip"}

                self.writeInterface(yRouter, interface, mapping)

                self.output.write("\t</netif>\n")

            self.output.write("</vr>\n\n")


        tsfString = "<VN>\n"
        for yRouter in self.compile_list["yRouter"]:
            yid = yRouter.getID()
            tsfString += "\t<Station>\n"
            tsfString += "\t\t<ID>%d</ID>\n" %yid

            itf = 0
            for tun in yRouter.edges():
                subnet = tun.getOtherDevice(yRouter)
                node = subnet.getTarget(yRouter)
                mask = str(yRouter.getInterfaceProperty("mask", node))
                mac = str(yRouter.getInterfaceProperty("mac", node))
                ip = str(yRouter.getInterfaceProperty("ipv4", node))

                if node.device_type == "Router":
                    strOpen = "\t\t<BBInterface>\n"
                    dest = "\t\t\t<DestIface>%d</DestIface>\n" %node.getID()
                    strClose = "\t\t</BBInterface>\n"
                else:
                    strOpen = "\t\t<TunInterface>\n"
                    dest = "\t\t\t<DestStaID>%d</DestStaID>\n" %node.getID()
                    strClose = "\t\t</TunInterface>\n"

                tsfString += strOpen
                tsfString += "\t\t\t<InterfaceNo>%d</InterfaceNo>\n" %itf
                tsfString += dest
                tsfString += "\t\t\t<IPAddress>%s</IPAddress>\n" %ip
                tsfString += "\t\t\t<HWAddress>%s</HWAddress>\n" %mac

                interface = yRouter.getInterface(node)
                routes = interface[QtCore.QString("routing")]
                for route in routes:
                    tsfString += "\t\t\t<REntry>\n"
                    tsfString += "\t\t\t\t<Net>%s</Net>\n" %str(yRouter.getInterfaceProperty("subnet", node))
                    tsfString += "\t\t\t\t<NetMask>%s</NetMask>\n" %str(route[QtCore.QString("netmask")])
                    tsfString += "\t\t\t\t<NextHop>%s</NextHop>\n" %str(route[QtCore.QString("gw")])
                    tsfString += "\t\t\t</REntry>\n"

                tsfString += strClose
                itf += 1

            if yRouter.getProperty("WLAN") == "True":
                tsfString += "\t\t<WlanInterface>\n"
                tsfString += "\t\t\t<InterfaceNo>%d</InterfaceNo>\n" %itf
                tsfString += "\t\t\t<IPAddress>192.167.%d.1</IPAddress>\n" %yid
                #tsfString += "\t\t\t<SSID>%s</SSID>\n" %SSID
                tsfString += "\t\t\t<REntry>\n"
                tsfString += "\t\t\t\t<Net>192.167.%d.0</Net>\n" %yid
                tsfString += "\t\t\t\t<NetMask>255.255.255.0</NetMask>\n"
                tsfString += "\t\t\t\t<NextHop>None</NextHop>\n"
                tsfString += "\t\t\t</REntry>\n"
                tsfString += "\t\t</WlanInterface>\n"
            tsfString += "\t</Station>\n"
        tsfString += "</VN>"

        #print tsfString
        status = mainWidgets["wgini_client"].Create(tsfString)
        self.log.append(status)

    def writeInterface(self, device, interface, mapping):
        """
        Write an interface to file according to mapping.
        """
        if interface.has_key(QtCore.QString("target")):
            self.writeProperty("target", interface[QtCore.QString("target")].getName())

        for prop, eq in mapping.iteritems():
            try:
                value = interface[QtCore.QString(prop)]
            except:
                self.generateError(device, prop, "missing", interface)
         	return

            if not value:
                self.generateError(device, prop, "empty", interface)
            elif not self.validate(prop, value, interface):
                self.generateError(device, prop, "invalid", interface)
            else:
                self.writeProperty(eq, value)

        table = self.formatRoutes(interface[QtCore.QString("routing")], device.device_type)
        self.output.write(table)

    def autogen_switch(self):
        """
        Auto-generate properties for switches.
        """
        for switch in self.compile_list["Switch"]:
            switch.setProperty("mac", "fe:fd:04:00:00:%02x" % switch.getID())

    def compile_switch(self):
        """
        Compile all the Switches.
        """
        for switch in self.compile_list["Switch"]:
            self.output.write("<vs name=\"" + switch.getName() + "\">\n")

            self.output.write("\t<priority>" + switch.getProperty("Priority") + "</priority>\n")
            self.output.write("\t<mac>" + switch.getProperty("mac") + "</mac>\n")

            subnet = None
            if len(switch.edges()) < 2:
                self.generateConnectionWarning(switch, 2)

            first = True
            Q = [switch]
            switch_seen = set([switch])
            while Q:
                t = Q.pop(0)
                for edge in t.edges():
                    node = edge.getOtherDevice(t)
                    if node.device_type == "Subnet":
                        if (subnet is None) or (subnet == node):
                            subnet = node
                        else:
                            self.generateError(t, "subnet", "inconsistent due to multiple values (only connect to a single subnet)")
                            return
                    if node.device_type == "Switch":
                        # should look around for a subnet
                        if node not in switch_seen:
                            switch_seen.add(node)
                            Q.append(node)
                            if first:
                                self.output.write("\t<target>" + node.getName() + "</target>\n")
                first = False

            if subnet is None:
                self.generateError(switch, "subnet", "missing")
                return

            switch.setProperty("subnet", subnet.getProperty("subnet"))
            if switch.getProperty("Hub mode") == "True":
                self.output.write("\t<hub/>\n")
            self.output.write("</vs>\n\n")
            # self.pass_mask(switch)

    def switch_pass_mask(self):
        for switch in self.compile_list["Switch"]:
          for edge in switch.edges():
              node = edge.getOtherDevice(switch)
              if node.device_type == "Subnet":
                  has_subnet = True

          if has_subnet:
              target = switch.getTarget(None)
              gateway = target.getInterface(switch) if target is not None else None
              Q = [switch]
              switch_seen = set([switch])
              while Q:
                  t = Q.pop(0)
                  t.gateway = gateway
                  self.pass_mask(t)
                  for edge in t.edges():
                      node = edge.getOtherDevice(t)
                      if node.device_type == "Switch":
                          # should look around for a subnet
                          if node not in switch_seen:
                              switch_seen.add(node)
                              Q.append(node)



    def autogen_UML(self):
        """
        Auto-generate properties for UMLs.
        """
        for uml in self.compile_list["UML"]:
            for interface in uml.getInterfaces():
                if options["autogen"]:
                    try:
                        subnet = str(uml.getInterfaceProperty("subnet")).rsplit(".", 1)[0]
                    except:
                        continue
                    uml.setInterfaceProperty("ipv4", "%s.%d" % (subnet, uml.getID()+1))
                    uml.setInterfaceProperty("mac", "fe:fd:02:00:00:%02x" % uml.getID())

    def compile_UML(self):
        """
        Compile all the UMLs.
        """
        for uml in self.compile_list["UML"]:
            self.output.write("<vm name=\"" + uml.getName() + "\">\n")
            #self.output.write("\t<filesystem type=\"" + uml.getProperty("filetype") + "\">"
            #                  + uml.getProperty("filesystem") + "</filesystem>\n")

            interfaces = uml.getInterfaces()
            if len(interfaces) < 1:
                self.generateConnectionWarning(uml, 1)

            for interface in interfaces:

                self.output.write("\t<if>\n")

                mapping = {"subnet":"network", "mac":"mac", "ipv4":"ip"}
                self.writeInterface(uml, interface, mapping)

                self.output.write("\t</if>\n")

            self.output.write("</vm>\n\n")

#********************************* REALM
    def autogen_REALM(self):
        """
        Auto-generate properties for REALMs.
        """
        for realm in self.compile_list["REALM"]:
            for interface in realm.getInterfaces():
                if options["autogen"]:
                    try:
                        subnet = str(realm.getInterfaceProperty("subnet")).rsplit(".", 1)[0]
                    except:
                        continue
                    realm.setInterfaceProperty("ipv4", "%s.%d" % (subnet, realm.getID()+1+len(self.compile_list["UML"])))
                    realm.setInterfaceProperty("mac", "fe:fd:02:00:01:%02x" % realm.getID())

    def compile_REALM(self):
        """
        Compile all the REALMs.
        """
        if len(self.compile_list["REALM"]) > 1:
            self.generateREALMError()
        for realm in self.compile_list["REALM"]:
            self.output.write("<vrm name=\"" + realm.getName() + "\">\n")
            self.output.write("\t<filesystem type=\"" + realm.getProperty("filetype") + "\">"
                          + realm.getProperty("filesystem") + "</filesystem>\n")

            interfaces = realm.getInterfaces()
            if len(interfaces) < 1:
                self.generateConnectionWarning(realm, 1)

            for interface in interfaces:

                self.output.write("\t<if>\n")

                mapping = {"subnet":"network", "mac":"mac", "ipv4":"ip"}
                self.writeInterface(realm, interface, mapping)

                self.output.write("\t</if>\n")

            self.output.write("</vrm>\n\n")
#******************************FINISH REALM

    def autogen_mobile(self):
        """
        Auto-generate properties for Mobiles.
        """
        for uml in self.compile_list["Mobile"]:
            for interface in uml.getInterfaces():
                if options["autogen"]:
                    subnet = str(uml.getInterfaceProperty("subnet")).rsplit(".", 1)[0]
                    uml.setInterfaceProperty("ipv4", "%s.%d" % (subnet, uml.getID()+1))
                    uml.setInterfaceProperty("mac", "fe:fd:00:00:00:%02x" % uml.getID())

    def compile_mobile(self):
        """
        Compile all the Mobiles.
        """
        for uml in self.compile_list["Mobile"]:
            self.output.write("<vmb name=\"" + uml.getName() + "\">\n")
            self.output.write("\t<filesystem type=\"" + uml.getProperty("filetype") + "\">"
                              + uml.getProperty("filesystem") + "</filesystem>\n")

            interfaces = uml.getInterfaces()
            if len(interfaces) < 1:
                self.generateConnectionWarning(uml, 1)

            for interface in interfaces:

                self.output.write("\t<if>\n")

                mapping = {"subnet":"network", "mac":"mac", "ipv4":"ip"}
                self.writeInterface(uml, interface, mapping)

                self.output.write("\t</if>\n")

            self.output.write("</vmb>\n\n")

    def compile_OpenFlow_Controller(self):
        """
        Compile all the OpenFlow controllers.
        """
        for controller in self.compile_list["OpenFlow_Controller"]:
            self.output.write("<vofc name=\"" + controller.getName() + "\">\n")

            routerFound = False
            for con in controller.edges():
                node = con.getOtherDevice(controller)
                if node.device_type == "Router":
                    self.output.write("\t<router>" + node.getName() + "</router>\n")
                    routerFound = True
                else:
                    self.generateGenericWarning(controller, "has non-router connection; ignored")

            if not routerFound:
                self.generateGenericWarning(controller, "has no router connections")

            self.output.write("</vofc>\n\n")


    def generateGenericWarning(self, device, message):
        """
        Generate a compile warning.
        """
        self.warnings += 1
        message = ' '.join(("Warning:", device.getName(), message))
        self.log.append(message)



    def pass_mask(self, node):
        """
        Pass the mask between connected devices.
        """
        try:
            subnet = node.getProperty("subnet")
        except:
            self.generateError(node, "subnet", "missing")
            return

        try:
            mask = node.getProperty("mask")
        except:
            self.generateError(node, "mask", "missing")
            return

        for con in node.edges():
            otherDevice = con.getOtherDevice(node)
            if otherDevice.device_type in ["Router", "UML", "REALM", "Mobile", "yRouter"]:
                target = node
                if node.device_type == "Subnet":
                    target = node.getTarget(otherDevice)
                    if target is None:
                        continue
                otherDevice.setInterfaceProperty("subnet", subnet, target)
                otherDevice.setInterfaceProperty("mask", mask, target)
            else:
                otherDevice.setProperty("subnet", subnet)
                otherDevice.setProperty("mask", mask)

    def routing_table_clear(self):
        """
        Clear all route tables of interfaceable devices.
        """
	for interfaceable in self.compile_list["yRouter"]:
	    interfaceable.emptyAdjacentLists()
	    interfaceable.emptyRouteTable()

        for interfaceable in self.compile_list["Router"]:
            interfaceable.emptyAdjacentLists()
            interfaceable.emptyRouteTable()

        for interfaceable in self.compile_list["UML"]:
            interfaceable.emptyAdjacentLists()
            interfaceable.emptyRouteTable()

        for interfaceable in self.compile_list["REALM"]:
            interfaceable.emptyAdjacentLists()
            interfaceable.emptyRouteTable()

    def routing_table_interfaceable(self, devType):
        """
        Compute route tables of devices of type devType.
        """
        for interfaceable in self.compile_list[devType]:
            interfaceable.emptyAdjacentLists()
            interfaceable.emptyRouteTable()
            self.findAdjacentRouters(interfaceable)
            self.findAdjacentSubnets(interfaceable)

    def routing_table_uml(self):
        """
        Compute route tables of UMLs.
        """
        self.routing_table_interfaceable("UML")

        for uml in self.compile_list["UML"]:
            for subnet in self.compile_list["Subnet"]:
                if not uml.hasSubnet(subnet.getProperty("subnet")):
                    uml.addRoutingEntry(subnet.getProperty("subnet"))

    def routing_table_realm(self):
        """
        Compute route tables of REALMs.
        """
        self.routing_table_interfaceable("REALM")

        for uml in self.compile_list["REALM"]:
            for subnet in self.compile_list["Subnet"]:
                if not uml.hasSubnet(subnet.getProperty("subnet")):
                    uml.addRoutingEntry(subnet.getProperty("subnet"))

    def routing_table_mobile(self):
        """
        Compute route tables of Mobiles.
        """
        self.routing_table_interfaceable("Mobile")

        for uml in self.compile_list["Mobile"]:
            for subnet in self.compile_list["Subnet"]:
                if not uml.hasSubnet(subnet.getProperty("subnet")):
                    uml.addRoutingEntry(subnet.getProperty("subnet"))

    def routing_table_router(self):
        """
        Compute route tables of Routers.
        """
        self.routing_table_interfaceable("Router")

    def routing_table_yRouter(self):
	"""
	Compute route tables of yRouters.
	"""
        self.routing_table_interfaceable("yRouter")

    def routing_table_wireless_access_point(self):
        """
        Compute route tables of Wireless_access_points.
        """
        self.routing_table_interfaceable("Wireless_access_point")

    def routing_table_entry(self):
        """
        Add routing entries for Routers and yRouters.
        """
        for uml in self.compile_list["Router"]:
            for subnet in self.compile_list["Subnet"]:
                uml.addRoutingEntry(subnet.getProperty("subnet"))
	for uml in self.compile_list["yRouter"]:
	    for subnet in self.compile_list["Subnet"]:
		uml.addRoutingEntry(subnet.getProperty("subnet"))

    def findAdjacentRouters(self, device):
        """
        Find all Routers adjacent to device.
        """
        for interface in device.getInterfaces():
            for con in device.edges():
                otherDevice = con.getOtherDevice(device)
                if otherDevice.device_type == "Subnet":
                    otherDevice = otherDevice.getTarget(device)
                if interface[QtCore.QString("target")] == otherDevice:
                    break

            visitedNodes = []
            self.visitAdjacentRouters(device, con, device, interface, visitedNodes)

    def visitAdjacentRouters(self, myself, con, device, interface, visitedNodes):
        """
        Helper method to find adjacent Routers.
        """
        otherDevice = con.getOtherDevice(device)
        if otherDevice in visitedNodes:
            return

        visitedNodes.append(otherDevice)

        if otherDevice.device_type in ["Router", "Wireless_access_point", "yRouter"]:
            myself.addAdjacentRouter(otherDevice, interface)
        elif otherDevice.device_type in ["UML", "Mobile", "REALM"]:
            pass
        else:
            for c in otherDevice.edges():
                if con != c:
                    self.visitAdjacentRouters(myself, c, otherDevice, interface, visitedNodes)

    def findSwitchInterface(self, interfaces, switch):

        for i in interfaces:
            if i[QtCore.QString("target")] == switch:
                return i
        return None


    def findAdjacentSubnets(self, device):
        """
        Find all Subnets adjacent to device.
        """
        ainterfaces = device.getInterfaces()

        for con in device.edges():
            otherDevice = con.getOtherDevice(device)
            if otherDevice.device_type == "Subnet":
                device.addAdjacentSubnet(otherDevice.getProperty("subnet"))
            elif otherDevice.device_type == "Switch":
                for c in otherDevice.edges():
                    odevice = c.getOtherDevice(otherDevice)
                    if odevice != device and odevice.device_type == "Router":
                        iface = self.findSwitchInterface(ainterfaces, otherDevice)
                        device.addAdjacentRouter(odevice, iface)

                device.addAdjacentSubnet(otherDevice.getProperty("subnet"))
            elif otherDevice.device_type == "Wireless_access_point":
                device.addAdjacentSubnet(otherDevice.getProperty("subnet"))

    def formatRoutes(self, routes, devType):
        """
        Format the routes in xml.
        """
        if devType == "UML" or devType == "REALM":
            header = "\t\t<route type=\"net\" "
            gateway = "\" gw=\""
            footer = "</route>\n"
        else:
            header = "\t\t<rtentry "
            gateway = "\" nexthop=\""
            footer = "</rtentry>\n"

        # Because of gloader's getVMIFOutLine, we must preserve a specific order of the routes
        outstring = ""
        outstring2 = ""
        for route in routes:
            string = ""
            string += header
            string += "netmask=\"" + route[QtCore.QString("netmask")]
            string += gateway
            string += route[QtCore.QString("gw")]
            string += "\">" + route[QtCore.QString("subnet")]
            string += footer

            if route[QtCore.QString("gw")]:
                outstring2 += string
            else:
                outstring += string

        return outstring + outstring2

    def validate(self, prop, value, interface=None):
        """
        Validate a property of a device or interface.
        """
        if prop == "mac":
            return self.valid_mac(value)
        elif prop == "ipv4":
            return self.valid_ip_subnet(value, interface[QtCore.QString("subnet")], interface[QtCore.QString("mask")])
        elif prop == "mask":
            return self.valid_mask(value)
        else:
            return self.valid_ip(value)

    def valid_ip(self, ip):
        """
        Validate an ip-like address (includes mask).
        """
        ip = str(ip)
        if re.match(r'^\d+\.\d+\.\d+\.\d+$', ip) == None:
            return False

        p = re.compile('\d+')
        res = p.findall(ip)

        # Each chunk should be between 0 and 255 inc
        for chunk in res:
            if not int(chunk) in range(256):
                return False
        return True

    def valid_mask(self, mask):
        """
        Validate a subnet mask.
        """
        mask = str(mask)
        if mask == "255.255.255.0":
            return True
        else:
            self.warnings += 1
            message = "Warning: Using a mask other than 255.255.255.0 is not recommended."
            self.log.append(message)

        if not self.valid_ip(mask):
            return False

        # Make sure the chunks match the possible values
        chunks = mask.split(".")
        for chunk in chunks:
            if not int(chunk) in (0, 128, 192, 224, 240, 248, 252, 255):
                return False

        # The last chunk of a mask cannot be 255
        if int(chunks[-1]) == 255:
            return False

        return True

    def valid_ip_subnet(self, ip, subnet, mask):
        """
        Validate an ip address based on the subnet and mask.
        """
        ip = str(ip)
        subnet = str(subnet)
        mask = str(mask)

        if not self.valid_ip(ip):
            return False
        if not self.valid_mask(mask):
            return False

        p=re.compile('\d+')
        ip_chunk=p.findall(ip)
        subnet_chunk=p.findall(subnet)
        mask_chunk=p.findall(mask)

        # Make sure the ip addresses are not reserved
        if ip_chunk[3] == "0" or ip_chunk[3] == "255":
            return False

        # Check each chunk against subnet and mask
        for i in range(len(subnet_chunk)):
            if mask_chunk[i] == "255":
                if ip_chunk[i] != subnet_chunk[i]:
                    return False
            elif mask_chunk[i] == "0":
                if ip_chunk[i] == "0":
                    return False
            else:
                mask_value = int(mask_chunk[i])
                ip_value = int(ip_chunk[i])
                subnet_value = int(subnet_chunk[i])

                if i == 3:
                    ip_range = 254 - mask_value
                    if not ip_value - 1 in range(ip_range):
                        return False
                else:
                    ip_range = 256 - mask_value
                    if not ip_value in range(ip_range):
                        return False
        return True

    def valid_mac(self, mac):
        """
        Validate a mac address.
        """
        mac = str(mac)
        if re.match(r'^[a-f|0-9]{2}:[a-f|0-9]{2}:[a-f|0-9]{2}:[a-f|0-9]{2}:[a-f|0-9]{2}:[a-f|0-9]{2}$', mac) == None:
            return False
        else:
            return True
