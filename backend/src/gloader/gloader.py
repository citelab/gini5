#!/usr/bin/python2

# Revised by Daniel Ng
# Revised to Docker version by Mahesh

import sys, os, signal, time, subprocess, re, socket

from program import Program
#import batch_ipcrm

# set the program names
VS_PROG = "uswitch"
VM_PROG = "glinux"
GR_PROG = "grouter"
VOFC_PROG = "gpox"
GWR_PROG = "gwcenter.sh"
MCONSOLE_PROG = "mach_mconsole"
SOCKET_NAME = "gini_socket"
VS_PROG_BIN = VS_PROG
VM_PROG_BIN = VM_PROG
GR_PROG_BIN = GR_PROG
VOFC_PROG_BIN = VOFC_PROG
GWR_PROG_BIN = GWR_PROG
MCONSOLE_PROG_BIN = MCONSOLE_PROG
SRC_FILENAME = "%s/gini_setup" % os.environ["GINI_HOME"] # setup file name
GINI_TMP_FILE = ".gini_tmp_file" # tmp file used when checking alive Mach
nodes = []
tapNameMap = dict()
subnetMap = dict()
dockerNetworkNameMap = dict()

# set this switch True if running gloader without gbuilder
independent = False

def system(command):
    subprocess.call(["/bin/bash", "-c", command])

def popen(command):
    subprocess.Popen(["/bin/bash", "-c", command])

def startGINI(myGINI, options):
    "starting the GINI network components"
    # the starting order is important here
    # first switches, then routers, and at last Machs.
    print "\nStarting Docker Switches..."
    success = createVS(myGINI, options.switchDir)
    #print "\nStarting Mobiles..."
    #success = success and createVMB(myGINI, options)
    print "\nStarting OpenFlow controllers..."
    success = success and createVOFC(myGINI, options)
    print "\nStarting GINI routers..."
    success = success and createVR(myGINI, options)
    print "\nStarting Docker Machines..."
    success = success and createVM(myGINI, options)
    #print "\nStarting Wireless access points..."
    #success = success and createVWR(myGINI, options)
    #print "\nStarting REALMs..."
    #success = success and createVRM(myGINI, options)

    if (not success):
        print "Problem in creating GINI network"
        print "Terminating the partally started network (if any)"
        destroyGINI(myGINI, options)
    return success

def findSubnet4Switch(myGINI, sname):

    # Search the VMs for a matching target
    for mach in myGINI.vm:
        for netif in mach.interfaces:
            if netif.target == sname:
                return netif.network

    # Search the Routers for a matching target
    for vr in myGINI.vr:
        for nif in vr.netIF:
            if nif.target == sname:
                return nif.network

    return ""


def create_ovs(my_gini, switch_dir, switch):
    print "Starting %s...\t" % switch.name
    sub_switch_dir = switch_dir + "/" + switch.name
    makeDir(sub_switch_dir)
    old_dir = os.getcwd()
    os.chdir(sub_switch_dir)

    undo_file = "%s/stopit.sh" % sub_switch_dir
    undo_out = open(undo_file, "w")
    undo_out.write("#!/bin/bash\n\n")

    subnet = findSubnet4Switch(my_gini, switch.name)
    if subnet != "":
        if subnetMap.get(subnet):
            dockerNetworkNameMap[switch.name] = subnetMap[subnet]
            os.chmod(undo_file, 0755)
            undo_out.close()
            print "[OK]"
            os.chdir(old_dir)
            return True

        start_file = "%s/startit.sh" % sub_switch_dir
        start_out = open(start_file, "w")
        start_out.write("#!/bin/bash\n\n")
        startup_commands = "ovs-vsctl add-br %s &&\n" % switch.name
        startup_commands += "ip addr add %s/24 dev %s &&\n" % (subnet, switch.name)
        startup_commands += "ip link set %s up &&\n" % switch.name
        startup_commands += "ovs-vsctl set-fail-mode %s standalone &&" % switch.name
        start_out.write(startup_commands)

        screen_command = "screen -d -m -L -S %s " % switch.name
        screen_command += "gvirtual-switch %s\n" % switch.name
        start_out.write(screen_command)

        os.chmod(start_file, 0755)
        start_out.close()

        undo_out.write("ovs-vsctl del-br %s\n" % switch.name)
        undo_out.write("screen -S %s -X quit\n" % switch.name)
        os.chmod(undo_file, 0755)
        undo_out.close()

        runcmd = subprocess.Popen(start_file, shell=True, stdout=subprocess.PIPE)
        runcmd.communicate()
        if runcmd.returncode == 0:
            subnetMap[subnet] = switch.name
            print "[OK]"
            os.chdir(old_dir)
            return True
        else:
            print "[Failed]"
            return False
    else:
        print "[Failed] Cannot find a subnet"
        undo_out.close()
        return False

def createVS(myGINI, switchDir):
    "create the switch config file and start the switch"
    # create the main switch directory
    makeDir(switchDir)

    for switch in myGINI.switches:
        if switch.isOVS:
            if create_ovs(myGINI, switchDir, switch):
                continue
            else:
                print "[Failed] Error when creating Open virtual switch"
                return False

        print "Starting %s...\t" % switch.name,
        subSwitchDir = switchDir + "/" + switch.name
        makeDir(subSwitchDir)
        undoFile = "%s/stopit.sh" % subSwitchDir
        undoOut = open(undoFile, "w")
        undoOut.write("#!/bin/bash\n")

        subnet = findSubnet4Switch(myGINI, switch.name)
        if (subnet != ""):
            # Check if the network is already created under another switch name
            if subnetMap.get(subnet):
                dockerNetworkNameMap[switch.name] = subnetMap[subnet]
                os.chmod(undoFile, 0755)
                undoOut.close()
                continue

            command = "docker network create %s --subnet %s/24" % (switch.name, subnet)
            runcmd = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
            out,err = runcmd.communicate()
            if runcmd.returncode == 0:

                subnetMap[subnet] = switch.name
                if switch.hub:
                    print "Activating hub mode..."
                    bridge_name = "br-" + out[:12]
                    subprocess.call("brctl setageing %s 0" % bridge_name, shell=True)

                undoOut.write(
                    """for i in ` docker network inspect -f '{{range .Containers}}{{.Name}} {{end}}' %s`;
                    do
                    docker network disconnect -f %s $i;
                    done;
                    """ % (out, out)
                )
                undoOut.write("docker network remove %s\n" % out)
                os.chmod(undoFile, 0755)
                print "[OK]"
            else:
                command = """docker network inspect %s --format='{{.Id}}'""" % switch.name
                q = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
                out,err = q.communicate()
                if q.returncode == 0:
                    undoOut.write(
                        """for i in ` docker network inspect -f '{{range .Containers}}{{.Name}} {{end}}' %s`;
                        do
                        docker network disconnect -f %s $i;
                        done;
                        """ % (out, out)
                    )
                    undoOut.write("docker network remove %s\n" % out)
                    os.chmod(undoFile, 0755)
                    print "[OK]"
                else:
                    print "[Failed]"
                    undoOut.close()
                    return False
        else:
            print "cannot find a subnet"
            print "[Failed]"
            undoOut.close()
            return False

        os.chmod(undoFile, 0755)
        undoOut.close()
    return True
