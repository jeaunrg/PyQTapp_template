from PyQt5 import QtCore, QtWidgets
from src import RESULT_STACK
import copy


class Runner(QtCore.QThread):
    """
    QThread that activate a function with arguments

    Parameters
    ----------
    target: function
    *args, **kwargs: function arguments
    """
    def __init__(self, target, *args, **kwargs):
        super().__init__()
        self._target = target
        self._args = args
        self._kwargs = kwargs

        # where the function result is stored
        self.out = None

    def run(self):
        self.out = self._target(*self._args, **self._kwargs)


def view_manager(threadable=True):
    """
    this decorator manage threading

    Parameters
    ----------
    threadable: bool, default=True
        if True, the model function will be processed inside a QThread (if allowed)

    """
    def decorator(foo):
        def inner(presenter, module):
            presenter.prior_to_function(module)
            function, args = foo(presenter, module)

            # start the process inside a QThread
            if threadable and presenter.threading_enabled:
                runner = Runner(function, **args)
                module._runners.append(runner)
                runner.finished.connect(lambda: (presenter.post_function(module, runner.out),
                                                 module._runners.remove(runner)))
                runner.start()
            else:
                presenter.post_function(module, function(**args))
        return inner
    return decorator


def get_data(name):
    if name in RESULT_STACK:
        return copy.copy(RESULT_STACK[name])


def get_checked(widget, names=None):
    checked = []
    if names is None:
        for name, w in widget.__dict__.items():
            if w.isChecked():
                checked.append(name)
    else:
        for name in names:
            w = widget.__dict__[name]
            if w.isChecked():
                checked.append(name)
    return checked


def store_data(name, df):
    RESULT_STACK[name] = df


def build_widgets_grid(widget_type, names, ncol=2, checked=None):
    grid = QtWidgets.QWidget()
    layout = QtWidgets.QGridLayout()
    ncol = 2
    i, j = 0, 0
    for name in names:
        widget = widget_type(name)
        if checked:
            if isinstance(widget, QtWidgets.QPushButton):
                widget.setCheckable(True)
            if isinstance(widget, QtWidgets.QRadioButton):
                widget.setAutoExclusive(True)
            if checked == 'all' or checked == 'first' and name == names[0]:
                widget.setChecked(True)

        grid.__dict__[name] = widget
        layout.addWidget(widget, i, j)
        j += 1
        if j == ncol:
            j, i = 0, i+1
    if len(names) == 1:
        widget.setEnabled(False)
    grid.setLayout(layout)
    return grid
