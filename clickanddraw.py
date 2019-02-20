from PyQt5 import QtCore, QtGui, QtWidgets
from collections import namedtuple


Rect = namedtuple('Rect','x0 y0 xf yf')

class QDragPoint(QtWidgets.QGraphicsEllipseItem):
    def __init__(self, x, y, traceline = None, r = 8):
        super(QtWidgets.QGraphicsEllipseItem,self).__init__(x-r/2, y-r/2, r, r)
        # Position variables
        self._x = x
        self._y = y
        self.x = x
        self.y = y
        self.r = r
        # Relations to other objects in scene
        self.traceline = traceline
        self.next = None 
        self.prev = None

        # Set flags
        self.setZValue(9999)
        self.setFlags(self.ItemIsSelectable)

        # Set artists
        self._updatePens()
        self.setBrush(QtGui.QBrush(QtGui.QColor("white")))

    def _updatePens(self):
        self._normalPen = QtGui.QPen(QtGui.QColor("black"))
        self._normalPen.setWidth(self.r/8)
        self.setPen(self._normalPen)

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

    def moveScenePos(self, dx, dy):
        self.setScenePos(self.x + dx, self.y + dy)

    def scaleSize(self,factor):
        self.r *= factor
        self.setRect(self._x-self.r/2,self._y-self.r/2,self.r,self.r)
        self._updatePens()

    @property
    def info(self):
        return {"x":self.x,"y":self.y,"action":None}

class QMachineIcon(QDragPoint):
    def __init__(self, *args,**kwargs):
        super().__init__(*args,**kwargs)
        # Set flags
        self.setZValue(99999)
        self.setFlag(self.ItemIsSelectable,False)

        # Set artists
        self._updatePens()
        self.setBrush(QtGui.QBrush(QtGui.QColor("yellow")))
    def setScenePos(self,x,y):
        pass

def onlywhendrawing(function):
    """Only call function if object's drawing property is true"""
    def wrapper(self,*args,**kwargs):
        if self.drawing:
            return function(self,*args,**kwargs)
    return wrapper

class QCDScene(QtWidgets.QGraphicsScene):
    def __init__(self,parent):
        super(QtWidgets.QGraphicsScene,self).__init__(parent)
        self.parent = parent
        self.traceline = None
        self._moved = False
        self._mover = None 
        self._pen = QtGui.QPen(QtGui.QColor("red"))
        self._pen.setWidth(4)
        self._pen.setCosmetic(True)
        self.head = None
        self.tail = None
        self.head = QDragPoint(0,0)
        self.tail = self.head
        self.addItem(self.head)
        self.addItem(QMachineIcon(0,0))
        self.drawing = True

    def setGrid(self, xf, yf,GRID_STEP = 50):
        self.rect = Rect(0, 0, xf, yf)
        self._drawGrid(GRID_STEP)

    def _drawGrid(self, GRID_STEP = 50):
        gridpen = QtGui.QPen(QtGui.QColor(0,0,0,100))
        gridpen.setCosmetic(True)
        gridpen.setDashPattern([4,5])
        gridpen.setWidth(2)
        x0, xf = sorted((self.rect.x0, self.rect.xf))
        y0, yf = sorted((self.rect.y0, self.rect.yf))
        for i in range(x0, xf+GRID_STEP,GRID_STEP):
            self.addLine(i,self.rect.y0,i,self.rect.yf,gridpen)

        for i in range(y0, yf+GRID_STEP,GRID_STEP):
            self.addLine(self.rect.x0,i,self.rect.xf,i,gridpen)
    
    @onlywhendrawing
    def mousePressEvent(self, event):
        self._mover = None
        self._moving = False
        self._lastpos = event.scenePos()
        if event.buttons() == QtCore.Qt.LeftButton:
            self._mover = self.itemAt(event.scenePos(),QtGui.QTransform())
            if not isinstance(self._mover,QDragPoint):
                self._mover = None
                self._moving = True
            else:
                # unselect all items besides the mover
                for item in self.selectedItems():
                    item.setSelected(False)
                self._mover.setSelected(True)
        elif event.buttons() == QtCore.Qt.RightButton:
            mover = self.itemAt(event.scenePos(),QtGui.QTransform())
            if isinstance(mover,QDragPoint):
                self._removeMover(mover)

    def _removeMover(self, mover):
        if mover == self.head:
            return
        self.removeItem(mover)
        self.removeItem(mover.traceline)
        if mover.next and mover.next.traceline:
            self.removeItem(mover.next.traceline)

        if mover.prev and mover.next:
            mover.next.traceline = self.addLine(
                    mover.prev.x, mover.prev.y,
                    mover.next.x, mover.next.y,self._pen)

        if mover.next:
            mover.next.prev = mover.prev
        if mover.prev:
            mover.prev.next = mover.next

        if mover == self.tail:
            self.tail = mover.prev
        
    @onlywhendrawing
    def mouseDoubleClickEvent(self, event):
        """ Append a new line segment at the clicked node """
        pos = event.scenePos()
        if self._mover:
            self._mover.setSelected(False)
            new_mover = QDragPoint(pos.x(),pos.y(), r = self.head.r)
            new_mover.traceline = self.addLine(self._mover.x,self._mover.y,
                                               pos.x(),pos.y(),self._pen)
            new_mover.next = self._mover.next
            self._mover.next = new_mover
            new_mover.prev = self._mover
            self.addItem(new_mover)
            if self._mover == self.tail:
                self.tail = new_mover
            self._mover = new_mover
            self._mover.setSelected(True)

    def _movenew(self,event):
        self._moved = True
        pos = event.scenePos()
        if self.traceline:
            self.removeItem(self.traceline)
            self.traceline = None
        start = self.tail
        self.traceline = self.addLine(start.x,start.y,pos.x(),pos.y(),self._pen)

    def _moveexisting(self,event):
        pos = event.scenePos()
        self._mover.setScenePos(pos.x(),pos.y())

    def _movemultiple(self,event):
        pos = event.scenePos()
        dx = pos.x() - self._lastpos.x()
        dy = pos.y() - self._lastpos.y()
        for mover in self.selectedItems():
            if isinstance(mover, QDragPoint):
                mover.moveScenePos(dx,dy)


    def removeMultiple(self):
        for mover in self.selectedItems():
            self._removeMover(mover)

    def appendWaypoint(self,x=0,y=0,action=None):
        start = self.tail
        if not self.traceline:
            self.traceline = self.addLine(start.x,start.y, x, y, self._pen)
        new_tail = QDragPoint(x,y,self.traceline,r=self.head.r)
        self.tail.next = new_tail
        new_tail.prev = self.tail
        self.tail = new_tail
        self.traceline = None
        self.addItem(new_tail)

    @onlywhendrawing
    def mouseMoveEvent(self, event):
        if event.buttons() == QtCore.Qt.NoButton:
            return
        if self._mover:
            self._moveexisting(event)
        elif self._moving and not self.selectedItems():
            self._movenew(event)
        elif self.selectedItems():
            self._movemultiple(event)
        self._lastpos = event.scenePos()

    @onlywhendrawing
    def mouseReleaseEvent(self,event):
        pos = event.scenePos()
        if self._moved:
            self._moved = False
            self.appendWaypoint(pos.x(),pos.y())

