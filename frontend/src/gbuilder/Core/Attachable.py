"""A device that can be attached to"""

from Device import *
import subprocess


class Attachable(Device):
    def __init__(self):
        """
        Create a device that can be attached to.
        """
        Device.__init__(self)

        self.menu.addAction("Restart", self.restart)
        self.menu.addAction("Stop", self.terminate)
        self.shell = None

    def attach(self):
        """
        Attach to corresponding device on backend.
        """
        name = self.getName()
        command = ""

        window_name = str(self.getProperty("Name"))  # the string cast is necessary for cloning
        if self.getName() != window_name:
            window_name += " (" + self.getName() + ")"

        print("Attaching to device: %s" % name)
        command += "xterm -fa 'Monospace' -fs 14 -title \"" + window_name + "\" -e  screen -r " + window_name

        self.shell = subprocess.Popen(str(command), shell=True)
