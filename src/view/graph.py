from PyQt5 import QtWidgets, QtCore, QtGui, uic
from src.view import ui, utils
from src import DESIGN_DIR, DEFAULT, RESULT_STACK
import copy
import os
import pandas as pd


class QCustomGraphicsNode(ui.QGraphicsNode):

    def __init__(self, *args, **kwargs):
        super(QCustomGraphicsNode, self).__init__(*args, **kwargs)

        # add parameters widget
        uifile_path = os.path.join(DESIGN_DIR, 'ui', 'modules', self.type+'.ui')
        if not os.path.isfile(uifile_path):
            print("{} does not exists".format(uifile_path))
        else:
            self.setParametersWidget(uifile_path)

        # initialize
        self._font = None

    def updateHeight(self, force=False):
        """
        This function set the height of the widget to its minimum if the
        result is not shown

        Parameters
        ----------
        force: bool, default=False
            if True, use a trick to force resize in extreme cases
        """
        if self.widget.isHidden() or self.result.isHidden() or self.result.sizeHint() == QtCore.QSize(-1, -1):
            if force:
                width = self.width()
                self.adjustSize()
                self.resize(width, self.minimumHeight()+1)
            self.resize(self.width(), 0)

    def updateResult(self, result):
        """
        This function create widget from result and show it. The created widget
        depends on the result type

        Parameters
        ----------
        result: any type data

        """
        # create the output widget depending on output type
        if result is None:
            return
        elif isinstance(result, Exception):
            new_widget = QtWidgets.QWidget()
            self.updateHeight(True)
            self.hideResult.hide()
        else:
            if isinstance(result, (int, float, str, bool)):
                new_widget = self.computeTextWidget(result)
            elif isinstance(result, pd.DataFrame):
                new_widget = self.computeTableWidget(result)
            self.hideResult.show()

        # replace current output widget with the new one
        self.widget.layout().setStretchFactor(self.result, 10)
        self.widget.layout().replaceWidget(self.result, new_widget)
        self.result.deleteLater()
        self.result = new_widget

    def computeTextWidget(self, data):
        """
        This function create a QLabel widget with resizable font based on the
        widget size

        Parameters
        ----------
        data: float, int, str, bool

        Return
        ------
        widget: QLabel

        """
        default_fontsize = 30
        min_fontsize = 10

        # set font
        if self._font is None:
            self._font = QtGui.QFont()
            self._font.setPointSize(default_fontsize)

        # set widget
        widget = QtWidgets.QLabel(str(data))
        widget.setAlignment(QtCore.Qt.AlignCenter)
        widget.setFont(self._font)

        # update fontsize to fit widget size
        metric = QtGui.QFontMetrics(self._font)
        ratio = metric.boundingRect(str(data)).size() / self._font.pointSize()

        def fitFontSize():
            if isinstance(self.result, QtWidgets.QLabel):
                fontsize = max([min([self.result.width() / ratio.width(),
                                     self.result.height() / ratio.height()]) - 10, min_fontsize])
                self._font.setPointSize(fontsize)
                self.result.setFont(self._font)
        self.sizeChanged.connect(fitFontSize)
        return widget

    def computeTableWidget(self, data):
        """
        This function create a table widget which can be windowed

        Parameters
        ----------
        data: pd.DataFrame

        Return
        ------
        widget: QTableWidget

        """
        widget = uic.loadUi(os.path.join(DESIGN_DIR, 'ui', 'TableWidget.ui'))
        widget.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
        widget.Vheader.addItems(['--'] + list(data.columns.astype(str)))

        def updateVheader(index):
            model = ui.PandasModel(data, index-1)
            proxyModel = QtCore.QSortFilterProxyModel()
            proxyModel.setSourceModel(model)
            widget.table.setModel(proxyModel)
        widget.Vheader.currentIndexChanged.connect(updateVheader)
        updateVheader(0)

        def openInDock():
            widget = self.computeTableWidget(data)
            dock = self.graph._view.addWidgetInDock(widget)
            self.nameChanged.connect(lambda _, new: dock.setWindowTitle(new))
            dock.setWindowTitle(self.name)

        widget.maximize.clicked.connect(openInDock)
        self.leftfoot.setText("{0} x {1}    ({2} {3})".format(*data.shape, *utils.getMemoryUsage(data)))

        return widget


