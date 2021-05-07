from PyQt5 import QtCore
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


def manager(threadable=True):
    """
    this decorator manage threading

    Parameters
    ----------
    threadable: bool, default=True
        if True, the model function will be processed inside a QThread (if allowed)

    """
    def decorator(foo):
        def inner(presenter, module):
            presenter.prior_manager(module)
            function, args = foo(presenter, module)

            # start the process inside a QThread
            if threadable and presenter.threading_enabled:
                runner = Runner(function, **args)
                module._runners.append(runner)
                runner.finished.connect(lambda: (presenter.post_manager(module, runner.out),
                                                 module._runners.remove(runner)))
                runner.start()
            else:
                presenter.post_manager(module, function(**args))
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
