#!/usr/bin/python2

# Revised by Daniel Ng
# Revised to Docker version by Mahesh

import sys
import os
import time
import subprocess
import socket
import json

from program import Program

# set the program names
VIRTUAL_SWITCH_PROGRAM = "uswitch"
OPEN_VIRTUAL_SWITCH_PROGRAM = "gvirtual-switch"
VIRTUAL_MACHINE_PROGRAM = "glinux"
GROUTER_PROGRAM = "grouter"
OPENFLOW_CONTROLLER_PROGRAM = "gpox"
GWIRELESS_ROUTER_PROGRAM = "gwcenter.sh"
MACHINE_CONSOLE_PROGRAM = "mach_mconsole"
SOCKET_NAME = "gini_socket"
VIRTUAL_SWITCH_PROGRAM_BIN = VIRTUAL_SWITCH_PROGRAM
OPEN_VIRTUAL_SWITCH_PROGRAM_BIN = OPEN_VIRTUAL_SWITCH_PROGRAM
VIRTUAL_MACHINE_PROGRAM_BIN = VIRTUAL_MACHINE_PROGRAM
GROUTER_PROGRAM_BIN = GROUTER_PROGRAM
OPENFLOW_CONTROLLER_PROGRAM_BIN = OPENFLOW_CONTROLLER_PROGRAM
GWIRELESS_ROUTER_PROGRAM_BIN = GWIRELESS_ROUTER_PROGRAM
MACHINE_CONSOLE_PROGRAM_BIN = MACHINE_CONSOLE_PROGRAM
SOURCE_FILE_NAME = "%s/gini_setup" % os.environ["GINI_HOME"]    # setup file name
GINI_TEMP_DIR = "%s/tmp/" % os.environ["GINI_HOME"]
GINI_TEMP_FILE = ".gini_tmp_file"    # tmp file used when checking alive Mach
nodes = []
tap_interface_names_map = dict()
subnet_map = dict()
network_name_map = dict()

# set this switch True if running gloader without gbuilder
independent = False


def system(command):
    subprocess.call(["/bin/bash", "-c", command])


def popen(command):
    subprocess.Popen(["/bin/bash", "-c", command])


def start_GINI(gini, opts):
    """Start the GINI network components"""
    # the starting order is important here
    # first switches, then routers, and at last Machs.
    print "\nStarting Switches..."
    status = create_virtual_switches(gini, opts.switchDir)
    print "\nStarting OpenFlow controllers..."
    status = status and create_open_flow_controllers(gini, opts)
    print "\nStarting GINI routers..."
    status = status and create_virtual_routers(gini, opts)
    print "\nStarting Docker Machines..."
    status = status and create_virtual_machines(gini, opts)

    if not status:
        print "Problem in creating GINI network"
        print "Terminating the partially started network (if any)"
        destroy_GINI(gini, opts)
    return status


def find_subnet_for_switch(gini, switch_name):
    # Search the VMs for a matching target
    for mach in gini.vm:
        for netif in mach.interfaces:
            if netif.target == switch_name:
                return netif.network

    # Search the Routers for a matching target
    for vr in gini.vr:
        for nif in vr.netIF:
            if nif.target == switch_name:
                return nif.network

    return ""


def create_open_virtual_switches(gini, switch_dir, switch):
    print "\tStarting %s...\t" % switch.name,
    sub_switch_dir = switch_dir + "/" + switch.name
    make_dir(sub_switch_dir)
    old_dir = os.getcwd()
    os.chdir(sub_switch_dir)

    undo_file = "%s/stopit.sh" % sub_switch_dir
    undo_out = open(undo_file, "w")
    undo_out.write("#!/bin/bash\n\n")

    subnet = find_subnet_for_switch(gini, switch.name)
    if subnet != "":
        if subnet_map.get(subnet):
            network_name_map[switch.name] = subnet_map[subnet]
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
        startup_commands += "ovs-vsctl set-fail-mode %s standalone &&\n" % switch.name
        start_out.write(startup_commands)

        screen_command = "screen -d -m -L -S %s " % switch.name
        screen_command += "%s %s\n" % (OPEN_VIRTUAL_SWITCH_PROGRAM, switch.name)
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
            subnet_map[subnet] = switch.name
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


