from PyQt5 import QtWidgets, uic, QtCore, QtGui
from src.view import ui
from src import DESIGN_DIR
import os
import numpy as np


class QGrap(QtWidgets.QWidget):
    moved = QtCore.pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj is self:
            if event.type() == QtCore.QEvent.Leave:
                QtWidgets.QApplication.restoreOverrideCursor()
            if event.type() in [QtCore.QEvent.Enter, QtCore.QEvent.MouseButtonRelease]:
                # !!! mouse release is not detected because its event is rejected !!!
                QtWidgets.QApplication.restoreOverrideCursor()
                QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.OpenHandCursor)
            elif event.type() == QtCore.QEvent.MouseButtonPress:
                QtWidgets.QApplication.restoreOverrideCursor()
                QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.ClosedHandCursor)
        return QtWidgets.QWidget.eventFilter(self, obj, event)


class QViewWidget(QtWidgets.QWidget):
    sizeChanged = QtCore.pyqtSignal()
    positionChanged = QtCore.pyqtSignal()
    focused = QtCore.pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        # create header
        header = QtWidgets.QHBoxLayout()
        self.lefthead = QtWidgets.QLabel()
        self.grap = QGrap()
        self.selected = QtWidgets.QCheckBox()
        self.selected.setStyleSheet("QCheckBox::indicator {border: 0px; };")
        header.addWidget(self.selected)
        header.addWidget(self.lefthead)
        header.addWidget(self.grap)

        # create left and right footer
        footer = QtWidgets.QHBoxLayout()
        self.leftfoot = QtWidgets.QLabel()
        self.rightfoot = QtWidgets.QLabel()
        self._sizeGrip = QtWidgets.QSizeGrip(self)
        self._sizeGrip.mouseMoveEvent = lambda event: self.resize(self.width() + event.pos().x(),
                                                                  self.height() + event.pos().y())
        footer.addWidget(self.leftfoot)
        footer.addStretch(0)
        footer.addWidget(self.rightfoot)
        footer.addWidget(self._sizeGrip)

        # fill layout
        vbox = QtWidgets.QVBoxLayout()
        vbox.setSpacing(0)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.addLayout(header)
        vbox.addWidget(QtWidgets.QWidget())
        vbox.addLayout(footer)
        self.setLayout(vbox)

        # create proxy and item to interact with widget
        self._item = self.QCustomRectItem(self)
        self._proxy = QtWidgets.QGraphicsProxyWidget(self._item)
        self._proxy.setWidget(self)

        # initialize self function from handle functions
        self.moveBy = self._item.moveBy
        self.pos = self._item.pos

    class QCustomRectItem(QtWidgets.QGraphicsRectItem):
        """
        graphic item which allow to move the widget in graphic view

        Parameters
        ----------
        parent: QViewWidget
        """
        def __init__(self, parent):
            super().__init__()
            self.parent = parent
            self.setAcceptHoverEvents(True)
            self.setFlags(QtWidgets.QGraphicsItem.ItemIsMovable |
                          QtWidgets.QGraphicsItem.ItemIsFocusable |
                          QtWidgets.QGraphicsItem.ItemSendsScenePositionChanges)

        def itemChange(self, change, value):
            if change in [QtWidgets.QGraphicsItem.ItemPositionChange,
                          QtWidgets.QGraphicsItem.ItemVisibleChange]:
                self.parent.positionChanged.emit()
            return QtWidgets.QGraphicsRectItem.itemChange(self, change, value)

    def enterEvent(self, event):
        self.focused.emit(True)
        return QtWidgets.QWidget.enterEvent(self, event)

    def leaveEvent(self, event):
        self.focused.emit(False)
        return QtWidgets.QWidget.leaveEvent(self, event)

    def resizeEvent(self, event):
        self.sizeChanged.emit()
        return QtWidgets.QWidget.resizeEvent(self, event)

    def isSelected(self):
        return self.selected.isChecked()

    def setWidget(self, widget):
        inter = set(widget.__dict__).intersection(set(self.__dict__))
        if inter:
            return print("FAILED setWidget: you cannot set widget in QViewWidget " +
                         "containing parameters like:\n " + " ".join(list(inter)))
        self.layout().replaceWidget(self.layout().itemAt(1).widget(), widget)
        self.__dict__.update(widget.__dict__)

    def addToScene(self, scene):
        self.sizeChanged.connect(lambda: self._item.setRect(QtCore.QRectF(self.geometry().adjusted(0, 0, 0, 0))))
        self.sizeChanged.emit()
        scene.addItem(self._item)