#End - createVS


def createVWR(myGINI, options):

    oldDir = os.getcwd()
    routerDir = options.routerDir

    for wrouter in myGINI.vwr:
        print "Starting Wireless access point %s...\t" % wrouter.name
        subRouterDir = routerDir + "/" + wrouter.name
        makeDir(subRouterDir)
        configFile = "%s/wrouter.conf" % subRouterDir
        configOut = open(configFile, "w")
        configOut.write("ch set prop mode F\n")

        if not independent:
            canvasIn = open("%s/mobile_data/canvas.data" % routerDir, "r")
            line = canvasIn.readline()
            canvasIn.close()
            x = int(line.split(",")[0]) / 4
            y = int(line.split(",")[1]) / 4
            configOut.write("sys set map size %d %d 0\n" % (x, y))
            wrouterIn = open("%s/mobile_data/%s.data" % (routerDir,wrouter.name), "r")
            line = wrouterIn.readline()
            wrouterIn.close()
            relx = int(line.split(",")[0]) / 4
            rely = int(line.split(",")[1]) / 4

        else:
            configOut.write("sys set map size 100 100 0\n")

        for mobile in myGINI.vmb:
            node = nodes.index(mobile.name) + 1
            configOut.write("mov set node %d switch off\n" % node)
            if not independent:
                nodeIn = open("%s/mobile_data/%s.data" % (routerDir,mobile.name), "r")
                line = nodeIn.readline()
                nodeIn.close()
                x = int(line.split(",")[0]) / 4
                y = int(line.split(",")[1]) / 4
                configOut.write("mov set node %d location %d %d 0\n" % (node, x - relx, y - rely))
            else:
                configOut.write("mov set node %d location 0 0 0\n" % node)

        for netWIF in wrouter.netIFWireless:
            #netWIF.printMe()
            configOut.write(get_IF_properties(netWIF, len(myGINI.vmb)))

        index = len(nodes)-1
        if nodes and nodes[index].find("Mach_") >= 0:
            configOut.write("mov set node %d switch off\n" % (index + 1))
            if not independent:
                configOut.write("mov set node %d location %d %d 0\n" % (index + 1, relx, rely))
            else:
                configOut.write("mov set node %d location 0 0 0\n" % (index + 1))
        configOut.write("echo -ne \"\\033]0;" + wrouter.name + "\\007\"")
        configOut.close()

        ### ------- execute ---------- ###
        # go to the router directory to execute the command
        os.chdir(os.environ["GINI_HOME"]+"/data")
        cmd = "%s -i 1 -c %s -n %d -d mach_virtual_switch" % (GWR_PROG_BIN, configFile, len(nodes))
        #print "running cmd %s" % cmd
        wrouter.num = wrouter.name.split("Wireless_access_point_")[-1]
        command = "screen -d -m -L -S WAP_%s %s" % (wrouter.num, cmd)
        print "Waiting for Mobiles to finish starting up...\t",
        sys.stdout.flush()
        i = 0
        ready = False
        while not ready:
            if i > 5:
                print "There was an error in waiting for the mobiles to start up"
                print "%s may not function properly" % wrouter.name
                break
            time.sleep(2)
            for mobile in myGINI.vmb:
                nwIf = mobile.interfaces[0]
                configFile = "/tmp/%s.sh" % nwIf.mac.upper()
                if os.access(configFile, os.F_OK):
                    ready = False
                    break
                else:
                    ready = True
            i += 1

        scriptOut = open("WAP%s_start.sh" % wrouter.num, "w")
        scriptOut.write(command)
        scriptOut.close()
        os.chmod("WAP%s_start.sh" % wrouter.num, 0777)
        system("./WAP%s_start.sh" % wrouter.num)
        system("screen -d -m -L -S VWAP_%s Wireless_Parser" % wrouter.num)
        os.chdir(oldDir)
        print "[OK]"
    return True

def get_IF_properties(netWIF, num_nodes):
    wcard = netWIF.wireless_card
    #energy = netWIF.energy     not implemented by GWCenter
    mobility = netWIF.mobility
    antenna = netWIF.antenna
    mlayer = netWIF.mac_layer

    prop = ""
    prop += "wcard set node 1 freq %f\n" % (float(wcard.freq)/1000000)
    prop += "wcard set node 1 bandwidth %f\n" % (float(wcard.bandwidth)/1000000)
    prop += "wcard set node 1 csthreshold %f\n" % (float(wcard.cs) * 1e8)
    prop += "wcard set node 1 rxthreshold %f\n" % (float(wcard.rx) * 1e8)
    prop += "wcard set node 1 cpthreshold %s\n" % wcard.cp
    prop += "wcard set node 1 pt %s\n" % wcard.pt
    prop += "wcard set node 1 ptx %s\n" % wcard.ptC
    prop += "wcard set node 1 prx %s\n" % wcard.prC
    prop += "wcard set node 1 pidle %s\n" % wcard.pIdle
    prop += "wcard set node 1 psleep %s\n" % wcard.pSleep
    prop += "wcard set node 1 poff %s\n" % wcard.pOff
    prop += "wcard set node 1 modtype %s\n" % wcard.module[0]
    for i in range(num_nodes):
        prop += "ant set node %d height %s\n" % (i+1, antenna.ant_h)
        prop += "ant set node %d gain %s\n" % (i+1, antenna.ant_g)
        prop += "ant set node %d sysloss %s\n" % (i+1, antenna.ant_l)
        prop += "ant set node %d jam %s\n" % (i+1, antenna.jam)
    for i in range(num_nodes):
        prop += "mov set node %d mode %s\n" % (i+1, mobility.mType[0])
        prop += "mov set node %d spd min %s\n" % (i+1, mobility.ranMin)
        prop += "mov set node %d spd max %s\n" % (i+1, mobility.ranMax)
    for i in range(num_nodes):
        if mlayer.macType == "MAC 802.11 DCF":
            prop += "mac set node %d mode D11\n" % (i+1)
        else:
            prop += "mac set node %d mode %s\n" % (i+1, mlayer.macType[0])
            prop += "mac set node %d txprob %s\n" % (i+1, mlayer.trans)
    return prop