def create_virtual_switches(gini, switch_dir):
    """create the switch config file and start the switch"""
    # create the main switch directory
    make_dir(switch_dir)

    for switch in gini.switches:
        if switch.isOVS:
            if create_open_virtual_switches(gini, switch_dir, switch):
                continue
            else:
                print "[Failed] Error when creating Open virtual switch"
                return False

        print "\tStarting %s...\t" % switch.name,
        subSwitchDir = switch_dir + "/" + switch.name
        make_dir(subSwitchDir)
        undoFile = "%s/stopit.sh" % subSwitchDir
        undoOut = open(undoFile, "w")
        undoOut.write("#!/bin/bash\n")

        subnet = find_subnet_for_switch(gini, switch.name)
        if subnet != "":
            # Check if the network is already created under another switch name
            if subnet_map.get(subnet):
                network_name_map[switch.name] = subnet_map[subnet]
                os.chmod(undoFile, 0755)
                undoOut.close()
                continue

            command = "docker network create %s --subnet %s/24" % (switch.name, subnet)
            runcmd = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
            out, err = runcmd.communicate()
            if runcmd.returncode == 0:

                subnet_map[subnet] = switch.name
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
                out, err = q.communicate()
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


def find_hidden_switch(router_name, switch_name):
    x, rnum = router_name.split("_")
    x, snum = switch_name.split("_")
    if x != "Router":
        switch_name = "Switch_r%sm%s" % (rnum, snum)
    else:
        switch_name = "Switch_r%sr%s" % (rnum, snum)

    command = """docker network inspect %s --format='{{.Id}}'""" % switch_name
    q = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
    q.communicate()
    if q.returncode == 0:
        return switch_name
    else:
        return None


def find_bridge_name(switch_name):
    if switch_name.split("_")[0] == "Switch":
        command = "docker network inspect %s --format='{{.Id}}'" % switch_name
        is_ovs = False
    else:
        command = "ovs-ofctl show %s" % switch_name
        is_ovs = True

    q = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
    out, err = q.communicate()

    if q.returncode == 0:
        if is_ovs:
            return switch_name, is_ovs
        else:
            return "br-" + out[:12], is_ovs
    else:
        return None, None


def create_new_switch(router_name, switch_name, subnet, out_file):
    x, router_num = router_name.split("_")
    x, switch_num = switch_name.split("_")
    if x != "Router":
        switch_name = "Switch_r%sm%s" % (router_num, switch_num)
    else:
        switch_name = "Switch_r%sr%s" % (router_num, switch_num)

    # Similar to switch_name devices, check if the network is already created under another name
    if subnet_map.get(subnet):
        network_name_map[switch_name] = subnet_map[subnet]
        switch_name = subnet_map[subnet]

        command = "docker network inspect %s --format='{{.Id}}'" % switch_name
        q = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
        out, err = q.communicate()
        if q.returncode == 0:
            brname = "br-" + out[:12]
            return switch_name, brname

    command = "docker network create %s --subnet %s/24" % (switch_name, subnet)
    q = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
    out, err = q.communicate()
    if q.returncode == 0:
        subnet_map[subnet] = switch_name

        brname = "br-" + out[:12]
        out_file.write(
            """for i in ` docker network inspect -f '{{range .Containers}}{{.Name}} {{end}}' %s`;
            do
            docker network disconnect -f %s $i;
            done;
            """ % (out, out)
        )
        out_file.write("docker network remove %s" % out)
        return switch_name, brname
    else:
        command = """docker network inspect %s --format='{{.Id}}'""" % switch_name
        q = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
        out, err = q.communicate()
        if q.returncode == 0:
            brname = "br-" + out[:12]
            out_file.write(
                """for i in ` docker network inspect -f '{{range .Containers}}{{.Name}} {{end}}' %s`;
                do
                docker network disconnect -f %s $i;
                done;
                """ % (out, out)
            )
            out_file.write("\ndocker network remove %s\n" % out)
            return switch_name, brname
        return None, None