class QCustomGraphicsView(QtWidgets.QGraphicsView):
    """
    widget containing a view to display a tree-like architecture with nodes
    and branches

    Parameters
    ----------
    mainwin: MainWindow
        QMainWindow where the graph is displayed
    direction: {'horizontal', 'vertical'}, default='horizontal'
        direction of the pipeline;
        horizontal is left to right, vertical is top to bottom

    """
    nodeAdded = QtCore.pyqtSignal(QCustomGraphicsNode)

    def __init__(self, mainwin, direction='horizontal'):
        super().__init__()
        self._view = mainwin
        self.direction = direction
        self.setWindowState(QtCore.Qt.WindowMaximized)
        self.scene = QtWidgets.QGraphicsScene()
        self.setRenderHint(QtGui.QPainter.Antialiasing)
        self.setScene(self.scene)
        self.contextMenuEvent = lambda e: self.openMenu()
        self.setBackgroundBrush(eval(self._view.theme['background_brush']))

        self.installEventFilter(self)
        self.holdShift = False
        self.holdCtrl = False
        self._mouse_position = QtCore.QPoint(0, 0)
        self.nodes = {}
        self.focus = None

    def bind(self, parent, child):
        """
        create a link between a parent and a child node

        Parameters
        ----------
        parent, child: Node
            nodes to visually bind
        """

        link = ui.QGraphicsLink(parent, child, **self._view.theme['arrow'])

        parent.positionChanged.connect(link.updatePos)
        parent.sizeChanged.connect(link.updatePos)
        child.positionChanged.connect(link.updatePos)
        child.sizeChanged.connect(link.updatePos)
        child.sizeChanged.emit()

        parent.links.append(link)
        child.links.append(link)
        self.scene.addItem(link)

    def setEnabledScroll(self, enable_scroll=True):
        """
        enable/disable view scrolling

        Parameters
        ----------
        enable_scroll: bool, default True
        """
        self.verticalScrollBar().setEnabled(enable_scroll)
        self.horizontalScrollBar().setEnabled(enable_scroll)

    def getSelectedNodes(self, exceptions=[]):
        """
        get all selected nodes (with ctrl+click shortcut)

        Return
        ------
        result: list of Node
        """
        return [n for n in self.nodes.values() if n.isSelected() and n not in exceptions]

    def eventFilter(self, obj, event):
        """
        manage keyboard shortcut and mouse events on graph view
        """
        if obj == self:
            if event.type() == QtCore.QEvent.Wheel:
                return True
            if event.type() == QtCore.QEvent.MouseButtonPress:
                self.unselectNodes()
            elif event.type() == QtCore.QEvent.KeyPress:
                if event.key() == QtCore.Qt.Key_Shift:
                    self.holdShift = True
                elif event.key() == QtCore.Qt.Key_Control:
                    self.holdCtrl = True
            elif event.type() == QtCore.QEvent.KeyRelease:
                if event.key() == QtCore.Qt.Key_Shift:
                    self.holdShift = False
                elif event.key() == QtCore.Qt.Key_Control:
                    self.holdCtrl = False
        return super(QCustomGraphicsView, self).eventFilter(obj, event)

    def unselectNodes(self):
        for node in self.nodes.values():
            node.selected.setChecked(False)

    def getUniqueName(self, name, exception=None):
        """
        find an unused name by adding _n at the end of the name

        Parameters
        ----------
        name: str
            default non-unique name of the node
        exception: None or str
            if new name is exception, keep it

        Return
        ------
        new_name: str
            unique name for the node

        """
        i = 1
        new_name = copy.copy(name)
        while new_name in self.nodes and new_name != exception:
            new_name = "{0}_{1}".format(name, i)
            i += 1
        return new_name

    def openMenu(self, node=None):
        """
        open menu on right-clic at clicked position

        Parameters
        ----------
        node: QCustomGraphicsNode, default None
            if None open a menu with primary actions (load, ...)
            else open a menu with secondary actions (erosion, ...)

        """
        node = self.focus
        if node is None:
            acts = self._view.menu.get('primary')
            nodes = []
        else:
            acts = self._view.menu.get('secondary')
            nodes = [node] + self.getSelectedNodes()
            nodes = list(set(nodes))

        if acts is None:
            return

        def activate(action):
            type = action.text()
            if type in ["delete", "delete all"]:
                self.deleteBranch(node)
            else:
                self.addNode(action.text(), nodes)

        menu = utils.menu_from_dict(acts, activation_function=activate)
        pos = QtGui.QCursor.pos()
        self._mouse_position = self.mapToScene(self.mapFromGlobal(pos))
        menu.exec_(QtGui.QCursor.pos())

    def renameNode(self, node, new_name=None):
        # open input dialog
        if new_name is None:
            new_name, valid = QtWidgets.QInputDialog.getText(self, "user input", "new name",
                                                             QtWidgets.QLineEdit.Normal, node.type)
            if not valid:
                return
        new_name = self.getUniqueName(new_name, exception=node.name)
        self.nodes[new_name] = self.nodes.pop(node.name)
        node.rename(new_name)
        if node.name in RESULT_STACK:
            RESULT_STACK[new_name] = RESULT_STACK.pop(node.name)

    def deleteBranch(self, parent, childs_only=False):
        """
        delete node, its children and the associated data recursively

        Parameters
        ----------
        parent: QCustomGraphicsNode
        child_only: bool, default=False
            if True do not delete the parent node else delete parent and children

        """
        # delete data
        if parent.name in RESULT_STACK:
            del RESULT_STACK[parent.name]
        # delete children if has no other parent
        for child in parent.childs:
            child.parents.remove(parent)
            if not child.parents:
                self.deleteBranch(child)
        # remove node from parent children
        for p in parent.parents:
            p.childs.remove(parent)
        # delete node and links
        parent.delete()
        del self.nodes[parent.name]

    def addNode(self, type, parents=None, position=None):
        """
        create a node with specified parent nodes

        Parameters
        ----------
        type: str
            type of node
        parents: list of QCustomGraphicsNode or QCustomGraphicsNode

        """
        if parents is None:
            parents = []
        if not isinstance(parents, list):
            parents = [parents]

        for i, parent in enumerate(parents):
            if isinstance(parent, str):
                parents[i] = self.nodes[parent]

        name = self.getUniqueName(type)
        node = QCustomGraphicsNode(self, type, name, parents)
        node.addToScene(self.scene)

        if not parents:
            x, y = self._mouse_position.x(), self._mouse_position.y()
        else:
            max_x_parent = parents[0]
            for parent in parents:
                if parent.pos().x() > max_x_parent.pos().x():
                    max_x_parent = parent
                self.bind(parent, node)
                parent.childs.append(node)
            Ys = [c.pos().y() + c.height() for c in max_x_parent.childs if c is not node]
            x = max_x_parent.pos().x() + max_x_parent.width() + DEFAULT['space_between_nodes'][0]
            y = max_x_parent.pos().y() if not Ys else max(Ys) + DEFAULT['space_between_nodes'][1]

        # set state
        if position is not None:
            x, y = position.x(), position.y()

        node.moveBy(x, y)
        self.nodes[name] = node
        self.nodeAdded.emit(node)
        return node

    def setSettings(self, settings):
        """
        restore graph architecture and node parameters

        Parameters
        ----------
        settings: dict
            the dict-like description of the graph

        """
        for name, values in settings.items():
            node = self.addNode(values['state']['type'], values['state']['parents'], values['state']['position'])
            node.setSettings(values)

    def getSettings(self):
        """
        get graph architecture and node parameters

        Return
        ------
        settings: dict

        """
        settings = {}
        orderedNodes = []
        nodes = list(self.nodes.values())
        while nodes:
            node = nodes.pop(0)
            if not node.parents or set(node.parents).intersection(orderedNodes):
                settings[node.name] = node.getSettings()
                orderedNodes.append(node)
            else:
                nodes.append(node)
        return settings
