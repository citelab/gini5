"""A device that can be attached to"""

from Device import *

class Attachable(Device):
    def __init__(self):
        """
        Create a device that can be attached to.
        """
        Device.__init__(self)

        self.menu.addAction("Restart", self.restart)
        self.menu.addAction("Stop", self.terminate)

    def attach(self):
        """
        Attach to corresponding device on backend.
        """

        screen = " screen -r "
        if self.device_type == "Wireless_access_point":
            screen += "WAP_%d" % self.getID()
        elif self.device_type == "yRouter":
            yrouter = "yrouter --interactive=1 --config=/root/script_t1_y1.conf test3"
            screen_yrouter = "%s ssh %s \"source /root/.profile; %s\""%(sshpass, remote_Station, yrouter)
        else:
            name = self.getName()
            pid = mainWidgets["tm"].getPID(name)
            print "Pid", pid, "...."
            #if not pid:
            #    return
            #screen += pid + "." + name

        command = ""

        window_name = str(self.getProperty("Name"))  # the strcast is necessary for cloning
        if(self.getName() != window_name):
            window_name += " (" + self.getName() + ")"
        if environ["os"] == "Windows":

            startpath = environ["tmp"] + self.getName() + ".start"
            try:
                outfile = open(startpath, "w")
                outfile.write(screen)
                outfile.close()
            except:
                mainWidgets["log"].append("Failed to write to start file!")
                return

            command += "putty -"
            if options["session"]:
                command += "load " + options["session"] + " -l " + options["username"] + " -t"
            else:
                command += base
            command += " -m \"" + startpath + "\""
        else:

            print "-------- HOLA -------------" + self.device_type
            if self.device_type == "yRouter":
                command += "rxvt -T \"" + window_name + "\" -e " + screen_yrouter
            elif self.device_type == "UML":
                command += "xterm -font 12x24 -title \"" + window_name + "\" -e  docker exec -it " + window_name + " sh"
            else:
                command += "xterm -font 12x24 -title \"" + window_name + "\" -e  screen -r " + window_name

        self.shell = subprocess.Popen(str(command), shell=True)