def findHiddenSwitch(rtname, swname):

    x,rnum = rtname.split("_")
    x,snum = swname.split("_")
    if x != "Router":
        swname = "Switch_r%sm%s" % (rnum, snum)
    else:
        swname = "Switch_r%sr%s" % (rnum, snum)

    command = """docker network inspect %s --format='{{.Id}}'""" % swname
    q = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
    out,err = q.communicate()
    if q.returncode == 0:
        return swname

    return None
#End findHiddenSwitch

def findBridgeName(swname):

    command = """docker network inspect %s --format='{{.Id}}'""" % swname
    q = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
    out,err = q.communicate()
    if q.returncode == 0:
        return "br-" + out[:12]

    return None


def createASwitch(rtname, swname, subnet, ofile):

    x,rnum = rtname.split("_")
    x,snum = swname.split("_")
    if x != "Router":
        swname = "Switch_r%sm%s" % (rnum, snum)
    else:
        swname = "Switch_r%sr%s" % (rnum, snum)

    # Similar to switch devices, check if the network is already created under another name
    if subnetMap.get(subnet):
        dockerNetworkNameMap[swname] = subnetMap[subnet]
        swname = subnetMap[subnet]

        command = "docker network inspect %s --format='{{.Id}}'" % swname
        q = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
        out, err = q.communicate()
        if q.returncode == 0:
            brname = "br-" + out[:12]
            return swname, brname

    command = "docker network create %s --subnet %s/24" % (swname, subnet)
    q = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
    out,err = q.communicate()
    if q.returncode == 0:
        subnetMap[subnet] = swname

        brname = "br-" + out[:12]
        ofile.write(
            """for i in ` docker network inspect -f '{{range .Containers}}{{.Name}} {{end}}' %s`;
            do
            docker network disconnect -f %s $i;
            done;
            """ % (out, out)
        )
        ofile.write("docker network remove %s" % out)
        return swname, brname
    else:
        command = """docker network inspect %s --format='{{.Id}}'""" % swname
        q = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
        out,err = q.communicate()
        if q.returncode == 0:
            brname = "br-" + out[:12]
            ofile.write(
                """for i in ` docker network inspect -f '{{range .Containers}}{{.Name}} {{end}}' %s`;
                do
                docker network disconnect -f %s $i;
                done;
                """ % (out, out)
            )
            ofile.write("\ndocker network remove %s\n" % out)
            return swname, brname
        return None, None
    # return the name of the newly created switch, bridge name
# NOTE We can use the following command string to pull subne information
# command = """docker network inspect %s --format='{{index .IPAM.Config 0 "Subnet"}}'""" % swname

def setupTapInterface(rtname, swname, brname, ofile):
    # This assumes that the iproute2 (ip) utils work without
    # sudo - you need to turn on the setuid bit

    x,rnum = rtname.split("_")
    x,snum = swname.split("_")
    if x != "Router":
        tapKey = "Switch_r%sm%s" % (rnum, snum)
    else:
        tapKey = "Switch_r%sr%s" % (rnum, snum)

    if tapNameMap.get(tapKey) is None:
        tapNameMap[tapKey] = "tap" + str(len(tapNameMap)+1)
    tapName = tapNameMap[tapKey]

    subprocess.call("ip tuntap add mode tap dev %s" % tapName, shell=True)
    subprocess.call("ip link set %s up" % tapName, shell=True)

    subprocess.call("brctl addif %s %s" % (brname, tapName), shell=True)

    ofile.write("\nip link del %s\n" % tapName)

    return tapName


def createVR(myGINI, options):
    "create router config file, and start the router"

    routerDir = options.routerDir
    switchDir = options.switchDir
    # create the main router directory
    makeDir(routerDir)
    for router in myGINI.vr:
        print "Starting %s...\t" % router.name,
        sys.stdout.flush()
        ### ------ config ---------- ###
        # name the config file
        subRouterDir = "%s/%s" % (routerDir, router.name)
        makeDir(subRouterDir)
        # go to the router directory to execute the command
        oldDir = os.getcwd()
        os.chdir(subRouterDir)
        configFile = "%s.conf" % GR_PROG
        # delete confFile if already exists
        if (os.access(configFile, os.F_OK)):
            os.remove(configFile)
        # create the config file
        configOut = open(configFile, "w")
        stopOut = open("stopit.sh", "w")
        stopOut.write("#!/bin/bash\n")

        for nwIf in router.netIF:
            swname = nwIf.target
            print "Checking switch: " + swname
            if not checkSwitch(myGINI, swname):
                print "It is not a switch..."
                # Router could be conected to a machine
                if checkRouter(myGINI, swname):
                    print "It is a router at the other end."
                    # Check whether the other router has already created the hidden switch
                    # If so, this router can just tap into it
                    x,rnum = router.name.split("_")
                    x,snum = swname.split("_")
                    scheck = "Switch_r%sr%s" % (snum, rnum)
                    brname = findBridgeName(scheck)
                    if (brname == None):
                        swname, brname = createASwitch(router.name, swname, nwIf.network, stopOut)
                        if swname == None:
                            print "[Failed]"
                            return False
                else:
                    # We are connected to a machine

                    swname, brname = createASwitch(router.name, swname, nwIf.network, stopOut)
                    if swname == None:
                        print "[Failed]"
                        return False
            else:
                brname = findBridgeName(swname)
            tapname = setupTapInterface(router.name, swname, brname, stopOut)
            if (tapname == "None"):
                print "[Failed]"
                print "\nRouter %s: unable to create tap interface"  % router.name
                return False
            else:
                configOut.write(getVRIFOutLine(nwIf, tapname))
        configOut.write("echo -ne \"\\033]0;" + router.name + "\\007\"")
        configOut.close()
        stopOut.close()
        ### ------- commands to execute ---------- ###
        command = "screen -d -m -L -S %s %s " % (router.name, GR_PROG_BIN)
        command += "--config=%s.conf " % GR_PROG
        command += "--confpath=" + os.environ["GINI_HOME"] + "/data/" + router.name + " "
        command += "--interactive=1 "

        if router.openFlowController:
            command += "--openflow="
            for controller in myGINI.vofc:
                for r in controller.routers:
                    if r == router.name:
                        port = None
                        try:
                            # Determine PID of controller and find the netstat entry associated with that PID
                            print "%s/%s/%s.pid" % (options.controllerDir, controller.name, controller.name)
                            pid_file = open("%s/%s/%s.pid" % (options.controllerDir, controller.name, controller.name), "r")
                            cmd = "netstat -tlpn | egrep %s/" % pid_file.read().strip()

                            process = subprocess.Popen(cmd, shell=True,
                                                       stdout=subprocess.PIPE,
                                                       stderr=subprocess.PIPE)
                            out = process.stdout.read().strip()
                            if out == "":
                                raise StandardError()
                            pid_file.close()
                            process.stdout.close()

                            # Get TCP port number from netstat entry
                            regex = re.compile("^.+:([0-9]+)[^0-9].*$")
                            matches = regex.match(out)
                            if matches and len(matches.groups()) == 1:
                                port = matches.group(1)
                            else:
                                raise StandardError()
                        except StandardError as e:
                            print "[Failed]"
                            print "Failed to identify OpenFlow controller TCP port"
                            return False

                        # Pass controller port number to router so that router can connect to controller
                        command += port + " "

        command += "%s" % router.name
        #print command
        startOut = open("startit.sh", "w")
        startOut.write(command)
        startOut.close()
        os.chmod("startit.sh",0755)
        os.chmod("stopit.sh",0755)

        system("./startit.sh")
        print "[OK]",
        if router.openFlowController:
            print " (OF port: " + port + ")",
        print ""
        os.chdir(oldDir)


    return True