# class QViewWidget1(QtWidgets.QWidget):
#     """
#     resizable and movable widget inside QGraphicsScene
#
#     Parameters
#     ----------
#     resizable: bool, default=True
#         if True add a grip at the bootom right corner to resize the widget
#     handleSize: tuple of 4 float, default=(0, -20, 0, 0)
#         size of the handle to move the view widget (left, top, right, bottom)
#     handleColor: QtGui.QColor, default=(180, 200, 180)
#         rgb color of the handle
#
#     """
#     sizeChanged = QtCore.pyqtSignal()
#     positionChanged = QtCore.pyqtSignal()
#     focused = QtCore.pyqtSignal(bool)
#
#     def __init__(self, resizable=True, handleSize=(0, -20, 0, 0), handleColor=None):
#         super().__init__()
#         self.handleSize = handleSize
#         self.handleColor = handleColor
#         self._state = None
#         self.currentPosition = None
#         self.current_state = 'released'
#         self.initUI(resizable)
#
#     def initUI(self, resizable):
#         """
#         initialize widget with footer and handle
#
#         Parameters
#         ----------
#         resizable: bool
#             if True add sizegrip to footer
#         """
#         vbox = QtWidgets.QVBoxLayout()
#         vbox.setSpacing(0)
#         vbox.setContentsMargins(0, 0, 0, 0)
#
#         # create header
#         header = QtWidgets.QHBoxLayout()
#         self.state = QtWidgets.QLabel()
#         self.grap = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum,
#                    QtWidgets.QSizePolicy.Expanding)#QGrapWidget()
#         self.selected = QtWidgets.QCheckBox()
#         header.addWidget(self.state)
#         header.addItem(self.grap)
#         header.addWidget(self.selected)
#
#
#         # create left and right footer
#         footer = QtWidgets.QHBoxLayout()
#         self.leftfoot = QtWidgets.QLabel()
#         self.rightfoot = QtWidgets.QLabel()
#         footer.addWidget(self.leftfoot)
#         footer.addStretch(0)
#         footer.addWidget(self.rightfoot)
#
#         # add size gripto footer  if rezizable
#         if resizable:
#             self.sizeGrip = QtWidgets.QSizeGrip(self)
#             self.sizeGrip.mouseMoveEvent = self._mouseMoveEvent
#             footer.addWidget(self.sizeGrip)
#
#         vbox.addLayout(header)
#         vbox.addWidget(QtWidgets.QWidget())
#         vbox.addLayout(footer)
#         self.setLayout(vbox)
#
#         # create handle to move widget
#         self.handle = self.RectItem(self)
#         self.handle.setPen(QtGui.QPen(QtCore.Qt.transparent))
#         if self.handleColor is not None:
#             self.handle.setBrush(self.handleColor)
#
#         # initialize self function from handle functions
#         self.moveBy = self.handle.moveBy
#         self.pos = self.handle.pos
#
#         self.proxy = QtWidgets.QGraphicsProxyWidget(self.handle)
#         self.proxy.setWidget(self)
#
#     def _mouseMoveEvent(self, event):
#         self.resize(self.width()+event.pos().x(), self.height()+event.pos().y())
#
#     def setWidget(self, widget):
#         """
#         update the central widget with new widget
#
#         Parameters
#         ----------
#         widget: QWidget
#         """
#         inter = set(widget.__dict__).intersection(set(self.__dict__))
#         if inter:
#             return print("FAILED setWidget: you cannot set widget in QViewWidget " +
#                          "containing parameters like:\n " + " ".join(list(inter)))
#
#         self.layout().replaceWidget(self.layout().itemAt(0).widget(), widget)
#         self.__dict__.update(widget.__dict__)
#         print(self.__dict__.keys())
#
#     class RectItem(QtWidgets.QGraphicsRectItem):
#         """
#         graphic item which allow to move the widget in graphic view
#
#         Parameters
#         ----------
#         parent: QViewWidget
#         """
#         def __init__(self, parent):
#             super().__init__()
#             self.parent = parent
#             self.setAcceptHoverEvents(True)
#             self.setFlags(QtWidgets.QGraphicsItem.ItemIsMovable |
#                           QtWidgets.QGraphicsItem.ItemIsFocusable |
#                           # QtWidgets.QGraphicsItem.ItemIsSelectable |
#                           QtWidgets.QGraphicsItem.ItemSendsScenePositionChanges)
#
#         def itemChange(self, change, value):
#             if change in [QtWidgets.QGraphicsItem.ItemPositionChange,
#                           QtWidgets.QGraphicsItem.ItemVisibleChange]:
#                 self.parent.positionChanged.emit()
#                 self.parent.currentPosition = self.parent.handle.pos()
#             return QtWidgets.QGraphicsRectItem.itemChange(self, change, value)
#
#         def mousePressEvent(self, event=None):
#             self.parent.state = 'pressed'
#             self.setSelected(True)
#             return QtWidgets.QGraphicsRectItem.mousePressEvent(self, event)
#
#         def mouseReleaseEvent(self, event=None):
#             self.parent.state = 'released'
#             self.setSelected(False)
#             return QtWidgets.QGraphicsRectItem.mouseReleaseEvent(self, event)
#
#         def hoverEnterEvent(self, event):
#             self.parent.focused.emit(True)
#             return QtWidgets.QGraphicsRectItem.hoverEnterEvent(self, event)
#
#         def hoverLeaveEvent(self, event):
#             self.parent.focused.emit(False)
#             return QtWidgets.QGraphicsRectItem.hoverLeaveEvent(self, event)
#
#     def enterEvent(self, event):
#         self.focused.emit(True)
#         return QtWidgets.QWidget.enterEvent(self, event)
#
#     def leaveEvent(self, event):
#         self.focused.emit(False)
#         return QtWidgets.QWidget.leaveEvent(self, event)
#
#     def resizeEvent(self, event):
#         self.sizeChanged.emit()
#         return QtWidgets.QWidget.resizeEvent(self, event)
#
#     def addToScene(self, scene):
#         """
#         add widget to a specified scene
#
#         Parameters
#         ----------
#         handle_size: tuple of size 4
#             (left, top, right, bottom)
#         """
#         self.sizeChanged.connect(lambda: self.handle.setRect(QtCore.QRectF(
#                                self.geometry().adjusted(*self.handleSize))))
#         self.sizeChanged.emit()
#         scene.addItem(self.handle)


