from PyQt5 import QtWidgets, QtCore, QtGui
from src.view import ui, utils
from src import RESULT_STACK, DESIGN_DIR, DEFAULT
import pandas as pd
import copy
import os


class QCustomGraphicsNode(ui.QGraphicsNode):

    def __init__(self, *args, **kwargs):
        super(QCustomGraphicsNode, self).__init__(*args, **kwargs)
        self.button.clicked.connect(self.hideShowParameters)

        # add parameters widget
        uifile_path = os.path.join(DESIGN_DIR, 'ui', self.type+'.ui')
        if not os.path.isfile(uifile_path):
            return print("{} does not exists".format(uifile_path))
        self.setParametersWidget(uifile_path)
        self.parameters.hide()

    def hideShowParameters(self):
        if self.parameters.isHidden():
            self.parameters.show()
        else:
            self.parameters.hide()
        self.updateHeight(True)

    def updateResult(self):
        result = RESULT_STACK.get(self.name)

        # create the output widget depending on output type
        if isinstance(result, (int, float, str, bool)):
            new_widget = self.computeTextWidget(result)
        elif isinstance(result, pd.DataFrame):
            new_widget = self.computeTableWidget(result)
        else:
            new_widget = QtWidgets.QWidget()

        # replace current output widget with the new one
        self.vbox.replaceWidget(self.result, new_widget)
        self.result.deleteLater()
        self.result = new_widget
        self.updateHeight(True)

    def updateHeight(self, force=False):
        if self.result.sizeHint() == QtCore.QSize(-1, -1):
            if force:
                width = self.width()
                self.adjustSize()
                self.resize(width, self.minimumHeight()+1)
            self.resize(self.width(), 0)

    def computeTextWidget(self, data):
        default_fontsize = 30

        widget = QtWidgets.QLabel(str(data))
        widget.setAlignment(QtCore.Qt.AlignCenter)
        widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        font = QtGui.QFont()
        font.setPointSize(default_fontsize)
        widget.setFont(font)

        # update fontsize to fit widget size
        metric = QtGui.QFontMetrics(font)
        ratio = metric.boundingRect(str(data)).size() / default_fontsize

        def fitFontSize():
            if isinstance(self.result, QtWidgets.QLabel):
                fontsize = max([min([self.result.width() / ratio.width(),
                                     self.result.height() / ratio.height()]) - 10, 10])
                font.setPointSize(fontsize)
                self.result.setFont(font)
        self.sizeChanged.connect(fitFontSize)
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
        self.settings = {}
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
            if type == "rename":
                self.renameNode(node)
            elif type in ["delete", "delete all"]:
                self.deleteBranch(node)
            else:
                self.addNode(action.text(), nodes)

        menu = utils.menu_from_dict(acts, activation_function=activate)
        pos = QtGui.QCursor.pos()
        self._mouse_position = self.mapToScene(self.mapFromGlobal(pos))
        menu.exec_(QtGui.QCursor.pos())

    def renameNode(self, node):
        # open input dialog
        new_name, valid = QtWidgets.QInputDialog.getText(self, "user input", "new name",
                                                         QtWidgets.QLineEdit.Normal, node.type)
        if valid:
            new_name = self.getUniqueName(new_name, exception=node.name)
            self.nodes[new_name] = self.nodes.pop(node.name)
            node.rename(new_name)

    def deleteBranch(self, parent, childs_only=False):
        """
        delete node, its children and the associated data recursively

        Parameters
        ----------
        parent: QCustomGraphicsNode
        child_only: bool, default=False
            if True do not delete the parent node else delete parent and children

        """
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

    def restoreGraph(self, settings):
        """
        restore graph architecture

        Parameters
        ----------
        settings: dict
            the dict-like description of the graph

        """
        for k, values in settings.items():
            self.addNode(**values)

    def addNode(self, type, parents=None):
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

        node.moveBy(x, y)
        self.nodes[name] = node
        self.settings[name] = {'type': type, 'parents': [p.name for p in parents]}
        self.nodeAdded.emit(node)
        return node