def set_up_tap_interface(router_name, switch_name, bridge_name, out_file, is_ovs=False):
    # This assumes that the iproute2 (ip) utils work without
    # sudo - you need to turn on the setuid bit
    x, router_num = router_name.split("_")
    x, switch_num = switch_name.split("_")

    target_mode = {
        "Mach": "m",
        "Router": "r",
        "Switch": "s",
        "OVSwitch": "o"
    }

    tap_key = "Switch_r%s%s%s" % (router_num, target_mode[x], switch_num)
    if tap_interface_names_map.get(tap_key) is None:
        tap_interface_names_map[tap_key] = "tap" + str(len(tap_interface_names_map) + 1)
    tap_name = tap_interface_names_map[tap_key]

    command_to_execute = "ip tuntap add mode tap dev %s &&\n" % tap_name
    command_to_execute += "ip link set %s up &&\n" % tap_name
    if is_ovs:
        command_to_execute += "ovs-vsctl add-port %s %s" % (bridge_name, tap_name)
    else:
        command_to_execute += "brctl addif %s %s" % (bridge_name, tap_name)

    create_tap_process = subprocess.Popen(command_to_execute, shell=True, stdout=subprocess.PIPE)
    create_tap_process.wait()
    if create_tap_process.returncode == 0:
        out_file.write("\nip link del %s\n" % tap_name)
        return tap_name
    else:
        return None


def create_virtual_routers(gini, opts):
    """Create router config file, and start the router"""
    routerDir = opts.routerDir
    # create the main router directory
    make_dir(routerDir)
    for router in gini.vr:
        print "\tStarting %s...\t" % router.name,
        sys.stdout.flush()
        # name the config file
        subRouterDir = "%s/%s" % (routerDir, router.name)
        make_dir(subRouterDir)
        # go to the router directory to execute the command
        oldDir = os.getcwd()
        os.chdir(subRouterDir)
        configFile = "%s.conf" % GROUTER_PROGRAM
        # delete confFile if already exists
        if os.access(configFile, os.F_OK):
            os.remove(configFile)
        # create the config file
        configOut = open(configFile, "w")
        stopOut = open("stopit.sh", "w")
        stopOut.write("#!/bin/bash\n")

        interfaces_map = dict()

        for nwIf in router.netIF:
            target_name = nwIf.target
            switch = check_switch(gini, target_name)
            if not switch:
                interface_name = "%s - %s" % (router.name, target_name)
                # Router could be connected to a machine
                if check_router(gini, target_name):
                    print "It is a router at the other end."
                    # Check whether the other router has already created the hidden switch
                    # If so, this router can just tap into it
                    x, rnum = router.name.split("_")
                    x, snum = target_name.split("_")
                    scheck = "Switch_r%sr%s" % (snum, rnum)
                    bridge_name, is_ovs = find_bridge_name(scheck)
                    if bridge_name is None:
                        switch_name, bridge_name = create_new_switch(router.name, target_name, nwIf.network, stopOut)
                        if target_name is None:
                            print "[Failed]"
                            return False
                else:
                    # We are connected to a machine
                    switch_name, bridge_name = create_new_switch(router.name, target_name, nwIf.network, stopOut)
                    if target_name is None:
                        print "[Failed]"
                        return False
                is_ovs = False
            else:
                bridge_name, is_ovs = find_bridge_name(target_name)
                interface_name = target_name
                is_ovs = switch.isOVS
            tapname = set_up_tap_interface(router.name, target_name, bridge_name, stopOut, is_ovs)
            if tapname is None:
                print "[Failed]"
                print "\nRouter %s: unable to create tap interface" % router.name
                return False
            else:
                configOut.write(get_virtual_router_interface_outline(nwIf, tapname))
                interfaces_map[interface_name] = bridge_name
        configOut.write("echo -ne \"\\033]0;" + router.name + "\\007\"")
        configOut.close()
        stopOut.close()
        ### ------- commands to execute ---------- ###
        command = "screen -d -m -L -S %s %s " % (router.name, GROUTER_PROGRAM_BIN)
        command += "--config=%s.conf " % GROUTER_PROGRAM
        command += "--confpath=" + os.environ["GINI_HOME"] + "/data/" + router.name + " "
        command += "--interactive=1 "
        command += "%s" % router.name

        startOut = open("startit.sh", "w")
        startOut.write(command)
        startOut.close()
        os.chmod("startit.sh", 0755)
        os.chmod("stopit.sh", 0755)

        system("./startit.sh")

        # Write switch names and the corresponding bridges for Wireshark
        router_tmp_file = GINI_TEMP_DIR + router.name + ".json"
        with open(router_tmp_file, "w") as f:
            f.write(json.dumps(interfaces_map, sort_keys=True, indent=2))

        print "[OK]"
        os.chdir(oldDir)

    return True


