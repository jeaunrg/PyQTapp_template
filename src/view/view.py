from PyQt5 import QtWidgets, QtCore, QtGui, uic
from src import DESIGN_DIR, DEFAULT
import json
import os
import pdb

class View(QtWidgets.QMainWindow):
    """
    this class is a part of the MVP app design, it shows all the user interface
    and send signals for specific actions

    """
    def __init__(self):
        super().__init__()
        uic.loadUi(os.path.join(DESIGN_DIR, "ui", "MainView.ui"), self)

        self.modules = {}
        self.add.clicked.connect(lambda: self.addModule("module1"))

        self.initUI()

    def initUI(self):
        self._fail = QtGui.QPixmap(os.path.join(DESIGN_DIR, "icon", "fail.png"))
        self._fail = self._fail.scaled(20, 20, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
        self._valid = QtGui.QPixmap(os.path.join(DESIGN_DIR, "icon", "valid.png"))
        self._valid = self._valid.scaled(20, 20, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)

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

        # set default style
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




    module_added = QtCore.pyqtSignal(str)
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
        self.module_added.emit(moduleName)
