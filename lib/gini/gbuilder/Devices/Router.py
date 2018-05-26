from Core.Connection import *
from Core.Interfaceable import *
from Core.globals import environ
from PyQt4.QtCore import QPoint
import Core.util

class Router(Interfaceable):
    device_type = "Router"

    def __init__(self):
        Interfaceable.__init__(self)
        self.menu.addAction("Wireshark", self.wireshark)
        self.menu.addAction("Graph", self.graph)
        self.tail = None
        self.wshark = None
        self.rstatsWindow = None

        self.lightPoint = QPoint(-19,-6)

    def graph(self):
        """
        Graph the stats of the running router
        """
        if not mainWidgets["main"].isRunning():
            mainWidgets["log"].append("You must start the topology first!")
            return

        if options["graphing"]:
            try:
                from UI.GraphWindow import GraphWindow
            except:
                mainWidgets["log"].append(
                        "Error: matplotlib required for graphing capabilities")
            else:
                self.rstatsWindow = GraphWindow(self.getName(),
                                                mainWidgets["canvas"])
                self.rstatsWindow.show()

    def wireshark(self):
        """
        Open wireshark with the running device.
        """
        if not mainWidgets["main"].isRunning():
            mainWidgets["log"].append("You must start the topology first!")
            return

        progName = "wireshark"
        if environ["os"] == "Windows":
            progName += ".exe"
        if Core.util.progExists(progName):
            outfile = environ["tmp"].replace("\\", "/") + \
                    str(self.getName()) + ".out"

            if not os.access(outfile, os.F_OK):
                open(outfile, "w").close()
                client = mainWidgets["client"]
                if client:
                    client.send("wshark " + self.getName())

            command = ["tail", "-n", "+1", "-f", "%s" % outfile]
            command2 = [progName, "-k", "-i", "-"]

            try:
                self.tail = subprocess.Popen(command, stdout=subprocess.PIPE)
            except:
                mainWidgets["log"].append("Error: tail not found in path!\nPlease add GINI_HOME/bin to PATH.")

            self.wshark = subprocess.Popen(command2, stdin=self.tail.stdout)
        else:
            mainWidgets["log"].append("Error: wireshark not found in path")