def get_network_name(switch_name):
    if network_name_map.get(switch_name):
        return network_name_map[switch_name]
    else:
        return switch_name


def check_switch(gini, switch_name):
    for switch in gini.switches:
        if switch.name == switch_name:
            return switch
    return None


def check_router(gini, router_name):
    for router in gini.vr:
        if router.name == router_name:
            return router
    return None


def get_switch_to_connect(gini, machine):
    # one of the interfaces is
    for nwi in machine.interfaces:
        target = nwi.target
        if check_switch(gini, target):
            return get_network_name(target), nwi.ip

    for nwi in machine.interfaces:
        target = nwi.target
        if check_router(gini, target):
            # create a 'hidden' switch because docker needs a
            # switch to connect to the router
            swname = find_hidden_switch(target, machine.name)
            return get_network_name(swname), nwi.ip

    return None, None


def create_virtual_machines(gini, opts):
    """create Mach config file, and start the Mach"""
    make_dir(opts.machDir)
    for mach in gini.vm:
        print "\tStarting %s...\t" % mach.name,
        subMachDir = "%s/%s" % (opts.machDir, mach.name)
        make_dir(subMachDir)

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
            # end each route
        # end each interface

        stopOut = open("stopit.sh", "w")
        stopOut.write("#!/bin/bash\n")
        # Get switch to connect
        sname, ip = get_switch_to_connect(gini, mach)

        # Export command prompt for VM, start shell inside docker container
        startOut.write("\nexport PS1='root@%s >> '\n" % ip)
        startOut.write("/bin/ash\n")
        startOut.close()
        os.chmod("entrypoint.sh", 0755)

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

            runcmd = subprocess.Popen(baseScreenCommand + command, shell=True, stdout=subprocess.PIPE)
            runcmd.communicate()

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
        os.chmod("stopit.sh", 0755)
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


def create_open_flow_controllers(gini, opts):
    """Create OpenFlow controller config file, and start the OpenFlow controller"""
    make_dir(opts.controllerDir)
    for controller in gini.vofc:
        print "\tStarting OpenFlow controller %s...\t" % controller.name,
        subControllerDir = "%s/%s" % (opts.controllerDir, controller.name)
        make_dir(subControllerDir)

        port = find_available_port(6633, 6653)
        if port == -1:
            print "[FAILED] Cannot find an unused port"
            return False

        vofcFlags = "py "
        vofcFlags += "openflow.of_01 --address=0.0.0.0 --port=%d " % port
        vofcFlags += "gini.core.forwarding_l2_pairs "
        vofcFlags += "gini.support.gini_pid --pid_file_path='%s/%s/%s.pid' " % (opts.controllerDir, controller.name, controller.name)
        vofcFlags += "gini.support.gini_module_load --module_file_path='%s/%s/%s.modules' " % (opts.controllerDir, controller.name, controller.name)

        command = "screen -d -m -L -S %s %s %s\n\n" % (controller.name, OPENFLOW_CONTROLLER_PROGRAM_BIN, vofcFlags)

        connect_commands = ""
        for ovs in controller.open_virtual_switches:
            connect_commands += "ovs-vsctl set-controller %s tcp:0.0.0.0:%d\n" % (ovs, port)

        old_dir = os.getcwd()
        os.chdir(subControllerDir)
        startOut = open("startit.sh", "w")
        startOut.write(command)
        startOut.write(connect_commands)
        startOut.close()
        os.chmod("startit.sh", 0755)
        system("./startit.sh")
        os.chdir(old_dir)
        print "[OK]"
    return True


def make_dir(dir_name):
    """create a directory if not exists"""
    if not os.access(dir_name, os.F_OK):
        os.mkdir(dir_name, 0755)
    return


