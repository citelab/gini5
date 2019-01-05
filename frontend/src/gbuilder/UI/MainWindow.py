"""The main window for gbuilder 2.0"""

import os, time, math, subprocess, sys
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from DropBar import *
from LogWindow import *
from Canvas import *
from Node import *
from Edge import *
from Configuration import *
from Core.globals import *
import thread
import socket
import atexit
import fcntl
import struct
from ExportWindow import *
from SendDirectoryWindow import *
from Properties import *
from Systray import *
from Network.gclient import *
from Core.Compiler import *
from TabWidget import *
from Tutorial import *
from TaskManagerWindow import *
import Core.globals
from Wireless.ClientAPI import *
from Wireless.ServerAPI import *

class MainWindow(Systray):
    def __init__(self,app):
        """
        Create a main window for the application
        """
        defaultOptions["palette"]=app.palette()
        Systray.__init__(self)

        self.expansions=0
        self.client=None
        self.server=None
        self.wserverIP=None
        self.wserverPort=None
        self.wgini_client=None
        self.wgini_server=None
        self.running=False
        self.recovery=False
        mainWidgets["main"] = self
        mainWidgets["app"] = app

        self.canvas = Canvas(self)
        mainWidgets["canvas"] = self.canvas

        self.tabWidget = TabWidget(self)
        mainWidgets["tab"] = self.tabWidget

        self.setCentralWidget(self.tabWidget)
        #self.setCentralWidget(self.canvas)

        self.createActions()
        self.createMenus()
        self.createToolBars()
        self.createStatusBar()
        self.createDockWindows()
        self.createConfigWindows()
        self.createPopupWindows()
        self.createProgressBar()

        self.newScene()

        self.debugWindow.hide()
        self.tm.hide()
        self.routes.hide()

        self.setVisible(True)
        self.center()
        self.saveLayout(environ["config"] + "defaultLayout")

        if options["menumods"]:
            self.setStyleSheet("""QToolTip {
                               background-color: black;
                               color: white;
                               border: black solid 1px
                               }
                               QMenu {
                               color: white;
                               }""")
        else:
            self.setStyleSheet("""QToolTip {
                               background-color: black;
                               color: white;
                               border: black solid 1px
                               }""")

        self.defaultLayout = True
        if options["restore"]:
            self.loadLayout()
            self.defaultLayout = False



        self.loadProject()
        atexit.register(self.cleanup)


    def center(self):
        """
        Center the window.
        """
        screen = QtGui.QDesktopWidget().screenGeometry()
        rect = self.geometry()
        self.move((screen.width()-rect.width())/2, (screen.height()-rect.height())/2)
        self.show()

    def getProject(self):
        """
        Return the project.
        """
        return self.project

    def startTutorial(self):
        """
        Start the interactive tutorial.
        """
        if isinstance(mainWidgets["canvas"], Tutorial):
            self.log.append("You are already doing the tutorial!  If you would like to stop or restart, select 'Close' from the File menu now.")
            return

        if not self.closeTopology():
            return

        self.project = "Tutorial"
        self.filename = ""

        self.canvas = Tutorial(self)
        mainWidgets["canvas"] = self.canvas

        self.tabWidget.removeTab(0)
        self.tabWidget.addTab(self.canvas, "Tutorial")
        self.canvas.start()

        for nodeType in nodeTypes.keys():
            itemTypes = nodeTypes[nodeType]
            itemTypes[nodeType] = 0

        self.properties.clear()
        self.interfaces.clear()
        self.routes.clear()

        self.resetLayout(True)
        self.lockDocks()

    def lockDocks(self):
        """
        Lock the dock windows so they cannot be moved, closed or resized.
        """
        self.tm.hide()
        for dock in self.docks.values():
            dock.setFeatures(dock.NoDockWidgetFeatures)

    def unlockDocks(self):
        """
        Unlock the dock windows.
        """
        self.tm.show()
        for dock in self.docks.values():
            dock.setFeatures(dock.DockWidgetClosable | dock.DockWidgetMovable | dock.DockWidgetFloatable)

    def faq(self):
        """
        Open the FAQ in the default browser.
        """
        olddir = os.getcwd()
        os.chdir(environ["doc"])
        loadpath = os.getcwd()
        os.chdir(olddir)

        if environ["os"] == "Windows":
            url = QtCore.QUrl("file:///" + loadpath + "/FAQ.html")
        else:
            url = QtCore.QUrl("file://" + loadpath + "/FAQ.html")
        QtGui.QDesktopServices.openUrl(url)

    def closeTopology(self,usedyRouters=usedyRouters):
        """
        Close the current topology.
        """
        if self.running:
            self.log.append("You cannot close a topology when one is still running!")
            return False

        scene = self.canvas.scene()
        if scene and scene.items():
            reply = QtGui.QMessageBox.warning(self, self.tr(Core.globals.PROG_NAME), self.tr("Save before closing?"), QtGui.QMessageBox.Yes | QtGui.QMessageBox.No | QtGui.QMessageBox.Cancel)
            if reply == QtGui.QMessageBox.Yes:
                if not self.saveTopology():
                    return False
            elif reply == QtGui.QMessageBox.No:
                pass
            else:
                return False

        if isinstance(mainWidgets["canvas"], Tutorial):
            self.canvas = Canvas(self)
            mainWidgets["canvas"] = self.canvas
            self.tabWidget.removeTab(0)
            self.tabWidget.addTab(self.canvas, "Default Project")
            self.project = ""
            self.unlockDocks()

        self.filename = ""
        scene = Scene(self.canvas)
        scene.setItemIndexMethod(QtGui.QGraphicsScene.NoIndex)
        self.canvas.setScene(scene)
        self.expansions = 0

        for nodeType in nodeTypes.keys():
            itemTypes = nodeTypes[nodeType]
            itemTypes[nodeType] = 0

	    if usedyRouters:
	        for yunid, yun in usedyRouters.iteritems():
		        availableyRouters.append(yun)
		        availableyRouters.sort(key=lambda YunEntity: YunEntity['ID'])
	        usedyRouters = {}

        self.properties.clear()
        self.interfaces.clear()
        self.routes.clear()

        return True

    def sendFile(self):
        """
        Start a process to select and send a file to the server.
        """
        if not self.server or self.server.poll() != None:
            self.log.append("Please start the server first!")
            return
        if not self.client or not self.client.isConnected():
            self.startClient()

        filename = self.loadFile("All Files (*.*)")
        if not filename:
            return

        self.sendWindow.setFilename(filename)
        self.sendWindow.show()

    def newScene(self):
        """
        Close the current topology and create a new one.
        """
        if self.running:
            self.log.append("You cannot create a new topology when one is still running!")
            return

        if isinstance(mainWidgets["canvas"], Tutorial):
            self.log.append("You cannot create a new topology during the tutorial!")
            return

        if not self.closeTopology(usedyRouters):
            return

        self.expandScene()

    def expandScene(self):
        """
        Expand the scene based on number of expansions.
        """
        x = 175 + self.expansions * 30
        y = 160 + self.expansions * 20
        scene = self.canvas.scene()
        item = QtGui.QGraphicsLineItem(-x, -y, x, y)
        scene.addItem(item)
        scene.removeItem(item)
        self.expansions += 1

    def newProject(self):
        """
        Create a new project for device sharing.
        """
        if self.running:
            self.log.append("You cannot create a new project when one is still running!")
            return

        if isinstance(mainWidgets["canvas"], Tutorial):
            self.log.append("You cannot create a new project during the tutorial!")
            return

        filename = self.saveFile("gproj")
        if filename.isEmpty():
            return

        projectname = str(filename).split("/")[-1].strip(".gproj")
        from Core.Item import nodeTypes
        for nodeType in nodeTypes:
            if projectname.startswith(nodeType + "_"):
                self.popup.setWindowTitle("Invalid Project Name")
                self.popup.setText("You cannot name a project starting with the name of a device and underscore!")
                self.popup.show()
                return

        self.project = str(filename)
        file = QtCore.QFile(filename)
        if not file.open(QtCore.QFile.WriteOnly | QtCore.QFile.Text):
            QtGui.QMessageBox.warning(self, self.tr("Save Error"),
                                      self.tr("Cannot write file %1:\n%2.")
                                      .arg(self.filename)
                                      .arg(file.errorString()))
            return

        out = QtCore.QTextStream(file)
        QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)

        if options["username"]:
            out << "username=" + options["username"] + "\n"
        else:
            self.log.append("Warning, no username is specified!")

        if options["session"]:
            out << "session=" + options["session"] + "\n"
        elif options["server"]:
            out << "server=" + options["server"] + "\n"
        else:
            self.log.append("Warning, no server or session name is specified!")

        QtGui.QApplication.restoreOverrideCursor()

        self.tabWidget.addTab(self.canvas, projectname)

    def openProject(self):
        """
        Load an existing project for device sharing.
        """
        if self.running:
            self.log.append("You cannot open a project when one is still running!")
            return

        if isinstance(mainWidgets["canvas"], Tutorial):
            self.log.append("You cannot open a project during the tutorial!")
            return

        filename = self.loadFile("GPROJ (*.gproj)")
        if filename.isEmpty():
            return

        self.project = str(filename)
        self.loadProject()

    def loadProject(self):
        """
        Load project file data into options.
        """

        if not self.project:
            self.tabWidget.addTab(self.canvas, "Default Project")
            return

        file = QtCore.QFile(self.project)
        if not file.open(QtCore.QFile.ReadOnly | QtCore.QFile.Text):
            QtGui.QMessageBox.warning(self, self.tr("Load Error"),
                                      self.tr("Cannot read file %1:\n%2.")
                                      .arg(self.project)
                                      .arg(file.errorString()))
            self.tabWidget.addTab(self.canvas, "Default Project")
            return

        _in = QtCore.QTextStream(file)
        QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)

        while not _in.atEnd():
            line = str(_in.readLine())
            option, value = line.split("=", 1)
            options[option] = value

        self.configWindow.updateSettings()

        QtGui.QApplication.restoreOverrideCursor()
        projectname = self.project.split("/")[-1].strip(".gproj")
        self.tabWidget.addTab(self.canvas, projectname)

    def closeProject(self):
        """
        Close the current project.
        """
        if self.running:
            self.log.append("You cannot close a project when it is still running!")
            return

        if isinstance(mainWidgets["canvas"], Tutorial):
            self.log.append("You cannot close a project during the tutorial!")
            return

        if self.tabWidget.count() == 1:
            self.tabWidget.addTab(self.canvas, "Default Project")
            self.project = ""
        else:
            self.tabWidget.removeTab(0)

    def export(self):
        """
        Open an export window to generate an image from the canvas.
        """
        self.exportWindow.show()

    def startBackend(self):
        """
        Start the backend server.
        """
        self.startServer()
        #self.startClient()
    def setRecovery(self, recovery):
        """
        Set the recovering state of the topology.
        """
        self.recovery = recovery

    def isRunning(self):
        """
        Returns whether a topology is running or not.
        """
        return self.running

    def startWServer(self):
        """
        Call the startwgini_server function
        """
        self.startwgini_server()
        #thread.join()

    def startServer(self):
        """
        Start the server backend of gbuilder, which controls running topologies.
        """
        if self.server and self.server.poll() == None:
            self.log.append("A server is already running!")
            return

        base = "ssh -t " + options["username"] + "@" + options["server"]
        tunnel = " -L " + options["localPort"] + ":localhost:" + options["remotePort"]
        server = "bash -c -i 'gserver " + options["remotePort"] + "' || sleep 5"
        command = ""
        gserver = "gserver"

        if environ["os"] == "Windows":
            startpath = environ["tmp"] + "gserver.start"
            try:
                startFile = open(startpath, "w")
                startFile.write("echo -ne \"\\033]0;" + gserver + "\\007\"\n")
                startFile.write(server)
                startFile.close()
            except:
                self.log.append("Failed to write to start file!")
                return

            command += "putty -"
            if options["session"]:
                command += "load " + options["session"] + " -l " + options["username"] + " -t"
            else:
                command += base
            command += tunnel + " -m \"" + startpath + "\""
        else:
            command += "xterm -fa 'Monospace' -fs 14 -title \"" + gserver + "\" -e " + base + tunnel + " \" " + server + "\""

        self.server = subprocess.Popen(str(command), shell=True,preexec_fn=os.setpgrp)

    def startwgini_server(self):
        """
        Start the wireless GINI server
        """
        base = "ssh -t " + options["username"] + "@" + options["wserver"]
        tunnel = " -L " + options["wlocalPort"] + ":localhost:" + options["wremotePort"]
        server = "bash -c -i 'ServerAPI'"
        command = ""
        gserver = "WGINI Server"


        command += "rxvt -T \"" + gserver + "\" -e " + base + tunnel + " \" " + server + "\""

        command1 = 'route add -net 192.168.0.0 gw 192.168.54.24 netmask 255.255.255.0 eth1' #change accordingly!
        p = os.system('echo %s|sudo -S %s' % (sudoPassword, command1))

        self.wgini_server = subprocess.Popen(str(command), shell=True,preexec_fn=os.setpgrp)

    def startClient(self):
        """
        Start the client of gbuilder, which communicates with the server.
        """
        self.client = Client(self)
        self.client.connectTo("localhost", int(options["localPort"]), 10)
        #self.client.start()
        mainWidgets["client"] = self.client

    def compile(self):
        """
        Compile the current topology.
        """
        if self.running:
            self.log.append("You cannot compile a topology when one is still running!")
            return False

        if self.saveTopology() == False:
            return False

        scene = self.canvas.scene()
        compiler = Compiler(scene.items(), self.filename)
        xmlFile = compiler.compile()

        self.properties.display()
        self.interfaces.display()
        self.routes.display()

        if xmlFile:
            self.statusBar().showMessage(self.tr("Compiled '%1'").arg(xmlFile), 2000)
            return True
        else:
            self.statusBar().showMessage(self.tr("Compile failed"), 2000)
            return False

    def run(self):
        """
        Run the current topology.
        """
        print "???????????????????????????????????????????????????"
        if not self.server or self.server.poll() != None:
            self.log.append("Please start the server first!")
            return
        if not self.client or not self.client.isConnected():
            self.startClient()

        if self.isRunning() and not self.recovery:
            self.log.append("A topology is already running, please stop it first!")
            return

        scene = self.canvas.scene()
        items = scene.items()
        if items:
            if self.recovery:
                self.recovery = False
            elif options["autocompile"] and not self.compile():
                return
        else:
            self.log.append("Please create or load a topology first!")
            return

        options["elasticMode"] = False

        xmlFile = self.filename.replace(".gsav", ".xml")

        if not os.access(xmlFile, os.F_OK):
            self.log.append("Please compile the topology first!")
            return

        print ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> "
        self.tm.show()

        #self.progressBar.setValue(0)
        self.client.process("file . " + xmlFile)
        self.client.send("init " + self.project.split("/")[-1].strip(".gproj"))
        self.client.send("canvas %d,%d" % (scene.width(), scene.height()))
        for item in items:
            if item.device_type == "Mobile" or item.device_type == "Wireless_access_point":
                x = item.pos().x()
                y = item.pos().y()
                self.client.send("mobile %s %d,%d" % (item.getName(), x, y))
        self.client.process("start " + xmlFile)

        self.running = True
        self.canvas.setAcceptDrops(False)
        scene = self.canvas.scene()
        scene.startRefresh()
        scene.clearSelection()

        self.properties.clear()
        self.interfaces.clear()
        self.routes.clear()

    def stop(self):
        """
        Stop the current running topology.
        """
        if not self.server or self.server.poll() != None:
            self.log.append("Please start the server first!")
            return
        if not self.isRunning():
            self.log.append("No network topology is running!")
            return
        if not self.client or not self.client.isConnected():
            self.startClient()

        if (self.wgini_client is not None) and usedyRouters:
            status = self.wgini_client.Delete()
            self.log.append(status)

        if self.recovery:
            self.recovery = False

        scene = self.canvas.scene()
        activeDevices = False
        from Core.Device import Device
        for item in scene.items():
            if not isinstance(item, Device):
                continue
            if item.device_type == "Router":
                item.stop()
            if item.status:
                activeDevices = True

        if not activeDevices:
            self.stopped()
        elif not scene.isRefreshing():
            scene.startRefresh()

        self.client.process("stop")

    def stopped(self):
        """
        Handle a fully stopped topology.
        """
        self.running = False
        self.canvas.scene().stopRefresh()
        self.tm.hide()
        self.canvas.setAcceptDrops(True)

        olddir = os.getcwd()
        os.chdir(environ["tmp"])
        for tmpfile in os.listdir("."):
            if tmpfile.startswith("."):
                continue
            try:
                os.remove(tmpfile)
            except:
                continue
        os.chdir(olddir)

    def loadFile(self, filetype):
        """
        Load a file through a file dialog.
        """
        # Qt is very picky in the filename structure but python is not, so we use python
        # to form the correct path which will work for both Windows and Linux
        olddir = os.getcwd()
        os.chdir(environ["sav"])
        loadpath = os.getcwd()
        os.chdir(olddir)

        filename = QtGui.QFileDialog.getOpenFileName(self,
                    self.tr("Choose a file name"), loadpath,
                    self.tr(filetype))

        return filename

    def loadrealTopologyfile(self, filetype):
        """
        Load a real topology name
        """
        self.popup.setWindowTitle("Topology Names")
        self.popup.setText("You are about to select from the list:\n1.Ernet")
        self.popup.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        self.popup.show()
        retval = self.popup.exec_()

        if retval==1024:
            olddir = os.getcwd()
            os.chdir(environ["sav"])
            os.chdir("exist")
            loadpath = os.getcwd()
            os.chdir(olddir)

            filename = QtGui.QFileDialog.getOpenFileName(self,
                        self.tr("Choose a file name"), loadpath,
                        self.tr(filetype))

            return filename



    def loadrealTopology(self):
        """
        Load a real topology.
        """
        if self.running:
            self.log.append("You cannot load a topology when one is still running!")
            return

        if isinstance(mainWidgets["canvas"], Tutorial):
            self.log.append("You cannot load a topology during the tutorial!")
            return

        def loadIntoScene(line, *args):
            scene = self.canvas.scene()
            itemType,arg = line.split(":")
            args = str(arg).strip("()").split(",")

            if itemType == "edge":
                source = scene.findItem(args[0])
                dest = scene.findItem(args[1])
                if source.device_type == "Mobile" or dest.device_type == "Mobile":
                    item = Wireless_Connection(source, dest)
                else:
                    item = Connection(source, dest)
                scene.addItem(item)
            else:
                devType, index = str(itemType).rsplit("_", 1)
                item = deviceTypes[devType]()
                item.setIndex(int(index))
                scene.addItem(item)
                item.setPos(float(args[0]), float(args[1]))
                item.nudge()

            return item

        def loadProperties(itemDict):
            currentInterfaceTarget = None
            currentRouteSubnet = None

            for item, properties in itemDict.iteritems():
                for line in properties:
                    count = 0
                    while line.find("\t") == 0:
                        line = line[1:]
                        count += 1

                    prop, value = line.split(":", 1)
                    if count == 1:
                        item.setProperty(prop, value)
                    elif count == 2:
                        currentInterfaceTarget = self.canvas.scene().findItem(value)
                    elif count == 3:
                        item.setInterfaceProperty(prop, value, currentInterfaceTarget)
                    elif count == 4:
                        currentRouteSubnet = value
                        item.addEntry("", "", value, currentInterfaceTarget)
                    elif count == 5:
                        item.setEntryProperty(prop, value, currentRouteSubnet, currentInterfaceTarget)

        filename = self.loadrealTopologyfile("GSAV (*.gsav)")
        if not filename:
            return

        file = QtCore.QFile(filename)
        if not file.open(QtCore.QFile.ReadOnly | QtCore.QFile.Text):
            QtGui.QMessageBox.warning(self, self.tr("Load Error"),
                                      self.tr("Cannot read file %1:\n%2.")
                                      .arg(filename)
                                      .arg(file.errorString()))
            return

        self.newScene()
        self.filename = str(filename)

        _in = QtCore.QTextStream(file)

        yRouters = False
        if "yRouter" in str(_in.readAll()):
	        yRouters = True
	        QtGui.QMessageBox.warning(self, self.tr("Load Warning"), self.tr("This file contains yRouters, which may not be physically available right now. Any yRouters no longer physically available will automatically be removed from the topology."))

	        if not self.wgini_server:
		        if not self.startWGINIClient():
		            QtGui.QMessageBox.warning(self, self.tr("Load Error"), self.tr("Cannot open file with yRouters without connecting to wireless server."))
		        return

        if yRouters:
	        self.discover()

        QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)

        itemDict = {}
        _in.seek(0)
        line = str(_in.readLine())
        lines = []

        while not _in.atEnd():
            item=loadIntoScene(line)
            line=str(_in.readLine())
            while line.find("\t") == 0:
                lines.append(line)
                line=str(_in.readLine())
            itemDict[item] = lines
            lines = []

        loadProperties(itemDict)

        QtGui.QApplication.restoreOverrideCursor()

        self.statusBar().showMessage(self.tr("Loaded '%1'").arg(filename), 2000)




    def loadTopology(self):
        """
        Load a topology.
        """
        if self.running:
            self.log.append("You cannot load a topology when one is still running!")
            return

        if isinstance(mainWidgets["canvas"], Tutorial):
            self.log.append("You cannot load a topology during the tutorial!")
            return

        def loadIntoScene(line, *args):
            scene = self.canvas.scene()
            itemType,arg = line.split(":")
            args = str(arg).strip("()").split(",")

            if itemType == "edge":
                source = scene.findItem(args[0])
                dest = scene.findItem(args[1])
                if source.device_type == "Mobile" or dest.device_type == "Mobile":
                    item = Wireless_Connection(source, dest)
                else:
                    item = Connection(source, dest)
                scene.addItem(item)
            else:
                devType, index = str(itemType).rsplit("_", 1)
                item = deviceTypes[devType]()
                item.setIndex(int(index))
                scene.addItem(item)
                item.setPos(float(args[0]), float(args[1]))
                item.nudge()

            return item

        def loadProperties(itemDict):
            currentInterfaceTarget = None
            currentRouteSubnet = None

            for item, properties in itemDict.iteritems():
                for line in properties:
                    count = 0
                    while line.find("\t") == 0:
                        line = line[1:]
                        count += 1

                    prop, value = line.split(":", 1)
                    if count == 1:
                        item.setProperty(prop, value)
                    elif count == 2:
                        currentInterfaceTarget = self.canvas.scene().findItem(value)
                    elif count == 3:
                        item.setInterfaceProperty(prop, value, currentInterfaceTarget)
                    elif count == 4:
                        currentRouteSubnet = value
                        item.addEntry("", "", value, currentInterfaceTarget)
                    elif count == 5:
                        item.setEntryProperty(prop, value, currentRouteSubnet, currentInterfaceTarget)

        filename = self.loadFile("GSAV (*.gsav)")
        if filename.isEmpty():
            return

        file = QtCore.QFile(filename)
        if not file.open(QtCore.QFile.ReadOnly | QtCore.QFile.Text):
            QtGui.QMessageBox.warning(self, self.tr("Load Error"),
                                      self.tr("Cannot read file %1:\n%2.")
                                      .arg(filename)
                                      .arg(file.errorString()))
            return

        self.newScene()
        self.filename = str(filename)

        _in = QtCore.QTextStream(file)

        yRouters = False
        if "yRouter" in str(_in.readAll()):
	        yRouters = True
	        QtGui.QMessageBox.warning(self, self.tr("Load Warning"), self.tr("This file contains yRouters, which may not be physically available right now. Any yRouters no longer physically available will automatically be removed from the topology."))

	        if not self.wgini_server:
		        if not self.startWGINIClient():
		            QtGui.QMessageBox.warning(self, self.tr("Load Error"), self.tr("Cannot open file with yRouters without connecting to wireless server."))
		        return

        if yRouters:
	        self.discover()

        QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)

        itemDict = {}
        _in.seek(0)
        line = str(_in.readLine())
        lines = []

        while not _in.atEnd():
            item=loadIntoScene(line)
            line=str(_in.readLine())
            while line.find("\t") == 0:
                lines.append(line)
                line=str(_in.readLine())
            itemDict[item] = lines
            lines = []

        loadProperties(itemDict)

        QtGui.QApplication.restoreOverrideCursor()

        self.statusBar().showMessage(self.tr("Loaded '%1'").arg(filename), 2000)

    def saveFile(self, filetype):
        """
        Save a file through a file dialog.
        """
        olddir = os.getcwd()
        os.chdir(environ["sav"])
        savepath = os.getcwd()
        os.chdir(olddir)

        filename = QtGui.QFileDialog.getSaveFileName(self,
                    self.tr("Choose a file name"), savepath,
                    self.tr(filetype.upper() + " (*.%s)" % filetype))

        if filename.isEmpty():
            return filename

        if not filename.toLower().endsWith("." + filetype):
            filename += "." + filetype

        return filename

    def saveTopologyAs(self):
        """
        Save a topology under a given filename.
        """
        if not self.canvas.scene().items():
            self.log.append("There is nothing to save!")
            return False

        filename = self.saveFile("gsav")
        if filename.isEmpty():
            return False

        self.filename = str(filename)

        return self.saveTopology()

    def saveTopology(self):
        """
        Save a topology.
        """
        scene=self.canvas.scene()

        if not scene.items():
            self.log.append("There is nothing to save!")
            return False

        #for first time used
        if not self.filename:
            return self.saveTopologyAs()

	    if usedyRouters:
	        self.popup.setWindowTitle("Save Warning")
	        self.popup.setText("This topology contains yRouters, which may not be available when loading the project later.")
	        self.popup.show()

        file = QtCore.QFile(self.filename)
        if not file.open(QtCore.QFile.WriteOnly | QtCore.QFile.Text):
            QtGui.QMessageBox.warning(self, self.tr("Save Error"),
                                      self.tr("Cannot write file %1:\n%2.")
                                      .arg(self.filename)
                                      .arg(file.errorString()))
            return False

        out = QtCore.QTextStream(file)
        QtGui.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        outstring = ""
        for item in scene.items():
            if isinstance(item, Node):
                outstring += item.toString()

        for item in scene.items():
            if isinstance(item, Edge):
                outstring += item.toString()

        out << outstring
        QtGui.QApplication.restoreOverrideCursor()

        self.statusBar().showMessage(self.tr("Saved '%1'").arg(self.filename), 2000)

        return True

    def copy(self):
        """
        Copy selected text from the log into the paste buffer.
        """
        self.log.copy()

    def config(self):
        """
        Open the options window.
        """
        self.configWindow.show()

    def startWGINIClient(self):
        """
	    Start wireless GINI client
	    """
        ok=None
        if not self.server or self.server.poll() is not None:
            self.log.append("You must start the main server before you can start the wireless client!")
        elif not self.wgini_server or self.wgini_server.poll() is not None:
            self.popup.setWindowTitle("Start server")
            self.popup.setText("You must start the WGINI server first! Please start it from the system tray above canvas.")
            self.popup.show()
        elif self.wgini_client is not None:
	        self.log.append("Wireless GINI client is already running!")
        else:
	        windowTitle = "Client data"
	        labelText = "Enter wireless client IP:"
	        text, ok = self.inputDialog.getText(self.inputDialog, windowTitle, labelText)

        if ok:
            if not text:
                self.log.append("Nothing entered; starting wireless GINI client cancelled!")
                return False
            else:
                ipportip=text
                if not (socket.inet_aton(str(ipportip))):
                    self.log.append("Invalid entry, starting wireless GINI client cancelled.")
                    return False
                self.wserverIP = get_ip_address('eth1')
                self.wserverPort = '60000'
                wclientIP = str(ipportip)
                try:
                    self.wgini_client= WGINI_Client(self.wserverIP,self.wserverPort,wclientIP)
                    mainWidgets["wgini_client"]=self.wgini_client
                    self.log.append("Wireless GINI client connected at %s" %(ipportip[0]))
                    return True
                except:
                    self.log.append("Starting wireless GINI client failed.")
                    return False
        else:
            return False

    def get_ip_address(ifname):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        return socket.inet_ntoa(fcntl.ioctl(
            s.fileno(),
            0x8915,  # SIOCGIFADDR
            struct.pack('256s', ifname[:15])
        )[20:24])

    def discover(self):
        """
        Add yRouters within range of topology
        """
        if self.wgini_client is None:
            self.log.append("You must connect to the wireless server before you can discover any new devices!")
            if not self.startWGINIClient():
                return

        if self.isRunning() and not self.recovery:
            self.log.append("A topology is currently running, please stop it before discovering any new devices!")
            return

        if isinstance(mainWidgets["canvas"],Tutorial):
            self.log.append("You cannot discover any new devices during this tutorial!")
            return

        if not self.client or not self.client.isConnected():
            self.startClient()

        self.popup.setWindowTitle("yRouter discovery")

        tempList=self.wgini_client.Check()
        scene=self.canvas.scene()

        removed = 0
        for yid, yun in usedyRouters.iteritems():
            if (yun not in tempList) or (yun in tempList and ((yun['MaxWlan'] - yun['CurrWlan']) == 0)):
                self.popup.setText("yRouter_%d is no longer available. It will be removed from the topology." %yid)
                self.popup.show()
                yRouter=scene.findItem(self.device_type + "_%d" %yid)
                yRouter.delete()
                del usedyRouters[yid]
                removed += 1

        found=0
        updated=0
        for yun in tempList:
            openYun = yun['MaxWlan'] - yun['CurrWlan']
            if ((yun['MaxWlan'] - yun['CurrWlan']) == 0):
                if yun['ID'] in usedyRouters.keys():
                    self.popup.setText("yRouter_%d is no longer available. It will be removed from the topology." %yun['ID'])
                    self.popup.show()
                    yRouter = scene.findItem(self.device_type + "_%d" %yun['ID'])
                    yRouter.delete()
                    del usedyRouters[yun['ID']]
                    removed += 1
                else:
                    continue
            elif (yun['ID'] not in yRouters.keys()):
                yRouters[yun['ID']] = yun
                availableyRouters.append(yun)
                found += 1
            else:
                if not yRouters[yun['ID']] == yun:
                    yRouters[yun['ID']] = yun
                    yRouter = (y for y in availableyRouters if y['ID'] == yun['ID'])
                    availableyRouters.remove(yRouter)
                    availableyRouters.append(yun)
                    updated +=1
        availableyRouters.sort(key=lambda YunEntity: YunEntity['ID'])
        if found == 0 and updated == 0 and removed == 0:
            text = "No yRouters found, updated, or removed."
        else:
            if found == 0:
                text = "No yRouters found, "
            else:
                text = "%d yRouters found, " %found
            if updated == 0:
                text += "no yRouters updated, "
            else:
                text += "%d yRouters updated, " %updated
            if removed == 0:
                text += "no yRouters removed."
            else:
                text += "%d yRouters removed." %removed
            if mainWidgets["drop"].commonDropArea.yRouterDrop is not None:
                mainWidgets["drop"].commonDropArea.yRouterDrop.update()
            if mainWidgets["drop"].netDropArea.yRouterDrop is not None:
                mainWidgets["drop"].netDropArea.yRouterDrop.update()

        self.log.append(text)

    def arrange(self):
        """
        Rearrange the topology based on the distance between nodes.
        """
        if self.isRunning():
            self.log.append("Cannot arrange while running!")
            return

        if isinstance(mainWidgets["canvas"], Tutorial):
            mainWidgets["log"].append("Cannot arrange during the tutorial!")
            return

        options["elasticMode"] = not options["elasticMode"]

    def about(self):
        """
        Show the about window.
        """
        QtGui.QMessageBox.about(self,
                                self.tr("About %s %s"
                                    % (Core.globals.PROG_NAME,
                                       Core.globals.PROG_VERSION)),
                                self.tr("<b>%s %s</b><br>Written by Daniel Ng<br>under the supervision of Muthucumaru Maheswaran"
                                    % (Core.globals.PROG_NAME,
                                       Core.globals.PROG_VERSION)))

    def createActions(self):
        """
        Create the actions used in the menus and toolbars.
        """
        self.newSceneAct = QtGui.QAction(QtGui.QIcon(environ["images"] + "new.png"), self.tr("&New"), self)
        self.newSceneAct.setShortcut(self.tr("Ctrl+N"))
        self.newSceneAct.setStatusTip(self.tr("Create a new topology"))
        self.connect(self.newSceneAct, QtCore.SIGNAL("triggered()"), self.newScene)

        self.closeAct = QtGui.QAction(QtGui.QIcon(environ["images"] + "close.png"), self.tr("&Close"), self)
        self.closeAct.setShortcut(self.tr("Ctrl+W"))
        self.closeAct.setStatusTip(self.tr("Close the current topology"))
        self.connect(self.closeAct, QtCore.SIGNAL("triggered()"), self.closeTopology)

        self.loadAct = QtGui.QAction(QtGui.QIcon(environ["images"] + "open.png"), self.tr("&Open..."), self)
        self.loadAct.setShortcut(self.tr("Ctrl+O"))
        self.loadAct.setStatusTip(self.tr("Load a topology"))
        self.connect(self.loadAct, QtCore.SIGNAL("triggered()"), self.loadTopology)

        self.saveAct = QtGui.QAction(QtGui.QIcon(environ["images"] + "save.png"), self.tr("&Save..."), self)
        self.saveAct.setShortcut(self.tr("Ctrl+S"))
        self.saveAct.setStatusTip(self.tr("Save the current topology"))
        self.connect(self.saveAct, QtCore.SIGNAL("triggered()"), self.saveTopology)

        self.saveAsAct = QtGui.QAction(QtGui.QIcon(environ["images"] + "save.png"), self.tr("&Save As..."), self)
        self.saveAsAct.setShortcut(self.tr("Ctrl+Shift+S"))
        self.saveAsAct.setStatusTip(self.tr("Save the current topology under a given filename"))
        self.connect(self.saveAsAct, QtCore.SIGNAL("triggered()"), self.saveTopologyAs)

        self.sendFileAct = QtGui.QAction(QtGui.QIcon(environ["images"] + "send.png"), self.tr("&Send File..."), self)
        self.sendFileAct.setShortcut(self.tr("Ctrl+F"))
        self.sendFileAct.setStatusTip(self.tr("Choose a file to send to the server"))
        self.connect(self.sendFileAct, QtCore.SIGNAL("triggered()"), self.sendFile)

        self.exportAct = QtGui.QAction(QtGui.QIcon(environ["images"] + "export.png"), self.tr("&Export..."), self)
        self.exportAct.setShortcut(self.tr("Ctrl+P"))
        self.exportAct.setStatusTip(self.tr("Export the current topology as an image"))
        self.connect(self.exportAct, QtCore.SIGNAL("triggered()"), self.export)

        self.copyAct = QtGui.QAction(QtGui.QIcon(environ["images"] + "copy.png"), self.tr("&Copy"), self)
        self.copyAct.setShortcut(self.tr("Ctrl+C"))
        self.copyAct.setStatusTip(self.tr("Copy the selected text"))
        self.connect(self.copyAct, QtCore.SIGNAL("triggered()"), self.copy)

        # self.startWGINIClientAct = QtGui.QAction(QtGui.QIcon(environ["images"] + "startClient.png"), self.tr("&Start WGINI Client"), self)
        # self.startWGINIClientAct.setShortcut(self.tr("Ctrl+W"))
        # self.startWGINIClientAct.setStatusTip(self.tr("Start wireless GINI client"))
        # self.connect(self.startWGINIClientAct, QtCore.SIGNAL("triggered()"), self.startWGINIClient)

    	self.discoverAct = QtGui.QAction(QtGui.QIcon(environ["images"] + "discover.png"), self.tr("&Discover"), self)
    	self.discoverAct.setShortcut(self.tr("Ctrl+Shift+Y"))
    	self.discoverAct.setStatusTip(self.tr("Discover nearby yRouters"))
    	self.connect(self.discoverAct, QtCore.SIGNAL("triggered()"), self.discover)

        self.compileAct = QtGui.QAction(QtGui.QIcon(environ["images"] + "compile.png"), self.tr("&Compile"), self)
        self.compileAct.setShortcut(self.tr("Ctrl+E"))
        self.compileAct.setStatusTip(self.tr("Compile the current topology"))
        self.connect(self.compileAct, QtCore.SIGNAL("triggered()"), self.compile)

        self.runAct = QtGui.QAction(QtGui.QIcon(environ["images"] + "run.png"), self.tr("&Run"), self)
        self.runAct.setShortcut(self.tr("Ctrl+R"))
        self.runAct.setStatusTip(self.tr("Run the current topology"))
        self.connect(self.runAct, QtCore.SIGNAL("triggered()"), self.run)

        self.stopAct = QtGui.QAction(QtGui.QIcon(environ["images"] + "stop.png"), self.tr("&Stop"), self)
        self.stopAct.setShortcut(self.tr("Ctrl+D"))
        self.stopAct.setStatusTip(self.tr("Stop the current topology"))
        self.connect(self.stopAct, QtCore.SIGNAL("triggered()"), self.stop)

        self.startServerAct = QtGui.QAction(QtGui.QIcon(environ["images"] + "startServer.png"), self.tr("&Start Server"), self)
        self.startServerAct.setShortcut(self.tr("Ctrl+T"))
        self.startServerAct.setStatusTip(self.tr("Start the server"))
        self.connect(self.startServerAct, QtCore.SIGNAL("triggered()"), self.startBackend)

        # self.startwServerAct = QtGui.QAction(QtGui.QIcon(environ["images"] + "startServer.png"), self.tr("&Start WGINI Server"), self)
        # self.startwServerAct.setShortcut(self.tr("Ctrl+W"))
        # self.startwServerAct.setStatusTip(self.tr("Start the WGINI server"))
        # self.connect(self.startwServerAct, QtCore.SIGNAL("triggered()"), self.startWServer)

        self.optionsAct = QtGui.QAction(QtGui.QIcon(environ["images"] + "options.png"), self.tr("&Options"), self)
        self.optionsAct.setShortcut(self.tr("F2"))
        self.optionsAct.setStatusTip(self.tr("Show the options window"))
        self.connect(self.optionsAct, QtCore.SIGNAL("triggered()"), self.config)

        self.arrangeAct = QtGui.QAction(QtGui.QIcon(environ["images"] + "arrange.png"), self.tr("&Arrange"), self)
        self.arrangeAct.setShortcut(self.tr("Ctrl+A"))
        self.arrangeAct.setStatusTip(self.tr("Arranges the current topology"))
        self.connect(self.arrangeAct, QtCore.SIGNAL("triggered()"), self.arrange)

        self.resetLayoutAct = QtGui.QAction(QtGui.QIcon(environ["images"] + "layout.png"), self.tr("Reset Layout"), self)
        self.resetLayoutAct.setStatusTip(self.tr("Reset dock windows to the saved layout"))
        self.connect(self.resetLayoutAct, QtCore.SIGNAL("triggered()"), self.resetLayout)

        self.expandSceneAct = QtGui.QAction(QtGui.QIcon(environ["images"] + "expand.png"), self.tr("Expand Scene"), self)
        self.expandSceneAct.setStatusTip(self.tr("Expand the scene for more space"))
        self.connect(self.expandSceneAct, QtCore.SIGNAL("triggered()"), self.expandScene)

        self.quitAct = QtGui.QAction(QtGui.QIcon(environ["images"] + "exit.png"), self.tr("&Quit"), self)
        self.quitAct.setShortcut(self.tr("Ctrl+Q"))
        self.quitAct.setStatusTip(self.tr("Quit the application"))
        self.connect(self.quitAct, QtCore.SIGNAL("triggered()"), self.quit)

        self.newProjectAct = QtGui.QAction(QtGui.QIcon(environ["images"] + "new.png"), self.tr("&New"), self)
        self.newProjectAct.setShortcut(self.tr("Ctrl+Shift+N"))
        self.newProjectAct.setStatusTip(self.tr("Create a new project"))
        self.connect(self.newProjectAct, QtCore.SIGNAL("triggered()"), self.newProject)

        self.openProjectAct = QtGui.QAction(QtGui.QIcon(environ["images"] + "open.png"), self.tr("&Open"), self)
        self.openProjectAct.setShortcut(self.tr("Ctrl+Shift+O"))
        self.openProjectAct.setStatusTip(self.tr("Open an existing project"))
        self.connect(self.openProjectAct, QtCore.SIGNAL("triggered()"), self.openProject)

        self.closeProjectAct = QtGui.QAction(QtGui.QIcon(environ["images"] + "close.png"), self.tr("&Close"), self)
        self.closeProjectAct.setShortcut(self.tr("Ctrl+Shift+W"))
        self.closeProjectAct.setStatusTip(self.tr("Close the current project"))
        self.connect(self.closeProjectAct, QtCore.SIGNAL("triggered()"), self.closeProject)

        self.tutorialAct = QtGui.QAction(QtGui.QIcon(environ["images"] + "tutorial.png"), self.tr("&Tutorial"), self)
        self.connect(self.tutorialAct, QtCore.SIGNAL("triggered()"), self.startTutorial)

        self.faqAct = QtGui.QAction(QtGui.QIcon(environ["images"] + "help.png"), self.tr("&FAQ"), self)
        self.connect(self.faqAct, QtCore.SIGNAL("triggered()"), self.faq)

        self.aboutAct = QtGui.QAction(QtGui.QIcon(environ["images"] + "giniLogo.png"), self.tr("&About"), self)
        self.aboutAct.setStatusTip(self.tr("Show the application's About box"))
        self.connect(self.aboutAct, QtCore.SIGNAL("triggered()"), self.about)

        self.aboutQtAct = QtGui.QAction(QtGui.QIcon(environ["images"] + "Qt-logo.png"), self.tr("About &Qt"), self)
        self.aboutQtAct.setStatusTip(self.tr("Show the Qt library's About box"))
        self.connect(self.aboutQtAct, QtCore.SIGNAL("triggered()"),
                     QtGui.qApp, QtCore.SLOT("aboutQt()"))

    def createMenus(self):
        """
        Create the menus with actions.
        """
        self.fileMenu = self.menuBar().addMenu(self.tr("&File"))
        self.fileMenu.setPalette(defaultOptions["palette"])
        self.fileMenu.addAction(self.newSceneAct)
        self.fileMenu.addAction(self.loadAct)
        self.fileMenu.addAction(self.saveAct)
        self.fileMenu.addAction(self.saveAsAct)
        self.fileMenu.addAction(self.sendFileAct)
        self.fileMenu.addAction(self.exportAct)
        self.fileMenu.addAction(self.closeAct)
        self.fileMenu.addSeparator()
        self.fileMenu.addAction(self.quitAct)

        self.projectMenu = self.menuBar().addMenu(self.tr("&Project"))
        self.projectMenu.setPalette(defaultOptions["palette"])
        self.projectMenu.addAction(self.newProjectAct)
        self.projectMenu.addAction(self.openProjectAct)
        self.projectMenu.addAction(self.closeProjectAct)

        self.editMenu = self.menuBar().addMenu(self.tr("&Edit"))
        self.editMenu.setPalette(defaultOptions["palette"])
        self.editMenu.addAction(self.copyAct)
        self.editMenu.addAction(self.arrangeAct)
        self.editMenu.addAction(self.resetLayoutAct)
        self.editMenu.addAction(self.expandSceneAct)

        self.runMenu = self.menuBar().addMenu(self.tr("&Run"))
        self.runMenu.setPalette(defaultOptions["palette"])
        # self.runMenu.addAction(self.startWGINIClientAct)
        self.runMenu.addAction(self.discoverAct)
        self.runMenu.addAction(self.compileAct)
        self.runMenu.addAction(self.runAct)
        self.runMenu.addAction(self.stopAct)
        self.runMenu.addAction(self.startServerAct)
        # self.runMenu.addAction(self.startwServerAct)

        self.configMenu = self.menuBar().addMenu(self.tr("&Config"))
        self.configMenu.setPalette(defaultOptions["palette"])
        self.configMenu.addAction(self.optionsAct)

        self.menuBar().addSeparator()

        self.helpMenu = self.menuBar().addMenu(self.tr("&Help"))
        self.helpMenu.setPalette(defaultOptions["palette"])
        self.helpMenu.addAction(self.tutorialAct)
        self.helpMenu.addAction(self.faqAct)
        self.helpMenu.addAction(self.aboutAct)
        self.helpMenu.addAction(self.aboutQtAct)

    def createPopupMenu(self):
        """
        Customize the popup menu so that it is visible.
        """
        popupMenu = QtGui.QMainWindow.createPopupMenu(self)
        popupMenu.setPalette(defaultOptions["palette"])
        return popupMenu

    def createToolBars(self):
        """
        Create the toolbars with actions.
        """
        self.fileToolBar = self.addToolBar(self.tr("File"))
        self.fileToolBar.addAction(self.newSceneAct)
        self.fileToolBar.addAction(self.loadAct)
        self.fileToolBar.addAction(self.saveAct)
        self.fileToolBar.addAction(self.sendFileAct)
        self.fileToolBar.addAction(self.exportAct)
        self.fileToolBar.addAction(self.closeAct)

        self.editToolBar = self.addToolBar(self.tr("Edit"))
        self.editToolBar.addAction(self.copyAct)
        self.editToolBar.addAction(self.resetLayoutAct)
        self.editToolBar.addAction(self.expandSceneAct)

        self.runToolBar = self.addToolBar(self.tr("Run"))
        self.runToolBar.addAction(self.startServerAct)
        self.runToolBar.addAction(self.discoverAct)
        self.runToolBar.addAction(self.compileAct)
        self.runToolBar.addAction(self.runAct)
        self.runToolBar.addAction(self.stopAct)
        # self.runToolBar.addAction(self.startWGINIClientAct)
        # self.runToolBar.addAction(self.startwServerAct)

    def createStatusBar(self):
        """
        Create the status bar.
        """
        self.statusBar().showMessage(self.tr("Ready"))

    def createProgressBar(self):
        """
        Create the progress bar.
        """
        self.progressBar = QtGui.QProgressBar()
        self.progressBar.setRange(0, 10000)
        self.progressBar.setValue(0)

        self.statusBar().addPermanentWidget(self.progressBar)
        self.progressBar.show()

    def getDeviceCount(self, alive=False):
        """
        Return the interfaceable device count, or the alive ones if alive=True.
        """
        from Core.Interfaceable import Interfaceable

        count = 0.0
        for item in self.canvas.scene().items():
            if isinstance(item, Interfaceable):
                if item.device_type != "REALM":
                    if alive and item.status in ("", "dead"):
                        continue
                    count += 1.0

        return count

    def updateProgressBar(self):
        """
        Update the progress bar.
        """
        maxVal = self.progressBar.maximum()
        finalVal = (self.getDeviceCount(True) / self.getDeviceCount()) * maxVal

        if finalVal < 0:
            finalVal = 0

        self.progressBar.setValue(finalVal)

        if finalVal == 0:
            return True

        return False

    def createConfigWindows(self):
        """
        Create the options window.
        """
        self.configWindow = ConfigDialog(self)

    def createDockWindows(self):
        """
        Create the dock windows: dropbar, log, properties, interfaces, routes.
        """
        self.log = LogWindow(self.tr("Log"), self)
        self.log.append("Welcome to %s %s!\n"
                % (Core.globals.PROG_NAME, Core.globals.PROG_VERSION))
        self.log.append("To open an existing topology, please click the 'Open' icon from the tray above canvas!")
        self.log.setGeometry(QtCore.QRect(0, 0, 800, 114))
        mainWidgets["log"] = self.log

        self.dropbar = DropBar(self.tr("Components"), self)
        self.dropbar.setGeometry(QtCore.QRect(0, 0, 129, 390))
        mainWidgets["drop"] = self.dropbar

        self.properties = PropertiesWindow(self)
        self.properties.setWindowTitle("Properties")
        mainWidgets["properties"] = self.properties

        self.interfaces = InterfacesWindow(self)
        self.interfaces.setWindowTitle("Interfaces")
        mainWidgets["interfaces"] = self.interfaces

        self.routes = RoutesWindow(self.interfaces, self)
        self.routes.setWindowTitle("Routes")
        mainWidgets["routes"] = self.routes

        self.tm = TaskManagerWindow(self)
        self.tm.setWindowTitle("Task Manager")
        mainWidgets["tm"] = self.tm

        self.debugWindow = QtGui.QDockWidget(self.tr("Debug Window"))
        self.debugWindow.setWidget(DebugWindow(self))

        self.docks = {"Components":self.dropbar, "Log":self.log, "Properties":self.properties, "Interfaces":self.interfaces, "Routes":self.routes, "Task Manager":self.tm}

        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.dropbar)
        self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.log)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.properties)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.interfaces)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.routes)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.tm)

        self.tm.setFloating(True)
        self.routes.setFloating(True)
        self.debugWindow.setFloating(True)

    def createPopupWindows(self):
        """
        Create the different popup windows.
        """
        self.exportWindow = ExportWindow(self)
        self.sendWindow = SendDirectoryWindow(self)
        self.popup = QtGui.QMessageBox(self)
        self.popup.setIcon(QtGui.QMessageBox.Warning)
        self.popup.setWindowIcon(QtGui.QIcon(environ["images"]+"giniLogo.png"))
        mainWidgets["popup"] = self.popup
        # specific dialog for client IP and port input
        self.inputDialog = QtGui.QInputDialog(self)
        self.inputDialog.setWindowIcon(QtGui.QIcon(environ["images"]+"giniLogo.png"))
        mainWidgets["dialog"] = self.inputDialog

    def keyPressEvent(self, event):
        """
        Handle specific shortcut keys.
        """
        key = event.key()
        scene = self.canvas.scene()
        if key == QtCore.Qt.Key_Escape:
            scene.clearSelection()
        elif key == QtCore.Qt.Key_Delete:
            for item in scene.selectedItems():
                item.delete()
        elif key == QtCore.Qt.Key_C:
            items = scene.items()
            if not items:
                return
            selected = scene.selectedItems()
            scene.clearSelection()
            if selected:
                index = items.index(selected[0])
                items[index - 1].setSelected(True)
            else:
                items[0].setSelected(True)
        elif key == QtCore.Qt.Key_H:
            for dock in self.docks.values():
                dock.setFloating(not dock.isFloating())
        elif key == QtCore.Qt.Key_F10:
            self.debugWindow.show()

    def cleanup(self):
        if self.server != None:
            self.server.kill()

