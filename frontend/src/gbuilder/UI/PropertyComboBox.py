from PyQt4 import QtCore, QtGui

class PropertyComboBox(QtGui.QComboBox):

    def __init__(self, item,PropertiesWindow, prop, values, parent = None):

        QtGui.QComboBox.__init__(self, parent)

        self.item = item
        self.PropertiesWindow=PropertiesWindow

        self.addItems(values)

        if values:

            self.setCurrentIndex(self.item.hostIndex)

        self.connect(self, QtCore.SIGNAL("currentIndexChanged(int)"), self.changeIndex)



    def changeIndex(self, index):

        self.item.hostIndex = index
	text=self.currentText ()
	realip=self.item.hostsproperty[str(text)].ip
	self.item.setProperty("realmachineIPv4", realip)
	realmac=self.item.hostsproperty[str(text)].mac
 	self.item.setProperty("realmachineMac", realmac)
	realport=self.item.hostsproperty[str(text)].port
        self.item.setProperty("realmachinePort", realport)
	from Properties import PropertiesWindow
	self.PropertiesWindow.display()