# socket name is defined as:
# for switch: switchDir/switchName/SOCKET_NAME.ctl
# for router: routerDir/routerName/SOCKET_NAME_interfaceName.ctl
# the socket names are fully qualified file names
def get_socket_name(network_interface, name, gini, opts):
    """Get the socket name the interface is connecting to"""
    # waps = gini.vwr
    # for wap in waps:
    #     print wap
    #     # looking for a match in all waps
    #     if wap.name == network_interface.target:
    #         oldDir = os.getcwd()
    #         switch_sharing = False
    #         for i in range(len(nodes)):
    #             if (nodes[i].find("Mach_")+nodes[i].find("REALM_")) >= 0:
    #                 switch_sharing = True
    #                 break
    #         nodes.append(name)
    #         if switch_sharing:
    #             newDir = os.environ["GINI_HOME"] + "/data/mach_virtual_switch/VS_%d" % (i+1)
    #         else:
    #             newDir = os.environ["GINI_HOME"] + "/data/mach_virtual_switch/VS_%d" % len(nodes)
    #             system("mkdir %s" % newDir)
    #             os.chdir(newDir)
    #             configOut = open("uswitch.conf", "w")
    #             configOut.write("logfile uswitch.log\npidfile uswitch.pid\nsocket gw_socket.ctl\nfork\n")
    #             configOut.close()
    #             popen("%s -s %s -l uswitch.log -p uswitch.pid &" % (VIRTUAL_SWITCH_PROGRAM, newDir + "/gw_socket.ctl"))
    #             os.chdir(oldDir)
    #         return newDir + "/gw_socket.ctl"

    routers = gini.vr
    for router in routers:
        # looking for a match in all routers
        if router.name == network_interface.target:
            for remoteNWIf in router.netIF:
                # router matches, looking for a reverse match
                # print remoteNWIf.target, name
                if remoteNWIf.target == name:
                    # all match create and return the socket name
                    targetDir = get_fully_qualified_dir(opts.routerDir)
                    return "%s/%s/%s_%s.ctl" % \
                           (targetDir, router.name,
                            SOCKET_NAME, remoteNWIf.name)
            # router matches, but reverse match failed
            return "fail"
    switches = gini.switches
    for switch in switches:
        if switch.name == network_interface.target:
            targetDir = get_fully_qualified_dir(opts.switchDir)
            return "%s/%s/%s.ctl" % \
                   (targetDir, switch.name, SOCKET_NAME)
    machs = gini.vm
    for mach in machs:
        if mach.name == network_interface.target:
            # target matching a Mach; Mach can't create sockets
            # so return value is socket name of the current router
            targetDir = get_fully_qualified_dir(opts.routerDir)
            return "%s/%s/%s_%s.ctl" % \
                   (targetDir, name, SOCKET_NAME, network_interface.name)

    return "fail"


def get_fully_qualified_dir(dir_name):
    """Get a fully qualified name of a directory"""
    if dir_name[0] == '/':
        # absolute path
        target_dir = dir_name
    elif dir_name[0] == '.':
        # relative to the current path
        if len(dir_name) > 1:
            target_dir = "%s/%s" % (os.getcwd(), dir_name[1:])
        else:
            # just current path
            target_dir = os.getcwd()
    else:
        # relative path
        target_dir = "%s/%s" % (os.getcwd(), dir_name)
    return target_dir


def get_virtual_router_interface_outline(network_interface, interface_name):
    """Convert the router network interface specs into a string"""
    outLine = "ifconfig add %s " % interface_name
    outLine += "-addr %s " % network_interface.ip
    # TODO: address the "no network" attrib in VR IF DTD
    # outLine += "-network %s " % network_interface.network
    outLine += "-hwaddr %s " % network_interface.nic
    # TODO: address the "no gw" attrib in VR IF DTD
    if network_interface.gw:
        outLine += "-gw %s " % network_interface.gw
    if network_interface.mtu:
        outLine += "-mtu %s " % network_interface.mtu
    outLine += "\n"
    for route in network_interface.routes:
        outLine += "route add -dev %s " % interface_name
        outLine += "-net %s " % route.dest
        outLine += "-netmask %s " % route.netmask
        if route.nexthop:
            outLine += "-gw %s" % route.nexthop
        outLine += "\n"
    return outLine


