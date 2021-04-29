from PyQt5 import QtCore
RUNNERS = []

def manage_function(output_function, input_function, input_args, inthread=True):
    """
    this function activate a function with its arguments inside a thread or not
    and relay the result to an output function.

    Parameters
    ----------
    input_function: function
        function to be activated in the background (or not)
    input_args: dict
        arguments of the input_function
    output_function: function
        function activated at the end of the thread and that take
        input_function result as input
    inthread: bool, default=True
        if True activate input_function in a QThread

    """
    if inthread:
        runner = Runner(input_function, **input_args)
        RUNNERS.append(runner) # needed to keep a trace of the QThread
        runner.finished.connect(lambda: output_function(runner.out))
        runner.finished.connect(lambda: RUNNERS.remove(runner))
        runner.start()
    else:
        output_function(input_function(**input_args))


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

        # where the funciton result is stored
        self.out = None

    def run(self):
        self.out = self._target(*self._args, **self._kwargs)
