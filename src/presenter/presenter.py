from datetime import datetime
from src.presenter.utils import view_manager
from src.view import ui


class Presenter():
    """
    This class is part of the MVP app design, it acts as a bridge between
    the Model and the View

    Parameters
    ----------
    model: model.Model
    view: view.View

    """
    def __init__(self, model, view):
        self._model = model
        self._view = view
        self._view.module_added.connect(lambda e: self.init_module_connections(e))
        self.threading_enabled = True

    def init_module_connections(self, module_name):
        """
        initialize module parameters if necessary
        create connections between view widgets and functions

        Parameters
        ----------
        module_name: str
            name of the loaded module

        """
        module = self._view.modules[module_name]
        module._runners = []

        # do connections
        if module_name == "module1":
            module.button.clicked.connect(lambda: self.call_function1(module))


    def manage_output(self, module, output):
        """
        This method manage the output of a model function based on the output type
        it is called by the view_manager at the end of the model process

        Parameters
        ----------
        module: QWidget
        output: exception, str, pd.DataFrame, np.array, ...
        """

        if isinstance(output, Exception):
            module.state.setToolTip("[{0}] {1}".format(type(output).__name__, output))
            module.state.setPixmap(self._view._fail)
        else:
            if isinstance(output, int):
                module.result.setText(str(output))
            module.state.setPixmap(self._view._valid)

    # ----------------------------- MODEL CALL --------------------------------#
    @view_manager(True)
    def call_function1(self, module):
        # initialize
        module.result.setText("")

        # set model inputs
        function = self._model.function1
        args = {"minimum": module.minimum.value(),
                "maximum": module.maximum.value(),
                "sleep_time": module.sleeptime.value(),
                "insert_error": module.inserterror.isChecked()}

        # the view manager decorator will handle the function and its arguments
        return function, args