def get_virtual_machine_interface_outline(network_interface, socketName, name):
    """convert the Mach network interface specs into a string"""
    configFile = "%s/tmp/%s.sh" % (os.environ["GINI_HOME"], network_interface.mac.upper())
    # delete confFile if already exists
    # also checks whether somebody else using the same MAC address
    if os.access(configFile, os.F_OK):
        if os.access(configFile, os.W_OK):
            os.remove(configFile)
        else:
            print "Can not create config file for %s" % network_interface.name
            print "Probably somebody else is using the same ",
            print "MAC address %s" % network_interface.mac
            return None
    # create the config file
    configOut = open(configFile, "w")
    if network_interface.ip:
        configOut.write("ifconfig %s " % network_interface.name)
        configOut.write("%s " % network_interface.ip)
        for route in network_interface.routes:
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
        make_dir(bakDir)
    system("cp %s %s" % (configFile, bakDir))
    # prepare the output line
    outLine = "%s=daemon,%s,unix," % (network_interface.name, network_interface.mac)
    outLine += socketName
    return outLine


def create_machine_command_line(machine):
    command = "screen -d -m -S %s " % machine.name
    ## machine binary name
    if machine.kernel:
        command += "%s " % machine.kernel
    else:
        command += "%s " % VIRTUAL_MACHINE_PROGRAM_BIN
    ## machine ID
    command += "umid=%s " % machine.name
    ## handle the file system option
    # construct the cow file name
    fileSystemName = get_base_name(machine.fileSystem.name)
    fsCOWName = os.environ["GINI_HOME"] + "/data/" + machine.name + "/" + fileSystemName + ".cow"
    if machine.fileSystem.type.lower() == "cow":
        command += "ubd0=%s,%s " % (fsCOWName, os.environ["GINI_SHARE"] + "/filesystem/" + fileSystemName)
    else:
        command += "ubd0=%s " % machine.fileSystem.name
    ## handle the mem option
    if machine.mem:
        command += "mem=%s " % machine.mem
    ## handle the boot option
    if machine.boot:
        command += "con0=%s " % machine.boot
    command += "hostfs=%s " % os.environ["GINI_HOME"]
    return command


def get_base_name(path_name):
    """Extract the filename from the full path"""
    path_parts = path_name.split("/")
    return path_parts[-1]


def destroy_GINI(gini, opts):
    result = True

    tap_interface_names_map.clear()
    subnet_map.clear()
    network_name_map.clear()

    try:
        print "\nTerminating Machs..."
        result = result and destroy_virtual_machines(gini.vm, opts.machDir, 0)

        print "\nTerminating routers..."
        result = result and destroy_virtual_routers(gini.vr, opts.routerDir)

        print "\nTerminating OpenFlow controllers..."
        result = result and destroy_openflow_controllers(gini.vofc, opts.controllerDir)

        print "\nTerminating switches..."
        result = destroy_virtual_switches(gini.switches, opts.switchDir)
    except:
        result = False
    finally:
        return result


def destroy_virtual_switches(switches, switch_dir):
    for switch in switches:
        print "Stopping Switch %s..." % switch.name
        command = "%s/%s/stopit.sh" % (switch_dir, switch.name)
        system(command)
    return True


def destroy_virtual_routers(routers, router_dir):
    for router in routers:
        print "Stopping Router %s..." % router.name
        # get the pid file
        print "\tCleaning the PID file...\t",
        subRouterDir = "%s/%s" % (router_dir, router.name)
        pidFile = "%s/%s.pid" % (subRouterDir, router.name)
        # check the validity of the pid file
        pid_file_found = True
        if os.access(pidFile, os.R_OK):
            # kill the router
            # routerPID = get_pid_from_file(pidFile)
            # os.kill(routerPID, signal.SIGTERM)
            command = "screen -S %s -X quit" % router.name
            system(command)
        else:
            pid_file_found = False
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


def get_pid_from_file(file_name):
    file_in = open(file_name)
    lines = file_in.readlines()
    file_in.close()
    return int(lines[0].strip())


def destroy_virtual_machines(machs, machine_dir, mode):
    for mach in machs:
        # Run the stop command
        command = "%s/%s/stopit.sh" % (machine_dir, mach.name)
        system(command)
    return True


