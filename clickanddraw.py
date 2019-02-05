from PyQt5 import QtCore, QtGui, QtWidgets
from collections import namedtuple


Rect = namedtuple('Rect','x0 y0 xf yf')

class QDragPoint(QtWidgets.QGraphicsEllipseItem):
    def __init__(self, x, y, traceline = None, r = 8):
        super(QtWidgets.QGraphicsEllipseItem,self).__init__(x-r/2, y-r/2, r, r)
        self.setAcceptDrops(True)
        self._x = x
        self._y = y
        self.x = x
        self.y = y
        self.traceline = traceline
        self.next = None 
        self.prev = None
        self.setZValue(9999)
        self.setBrush(QtGui.QBrush(QtGui.QColor("white")))
        self._normalPen = QtGui.QPen(QtGui.QColor("black"))
        self._highlightPen = QtGui.QPen(QtGui.QColor("black"))
        self._highlightPen.setWidth(2)

    def setScenePos(self,x,y):
        self.setPos(x-self._x,y-self._y)
        if self.traceline:
            x1 = self.traceline.line().x1()
            y1 = self.traceline.line().y1()
            self.traceline.setLine(x1,y1,x,y)
        if self.next and self.next.traceline:
            x2 = self.next.traceline.line().x2()
            y2 = self.next.traceline.line().y2()
            self.next.traceline.setLine(x,y,x2,y2)
        self.x = x
        self.y = y

    def highlight(self):
        self.setPen(self._highlightPen)

    def unhighlight(self):
        self.setPen(self._normalPen)


GRID_STEP = 40
class QCDScene(QtWidgets.QGraphicsScene):
    def __init__(self,parent,x0=-800, y0=0, xf= 0, yf = 240):
        super(QtWidgets.QGraphicsScene,self).__init__(parent)
        self.parent = parent
        self.traceline = None
        self.head = QDragPoint(-GRID_STEP,0)
        self.addItem(self.head)
        self.tail = self.head
        self._moved = False
        self._mover = None 
        self._pen = QtGui.QPen(QtGui.QColor("red"))
        self._pen.setWidth(4)

        self.rect = Rect(x0, y0, xf, yf)
        self.setSceneRect(x0-GRID_STEP,y0-GRID_STEP,GRID_STEP+xf-x0,GRID_STEP+yf-y0)
        self.drawGrid()


    def drawGrid(self):
        gridpen = QtGui.QPen(QtGui.QColor(0,0,0,100))
        gridpen.setDashPattern([4,5])
        gridpen.setWidth(2)
        for i in range(self.rect.x0, self.rect.xf,GRID_STEP):
            self.addLine(i,self.rect.y0,i,self.rect.yf,gridpen)

        for i in range(self.rect.y0, self.rect.yf+GRID_STEP,GRID_STEP):
            self.addLine(self.rect.x0,i,self.rect.xf-GRID_STEP,i,gridpen)


    def mousePressEvent(self, event):
        if self._mover:
            self._mover.unhighlight()
        self._mover = None
        self._moving = False
        if event.buttons() == QtCore.Qt.LeftButton:
            self._mover = self.itemAt(event.scenePos(),QtGui.QTransform())
            if not isinstance(self._mover,QDragPoint):
                self._mover = None
                self._moving = True
            if self._mover:
                self._mover.highlight()
        elif event.buttons() == QtCore.Qt.RightButton:
            self._mover = self.itemAt(event.scenePos(),QtGui.QTransform())
            if isinstance(self._mover,QDragPoint):
                self._removeMover()

    def _removeMover(self):
        if self._mover == self.head:
            return
        self.removeItem(self._mover)
        self.removeItem(self._mover.traceline)
        if self._mover.next and self._mover.next.traceline:
            self.removeItem(self._mover.next.traceline)

        if self._mover.prev and self._mover.next:
            self._mover.next.traceline = self.addLine(
                    self._mover.prev.x, self._mover.prev.y,
                    self._mover.next.x, self._mover.next.y,self._pen)

        if self._mover.next:
            self._mover.next.prev = self._mover.prev
        if self._mover.prev:
            self._mover.prev.next = self._mover.next

        if self._mover == self.tail:
            self.tail = self._mover.prev

        self._mover = None
        
    def mouseDoubleClickEvent(self, event):
        """ Append a new line segment at the clicked node """
        pos = event.scenePos()
        if self._mover:
            self._mover.unhighlight()
            new_mover = QDragPoint(pos.x(),pos.y())
            new_mover.traceline = self.addLine(self._mover.x,self._mover.y,
                                               pos.x(),pos.y(),self._pen)
            new_mover.next = self._mover.next
            self._mover.next = new_mover
            new_mover.prev = self._mover
            self.addItem(new_mover)
            if self._mover == self.tail:
                self.tail = new_mover
            self._mover = new_mover

    def _movenew(self,event):
        self._moved = True
        pos = event.scenePos()
        if self.traceline:
            self.removeItem(self.traceline)
            self.traceline = None
        start = self.tail
        self.traceline = self.addLine(start.x,start.y,pos.x(),pos.y(),self._pen)

    def _moveexisting(self,event):
        self._mover.highlight()
        pos = event.scenePos()
        self._mover.setScenePos(pos.x(),pos.y())

    def mouseMoveEvent(self, event):
        if self._mover:
            self._moveexisting(event)
        elif self._moving:
            self._movenew(event)

    def mouseReleaseEvent(self,event):
        pos = event.scenePos()
        if self._moved:
            self._moved = False
            new_tail = QDragPoint(pos.x(),pos.y(),self.traceline)
            self.tail.next = new_tail
            new_tail.prev = self.tail
            self.tail = new_tail
            self.traceline = None
            self.addItem(new_tail)

class QClickAndDraw(QtWidgets.QGraphicsView):
    def __init__(self, parent):
        super(QtWidgets.QGraphicsView,self).__init__(parent)
        self.scene = QCDScene(self)
        self.setScene(self.scene)
        #self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

    def pan(self):
        self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)

    def draw(self):
        self.setDragMode(QtWidgets.QGraphicsView.NoDrag)

    def zoomIn(self):
        self.scale(1.25,1.25)

    def zoomOut(self):
        self.scale(.8,.8)
