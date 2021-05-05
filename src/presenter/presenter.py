from src.presenter.utils import view_manager, get_data, get_checked
from src import CONFIG_DIR
import json
import os
from src import RESULT_STACK, DESIGN_DIR, DATA_DIR, OUT_DIR
from src.utils import ceval, empty_to_none
from PyQt5 import QtWidgets, uic


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
        self._data_dir = DATA_DIR
        self._out_dir = OUT_DIR
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

        try:
            activation_function = eval('self.'+parameters['function'])
            module.parameters.apply.clicked.connect(lambda: activation_function(module))
        except AttributeError as e:
            print(e)

        # do connections
        if module.type in ["loadCSV", "SQLrequest"]:
            module.parameters.browse.clicked.connect(lambda: self.browse_data(module))

        elif module.type == "save":
            module.hideResult.hide()
            module.parameters.browse.clicked.connect(lambda: self.browse_savepath(module))

        else:
            parent_colnames = [list(get_data(name).columns) for name in
                               module.get_parent_names() if get_data(name) is not None]
            if not parent_colnames:
                pass

            elif module.type == "describe":
                module.parameters.column.addItems([''] + parent_colnames[0])
                module.parameters.group_by.addItems([''] + parent_colnames[0])

            elif module.type == "select":
                module.parameters.column.addItems(parent_colnames[0])

            elif module.type == "merge":
                flatten_colnames = sum(parent_colnames, [])
                module.parameters.on.addItems(flatten_colnames)
                module.parameters.left_on.addItems(['']+flatten_colnames)
                module.parameters.right_on.addItems(['']+flatten_colnames)

            elif module.type == "operation":
                def connectButton(but, txt_format="{0} {1}"):
                    txt = '/' if but.objectName() == 'divide' else but.text()
                    but.clicked.connect(lambda: module.parameters.formula.setText(
                                        txt_format.format(module.parameters.formula.text(), txt)))

                ncol = 2
                i, j = 0, 0
                for colname in parent_colnames[0]:
                    button = QtWidgets.QPushButton(colname)
                    module.parameters.grid.addWidget(button, i, j)
                    connectButton(button, "{0} [{1}]")
                    j += 1
                    if j == ncol:
                        j, i = 0, i+1

                for button in [module.parameters.subtract, module.parameters.add,
                               module.parameters.multiply, module.parameters.divide,
                               module.parameters.AND, module.parameters.OR,
                               module.parameters.parenthesis_l, module.parameters.parenthesis_r]:
                    connectButton(button)

            elif module.type == "standardize":
                dtypes = get_data(module.get_parent_names()[0]).dtypes.to_dict()

                def createTypeLine():
                    line = uic.loadUi(os.path.join(DESIGN_DIR, 'ui', 'modules', 'bricks', 'formatLine.ui'))

                    def hideFormat():
                        line.format.show() if line.types.currentText() == 'datetime' else line.format.hide()
                    line.types.currentIndexChanged.connect(hideFormat)
                    line.format.hide()

                    def hideUnit():
                        line.unit.show() if line.types.currentText() == 'timedelta' else line.unit.hide()
                    line.types.currentIndexChanged.connect(hideUnit)
                    line.unit.hide()

                    return line

                for i, colname in enumerate(dtypes):
                    module.parameters.form.addRow(QtWidgets.QLabel(colname), createTypeLine())

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

        module.updateResult(output)

        # stop loading if one process is still running (if click multiple time
        # on the same button)
        are_running = [r.isRunning() for r in module._runners]
        if not any(are_running):
            module.loading.setMaximum(1)  # deactivate eternal loading

    # ----------------------------- utils -------------------------------------#
    def browse_data(self, module):
        """
        open a browse window to select a csv file or sql database
        then update path in the corresponding QLineEdit
        """
        dialog = QtWidgets.QFileDialog()
        filename, valid = dialog.getOpenFileName(module.graph, "Select a file...", self._data_dir)
        if valid:
            self._data_dir = os.path.dirname(filename)
            module.parameters.path.setText(filename)
            module.parameters.path.setToolTip(filename)

    def browse_savepath(self, module):
        """
        open a browse window to define the nifti save path
        """
        name = module.get_parent_names()[0]
        filename, extension = QtWidgets.QFileDialog.getSaveFileName(module.graph, 'Save file',
                                                                    os.path.join(self._out_dir, name), filter=".csv")
        self._out_dir = os.path.dirname(filename)
        module.parameters.path.setText(filename+extension)
        module.parameters.path.setToolTip(filename+extension)

    # ----------------------------- MODEL CALL --------------------------------#
    @view_manager(True)
    def call_load_data(self, module):
        separator = module.parameters.separator.text()
        function = self._model.load_data
        args = {"path": module.parameters.path.text(),
                "separator": '\t' if separator == '\\t' else separator,
                "decimal": module.parameters.decimal.text(),
                "header": ceval(module.parameters.header.text()),
                "encoding": module.parameters.encoding.text(),
                "clean": module.parameters.clean.isChecked(),
                "sort": module.parameters.sort.isChecked()}
        return function, args

    @view_manager(True)
    def call_request_database(self, module):
        function = self._model.request_database
        args = {"url": module.parameters.path.text(),
                "sql_command": module.parameters.command.text()}
        return function, args

    @view_manager(True)
    def call_describe(self, module):
        function = self._model.compute_stats
        args = {"df": get_data(module.get_parent_names()[0]),
                "column": empty_to_none(module.parameters.column.currentText()),
                "groupBy": empty_to_none(module.parameters.group_by.currentText()),
                "statistics": get_checked(module.parameters, ["count", "minimum", "maximum",
                                                              "mean", "sum", "median", "std"]),
                "ignore_nan": module.parameters.ignore_nan.isChecked()}
        return function, args

    @view_manager(True)
    def call_select(self, module):
        function = self._model.select_data
        args = {"df": get_data(module.get_parent_names()[0]),
                "column": module.parameters.column.currentText(),
                "equal_to":  ceval(module.parameters.equal_to.text()),
                "different_from":  ceval(module.parameters.different_from.text()),
                "higher_than": ceval(module.parameters.higher_than.text()),
                "lower_than": ceval(module.parameters.lower_than.text()),
                "logical": get_checked(module.parameters, ["or", "and"])[0]}
        return function, args

    @view_manager(True)
    def call_operation(self, module):
        function = self._model.apply_formula
        args = {"df": get_data(module.get_parent_names()[0]),
                "formula": module.parameters.formula.text(),
                "formula_name": module.name}
        return function, args

    @view_manager(True)
    def call_standardize(self, module):
        type_dict, format_dict, unit_dict = {}, {}, {}
        for i in range(module.parameters.form.rowCount()):
            label = module.parameters.form.itemAt(i, 0).widget().text()
            hbox = module.parameters.form.itemAt(i, 1).widget().layout()
            type_dict[label] = hbox.itemAt(0).widget().currentText()
            if type_dict[label] == 'datetime':
                format_dict[label] = hbox.itemAt(1).widget().text()
            if type_dict[label] == 'timedelta':
                unit_dict[label] = hbox.itemAt(2).widget().currentText()
            if type_dict[label] == '--':
                type_dict[label] = ''

        function = self._model.standardize
        args = {"df": get_data(module.get_parent_names()[0]),
                "type_dict": type_dict,
                "format_dict": format_dict,
                "unit_dict": unit_dict}
        return function, args

    @view_manager(True)
    def call_save_data(self, module):
        function = self._model.save_data
        args = {"path": module.parameters.path.text(),
                "dfs": [get_data(n) for n in module.get_parent_names()]}
        return function, args

    @view_manager(True)
    def call_merge(self, module):
        function = self._model.merge
        args = {"dfs": [get_data(n) for n in module.get_parent_names()],
                "how": module.parameters.how.currentText(),
                "on": ceval(module.parameters.on.currentText()),
                "left_on": ceval(module.parameters.left_on.currentText()),
                "right_on": ceval(module.parameters.right_on.currentText()),
                "left_index": module.parameters.left_index.isChecked(),
                "right_index": module.parameters.right_index.isChecked(),
                "sort": ceval(module.parameters.suffixes.text())}
        return function, args
