from src.presenter.utils import view_manager


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
        self._view.add.clicked.connect(lambda: (self._view.addModule("module1"),
                                                self.init_module_connections("module1")))

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

    # --------------------- PRIOR  AND POST FUNCTION CALL ---------------------#

    def prior_to_function(self, module):
        """
        This method is called by the view_manager before of the function call

        Parameters
        ----------
        module: QWidget
        """
        module.loading.setMaximum(0)  # activate eternal loading
        module.state.clear()
        module.setToolTip(None)

    def post_function(self, module, output):
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
        args = {"minimum": module.minimum.value(),
                "maximum": module.maximum.value(),
                "sleep_time": module.sleeptime.value(),
                "insert_error": module.inserterror.isChecked()}

        # the view manager decorator will handle the function and its arguments
        return function, args
