from PyQt5 import QtCore, QtGui, QtWidgets
from collections import namedtuple
from commands import  Action


Rect = namedtuple('Rect','x0 y0 xf yf')

def scaleFactor(dz):
    return 1.01**-dz

def snap(x,y):
    mod = QClickAndDraw._scale
    return (x - x%mod, y - y%mod)

class TraceLine(QtWidgets.QGraphicsItem):
    def __init__(self, scene, x0, y0, xf, yf, pen):
        self._scene = scene
        mid_x, mid_y = self._midpoint(x0,y0,xf,yf)
        self.line1 = QtWidgets.QGraphicsLineItem(x0,y0,mid_x,mid_y)
        self.line2 = QtWidgets.QGraphicsLineItem(mid_x,mid_y,xf,yf)
        self.line1.setPen(pen)
        self.line2.setPen(pen)
        self._scene.addItem(self.line1)
        self._scene.addItem(self.line2)

    def _midpoint(self,x0,y0,xf,yf):
        return ((x0 + xf)/2., (y0 + yf)/2.)

    def setLine(self,x0,y0,xf,yf):
        mid_x, mid_y = self._midpoint(x0,y0,xf,yf)
        self.line1.setLine(x0,y0,mid_x,mid_y)
        self.line2.setLine(mid_x,mid_y,xf,yf)

    def pen1(self):
        return self.line1.pen()

    def setPen1(self,pen):
        self.line1.setPen(pen)

    def pen2(self):
        return self.line2.pen()

    def setPen2(self,pen):
        self.line2.setPen(pen)

    def line(self):
        return QtCore.QLineF(self.line1.line().x1(), self.line1.line().y1(),
                             self.line2.line().x2(), self.line2.line().y2())
    
    def setScale1(self,dz):
        sf = scaleFactor(-dz)
        pen = self.pen1()
        new_width = pen.widthF()*sf
        pen.setWidthF(new_width)
        self.setPen1(pen)

    def setScale2(self,dz):
        sf = scaleFactor(-dz)
        pen = self.pen2()
        new_width = pen.widthF()*sf
        pen.setWidthF(new_width)
        self.setPen2(pen)

    def remove(self):
        self._scene.removeItem(self.line1)
        self._scene.removeItem(self.line2)
        

class QDragPoint(QtWidgets.QGraphicsEllipseItem):
    v = 0
    def __init__(self, x, y, traceline = None, r = 8):
        super(QtWidgets.QGraphicsEllipseItem,self).__init__(x-r/2, y-r/2, r, r)
        # Position variables
        self._x, self._y = snap(x,y)
        self.x = self._x
        self.y = self._y
        self.z = 0
        self.r = r
        # Relations to other objects in scene
        self.traceline = traceline
        self.next = None 
        self.prev = None

        self.action = Action.NO_ACTION

        # Set flags
        self.setZValue(9999)
        self.setFlags(self.ItemIsSelectable)

        # Set artists
        self._updatePens()
        self.setBrush(QtGui.QBrush(QtGui.QColor("white")))
        self._dx = 0
        self._dy = 0

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
        self._dx += dx
        self._dy += dy
        if snap(self._dx,self._dy) != (0, 0):
            self.setScenePos(self.x + self._dx, self.y + self._dy)
            self._dx = 0
            self._dy = 0

    def scaleSize(self,factor):
        self.r *= factor
        self.setRect(self._x-self.r/2,self._y-self.r/2,self.r,self.r)
        self._updatePens()

    def setAction(self,action):
        self.action = action
        colors={
            Action.NO_ACTION:"white",
            Action.TAKE_PHOTO:"purple",
            Action.START_RECORDING:"green",
            Action.STOP_RECORDING:"red"
        }
        color = colors[self.action]
        self.setBrush(QtGui.QBrush(QtGui.QColor(color)))

    def setZ(self,z):
        # + 50 = twice as large
        # - 50 = half as large
        dz = self.z - z
        self.z = z
        sf = scaleFactor(dz)
        self.scaleSize(sf)
        if self.traceline:
            pen = self.traceline.pen2()
            new_width = pen.widthF()*sf
            pen.setWidthF(new_width)
            self.traceline.setPen2(pen)
        if self.next and self.next.traceline:
            pen = self.next.traceline.pen1()
            new_width = pen.widthF()*sf
            pen.setWidthF(new_width)
            self.next.traceline.setPen1(pen)

    @property
    def info(self):
        return {"x":self.x,"y":self.y,"z":self.z,"v":self.v,"action":self.action}

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
    
    def _setScenePos(self,x,y):
        """Change the function name so it doesn't get moved by mouse
        dragging, only function calls"""
        super().setScenePos(x,y)

def onlywhendrawing(function):
    """Only call function if object's drawing property is true"""
    def wrapper(self,event,*args,**kwargs):
        if self.drawing:
            return function(self,event,*args,**kwargs)
        else:
            event.ignore()
    return wrapper