def getDockerNetworkName(switch_name):
    if dockerNetworkNameMap.get(switch_name):
        return dockerNetworkNameMap[switch_name]
    else:
        return switch_name


def checkSwitch(myGINI, name):

    for switch in myGINI.switches:
        if switch.name == name:
            return True
    return False


def checkRouter(myGINI, name):

    for vr in myGINI.vr:
        if vr.name == name:
            return True
    return False


def getSwitch2Connect(myGINI, mach):
    # one of the interfaces is
    for nwi in mach.interfaces:
        target = nwi.target
        if checkSwitch(myGINI, target):
            return getDockerNetworkName(target), nwi.ip

    for nwi in mach.interfaces:
        target = nwi.target
        if checkRouter(myGINI, target):
            # create a 'hidden' switch because docker needs a
            # switch to connect to the router
            swname = findHiddenSwitch(target, mach.name)
            return getDockerNetworkName(swname), nwi.ip

    return (None, None)
#end - getSwitch2Connect


def createVM(myGINI, options):
    "create Mach config file, and start the Mach"

    makeDir(options.machDir)

    print ">>>>>>>>>>>>>> Start >>>>>"

    for mach in myGINI.vm:
        print "Starting %s...\t" % mach.name,
        subMachDir = "%s/%s" % (options.machDir, mach.name)
        makeDir(subMachDir)

        # Store current and go into the sub directory...
        oldDir = os.getcwd()
        os.chdir(subMachDir)

        # Write an init script to run at docker startup
        startOut = open("entrypoint.sh", "w")
        startOut.write("#!/bin/ash\n\n")
        for nwIf in mach.interfaces:
            for route in nwIf.routes:
                command = "route add -%s %s " % (route.type, route.dest)
                command += "netmask %s " % route.netmask
                if route.gw:
                    command += "gw %s " % route.gw
                startOut.write(command + "\n")
            #end each route
        #end each interface

        stopOut = open("stopit.sh", "w")
        stopOut.write("#!/bin/bash\n")
        # Get switch to connect
        print "Before get "
        sname, ip = getSwitch2Connect(myGINI, mach)

        # Export command prompt for VM, start shell inside docker container
        startOut.write("\nexport PS1='root@%s >> '\n" % ip)
        startOut.write("/bin/ash\n")
        startOut.close()
        os.chmod("entrypoint.sh", 0755)

        print "Sname " + sname + " IP " + ip
        baseScreenCommand = "screen -d -m -L -S %s " % mach.name

        if sname is not None:
            isOVS = False
            if sname[:3] == "OVS":
                isOVS = True

            # create command line
            command = "docker run -it --privileged --name %s " % mach.name
            command += "-v %s/data/%s:/root " % (os.environ["GINI_HOME"], mach.name)
            command += "--entrypoint /root/entrypoint.sh "
            if not isOVS:
                command += "--network %s " % sname
                command += "--ip %s " % ip
            command += "alpine /bin/ash"

            print "<<<<<<< " + baseScreenCommand + command

            runcmd = subprocess.Popen(baseScreenCommand + command, shell=True, stdout=subprocess.PIPE)
            out,err = runcmd.communicate()

            if runcmd.returncode == 0:
                if isOVS:
                    time.sleep(1)   # Avoid race condition
                    ovsCommand = "ovs-docker add-port %s eth1 %s --ipaddress=%s/24" % (sname, mach.name, ip)
                    print ovsCommand
                    runcmd = subprocess.Popen(ovsCommand, shell=True, stdout=subprocess.PIPE)
                    stopOut.write("ovs-docker del-port %s eth1 %s\n" % (sname, mach.name))
                    runcmd.communicate()

                stopOut.write("docker kill %s\n" % mach.name)
                stopOut.write("docker rm %s\n\n" % mach.name)
                if runcmd.returncode != 0:
                    stopOut.close()
                    os.chmod("stopit.sh", 0755)
                    system("./stopit.sh")
                    print "[Failed] ovs-docker error"
                    return False
            else:
                print "[Failed] Error when creating Docker container"
                return False
        else:
            print "[Failed] No Target found for Machine: %s " % mach.name
            return False

        print "[OK]"

        stopOut.close()
        os.chmod("stopit.sh",0755)
        # Restore the old directory...
        os.chdir(oldDir)

    return True