def destroy_openflow_controllers(controllers, controller_dir):
    for controller in controllers:
        print "Stopping OpenFlow controller %s..." % controller.name
        # get the pid file
        print "\tCleaning the PID file...\t",
        subControllerDir = "%s/%s" % (controller_dir, controller.name)
        pidFile = "%s/%s.pid" % (subControllerDir, controller.name)
        # check the validity of the pid file
        pidFileFound = True
        if os.access(pidFile, os.R_OK):
            # kill the controller
            command = "screen -S %s -X quit" % controller.name
            system(command)
            command = "kill -9 `cat %s`" % pidFile
            system(command)
        else:
            pidFileFound = False
            print "[FAILED]"

        print "\tCleaning the directory...\t",
        if os.access(subControllerDir, os.F_OK):
            for f in os.listdir(subControllerDir):
                fileName = "%s/%s" % (subControllerDir, f)
                if os.access(fileName, os.W_OK):
                    os.remove(fileName)
                else:
                    print "\nOpenFlow controller %s: Could not delete file %s" % (controller.name, fileName)
                    print "\tCheck your directory"
                    return False
            if os.access(subControllerDir, os.W_OK):
                os.rmdir(subControllerDir)
            else:
                print "\nOpenFlow controller %s: Could not remove directory" % controller.name
                print "\tCheck your directory"
                return False
        print "[OK]"
        if pidFileFound:
            print "\tStopping OpenFlow controller %s...\t[OK]" % controller.name
        else:
            print "\tStopping OpenFlow controller %s...\t[FAILED]" % controller.name
            print "\tKill the controller %s manually" % controller.name
    return True


def check_process_alive(process_name):
    alive = False
    # grep the Mach processes
    system("pidof -x %s > %s" % (process_name, GINI_TEMP_FILE))
    inFile = open(GINI_TEMP_FILE)
    line = inFile.readline()
    inFile.close()
    if not line:
        return False
    else:
        procs = line.split()

    for proc in procs:
        system("ps aux | grep %s > %s" % (proc, GINI_TEMP_FILE))
        inFile = open(GINI_TEMP_FILE)
        lines = inFile.readlines()
        inFile.close()
        for line in lines:
            if line.find("grep") >= 0:
                continue
            if line.find(os.getenv("USER")) >= 0:
                return True

    os.remove(GINI_TEMP_FILE)
    return alive


def write_source_file(opts):
    """Write the configuration in the setup file"""
    outFile = open(SOURCE_FILE_NAME, "w")
    outFile.write("%s\n" % opts.xmlFile)
    outFile.write("%s\n" % opts.switchDir)
    outFile.write("%s\n" % opts.routerDir)
    outFile.write("%s\n" % opts.machDir)
    outFile.write("%s\n" % opts.binDir)
    outFile.write("%s\n" % opts.controllerDir)
    outFile.close()


def delete_source_file():
    """Delete the setup file"""
    if os.access(SOURCE_FILE_NAME, os.W_OK):
        os.remove(SOURCE_FILE_NAME)
    else:
        print "Could not delete the GINI setup file"


def check_alive_GINI():
    """Check if any of the gini components is already running"""
    result = False
    if check_process_alive(VIRTUAL_SWITCH_PROGRAM_BIN):
        print "At least one of %s is alive" % VIRTUAL_SWITCH_PROGRAM_BIN
        result = True
    if check_process_alive(VIRTUAL_MACHINE_PROGRAM_BIN):
        print "At least one of %s is alive" % VIRTUAL_MACHINE_PROGRAM_BIN
        result = True
    if check_process_alive(GROUTER_PROGRAM_BIN):
        print "At least one of %s is alive" % GROUTER_PROGRAM_BIN
        result = True
    if check_process_alive(OPENFLOW_CONTROLLER_PROGRAM_BIN):
        print "At least one of %s is alive" % OPENFLOW_CONTROLLER_PROGRAM_BIN
        result = True
    return result


"""
Create the program processor. This
1. accepts and process the command line options
2. creates XML processing engine, that in turn
   a) validates the XML file
   b) extracts the DOM object tree
   c) populates the GINI network class library
   d) performs some semantic/syntax checks on
      the extracted specification
"""

