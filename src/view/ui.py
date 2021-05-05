from PyQt5 import QtWidgets, uic, QtCore, QtGui
from src.view import ui
from src import DESIGN_DIR
import os
import numpy as np


def ceval(arg):
    try:
        return eval(arg)
    except (NameError, TypeError):
        return arg


class QGrap(QtWidgets.QWidget):

    def __init__(self):
        super().__init__()
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
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
        header.setAlignment(QtCore.Qt.AlignTop)

        # create left and right footer
        footer = QtWidgets.QHBoxLayout()
        self.leftfoot = QtWidgets.QLabel()
        self.rightfoot = QtWidgets.QLabel()
        self._sizeGrip = QtWidgets.QSizeGrip(self)
        self._sizeGrip.mouseMoveEvent = self.sizeGripMoveEvent

        footer.addWidget(self.leftfoot)
        footer.addStretch(0)
        footer.addWidget(self.rightfoot)
        footer.addWidget(self._sizeGrip)

        self.centralWidget = QtWidgets.QWidget()

        # fill layout
        vbox = QtWidgets.QVBoxLayout()
        vbox.setSpacing(0)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.addLayout(header)
        vbox.addWidget(self.centralWidget)
        vbox.addLayout(footer)
        self.setLayout(vbox)

        vbox.setStretchFactor(header, 0)
        vbox.setStretchFactor(self.centralWidget, 1)
        vbox.setStretchFactor(footer, 0)

        # create proxy and item to interact with widget
        self._item = self.QCustomRectItem(self)
        self._proxy = QtWidgets.QGraphicsProxyWidget(self._item)
        self._proxy.setWidget(self)

        # initialize self function from handle functions
        self.moveBy = self._item.moveBy
        self.pos = self._item.pos

        self.last_position = QtCore.QPointF(0, 0)

    def sizeGripMoveEvent(self, event):
        self.resize(self.width() + event.pos().x(),
                    self.height() + event.pos().y())

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
            if change == QtWidgets.QGraphicsItem.ItemPositionChange:
                self.parent.deltaPosition = value - self.pos()
                self.parent.positionChanged.emit()
            elif change == QtWidgets.QGraphicsItem.ItemVisibleChange:
                self.parent.positionChanged.emit()
            return QtWidgets.QGraphicsRectItem.itemChange(self, change, value)

    def enterEvent(self, event):
        self.focused.emit(True)
        self._item.setZValue(10)
        return QtWidgets.QWidget.enterEvent(self, event)

    def leaveEvent(self, event):
        self.focused.emit(False)
        self._item.setZValue(1)
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
        self.layout().replaceWidget(self.centralWidget, widget)
        self.__dict__.update(widget.__dict__)
        self.centralWidget.deleteLater()
        self.centralWidget = widget
        self.layout().setStretchFactor(self.centralWidget, 1)

    def addToScene(self, scene):
        self.sizeChanged.connect(lambda: self._item.setRect(QtCore.QRectF(self.geometry().adjusted(0, 0, 0, 0))))
        self.sizeChanged.emit()
        scene.addItem(self._item)


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
        self.vbox.setStretchFactor(self.button, 0)
        self.vbox.setStretchFactor(self.parameters, 1)
        self.vbox.setStretchFactor(self.result, 10)

        self.button.clicked.connect(lambda: self.hideShowWidget(self.widget))
        self.hideResult.clicked.connect(lambda: self.hideShowWidget(self.result, self.hideResult))
        self.hideParameters.clicked.connect(lambda: self.hideShowWidget(self.parameters, self.hideParameters))
        self.hideResult.hide()

        self.button.mouseDoubleClickEvent = self._mouseDoubleClickEvent
        self.state = None
        self.focused.connect(self.focusNode)
        self.sizeChanged.connect(self.updateHeight)
        self.selected.stateChanged.connect(self.changeChildSelection)
        self.selected.stateChanged.connect(self._item.setSelected)
        self.positionChanged.connect(self.moveSelection)

        self.childs = []
        self.parents = parents
        self.links = []
        self.initialPosition = None

    def hideShowWidget(self, widget, button=None):
        widget.show() if widget.isHidden() else widget.hide()
        self.updateHeight(True)

        if button is not None:
            new_text = '+' + button.text()[1:] if widget.isHidden() else '-' + button.text()[1:]
            button.setText(new_text)

    def moveSelection(self):
        if self is self.graph.focus:
            for node in self.graph.getSelectedNodes(exceptions=[self]):
                node.moveBy(self.deltaPosition.x(), self.deltaPosition.y())

    def setInitialPosition(self):
        self.initialPosition = self.pos()

    def changeChildSelection(self, state):
        if self.graph.holdShift:
            for child in self.childs:
                child.selected.setChecked(state)

    def updateHeight(self, force=False):
        """
        resize widget to its minimum height
        """
        self.resize(self.width(), 0)

    def _mouseDoubleClickEvent(self, event):
        self.graph.renameNode(self)

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

    def setParametersWidget(self, ui_file):
        new_widget = uic.loadUi(ui_file)
        self.widget.layout().replaceWidget(self.parameters, new_widget)
        self.parameters.deleteLater()
        self.parameters = new_widget
        self.vbox.setStretchFactor(self.parameters, 1)


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
    def __init__(self, parent, child, width=5, arrowWidth=10, arrowLen=10, space=[0, 20],
                 color=QtGui.QColor(0, 150, 0), borderWidth=2, borderColor=QtGui.QColor(0, 150, 0)):
        super().__init__()
        self._parent = parent
        self._child = child
        self.setZValue(-1)
        self.setPen(QtGui.QPen(ceval(borderColor), borderWidth))
        self.setBrush(ceval(color))
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
        p1 = self.intersects(line, r1, self._parent.pos()) + unit * self.space[0]
        p2 = self.intersects(line, r2, self._child.pos()) - unit * self.space[1]
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
            self.setPolygon(QtGui.QPolygonF())


class PandasModel(QtCore.QAbstractTableModel):
    """
    Class to populate a table view with a pandas dataframe
    """
    def __init__(self, df, header_index=-1, parent=None):
        QtCore.QAbstractTableModel.__init__(self, parent)
        if header_index == -1:
            self._data = df
        else:
            header_colname = df.columns[header_index]
            self._data = df.set_index(header_colname)

    def format(self, value):
        return '' if np.isnan(value) else str(value)

    def rowCount(self, parent=None):
        return self._data.shape[0]

    def columnCount(self, parent=None):
        return self._data.shape[1]

    def data(self, index, role):
        if index.isValid():
            if role == QtCore.Qt.DisplayRole:
                return self.format(self._data.iloc[index.row(), index.column()])

    def headerData(self, col, orientation, role):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            return self.format(self._data.columns[col])
        elif orientation == QtCore.Qt.Vertical and role == QtCore.Qt.DisplayRole:
            return self.format(self._data.index[col])