def check_port_available(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(("0.0.0.0", port))
    if result == 0:
        return False
    else:
        return True

def find_available_port(lower_range, upper_range):
    for port in range(lower_range, upper_range+1):
        if check_port_available(port):
            return port
    return -1

def createVOFC(myGINI, options):
    "Create OpenFlow controller config file, and start the OpenFlow controller"

    makeDir(options.controllerDir)
    print("Controller directory", options.controllerDir)
    for controller in myGINI.vofc:
        print "Starting OpenFlow controller %s...\t" % controller.name,
        subControllerDir = "%s/%s" % (options.controllerDir, controller.name)
        makeDir(subControllerDir)

        port = find_available_port(6633, 6653)
        if port == -1:
            print "[FAILED] Cannot find an unused port"
            return False

        vofcFlags = "py "
        vofcFlags += "openflow.of_01 --address=0.0.0.0 --port=%d " % port
        vofcFlags += "gini.core.forwarding_l2_pairs "
        vofcFlags += "gini.support.gini_pid --pid_file_path='%s/%s/%s.pid' " % (options.controllerDir, controller.name, controller.name)
        vofcFlags += "gini.support.gini_module_load --module_file_path='%s/%s/%s.modules' " % (options.controllerDir, controller.name, controller.name)

        print "------------------------------------"
        print "VOFC: " + vofcFlags
        print "------------------------------------"

        command = "screen -d -m -L -S %s %s %s\n\n" % (controller.name, VOFC_PROG_BIN, vofcFlags)

        connect_commands = ""
        for ovs in controller.open_virtual_switches:
            connect_commands += "ovs-vsctl set-controller %s tcp:0.0.0.0:%d\n" % (ovs, port)

        oldDir = os.getcwd()
        os.chdir(subControllerDir)
        startOut = open("startit.sh", "w")
        startOut.write(command)
        startOut.write(connect_commands)
        startOut.close()
        os.chmod("startit.sh",0755)
        system("./startit.sh")
        print "[OK]"
    return True

def createVMB(myGINI, options):
    "create Mach config file, and start the Mach"
    baseDir = os.environ["GINI_HOME"] + "/data/mach_virtual_switch"
    makeDir(baseDir)
    makeDir(options.machDir)
    oldDir = os.getcwd()
    del nodes[:]
    for mobile in myGINI.vmb:
        print "Starting virtual Switch for Mobile %s...\t" % mobile.name,
        #print nodes
        nodes.append(mobile.name)
        node = len(nodes)
        subMachDir = baseDir+"/VS_%d" % node
        makeDir(subMachDir)
        os.chdir(subMachDir)
#        vsconf = open("uswitch.conf", "w")
#        vsconf.write("logfile uswitch.log\npidfile uswitch.pid\nsocket gw_socket.ctl\nfork\n")
#        vsconf.close()
        popen("%s -s gw_socket.ctl -l uswitch.log -p uswitch.pid&" % VS_PROG)
        print "[OK]"

        print "Starting Mobile %s...\t" % mobile.name,
        # create command line
        command = createMachCmdLine(mobile)

        for nwIf in mobile.interfaces:
            socketName = subMachDir + "/gw_socket.ctl"
            # create the config file in /tmp and
            # return a line to be added in the command
            outLine = getVMIFOutLine(nwIf, socketName, mobile.name)
            if (outLine):
                command += "%s " % outLine
            else:
                print "[FAILED]"
                return False
        ### ------- execute ---------- ###
        # go to the Mach directory to execute the command
        makeDir(options.machDir+"/"+mobile.name)
        os.chdir(options.machDir+"/"+mobile.name)
        startOut = open("startit.sh", "w")
        startOut.write(command)
        startOut.close()
        os.chmod("startit.sh",0755)
        system("./startit.sh")
        #print command
        print "[OK]"
        os.chdir(oldDir)
    return True

def createVRM(myGINI, options):
    "create REALM config file, and start the REALM"
    makeDir(options.machDir)
    for realm in myGINI.vrm:
        print "Starting REALM %s...\t" % realm.name,
        subMachDir = "%s/%s" % (options.machDir, realm.name)
        makeDir(subMachDir)
        # create command line
        command = createMachCmdLine(realm)
        ### ---- process the Mach interfaces ---- ###
        # it creates one config for each interface in the /tmp/ directory
        # and returns a string to be attached to the Mach exec command line
        for nwIf in realm.interfaces:
            # check whether it is connecting to a switch or router
            socketName = getSocketName(nwIf, realm.name, myGINI, options);
            if (socketName == "fail"):
                print "REALM %s [interface %s]: Target not found" % (realm.name, nwIf.name)
                return False
            else:
                # create the config file in /tmp and
                # return a line to be added in the command
                outLine = getVMIFOutLine(nwIf, socketName, realm.name)
            if (outLine):
                command += "%s " % outLine
            else:
                print "[FAILED]"
                return False
        ### ------- execute ---------- ###
        # go to the Mach directory to execute the command

            oldDir = os.getcwd()
            # os.chdir(subMachDir)
            # startOut = open("startit.sh", "w")
            # startOut.write(command)
            # startOut.close()
            # os.chmod("startit.sh",0755)
            # system("./startit.sh")
            # os.chdir(os.environ["GINI_SHARE"]+"/vgini")
            vtap = "screen -d -m -S %s-vtap vtap" % realm.name
            print vtap
            system(vtap)
            vtproxy = "screen -d -m -S %s-vtproxy vtproxy %s %s %s" % (realm.name, nwIf.ip, nwIf.mac, socketName)
            print vtproxy
            system(vtproxy)
            print "[OK]"
            os.chdir(oldDir)
    return True

def makeDir(dirName):
    "create a directory if not exists"
    if (not os.access(dirName, os.F_OK)):
        os.mkdir(dirName, 0755)
    return



#########################
# TO DELETE
# After making it no use from other functions
#########################

# socket name is defined as:
# for switch: switchDir/switchName/SOCKET_NAME.ctl
# for router: routerDir/routerName/SOCKET_NAME_interfaceName.ctl
# the socket names are fully qualified file names
def getSocketName(nwIf, name, myGINI, options):
    "Get the socket name the interface is connecting to"
    waps = myGINI.vwr
    for wap in waps:
        print wap
        # looking for a match in all waps
        if (wap.name == nwIf.target):
            oldDir = os.getcwd()
            switch_sharing = False
            for i in range(len(nodes)):
                if (nodes[i].find("Mach_")+nodes[i].find("REALM_")) >= 0:
                    switch_sharing = True
                    break
            nodes.append(name)
            if switch_sharing:
                newDir = os.environ["GINI_HOME"] + "/data/mach_virtual_switch/VS_%d" % (i+1)
            else:
                newDir = os.environ["GINI_HOME"] + "/data/mach_virtual_switch/VS_%d" % len(nodes)
                system("mkdir %s" % newDir)
                os.chdir(newDir)
                configOut = open("uswitch.conf", "w")
                configOut.write("logfile uswitch.log\npidfile uswitch.pid\nsocket gw_socket.ctl\nfork\n")
                configOut.close()
                popen("%s -s %s -l uswitch.log -p uswitch.pid &" % (VS_PROG, newDir+"/gw_socket.ctl"))
                os.chdir(oldDir)
            #else:
                #newDir = os.environ["GINI_HOME"] + "/bin/mach_virtual_switch/VS_%d" % len(nodes)
            return newDir + "/gw_socket.ctl"

    routers = myGINI.vr
    for router in routers:
        # looking for a match in all routers
        if (router.name == nwIf.target):
            for remoteNWIf in router.netIF:
                # router matches, looking for a reverse match
                #print remoteNWIf.target, name
                if (remoteNWIf.target == name):
                    # all match create and return the socketname
                    targetDir = getFullyQualifiedDir(options.routerDir)
                    return "%s/%s/%s_%s.ctl" % \
                           (targetDir, router.name, \
                            SOCKET_NAME, remoteNWIf.name)
            # router matches, but reverse match failed
            return "fail"
    switches = myGINI.switches
    for switch in switches:
        if (switch.name == nwIf.target):
            targetDir = getFullyQualifiedDir(options.switchDir)
            return "%s/%s/%s.ctl" % \
                   (targetDir, switch.name, SOCKET_NAME)
    machs = myGINI.vm
    for mach in machs:
        if (mach.name == nwIf.target):
            # target matching a Mach; Mach can't create sockets
            # so return value is socket name of the current router
            targetDir = getFullyQualifiedDir(options.routerDir)
            return "%s/%s/%s_%s.ctl" % \
                   (targetDir, name, SOCKET_NAME, nwIf.name)

    realms = myGINI.vrm
    for realm in realms:
        if (realm.name == nwIf.target):
            targetDir = getFullyQualifiedDir(options.routerDir)
            return "%s/%s/%s_%s.ctl" % \
                       (targetDir, name, SOCKET_NAME, nwIf.name)
    return "fail"

def getFullyQualifiedDir(dirName):
    "get a fully qualified name of a directory"
    targetDir = ""
    if (dirName[0] == '/'):
        # absolute path
        targetDir = dirName
    elif (dirName[0] == '.'):
        # relative to the current path
        if (len(dirName) > 1):
            targetDir = "%s/%s" % (os.getcwd(), dirName[1:])
        else:
            # just current path
            targetDir = os.getcwd()
    else:
        # relative path
        targetDir = "%s/%s" % (os.getcwd(), dirName)
    return targetDir

def getVRIFOutLine(nwIf, intName):
    "convert the router network interface specs into a string"
    outLine = "ifconfig add %s " % intName
    outLine += "-addr %s " % nwIf.ip
    # TODO: address the "no network" attrib in VR IF DTD
    # outLine += "-network %s " % nwIf.network
    outLine += "-hwaddr %s " % nwIf.nic
    # TODO: address the "no gw" attrib in VR IF DTD
    if (nwIf.gw):
        outLine += "-gw %s " % nwIf.gw
    if (nwIf.mtu):
        outLine += "-mtu %s " % nwIf.mtu
    outLine += "\n"
    for route in nwIf.routes:
        outLine += "route add -dev %s " % intName
        outLine += "-net %s " % route.dest
        outLine += "-netmask %s " % route.netmask
        if (route.nexthop):
            outLine += "-gw %s" % route.nexthop
        outLine += "\n"
    return outLine

def getVMIFOutLine(nwIf, socketName, name):
    "convert the Mach network interface specs into a string"
    configFile = "%s/tmp/%s.sh" % (os.environ["GINI_HOME"], nwIf.mac.upper())
    # delete confFile if already exists
    # also checks whether somebody else using the same MAC address
    if (os.access(configFile, os.F_OK)):
        if (os.access(configFile, os.W_OK)):
            os.remove(configFile)
        else:
            print "Can not create config file for %s" % nwIf.name
            print "Probably somebody else is using the same ",
            print "MAC address %s" % nwIf.mac
            return None
    # create the config file
    configOut = open(configFile, "w")
    if nwIf.ip:
        configOut.write("ifconfig %s " % nwIf.name)
        configOut.write("%s " % nwIf.ip)
        for route in nwIf.routes:
            if route.dest:
                configOut.write("\nroute add -%s %s " % (route.type, route.dest))
            configOut.write("netmask %s " % route.netmask)
            if route.gw:
                configOut.write("gw %s" % route.gw)
        configOut.write("\n")
    configOut.write("echo -ne \"\\033]0;" + name + "\\007\"")
    configOut.close()
    os.chmod(configFile, 0777)
    bakDir = "%s/tmp/Mach_bak" % os.environ["GINI_HOME"]
    if not os.access(bakDir, os.F_OK):
        makeDir(bakDir)
    system("cp %s %s" % (configFile, bakDir))
    # prepare the output line
    outLine = "%s=daemon,%s,unix," % (nwIf.name, nwIf.mac)
    outLine += socketName
    return outLine

def createMachCmdLine(mach):
    command = "screen -d -m -S %s " % mach.name
    ## mach binary name
    if (mach.kernel):
        command += "%s " % mach.kernel
    else:
        command += "%s " % VM_PROG_BIN
    ## mach ID
    command += "umid=%s " % mach.name
    ## handle the file system option
    # construct the cow file name
    fileSystemName = getBaseName(mach.fileSystem.name)
    fsCOWName = os.environ["GINI_HOME"] + "/data/" + mach.name + "/" + fileSystemName + ".cow"
    if (mach.fileSystem.type.lower() == "cow"):
        command += "ubd0=%s,%s " % (fsCOWName, os.environ["GINI_SHARE"] + "/filesystem/" + fileSystemName)
    else:
        command += "ubd0=%s " % mach.fileSystem.name
    ## handle the mem option
    if (mach.mem):
        command += "mem=%s " % mach.mem
    ## handle the boot option
    if (mach.boot):
        command += "con0=%s " % mach.boot
    command += "hostfs=%s " % os.environ["GINI_HOME"]
    return command

def getBaseName(pathName):
    "Extract the filename from the full path"
    pathParts = pathName.split("/")
    return pathParts[len(pathParts)-1]

def destroyGINI(myGINI, options):
    result = True

    tapNameMap.clear()
    subnetMap.clear()
    dockerNetworkNameMap.clear()

    try:
        print "\nTerminating Machs..."
        result = result and  destroyVM(myGINI.vm, options.machDir, 0)

        print "\nTerminating routers..."
        result = result and destroyVR(myGINI.vr, options.routerDir)

        print "\nTerminating OpenFlow controllers..."
        result = result and destroyVOFC(myGINI.vofc, options.controllerDir)

        print "\nTerminating switches..."
        result = destroyVS(myGINI.switches, options.switchDir)
    except:
        pass

#    print "\nTerminating wireless access points..."
#    try:
#        result = result and destroyVWR(myGINI.vwr, options.routerDir)
#    except:
#        pass

#    print "\nTerminating Mobiles..."
#    try:
#        result = result and  destroyVM(myGINI.vmb, options.machDir, 1)
#    except:
#        pass

#    print "\nTerminating REALMs..."
#    try:
#        result = result and  destroyRVM(myGINI.vrm, options.machDir)
#    except:
#        pass
    #system("killall uswitch screen")
    return result


def destroyVS(switches, switchDir):
    for switch in switches:
        print "Stopping Switch %s..." % switch.name
        command = "%s/%s/stopit.sh" % (switchDir, switch.name)
        system(command)
    return True

def destroyVWR(wrouters, routerDir):
    for wrouter in wrouters:
        print "Stopping Router %s..." % wrouter.name
        subRouterDir = "%s/%s" % (routerDir, wrouter.name)
        wrouter.num = wrouter.name.split("Wireless_access_point_")[-1]
        system("screen -S %s -X eval quit" % ("WAP_%s" % wrouter.num))
        system("screen -S %s -X eval quit" % ("VWAP_%s" % wrouter.num))
        print "\tCleaning the directory...\t",
        try:
            os.remove(subRouterDir+"/wrouter.conf")
            #os.remove(subRouterDir+"/startit.sh")
            while os.access(subRouterDir+"/wrouter.conf", os.F_OK):
                pass
            os.rmdir(subRouterDir)
            print "[OK]"
        except:

            print "failed"
            return False

        oldDir = os.getcwd()
        switchDir = "%s/data/mach_virtual_switch" % os.environ["GINI_HOME"]
        os.chdir(switchDir)
        for filename in os.listdir(switchDir):
            pidfile = filename+"/uswitch.pid"
            if os.access(pidfile, os.F_OK):
                pidIn = open(pidfile)
                line = pidIn.readline().strip()
                pidIn.close()
                os.kill(int(line), signal.SIGTERM)
            while os.access("gw_socket.ctl", os.F_OK):
                time.sleep(0.5)
            system("rm -rf %s" % filename)

        os.chdir(oldDir)
    return True

def destroyVR(routers, routerDir):
    for router in routers:
        print "Stopping Router %s..." % router.name
        # get the pid file
        print "\tCleaning the PID file...\t",
        subRouterDir = "%s/%s" % (routerDir, router.name)
        pidFile = "%s/%s.pid" % (subRouterDir, router.name)
        # check the validity of the pid file
        pidFileFound = True
        if (os.access(pidFile, os.R_OK)):
            # kill the router
            # routerPID = getPIDFromFile(pidFile)
            # os.kill(routerPID, signal.SIGTERM)
            command = "screen -S %s -X quit" % router.name
            system(command)
        else:
            pidFileFound = False
            print "[FAILED]"
        system("%s/stopit.sh" % subRouterDir)


        # clean up the files in the directory
        print "\tCleaning the directory...\t",
#        if (os.access(subRouterDir, os.F_OK)):
#            for file in os.listdir(subRouterDir):
#                fileName = "%s/%s" % (subRouterDir, file)
#                if (os.access(fileName, os.W_OK)):
#                    os.remove(fileName)
#                else:
#                    print "\n\tRouter %s: Could not delete file %s" % (router.name, fileName)
#                    print "\tCheck your directory"
#                    return False
#            if (os.access(subRouterDir, os.W_OK)):
#                os.rmdir(subRouterDir)
#            else:
#                print "\n\tRouter %s: Could not remove router directory" % router.name
#                print "\tCheck your directory"
#                return False
#        print "[OK]"
#        if (pidFileFound):
#            print "\tStopping Router %s...\t[OK]" % router.name
#        else:
#            print "\tStopping Router %s...\t[FAILED]" % router.name
#            print "\tKill the router %s manually" % router.name

    return True

def getPIDFromFile(fileName):
    fileIn = open(fileName)
    lines = fileIn.readlines()
    fileIn.close()
    return int(lines[0].strip())

def destroyRVM(machs,machDir):
    for mach in machs:
        print "\tStopping REALM %s...\t[OK]" % mach.name
        system("screen -S " + mach.name + "-vtap -p 0 -X stuff \"quitt\n\"")
        system("screen -S " + mach.name + "-vtproxy -X quit")
        print "\tCleaning the directory...\t",
        subMachDir = "%s/%s" % (machDir, mach.name)

        # TODO: Determine if we need any data in this folder.
        if (os.access(subMachDir, os.F_OK)):
            for file in os.listdir(subMachDir):
                fileName = "%s/%s" % (subMachDir, file)
                if (os.access(fileName, os.W_OK)):
                    os.remove(fileName)
                else:
                    print "\n\tCould not delete file %s" % (mach.name, fileName)
                    print "\tCheck your directory"
                    return False
            if (os.access(subMachDir, os.W_OK)):
                 os.rmdir(subMachDir)
        print "[OK]"
        for nwIf in mach.interfaces:
            configFile = "%s/tmp/%s.sh" % (os.environ["GINI_HOME"],nwIf.mac.upper())
            if (os.access(configFile, os.W_OK)):
                os.remove(configFile)
    return True

def destroyVM(machs, machDir, mode):

    for mach in machs:
        # Run the stop command
        command = "%s/%s/stopit.sh" % (machDir, mach.name)
        system(command)
    return True

def destroyVOFC(controllers, controllerDir):
    for controller in controllers:
        print "Stopping OpenFlow controller %s..." % controller.name
        # get the pid file
        print "\tCleaning the PID file...\t",
        subControllerDir = "%s/%s" % (controllerDir, controller.name)
        pidFile = "%s/%s.pid" % (subControllerDir, controller.name)
        # check the validity of the pid file
        pidFileFound = True
        if (os.access(pidFile, os.R_OK)):
            # kill the controller
            command = "screen -S %s -X quit" % controller.name
            system(command)
            command = "kill -9 `cat %s`" % pidFile
            system(command)
        else:
            pidFileFound = False
            print "[FAILED]"

        print "\tCleaning the directory...\t",
        if (os.access(subControllerDir, os.F_OK)):
            for file in os.listdir(subControllerDir):
                fileName = "%s/%s" % (subControllerDir, file)
                if (os.access(fileName, os.W_OK)):
                    os.remove(fileName)
                else:
                    print "\n\OpenFlow controller %s: Could not delete file %s" % (controller.name, fileName)
                    print "\tCheck your directory"
                    return False
            if (os.access(subControllerDir, os.W_OK)):
                os.rmdir(subControllerDir)
            else:
                print "\n\OpenFlow controller %s: Could not remove directory" % controller.name
                print "\tCheck your directory"
                return False
        print "[OK]"
        if (pidFileFound):
            print "\tStopping OpenFlow controller %s...\t[OK]" % controller.name
        else:
            print "\tStopping OpenFlow controller %s...\t[FAILED]" % controller.name
            print "\tKill the controller %s manually" % controller.name
    return True

def checkProcAlive(procName):
    alive = False
    # grep the Mach processes
    system("pidof -x %s > %s" % (procName, GINI_TMP_FILE))
    inFile = open(GINI_TMP_FILE)
    line = inFile.readline()
    inFile.close()
    if not line:
        return False
    else:
        procs = line.split()

    for proc in procs:
        system("ps aux | grep %s > %s" % (proc, GINI_TMP_FILE))
        inFile = open(GINI_TMP_FILE)
        lines = inFile.readlines()
        inFile.close()
        for line in lines:
            if line.find("grep") >= 0:
                continue
            if line.find(os.getenv("USER")) >= 0:
                return True

    os.remove(GINI_TMP_FILE)
    return alive

def writeSrcFile(options):
    "write the configuration in the setup file"
    outFile = open(SRC_FILENAME, "w")
    outFile.write("%s\n" % options.xmlFile)
    outFile.write("%s\n" % options.switchDir)
    outFile.write("%s\n" % options.routerDir)
    outFile.write("%s\n" % options.machDir)
    outFile.write("%s\n" % options.binDir)
    outFile.write("%s\n" % options.controllerDir)
    outFile.close()

def deleteSrcFile():
    "delete the setup file"
    if (os.access(SRC_FILENAME, os.W_OK)):
        os.remove(SRC_FILENAME)
    else:
        print "Could not delete the GINI setup file"

def checkAliveGini():
    "check any of the gini components already running"
    result = False
    if checkProcAlive(VS_PROG_BIN):
        print "At least one of %s is alive" % VS_PROG_BIN
        result = True
    if checkProcAlive(VM_PROG_BIN):
        print "At least one of %s is alive" % VM_PROG_BIN
        result = True
    if checkProcAlive(GR_PROG_BIN):
        print "At least one of %s is alive" % GR_PROG_BIN
        result = True
    if checkProcAlive(VOFC_PROG_BIN):
        print "At least one of %s is alive" % VOFC_PROG_BIN
        result = True
    return result


#### -------------- MAIN start ----------------####

# create the program processor. This
# 1. accepts and process the command line options
# 2. creates XML processing engine, that in turn
#    a) validates the XML file
#    b) extracts the DOM object tree
#    c) populates the GINI network class library
#    d) performs some semantic/syntax checkings on
#       the extracted specification
myProg = Program(sys.argv[0], SRC_FILENAME)
if (not myProg.processOptions(sys.argv[1:])):
    sys.exit(1)
options = myProg.options

# set the Mach directory if is not given via -u option
if (not options.machDir):
    # set it to the directory pointed by the $Mach_DIR env
    # if no such env variable, set the mach dir to curr dir
    if (os.environ.has_key("Mach_DIR")):
        options.machDir = os.environ["Mach_DIR"]
    else:
        options.machDir = "."

# get the binaries
binDir = options.binDir
if (binDir):
    # get the absolute path for binary directory
    if (binDir[len(binDir)-1] == "/"):
        binDir = binDir[:len(binDir)-1]
    binDir = getFullyQualifiedDir(binDir)
    # assign binary names
    # if the programs are not in the specified binDir
    # they will be assumed to be in the $PATH env.
    VS_PROG_BIN = "%s/%s" % (binDir, VS_PROG)
    if (not os.access(VS_PROG_BIN, os.X_OK)):
        VS_PROG_BIN = VS_PROG
    VM_PROG_BIN = "%s/%s" % (binDir, VM_PROG)
    if (not os.access(VM_PROG_BIN, os.X_OK)):
        VM_PROG_BIN = VM_PROG
    GR_PROG_BIN = "%s/%s" % (binDir, GR_PROG)
    if (not os.access(GR_PROG_BIN, os.X_OK)):
        GR_PROG_BIN = GR_PROG
    MCONSOLE_PROG_BIN = "%s/%s" % (binDir, MCONSOLE_PROG)
    if (not os.access(MCONSOLE_PROG_BIN, os.X_OK)):
        MCONSOLE_PROG_BIN = MCONSOLE_PROG
    VOFC_PROG_BIN = "%s/%s" % (binDir, VOFC_PROG)
    if (not os.access(VOFC_PROG_BIN, os.X_OK)):
        VOFC_PROG_BIN = VOFC_PROG

# get the populated GINI network class
# its structure is the same as the XML specification
myGINI = myProg.giniNW

# create or terminate GINI network
print ""
if (myProg.destroyOpt):
    # terminate the current running specification
    print "Terminating GINI network..."
    success = destroyGINI(myGINI, options)
    if (success):
        print "\nGINI network is terminated!!\n"
    else:
        print "\nThere are errors in GINI network termination\n"
        sys.exit(1)
else:
    # create the GINI instance
    if (not options.keepOld):
        # fail if a GINI already alive
        if checkAliveGini():
            print "\nA Gini is already running"
            print "Terminate it before running another one\n"
            sys.exit(1)

    if not os.environ.has_key("GINI_HOME"):
        print "environment variable $GINI_HOME not set, please set it for GINI to run properly"
        sys.exit(1)

    # create network with current specifcation
    print "Creating GINI network..."
    success = startGINI(myGINI, options)
    writeSrcFile(options)
    if (success):
        print "\nGINI network up and running!!\n"
    else:
        print "\nGINI network start failed!!\n"
