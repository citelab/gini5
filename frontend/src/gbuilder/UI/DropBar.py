"""The drag and drop toolbar"""

from PyQt4 import QtCore, QtGui
from Node import *
from Core.globals import options
from Dockable import *

class DropArea(QtGui.QGraphicsView):
    def __init__(self, itemTypes):
        """
        Create a page of droppable nodes.
        """
        QtGui.QGraphicsView.__init__(self)
        self.itemTypes = itemTypes
        self.yRouterDrop = None

        scene = QtGui.QGraphicsScene(self)
        scene.setItemIndexMethod(QtGui.QGraphicsScene.NoIndex)
        self.setScene(scene)
        self.setRenderHint(QtGui.QPainter.Antialiasing)
        self.setTransformationAnchor(QtGui.QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QtGui.QGraphicsView.AnchorViewCenter)
        self.setViewportUpdateMode(self.FullViewportUpdate)

    def refactorLocation(self, location):
        """
        Resize and reposition nodes based on dock location.
        """
        scene = self.scene()
        scene.clear()

        # print location, QtCore.Qt.LeftDockWidgetArea, QtCore.Qt.RightDockWidgetArea
        # TODO: Fix icon spacing here

        if location == QtCore.Qt.LeftDockWidgetArea \
            or location == QtCore.Qt.RightDockWidgetArea:
            lastnode = None
            for i in range(len(self.itemTypes)):
                node = DropItem(self.itemTypes[i])
                if lastnode:
                    node.setPos(0, lastnode.pos().y() + 75)
                else:
                    node.setPos(0, 0)
                scene.addItem(node)
                lastnode = node

            self.setSceneRect(-35, -35, 75, lastnode.pos().y() + 100)

        else:
            lastnode = None
            for i in range(len(self.itemTypes)):
                node = DropItem(self.itemTypes[i])
                if lastnode:
                    node.setPos(lastnode.pos().x() + 75, 0)
                else:
                    node.setPos(0, 0)
                scene.addItem(node)
                lastnode = node

            self.setSceneRect(0, -35, 400, 75)

class DropBar(Dockable):
    def __init__(self, title, parent):
        """
        Create a drag and drop toolbar.
        """
        Dockable.__init__(self, title, parent)
        self.parent = parent

        self.toolBox = QtGui.QToolBox()
        self.setWidget(self.toolBox)

        self.commonDropArea = DropArea(commonTypes)
        self.hostDropArea = DropArea(hostTypes.keys())
        self.netDropArea = DropArea(netTypes.keys())

        self.toolBox.addItem(self.commonDropArea, self.tr("&Common Elements"))
        self.toolBox.addItem(self.hostDropArea, self.tr("&Host Elements"))
        self.toolBox.addItem(self.netDropArea, self.tr("&Net Elements"))

        self.connect(self.toolBox,
                     QtCore.SIGNAL("currentChanged(int)"),
                     self.toolChanged)

        self.connect(self, QtCore.SIGNAL("dockLocationChanged(Qt::DockWidgetArea)"), self.locationChanged)

        self.toolChanged(self.toolBox.currentIndex())
        self.setFocusPolicy(QtCore.Qt.NoFocus)

    def toolChanged(self, index):
        """
        Handle the page change.
        """
        widget = self.widget()
        droparea = widget.currentWidget()
        droparea.refactorLocation(self.location)

    def locationChanged(self, location):
        """
        Handle the dock location change.
        """
        droparea = self.widget().currentWidget()
        droparea.refactorLocation(location)
        Dockable.locationChanged(self, location)


"""Not being used"""
class DropBar2(QtGui.QDockWidget):
    def __init__(self, title, parent):
        QtGui.QDockWidget.__init__(self, title, parent)
        self.parent = parent
        self.currentLocation = None

        self.tabWidget = QtGui.QTabWidget()
        self.tabWidget.setTabPosition(QtGui.QTabWidget.West)
        self.setWidget(self.tabWidget)

        dropArea = DropArea(hostTypes.keys())
        dropArea2 = DropArea(netTypes.keys())
        dropArea3 = DropArea(customTypes.keys())
        self.tabWidget.addTab(dropArea, self.tr("&Host Element"))
        self.tabWidget.addTab(dropArea2, self.tr("&Net Element"))
        self.tabWidget.addTab(dropArea3, self.tr("&Custom Element"))

        self.connect(self,
                     QtCore.SIGNAL("dockLocationChanged(Qt::DockWidgetArea)"),
                     self.locationChanged)
        self.connect(self.tabWidget,
                     QtCore.SIGNAL("currentChanged(int)"),
                     self.tabChanged)

    def locationChanged(self, location):
        self.sizeHint()
        widget = self.widget()
        droparea = widget.currentWidget()
        droparea.refactorLocation(location, self.parent)
        self.currentLocation = location

        if location == QtCore.Qt.LeftDockWidgetArea:
            self.tabWidget.setTabPosition(QtGui.QTabWidget.West)
        elif location == QtCore.Qt.RightDockWidgetArea:
            self.tabWidget.setTabPosition(QtGui.QTabWidget.East)
        elif location == QtCore.Qt.TopDockWidgetArea:
            self.tabWidget.setTabPosition(QtGui.QTabWidget.North)
        elif location == QtCore.Qt.BottomDockWidgetArea:
            self.tabWidget.setTabPosition(QtGui.QTabWidget.South)

    def tabChanged(self, index):
        widget = self.widget()
        droparea = widget.currentWidget()
        droparea.refactorLocation(self.currentLocation, self.parent)
