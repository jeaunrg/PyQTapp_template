from PyQt5 import QtCore
import numpy as np
import copy
import os
RUNNERS = []
N_RUNNERS = {}


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
    this decorator manage the loading gif and threading

    Parameters
    ----------
    threadable: bool, default=True
        if True, the model function will be processed inside a QThread (if allowed)

    """
    def decorator(foo):
        def inner(presenter, module):
            module.loading.setMaximum(0)
            module.state.clear()
            module.setToolTip(None)
            function, args = foo(presenter, module)

            def del_run(runner=None):
                if runner is not None:
                    module._runners.remove(runner)
                stop_loading = 1
                for r in module._runners:
                    if r.isRunning():
                        stop_loading = 0
                module.loading.setMaximum(stop_loading)

            # start the process inside a QThread
            if threadable and presenter.threading_enabled:
                runner = Runner(function, **args)
                module._runners.append(runner)
                runner.finished.connect(lambda: (presenter.manage_output(module, runner.out),
                                                 del_run()))
                runner.start()
            else:
                presenter.manage_output(module, function(**args))
                del_run()
        return inner
    return decorator
