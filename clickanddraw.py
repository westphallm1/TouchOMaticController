from PyQt5 import QtCore, QtGui, QtWidgets


class QDragPoint(QtWidgets.QGraphicsEllipseItem):
    def __init__(self, x, y, traceline = None, r = 8):
        super(QtWidgets.QGraphicsEllipseItem,self).__init__(x-r/2, y-r/2, r, r)
        self.setAcceptDrops(True)
        self._x = x
        self._y = y
        self.x = x
        self.y = y
        self.traceline = traceline
        self.nextline = None 
        print(self.x, self.y)

    def setScenePos(self,x,y):
        self.setPos(x-self._x,y-self._y)
        if self.traceline:
            x1 = self.traceline.line().x1()
            y1 = self.traceline.line().y1()
            self.traceline.setLine(x1,y1,x,y)
        if self.nextline:
            x2 = self.nextline.line().x2()
            y2 = self.nextline.line().y2()
            self.nextline.setLine(x,y,x2,y2)

    def finalizeScenePos(self,x,y):
        self.x = x
        self.y = y

class TraceLine(QtWidgets.QGraphicsLineItem):
    pass

class QCDScene(QtWidgets.QGraphicsScene):
    def __init__(self,parent):
        super(QtWidgets.QGraphicsScene,self).__init__(parent)
        self.parent = parent
        self.traceline = None
        self.destinations = []
        self.destinations.append(QDragPoint(0,0))
        self.addItem(self.destinations[-1])
        self._moved = False
        self._mover = None 

    def mousePressEvent(self, event):
        self._mover = self.itemAt(event.scenePos(),QtGui.QTransform())
        if not isinstance(self._mover,QDragPoint):
            self._mover = None


    def _movenew(self,event):
        self._moved = True
        pos = event.scenePos()
        if self.traceline:
            self.removeItem(self.traceline)
            self.traceline = None
        start = self.destinations[-1]
        self.traceline = self.addLine(start.x,start.y,pos.x(),pos.y())

    def _moveexisting(self,event):
        pos = event.scenePos()
        self._mover.setScenePos(pos.x(),pos.y())


    def mouseMoveEvent(self, event):
        if self._mover:
            self._moveexisting(event)
        else:
            self._movenew(event)

    def mouseReleaseEvent(self,event):
        pos = event.scenePos()
        if self._mover:
            self._mover.finalizeScenePos(pos.x(),pos.y())
        if self._moved:
            self._moved = False
            self.destinations.append(QDragPoint(pos.x(),pos.y(),self.traceline))
            self.destinations[-2].nextline = self.traceline
            self.traceline = None
            self.addItem(self.destinations[-1])

class QClickAndDraw(QtWidgets.QGraphicsView):
    def __init__(self, parent):
        super(QtWidgets.QGraphicsView,self).__init__(parent)
        self.scene = QCDScene(self)
        self.setScene(self.scene)