class QClickAndDraw(QtWidgets.QGraphicsView):
    def __init__(self, parent):
        super(QtWidgets.QGraphicsView,self).__init__(parent)
        self._scene = QCDScene(self)
        self.setScene(self._scene)
        self.rotation = 0

    @property
    def waypoints(self):
        head = self._scene.head
        while head:
            yield head
            head = head.next

    @property
    def scene(self):
        return self._scene

    def pan(self):
        self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)

    def draw(self):
        self.setDragMode(QtWidgets.QGraphicsView.NoDrag)

    def zoomIn(self):
        self.scale(1.25,1.25)
        [h.scaleSize(0.8) for h in self.waypoints]

    def zoomOut(self):
        self.scale(.8,.8)
        [h.scaleSize(1.25) for h in self.waypoints]

    def setRBSelect(self):
        self.setDragMode(QtWidgets.QGraphicsView.RubberBandDrag)
        self._scene.drawing = False

    def unsetRBSelect(self):
        self.setDragMode(QtWidgets.QGraphicsView.NoDrag)
        self._scene.drawing = True

    def keyPressEvent(self,event):
        if event.key() == QtCore.Qt.Key_Shift:
            self.setRBSelect()
        elif event.key() == QtCore.Qt.Key_Delete:
            self._scene.removeMultiple()

    def keyReleaseEvent(self,event):
        self.unsetRBSelect()

    def rotateL(self):
        self.rotate(30)

    def rotateR(self):
        self.rotate(-30)

    def setMachine(self,machine):
        x_bound = machine['dimensions']['x-axis']
        y_bound = machine['dimensions']['y-axis']
        grid_size = machine['dimensions']['grid-size']
        self._scene.setGrid(x_bound,y_bound,grid_size)

    def waypointIndex(self,waypoint):
        # Todo: more efficient
        for i,wp in enumerate(self.waypoints):
            if wp == waypoint:
                return i
        raise IndexError

    def dumpWaypointsInfo(self):
        return [h.info for h in self.waypoints]

    def loadWaypointsInfo(self,info):
        for point in info[1:]:
            self._scene.appendWaypoint(**point)
