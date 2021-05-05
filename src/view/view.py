from PyQt5 import QtWidgets, QtCore, QtGui, uic
from src import DESIGN_DIR, DEFAULT
from src.view import graph, utils
import json
import os


class View(QtWidgets.QMainWindow):
    """
    this class is a part of the MVP app design, it shows all the user interface
    and send signals for specific actions

    """
    closed = QtCore.pyqtSignal()

    def __init__(self):
        super().__init__()
        uic.loadUi(os.path.join(DESIGN_DIR, "ui", "MainView.ui"), self)
        if DEFAULT['window_size'] == 'fullscreen':
            self.showMaximized()
        else:
            self.resize(*DEFAULT['window_size'])
        self.modules = {}
        self.initStyle()
        self.initUI()

    def initStyle(self):
        """
        This method initialize styles and useful icons
        """
        # initialize icons
        self._fail = QtGui.QPixmap(os.path.join(DESIGN_DIR, "icon", "fail.png"))
        self._fail = self._fail.scaled(15, 15, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
        self._valid = QtGui.QPixmap(os.path.join(DESIGN_DIR, "icon", "valid.png"))
        self._valid = self._valid.scaled(15, 15, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)

        # create menu and actions for stylesheet and themes
        self.theme, self.style = None, None

        def getAction(name, function):
            name = os.path.splitext(name)[0]
            act = QtWidgets.QAction(name, self)
            act.triggered.connect(lambda: function(name))
            return act
        # add menus
        menuStyles = self.menuPreferences.addMenu('Styles')
        for style in os.listdir(os.path.join(DESIGN_DIR, 'qss')):
            menuStyles.addAction(getAction(style, self.loadStyle))

        menuThemes = self.menuPreferences.addMenu('Themes')
        for theme in os.listdir(os.path.join(DESIGN_DIR, 'themes')):
            menuThemes.addAction(getAction(theme, self.loadTheme))

        # load default style and theme
        self.loadTheme()
        self.loadStyle()

    def loadTheme(self, theme=DEFAULT['theme']):
        with open(os.path.join(DESIGN_DIR, "themes", theme + ".json"), "r") as f:
            self.theme = json.load(f)
        if self.style is not None:
            QtWidgets.qApp.setStyleSheet(self.style % self.theme['qss'])

    def loadStyle(self, style=DEFAULT['style']):
        with open(os.path.join(DESIGN_DIR, "qss", style+".qss"), "r") as f:
            self.style = f.read()
        if self.theme is not None:
            QtWidgets.qApp.setStyleSheet(self.style % self.theme['qss'])
        else:
            QtWidgets.qApp.setStyleSheet(self.style)

    def initUI(self):
        """
        This method init widgets UI for the main window
        """
        self.graph = graph.QCustomGraphicsView(self, 'horizontal')
        self.setCentralWidget(self.graph)
        self.setWindowState(QtCore.Qt.WindowActive)

    def initMenu(self, modules):
        """
        create right-clic menu from modules
        """
        # initalize right-clic-menu
        self.menu = {}
        for k, values in modules.items():
            lst = [values['type']]
            if 'menu' in values:
                lst += values['menu'].split('/')
            lst.append(k)
            utils.dict_from_list(self.menu, lst)

    def addModule(self, moduleName):
        """
        add a new module in the central layout

        Parameters
        ----------
        moduleName: str

        """
        module = uic.loadUi(os.path.join(DESIGN_DIR, "ui", moduleName+".ui"))
        self.hbox.addWidget(module)

        self.modules[moduleName] = module

    def addWidgetInDock(self, widget):
        """
        put widget inside a qdock widget

        Parameters
        ----------
        widget: QWidget

        Return
        ------
        dock: QDockWidget

        """
        dock = QtWidgets.QDockWidget()
        dock.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        dock.setAllowedAreas(QtCore.Qt.RightDockWidgetArea | QtCore.Qt.LeftDockWidgetArea)
        dock.setFeatures(QtWidgets.QDockWidget.AllDockWidgetFeatures)
        docks = self.findChildren(QtWidgets.QDockWidget)

        dock.setWidget(widget)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, dock)

        if len(docks) > 1:
            self.tabifyDockWidget(docks[-1], dock)
        elif len(docks) > 0:
            self.splitDockWidget(docks[-1], dock, QtCore.Qt.Horizontal)
        self.setTabPosition(QtCore.Qt.RightDockWidgetArea, QtWidgets.QTabWidget.South)
        dock.show()
        dock.raise_()
        return dock

    def closeEvent(self, event):
        self.closed.emit()
        QtWidgets.QMainWindow.closeEvent(self, event)
