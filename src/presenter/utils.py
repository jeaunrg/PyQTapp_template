from PyQt5 import QtCore


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
                module._runners.remove(runner)
        return inner
    return decorator
