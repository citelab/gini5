"""Not being used"""

import math
from Core.globals import mainWidgets, environ, defaultOptions

class Arrow(QtGui.QGraphicsItem):
    def __init__(self, angle):
        QtGui.QGraphicsItem.__init__(self)
        self.angle = angle
        self.image = QtGui.QImage(environ["images"] + "arrow.png").transformed(self.getRotationMatrix())
        self.timer = QtCore.QTimer()
        self.tl = QtCore.QTimeLine(1000)
        self.tl.setFrameRange(0, 100)
        self.tl.setLoopCount(0)

    def getRotationMatrix(self):
        m11 = math.cos(self.angle)
        m12 = -math.sin(self.angle)
        m21 = math.sin(self.angle)
        m22 = math.cos(self.angle)
        return QtGui.QMatrix(m11, m12, m21, m22, 0, 0)

    def start(self):
        self.a = QtGui.QGraphicsItemAnimation()
        self.a.setItem(self)
        self.a.setTimeLine(self.tl)
        self.a.setTranslationAt(1, -math.cos(self.angle) * 20, math.sin(self.angle) * 20)
        self.tl.start()

    def paint(self, painter, option, widget):
        painter.drawImage(QtCore.QPoint(-self.image.width()/2, -self.image.height()/2), self.image)

    def boundingRect(self):
        rect = self.image.rect()
        return QtCore.QRectF(rect.left() - rect.width()/2, rect.top() - rect.height()/2, rect.right(), rect.bottom())


class Overlay(QtGui.QGraphicsView):#QtGui.QSplashScreen):
    def __init__(self, parent = None):
        #pixmap = QtGui.QPixmap(mainWidgets["canvas"].width(), mainWidgets["canvas"].height())
        #QtGui.QSplashScreen.__init__(self, parent, pixmap)#, QtCore.Qt.WindowStaysOnTopHint)
        QtGui.QGraphicsView.__init__(self, parent)

        p = defaultOptions["palette"]
        brush = QtGui.QBrush(QtGui.QColor(0,0,0,0))
        palette = QtGui.QPalette(p.windowText(), p.button(), p.light(), p.dark(), p.mid(), p.text(), p.brightText(), brush, p.window())
        self.setPalette(palette)

        self.scene = QtGui.QGraphicsScene()
        self.setScene(self.scene)
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.FramelessWindowHint)

        self.setWindowOpacity(0.4)
        self.show()

        self.addArrow(math.pi, QtCore.QPointF(-150,0))
        self.addArrow(0, QtCore.QPointF(150,75))
        self.addArrow(0, QtCore.QPointF(150,-75))
        self.addArrow(math.pi / 2, QtCore.QPointF(100,-145))
        self.addArrow(3 * math.pi / 2, QtCore.QPointF(0,145))
        self.addArrow(math.pi / 2, QtCore.QPointF(-125,-145))

    def addArrow(self, angle, pos):
        arrow = Arrow(angle)
        self.scene.addItem(arrow)
        arrow.setPos(pos)
        arrow.start()

    def dragEnterEvent(self, event):
        event.setAccepted(True)

    def dropEvent(self, event):
        mainWidgets["canvas"].dropEvent(event)

    def dragMoveEvent(self, event):
        pass

    def dragLeaveEvent(self, event):
        pass

    def mousePressEvent(self, event):
        mainWidgets["canvas"].mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        mainWidgets["canvas"].mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        mainWidgets["canvas"].mouseDoubleClickEvent(event)

    def mouseMoveEvent(self, event):
        mainWidgets["canvas"].mouseMoveEvent(event)

    def wheelEvent(self, event):
        mainWidgets["canvas"].wheelEvent(event)

    def keyPressEvent(self, event):
        mainWidgets["canvas"].keyPressEvent(event)

    def keyReleaseEvent(self, event):
        mainWidgets["canvas"].keyReleaseEvent(event)

    """
    def createTutorial(self):
        self.overlay = Overlay(mainWidgets["main"])
        self.overlay.setWindowModality(QtCore.Qt.WindowModal)
        self.refitOverlay()

    def refitOverlay(self):
        if not self.overlay:
            return
        geo = mainWidgets["canvas"].geometry()
        pos = mainWidgets["canvas"].mapToGlobal(geo.topLeft())
        self.overlay.setGeometry(pos.x(), pos.y(), geo.width(), geo.height())

    def resizeEvent(self, event):
        QtGui.QTabWidget.resizeEvent(self, event)
        self.refitOverlay()
    def moveEvent(self, event):
        QtGui.QTabWidget.moveEvent(self, event)
        self.refitOverlay()
    """
