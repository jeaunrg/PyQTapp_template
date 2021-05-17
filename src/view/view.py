from PyQt5 import QtWidgets, QtCore, QtGui, uic
from src import DESIGN_DIR, DEFAULT, CONFIG_DIR
from src.view import graph, utils
import json
import os


class View(QtWidgets.QMainWindow):
    """
    this class is a part of the MVP app design, it shows all the user interface
    and send signals for specific actions

    """

    def __init__(self):
        super().__init__()
        uic.loadUi(os.path.join(DESIGN_DIR, "ui", "MainView.ui"), self)
        if DEFAULT['window_size'] == 'fullscreen':
            self.showMaximized()
        else:
            self.resize(*DEFAULT['window_size'])

        # set short cuts
        self.save = QtWidgets.QShortcut(QtGui.QKeySequence('Ctrl+S'), self)
        self.save.activated.connect(self.saveSettings)

        self.restore = QtWidgets.QShortcut(QtGui.QKeySequence('Ctrl+R'), self)
        self.restore.activated.connect(self.restoreSettings)
        self.session = None

        self.modules = {}
        self.initStyle()
        self.initUI()

    def initStyle(self):
        """
        This method initialize styles and useful icons
        """
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
        if style is None:
            return QtWidgets.qApp.setStyleSheet('')

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
        self.setTabPosition(QtCore.Qt.RightDockWidgetArea, QtWidgets.QTabWidget.West)
        self.setTabPosition(QtCore.Qt.LeftDockWidgetArea, QtWidgets.QTabWidget.East)

        self.settings = {'graph': {}}

        self.actionOpenSession.triggered.connect(self.openSession)
        self.actionNewSession.triggered.connect(self.newSession)

        self.graph = graph.QGraph(self, 'vertical')
        self.setCentralWidget(self.graph)
        self.setWindowState(QtCore.Qt.WindowActive)

    def initModulesParameters(self, modules):
        """
        create right-clic menu from modules
        """
        # initalize right-clic-menu
        self.menu = {}
        self.modules_parameters = {}
        for k, values in modules.items():
            lst = [values['type']]
            if 'menu' in values:
                lst += values['menu'].split('/')
            lst.append(k)
            utils.dict_from_list(self.menu, lst)
            self.modules_parameters[k] = {'color': values.get('color'),
                                          'nparents': values.get('nparents')}

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

    def addWidgetInDock(self, widget, side=QtCore.Qt.RightDockWidgetArea, unique=True):
        """
        put widget inside a qdock widget

        Parameters
        ----------
        widget: QWidget

        Return
        ------
        dock: QDockWidget

        """
        if unique and isinstance(widget.parent(), QtWidgets.QDockWidget):
            dock = widget.parent()
            self.restoreDockWidget(dock)
        else:
            dock = QtWidgets.QDockWidget()
            # dock.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
            dock.setAllowedAreas(QtCore.Qt.RightDockWidgetArea | QtCore.Qt.LeftDockWidgetArea)
            dock.setFeatures(QtWidgets.QDockWidget.AllDockWidgetFeatures)

            docks = self.findChildren(QtWidgets.QDockWidget)

            dock.setWidget(widget)
            self.addDockWidget(side, dock)

            # tabify dock to existant docks
            for dk in docks:
                if self.dockWidgetArea(dk) == side:
                    self.tabifyDockWidget(dk, dock)
                    break

        dock.show()
        dock.raise_()
        return dock

    def openSession(self):
        sessions = [os.path.splitext(i)[0] for i in os.listdir(os.path.join(CONFIG_DIR, "sessions"))]
        session, ok = QtWidgets.QInputDialog.getItem(None, "Sessions", 'open session:', sessions, 0, False)
        if ok:
            self.graph.deleteAll()
            self.session = session
            self.loadSettings(False)
            self.restoreSettings()

    def newSession(self):
        session, ok = QtWidgets.QInputDialog.getText(None, "New session", 'session name:')
        if ok:
            self.session = session
            self.settings = {'graph': {}}
            self.graph.deleteAll()
            self.saveSettings()

    def loadSettings(self, append=True):
        if os.path.isfile(os.path.join(CONFIG_DIR, 'sessions', self.session + '.json')):
            with open(os.path.join(CONFIG_DIR, 'sessions', self.session + '.json'), 'r') as fp:
                if append:
                    self.settings.update(json.load(fp))
                else:
                    self.settings = json.load(fp)

    def saveSettings(self):
        self.settings['graph'] = self.graph.getSettings()
        with open(os.path.join(CONFIG_DIR, 'sessions', self.session + '.json'), 'w') as fp:
            json.dump(self.settings, fp, indent=4)

    def restoreSettings(self):
        self.graph.setSettings(self.settings['graph'])

    def closeEvent(self, event):
        QtWidgets.QMainWindow.closeEvent(self, event)
