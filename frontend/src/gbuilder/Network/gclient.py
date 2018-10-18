from PyQt4 import QtNetwork, QtCore
import os, sys, time
from Core.globals import environ, mainWidgets

class Client(QtCore.QThread):
    def __init__(self, parent = None):
        QtCore.QThread.__init__(self)
        self.tcpSocket = QtNetwork.QTcpSocket(parent)
        self.connected = False
        self.leftovers = ""
        self.readlength = 0
        self.connecting = False

        if not parent:
            return
        parent.connect(self.tcpSocket, QtCore.SIGNAL("readyRead()"), self.read)
        parent.connect(self.tcpSocket, QtCore.SIGNAL("connected()"), self.setConnected)
        parent.connect(self.tcpSocket, QtCore.SIGNAL("error(QAbstractSocket::SocketError)"), self.displayError)

        global client
        client = self

    def isReady(self):
        return self.tcpSocket.bytesToWrite() == 0

    def connectTo(self, ip, port, attempts=1):
        connected = False
        tries = 0
        self.connecting = True

        while not connected and tries != attempts:
            self.tcpSocket.abort()
            self.tcpSocket.connectToHost(ip, port)
            connected = self.tcpSocket.waitForConnected(1500)
            tries += 1

        self.connecting = False
        print "-- gclient output --"

    def isConnected(self):
        return self.connected

    def setConnected(self):
        self.connected = True

    def displayError(self, socketError):
        if self.connecting:
            return

        main = mainWidgets["main"]
        if main.isRunning():
            main.setRecovery(True)
            mainWidgets["log"].append("The connection was lost while a topology was running.\nYou can attempt to re-establish the connection by restarting the server.  You can then press run to resume the previous running topology, or stop to stop it.")
            mainWidgets["canvas"].scene().pauseRefresh()

        if socketError ==  QtNetwork.QAbstractSocket.RemoteHostClosedError:
            print "Lost connection to server."
        elif socketError ==  QtNetwork.QAbstractSocket.HostNotFoundError:
            print "The host was not found. Please check the host name and port settings."
        elif socketError ==  QtNetwork.QAbstractSocket.ConnectionRefusedError:
            print "The connection was refused by the peer. Make sure the server is running,"
            print "and check that the host name and port settings are correct."
        else:
            print "The following error occurred: %s." % self.tcpSocket.errorString()

        self.connected = False
        self.terminate()

    def read(self):
        instring = self.waitForMessage(str(self.tcpSocket.readAll()))
        if instring:
            self.process(instring)

    def waitForMessage(self, instring):
        instring = self.leftovers + instring

        if not self.readlength and instring.find(" ") == -1:
            self.leftovers = instring
            return
        else:
            if not self.readlength:
                length, buf = instring.split(" ", 1)
                self.readlength = int(length)
            else:
                buf = instring
            if len(buf) < self.readlength:
                self.leftovers = buf
                return
            else:
                self.leftovers = buf[self.readlength:]
                instring = buf[:self.readlength]
                self.readlength = 0

        return instring

    def process(self, instring):
        if not instring:
            return

        args = ""
        instring = str(instring)

        index = instring.find(" ")
        if index != -1:
            commandType, args = instring.split(" ", 1)
        else:
            commandType = instring

        try:
            command = Command.create(commandType, args)
            command.execute()
        except Exception, inst:
            print type(inst)
            print inst.args
            print "invalid command"
            print commandType, args

        self.process(self.waitForMessage(""))

    def send(self, text):
        length = str(len(text))
        self.tcpSocket.writeData(length + " " + text)

    def disconnect(self):
        self.tcpSocket.disconnectFromHost()

    def run(self):

        while not self.isConnected():
            time.sleep(1)
        print "connected!"

        text = raw_input("gclient> ")
        while text != "exit":
            self.process(text)
            text = raw_input("gclient> ")

        self.disconnect()

"""
class ShellStarter(QtCore.QThread):
    def __init__(self, command):
        QtCore.QThread.__init__(self)
        self.command = str(command)
        self.started = -1

    def startStatus(self):
        return self.started

    def run(self):
        self.started = 0
        os.system(self.command)
        self.started = 1
"""

class Callable:
    def __init__(self, anycallable):
        self.__call__ = anycallable

class Command:
    def __init__(self, args):
        global client
        self.args = args
        self.client = client

    def isolateFilename(self, path):
        return path.split("/")[-1].split("\\")[-1]

    def create(commandType, args):
        return commands[commandType](args)
    create = Callable(create)

class ReceivePathCommand(Command):
    def execute(self):
        print "setting remote path to " + self.args
        environ["remotepath"] = self.args + "/"

class SendFileCommand(Command):
    def execute(self):
        targetDir, path = self.args.split(" ", 1)
        filename = self.isolateFilename(path)
        print "sending file " + filename
        infile = open(path, "rb")
        self.client.send("file " + targetDir + "/" + filename + " " + infile.read())
        infile.close()

class SendStartCommand(Command):
    def execute(self):
        filename = self.isolateFilename(self.args)
        print "sending start " + filename
        self.client.send("start " + filename)

class SendStopCommand(Command):
    def execute(self):
        print "sending stop"
        self.client.send("stop")

class SendKillCommand(Command):
    def execute(self):
        print "killing " + self.args
        self.client.send("kill " + self.args)

class ReceiveDeviceStatusCommand(Command):
    def execute(self):
        scene = mainWidgets["canvas"].scene()
        tm = mainWidgets["tm"]
        device, pid, status = self.args.split(" ", 2)

        name = device
        if device.find("WAP") == 0:
            name = "Wireless_access_point_" + device.split("_")[-1]
        item = scene.findItem(name)
        if item is not None:
            item.setStatus(status)

        tm.update(device, pid, status)

class ReceiveWirelessStatsCommand(Command):
    def execute(self):
        name, stats = self.args.split(" ", 1)
        scene = mainWidgets["canvas"].scene()
        scene.findItem(name).setWirelessStats(stats)

class ReceiveRouterStatsCommand(Command):
    def execute(self):
        name, queue, size, rate = self.args.split(" ", 3)
        scene = mainWidgets["canvas"].scene()
        scene.findItem(name).setRouterStats(queue, size, rate)

class ReceiveYRouterStatsCommand(Command):
    def execute(self):
	name, queue, size, rate = self.args.split(" ", 3)
	scene = mainWidgets["canvas"].scene()
	scene.findItem(name).setYRouterStats(queue, size, rate)

class ReceiveWiresharkCaptureCommand(Command):
    def execute(self):
        name, capture = self.args.split(" ", 1)
        outfile = environ["tmp"] + name + ".out"
        fd = open(outfile, "ab")
        fd.write(capture)
        fd.close()

commands = \
    {
        "start":SendStartCommand,
        "stop":SendStopCommand,
        "path":ReceivePathCommand,
        "file":SendFileCommand,
        "status":ReceiveDeviceStatusCommand,
        "kill":SendKillCommand,
        "wstats":ReceiveWirelessStatsCommand,
        "rstats":ReceiveRouterStatsCommand,
        "yrstats":ReceiveYRouterStatsCommand,
        "wshark":ReceiveWiresharkCaptureCommand
    }
client = None

if __name__ == "__main__":
    app = QtCore.QCoreApplication(sys.argv)
    client.connectTo("localhost", 9000)

    text = raw_input("gclient> ")
    while text:
        client.send(text)
        text = raw_input("gclient> ")
