from src.presenter.utils import view_manager
from src import CONFIG_DIR
import json
import os
from src import RESULT_STACK


class Presenter():
    """
    This class is part of the MVP app design, it acts as a bridge between
    the Model and the View

    Parameters
    ----------
    model: model.Model
    view: view.View

    """
    def __init__(self, view, model=None):
        self._model = model
        self._view = view
        self.threading_enabled = True
        self.init_view_connections()

    # ------------------------------ CONNECTIONS ------------------------------#
    def init_view_connections(self):
        self.modules = json.load(open(os.path.join(CONFIG_DIR, "modules.json"), "rb"))
        self._view.initMenu(self.modules)
        self._view.graph.nodeAdded.connect(lambda m: self.init_module_connections(m))

    def init_module_connections(self, module):
        """
        initialize module parameters if necessary
        create connections between view widgets and functions

        Parameters
        ----------
        module_name: str
            name of the loaded module

        """
        parameters = self.modules[module.type]
        module._runners = []

        if 'function' in parameters:
            activation_function = eval('self.'+parameters['function'])
            module.parameters.apply.clicked.connect(lambda: activation_function(module))

        # do custom connections
        # ...

    # --------------------- PRIOR  AND POST FUNCTION CALL ---------------------#
    def prior_to_function(self, module):
        """
        This method is called by the view_manager before of the function call

        Parameters
        ----------
        module: QWidget
        """
        module.loading.setMaximum(0)  # activate eternal loading
        module.lefthead.clear()
        module.lefthead.setToolTip(None)

    def post_function(self, module, output):
        """
        This method manage the output of a model function based on the output type
        it is called by the view_manager at the end of the model process

        Parameters
        ----------
        module: QWidget
        output: exception, str, pd.DataFrame, np.array, ...
        """
        RESULT_STACK[module.name] = output
        if isinstance(output, Exception):
            module.lefthead.setToolTip("[{0}] {1}".format(type(output).__name__, output))
            module.lefthead.setPixmap(self._view._fail)
        else:
            module.lefthead.setPixmap(self._view._valid)
        module.updateResult()

        # stop loading if one process is still running (if click multiple time
        # on the same button)
        are_running = [r.isRunning() for r in module._runners]
        if not any(are_running):
            module.loading.setMaximum(1)  # deactivate eternal loading

    # ----------------------------- MODEL CALL --------------------------------#
    @view_manager(True)
    def call_function1(self, module):
        # set model inputs
        function = self._model.function1
        args = {"minimum": module.parameters.minimum.value(),
                "maximum": module.parameters.maximum.value(),
                "sleep_time": module.parameters.sleeptime.value(),
                "insert_error": module.parameters.inserterror.isChecked()}

        # the view manager decorator will handle the function and its arguments
        return function, args