my_program = Program(sys.argv[0], SOURCE_FILE_NAME)
if not my_program.processOptions(sys.argv[1:]):
    sys.exit(1)
options = my_program.options

# set the Mach directory if is not given via -u option
if not options.machDir:
    # set it to the directory pointed by the $Mach_DIR env
    # if no such env variable, set the mach dir to curr dir
    if "Mach_DIR" in os.environ:
        options.machDir = os.environ["Mach_DIR"]
    else:
        options.machDir = "."

# get the binaries
bin_dir = options.binDir
if bin_dir:
    # get the absolute path for binary directory
    if bin_dir[len(bin_dir) - 1] == "/":
        bin_dir = bin_dir[:len(bin_dir) - 1]
    bin_dir = get_fully_qualified_dir(bin_dir)
    # assign binary names
    # if the programs are not in the specified bin_dir
    # they will be assumed to be in the $PATH env.
    VIRTUAL_SWITCH_PROGRAM_BIN = "%s/%s" % (bin_dir, VIRTUAL_SWITCH_PROGRAM)
    if not os.access(VIRTUAL_SWITCH_PROGRAM_BIN, os.X_OK):
        VIRTUAL_SWITCH_PROGRAM_BIN = VIRTUAL_SWITCH_PROGRAM

    OPEN_VIRTUAL_SWITCH_PROGRAM_BIN = "%s/%s" % (bin_dir, OPEN_VIRTUAL_SWITCH_PROGRAM)
    if not os.access(OPEN_VIRTUAL_SWITCH_PROGRAM_BIN, os.X_OK):
        OPEN_VIRTUAL_SWITCH_PROGRAM_BIN = VIRTUAL_MACHINE_PROGRAM

    VIRTUAL_MACHINE_PROGRAM_BIN = "%s/%s" % (bin_dir, VIRTUAL_MACHINE_PROGRAM)
    if not os.access(VIRTUAL_MACHINE_PROGRAM_BIN, os.X_OK):
        VIRTUAL_MACHINE_PROGRAM_BIN = VIRTUAL_MACHINE_PROGRAM

    GROUTER_PROGRAM_BIN = "%s/%s" % (bin_dir, GROUTER_PROGRAM)
    if not os.access(GROUTER_PROGRAM_BIN, os.X_OK):
        GROUTER_PROGRAM_BIN = GROUTER_PROGRAM

    MACHINE_CONSOLE_PROGRAM_BIN = "%s/%s" % (bin_dir, MACHINE_CONSOLE_PROGRAM)
    if not os.access(MACHINE_CONSOLE_PROGRAM_BIN, os.X_OK):
        MACHINE_CONSOLE_PROGRAM_BIN = MACHINE_CONSOLE_PROGRAM

    OPENFLOW_CONTROLLER_PROGRAM_BIN = "%s/%s" % (bin_dir, OPENFLOW_CONTROLLER_PROGRAM)
    if not os.access(OPENFLOW_CONTROLLER_PROGRAM_BIN, os.X_OK):
        OPENFLOW_CONTROLLER_PROGRAM_BIN = OPENFLOW_CONTROLLER_PROGRAM

# get the populated GINI network class
# its structure is the same as the XML specification
myGINI = my_program.giniNW

# create or terminate GINI network
print ""
if my_program.destroyOpt:
    # terminate the current running specification
    print "Terminating GINI network..."
    success = destroy_GINI(myGINI, options)
    if success:
        print "\nGINI network is terminated!!\n"
    else:
        print "\nThere are errors in GINI network termination\n"
        sys.exit(1)
else:
    # create the GINI instance
    if not options.keepOld:
        # fail if a GINI already alive
        if check_alive_GINI():
            print "\nA Gini is already running"
            print "Terminate it before running another one\n"
            sys.exit(1)

    if "GINI_HOME" not in os.environ:
        print "environment variable $GINI_HOME not set, please set it for GINI to run properly"
        sys.exit(1)

    # create network with current specification
    print "Creating GINI network..."
    success = start_GINI(myGINI, options)
    write_source_file(options)
    if success:
        print "\nGINI network up and running!!\n"
    else:
        print "\nGINI network start failed!!\n"