class QCDScene(QtWidgets.QGraphicsScene):
    mousedrag = QtCore.pyqtSignal(tuple)
    def __init__(self,parent):
        super(QtWidgets.QGraphicsScene,self).__init__(parent)
        self.parent = parent
        self.traceline = None
        self._moved = False
        self._mover = None 
        self._pen = QtGui.QPen(QtGui.QColor("red"))
        self._pen.setWidth(4)
        self._pen.setCosmetic(True)
        self.tail = None
        self.head = None
        self.drawing = True

    def _addhead(self):
        self.head = QDragPoint(0,0)
        self.tail = self.head
        self.addItem(self.head)
        self.machine_icon = QMachineIcon(0,0)
        self.addItem(self.machine_icon)

    def setGrid(self, xf, yf,GRID_STEP = 50):
        self.rect = Rect(0, 0, xf, yf)
        self._drawGrid(GRID_STEP)

    def _drawGrid(self, GRID_STEP = 50):
        borderpen = QtGui.QPen(QtGui.QColor(0,0,0,150))
        gridpen = QtGui.QPen(QtGui.QColor(0,0,0,100))
        borderpen.setCosmetic(True)
        borderpen.setWidth(3)
        gridpen.setCosmetic(True)
        gridpen.setDashPattern([4,5])
        gridpen.setWidth(2)
        x0, xf = sorted((self.rect.x0, self.rect.xf))
        y0, yf = sorted((self.rect.y0, self.rect.yf))
        print(x0,xf,y0,yf)
        for i in range(x0+GRID_STEP, xf,GRID_STEP):
            super().addLine(i,y0,i,yf,gridpen)

        for i in range(y0+GRID_STEP, yf,GRID_STEP):
            super().addLine(x0,i,xf,i,gridpen)
        
        super().addLine(x0,y0,x0,yf,borderpen)
        super().addLine(x0,y0,xf,y0,borderpen)
        super().addLine(xf,y0,xf,yf,borderpen)
        super().addLine(x0,yf,xf,yf,borderpen)
    
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
                if len(self.selectedItems()) == 1:
                    self.selectedItems()[0].setSelected(False)
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
        mover.traceline.remove()
        #self.removeItem(mover.traceline)
        if mover.next and mover.next.traceline:
            #self.removeItem(mover.next.traceline)
            mover.next.traceline.remove()

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
                                               pos.x(),pos.y(),self._pen,False)
            new_mover.setZ(self._mover.z)
            new_mover.traceline.setScale1(self._mover.z)
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
            #self.removeItem(self.traceline)
            self.traceline.remove()
            self.traceline = None
        start = self.tail
        self.traceline = self.addLine(start.x,start.y,pos.x(),pos.y(),self._pen)
        self.mousedrag.emit(snap(pos.x(),pos.y()))

    def _moveexisting(self,event):
        pos = event.scenePos()
        self._mover.setScenePos(pos.x(),pos.y())
        self.selectionChanged.emit()

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

    def appendWaypoint(self,x=0,y=0,z=None,action=None):
        start = self.tail
        if not self.traceline:
            self.traceline = self.addLine(start.x,start.y, x, y, self._pen)
        new_tail = QDragPoint(x,y,self.traceline,r=self.head.r)
        if z is None:
            new_tail.setZ(self.tail.z)
        else:
            new_tail.setZ(z)
        self.tail.next = new_tail
        new_tail.prev = self.tail
        self.tail = new_tail
        self.traceline = None
        self.addItem(new_tail)

    def addLine(self,x0,y0,xf,yf,pen,last=True):
        x0, y0 = snap(x0,y0)
        xf, yf = snap(xf,yf)
        line = TraceLine(self,x0,y0,xf,yf,pen)
        if last:
            line.setScale1(self.tail.z)
        return line

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
        self.mousedrag = self._scene.mousedrag
        self.setScene(self._scene)
        self.rotation = 0
        self.scale(1,-1)

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
        self._scene.machine_icon.scaleSize(0.8)

    def zoomOut(self):
        self.scale(.8,.8)
        [h.scaleSize(1.25) for h in self.waypoints]
        self._scene.machine_icon.scaleSize(1.25)

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
    
    def moveMachineMarker(self,x,y,z=None):
        self._scene.machine_icon._setScenePos(x,y)
        if z is not None:
            self._scene.machine_icon.setZ(z)


    def setMachine(self,machine):
        x_bound = machine['dimensions']['x-axis']
        y_bound = machine['dimensions']['y-axis']
        grid_size = machine['dimensions']['grid-size']
        speed = machine['default-speed']
        QClickAndDraw._scale = machine['units-scale']

        self._scene._addhead()
        self._scene.setGrid(x_bound,y_bound,grid_size)
        self._scene.head.v = speed
        QDragPoint.v = speed

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

