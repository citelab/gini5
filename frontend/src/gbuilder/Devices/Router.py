from Core.Connection import *
from Core.Interfaceable import *
from Core.globals import environ
from PyQt4.QtCore import QPoint
import Core.util
import os
import json
from functools import partial


class Router(Interfaceable):
    device_type = "Router"

    def __init__(self):
        Interfaceable.__init__(self)
        self.menu.addAction("Graph", self.graph)
        self.tail = None
        self.wshark = []
        self.rstatsWindow = None

        self.wireshark_menu = self.menu.addMenu("Wireshark")
        self.wireshark_menu.aboutToShow.connect(self.load_wireshark_interfaces)

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

    def load_wireshark_interfaces(self):
        """Get connected interfaces and display as options on Wireshark menu"""
        self.wireshark_menu.clear()
        router_tmp_file = environ["tmp"] + self.getName() + ".json"
        if not os.access(router_tmp_file, os.R_OK):
            return
        interfaces_map = dict()
        with open(router_tmp_file, "r") as f:
            interfaces_map = json.load(f, encoding="utf-8")

        for key, value in interfaces_map.items():
            wireshark_action = partial(self.wireshark, value)
            self.wireshark_menu.addAction(key, wireshark_action)

    def wireshark(self, interface):
        """
        Open wireshark with the running device.
        """
        program_name = "wireshark"

        command_to_execute = [program_name, "-k", "-i", interface]
        wireshark_process = subprocess.Popen(command_to_execute)
        if Core.util.progExists(program_name):
            self.wshark.append(wireshark_process)
        else:
            mainWidgets["log"].append("Error: wireshark not found in path!")