class QGraphicsNode(ui.QViewWidget):
    """
    movable widget inside the graph associated to a pipeline's step

    Parameters
    ----------
    graph: Graph
    type: str
        type of node associated to specific widget and functions
    name: str
        unique name
    parents: list of Node, default=[]
        nodes whose outputs are self input
    position: tuple, default=(0,0)
        position of the node in the graphic view

    """
    nameChanged = QtCore.pyqtSignal(str, str)

    def __init__(self, graph, type, name, parents=[], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWidget(uic.loadUi(os.path.join(DESIGN_DIR, "ui", "Node.ui")))
        self.graph = graph
        self.type = type
        self.name = name
        self.button.setText(name)

        self.positionChanged.connect(self.moveChilds)
        self.sizeChanged.connect(self.updateHeight)
        self.focused.connect(self.focusNode)

        self.current_branch = []
        self.childs = []
        self.parents = parents
        self.links = []

    def updateHeight(self):
        """
        resize widget to its minimum height
        """
        self.resize(self.width(), self.minimumHeight())

    def moveChilds(self):
        """
        if shift is holded, move node childs with it
        """
        if self.graph.holdShift:
            if self.current_state == 'pressed':
                self.current_state = 'isMoving'
                self.updateCurrentBranch()
            if self.current_state == 'isMoving':
                delta = self.pos() - self.currentPosition
                self.currentPosition = self.pos()
                for child in self.current_branch:
                    child.moveBy(delta.x(), delta.y())

    @property
    def mid_pos(self):
        return self.width()/2, self.height()/2

    def delete(self):
        """
        delete itself and all related graphic items (links and junctions)
        """
        for link in self.links:
            self.graph.scene.removeItem(link)
        self.graph.scene.removeItem(self._item)
        self._proxy.deleteLater()
        self.deleteLater()

    def focusNode(self, boolean):
        self.graph.setEnabledScroll(not boolean)
        self.graph.focus = self if boolean else None

    def getChilds(self):
        """
        get all children

        Return
        ------
        childs: list of Node

        """
        childs = self.childs
        for child in self.childs:
            childs += child.getChilds()
        return childs

    def rename(self, new_name):
        self.button.setText(new_name)
        self.nameChanged.emit(self.name, new_name)
        self.name = new_name

    def updateCurrentBranch(self):
        """
        update the current branch as a unique list of nodes
        """
        self.current_branch = set(self.getChilds())


class QGraphicsLink(QtWidgets.QGraphicsPolygonItem):
    """
    graphic arrow between two graphic points

    Parameters
    ----------
    parent/child: Node
        the two nodes to link
    width: float, default=5
        width of the arrow line
    arrowWidth: float, default=10
        width of the arrow head
    arrowLen: float, default=10
        length of the arrow head
    space: float, default=20
        space between arrow extremity and nodes
    color: QColor, default=QtGui.QColor(0, 150, 0)
        color of the arrow background
    borderWidth: float, default=2
        width of the arrow border
    borderColor: QColor, default=QtGui.QColor(0, 150, 0)
        color of the arrow border

    """
    def __init__(self, parent, child, width=5, arrowWidth=10, arrowLen=10, space=20,
                 color=QtGui.QColor(0, 150, 0), borderWidth=2, borderColor=QtGui.QColor(0, 150, 0)):
        super().__init__()
        self._parent = parent
        self._child = child
        self.setZValue(-1)
        self.setPen(QtGui.QPen(borderColor, borderWidth))
        self.setBrush(color)
        self.width = width
        self.arrowWidth = arrowWidth
        self.arrowLen = arrowLen
        self.space = space
        self.updatePos()

    def intersects(self, line, rect, ref_position):
        """
        This method find the intersection between widget rect and line
        by checking the intersection between line and each rect border line.
        As the line comes from inside the rect, only one intersection exists

        Parameters
        ----------
        line: QLineF
        rect: QRect
            rect of the widget
        ref_position: QPoint
            absolute position of the rect int the graph

        Return
        ------
        result: QPointF
            first position found of the intersection
        """
        points = [rect.bottomLeft(), rect.bottomRight(), rect.topRight(), rect.topLeft()]
        for i in range(4):
            border = QtCore.QLineF(ref_position + points[i-1], ref_position + points[i])
            intersection_type, intersection_point = line.intersects(border)
            if intersection_type == QtCore.QLineF.BoundedIntersection:
                return intersection_point
        return QtCore.QPointF()

    def updatePos(self):
        """
        This method create the arrow between child and parent
        """
        # build direction line
        r1, r2 = self._parent.rect(), self._child.rect()
        line = QtCore.QLineF(self._parent.pos() + r1.center(),
                             self._child.pos() + r2.center())

        # build unit vectors
        unit = (line.unitVector().p2() - line.unitVector().p1())
        normal = (line.normalVector().unitVector().p2() - line.normalVector().unitVector().p1())

        # get arrow point
        p1 = self.intersects(line, r1, self._parent.pos()) + unit * self.space
        p2 = self.intersects(line, r2, self._child.pos()) - unit * self.space
        p11 = p1 + normal * self.width
        p12 = p1 - normal * self.width
        p21 = p2 + normal * self.width - unit * self.arrowLen
        p22 = p2 - normal * self.width - unit * self.arrowLen
        p23 = p2 + normal * self.arrowWidth - unit * self.arrowLen
        p24 = p2 - normal * self.arrowWidth - unit * self.arrowLen

        # build arrow
        if np.sign((p22 - p12).x()) == np.sign(unit.x()) and np.sign((p22 - p12).y()) == np.sign(unit.y()):
            self.setPolygon(QtGui.QPolygonF([p11, p21, p23, p2, p24, p22, p12, p11]))
        else:
            self.setPolygon(QtGui.QPolygonF([p23, p2, p24, p23]))