class DebugWindow(QtGui.QWidget):
    def __init__(self, parent):
        QtGui.QWidget.__init__(self)

        self.parent = parent
        self.layout = QtGui.QVBoxLayout()
        #self.list = QtGui.QListWidget()
        self.button = QtGui.QPushButton("Execute")
        self.lineedit = QtGui.QLineEdit()
        #self.layout.addWidget(self.list)
        self.layout.addWidget(self.lineedit)
        self.layout.addWidget(self.button)
        self.setLayout(self.layout)

        self.windows = {}
        for key, val in mainWidgets.iteritems():
            if key != "app" and key != "client" and val != None:
                self.windows[key] = val

        self.connect(self.button, QtCore.SIGNAL("clicked()"), self.execute)

    def fill(self):
        scene = mainWidgets["canvas"].scene()
        for i in range(125):
            scene.addItem(Mach())

    def execute(self):
        canvas = mainWidgets["canvas"]
        scene = canvas.scene()
        #self.list.clear()
        #for item in scene.items():
        #    try:
        #        self.list.addItem(item.getName() + "(%d,%d)" % (item.pos().x(), item.pos().y()))
        #    except:
        #        pass
        #for name, window in self.windows.iteritems():
        #    self.list.addItem(name + ":" + str(window.geometry()))

        text = str(self.lineedit.text())
        if text:
            lines = text.split(";")
            for line in lines:
                print eval(line)

        if isinstance(canvas, Tutorial):
            canvas.next()
