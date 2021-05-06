import json
import os
from src import RESULT_STACK, DATA_DIR, OUT_DIR, CONFIG_DIR
from src.utils import ceval, empty_to_none
from src.view.utils import replaceWidget
from src.presenter import utils
from PyQt5 import QtWidgets
from src.view import ui
import pandas as pd


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

        self.init_modules_custom_connections(module)

    def init_modules_custom_connections(self, module):

        if module.type == "loadCSV":
            module.parameters.browse.clicked.connect(lambda: self.browse_data(module))

        elif module.type == "SQLrequest":
            module.parameters.browse.clicked.connect(lambda: (self.browse_data(module),
                                                              self.update_sql_module(module)))

        elif module.type == "save":
            module.parameters.browse.clicked.connect(lambda: self.browse_savepath(module))

        else:
            parent_colnames = [list(utils.get_data(name).columns) for name in
                               module.get_parent_names() if isinstance(utils.get_data(name), pd.DataFrame)]
            if not parent_colnames:
                pass

            elif module.type == "describe":
                module.parameters.column.clear()
                module.parameters.column.addItems([''] + parent_colnames[0])
                module.parameters.group_by.clear()
                module.parameters.group_by.addItems([''] + parent_colnames[0])

            elif module.type == "selectColumns":
                ncol = 2
                i, j = 0, 0
                for colname in parent_colnames[0]:
                    button = QtWidgets.QPushButton(colname)
                    button.setCheckable(True)
                    button.setChecked(True)
                    module.parameters.grid.addWidget(button, i, j)
                    module.parameters.grid.__dict__[colname] = button
                    j += 1
                    if j == ncol:
                        j, i = 0, i+1

                def checkAll(state):
                    for b in module.parameters.grid.__dict__.values():
                        b.setChecked(state)
                module.parameters.selectAll.clicked.connect(lambda s: checkAll(True))
                module.parameters.deselectAll.clicked.connect(lambda s: checkAll(False))

            elif module.type == "selectRows":
                module.parameters.column.addItems(parent_colnames[0])

            elif module.type == "merge":
                flatten_colnames = sum(parent_colnames, [])
                module.parameters.on.clear()
                module.parameters.on.addItems(flatten_colnames)
                module.parameters.left_on.clear()
                module.parameters.left_on.addItems(['']+flatten_colnames)
                module.parameters.right_on.clear()
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
                for i in range(module.parameters.form.rowCount()):
                    module.parameters.form.removeRow(0)
                for i, colname in enumerate(parent_colnames[0]):
                    line = ui.QFormatLine()
                    module.parameters.form.addRow(QtWidgets.QLabel(colname), line)
                    module.parameters.__dict__['format_line_{}'.format(i)] = line
                module.resize(module.parameters.form.sizeHint().width()+50, module.height())

        module.setSettings(self._view.settings['graph'].get(module.name))

    def update_sql_module(self, module):
        description_dataframe = self._model.describe_database(module.parameters.path.text())
        if isinstance(description_dataframe, Exception):
            return self.call_test_database_connection(module)

        names = description_dataframe['name']
        grid = utils.build_widgets_grid(QtWidgets.QRadioButton, names, checked='first')
        module.parameters.tableNames = replaceWidget(module.parameters.tableNames, grid)

        def update_columns(state, name):
            if not state:
                return
            table_description = self._model.describe_table(module.parameters.path.text(), name)
            colnames_grid = utils.build_widgets_grid(QtWidgets.QPushButton, table_description['name'], checked='all')
            module.parameters.colnames = replaceWidget(module.parameters.colnames, colnames_grid)

        def connectRadio(radiobutton):
            radiobutton.toggled.connect(lambda s: update_columns(s, radiobutton.text()))

        for w in grid.__dict__.values():
            connectRadio(w)

        update_columns(True, names[0])

    # --------------------- PRIOR  AND POST FUNCTION CALL ---------------------#

    def prior_to_function(self, module):
        """
        This method is called by the utils.view_manager before of the function call

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
        it is called by the utils.view_manager at the end of the model process

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
        for child in module.childs:
            self.init_modules_custom_connections(child)

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
    @utils.view_manager(True)
    def call_test_database_connection(self, module):
        function = self._model.request_database
        args = {'url': module.parameters.path.text()}
        return function, args

    @utils.view_manager(True)
    def call_extract_from_database(self, module):
        function = self._model.extract_from_database
        args = {"url": module.parameters.path.text(),
                "table": utils.get_checked(module.parameters.tableNames)[0],
                "columns": utils.get_checked(module.parameters.colnames)}
        return function, args

    @utils.view_manager(True)
    def call_load_data(self, module):
        separator = module.parameters.separator.currentText()
        if separator == "{tabulation}":
            separator = '\t'
        elif separator == '{espace}':
            separator = ' '

        function = self._model.load_data
        args = {"path": module.parameters.path.text(),
                "separator": separator,
                "decimal": module.parameters.decimal.currentText(),
                "header": ceval(module.parameters.header.text()),
                "encoding": module.parameters.encoding.currentText(),
                "clean": module.parameters.clean.isChecked(),
                "sort": module.parameters.sort.isChecked()}
        return function, args

    @utils.view_manager(True)
    def call_describe(self, module):
        function = self._model.compute_stats
        args = {"df": utils.get_data(module.get_parent_names()[0]),
                "column": empty_to_none(module.parameters.column.currentText()),
                "groupBy": empty_to_none(module.parameters.group_by.currentText()),
                "statistics": utils.get_checked(module.parameters, ["count", "minimum", "maximum",
                                                                    "mean", "sum", "median", "std"]),
                "ignore_nan": module.parameters.ignore_nan.isChecked()}
        return function, args

    @utils.view_manager(True)
    def call_select_rows(self, module):
        function = self._model.select_rows
        args = {"df": utils.get_data(module.get_parent_names()[0]),
                "column": module.parameters.column.currentText(),
                "equal_to":  ceval(module.parameters.equal_to.text()),
                "different_from":  ceval(module.parameters.different_from.text()),
                "higher_than": ceval(module.parameters.higher_than.text()),
                "lower_than": ceval(module.parameters.lower_than.text()),
                "logical": utils.get_checked(module.parameters, ["or", "and"])[0]}
        return function, args

    @utils.view_manager(True)
    def call_select_columns(self, module):
        function = self._model.select_columns
        args = {"df": utils.get_data(module.get_parent_names()[0]),
                "columns": utils.get_checked(module.parameters.grid)}
        return function, args

    @utils.view_manager(True)
    def call_operation(self, module):
        function = self._model.apply_formula
        args = {"df": utils.get_data(module.get_parent_names()[0]),
                "formula": module.parameters.formula.text(),
                "formula_name": module.name}
        return function, args

    @utils.view_manager(True)
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
        args = {"df": utils.get_data(module.get_parent_names()[0]),
                "type_dict": type_dict,
                "format_dict": format_dict,
                "unit_dict": unit_dict}
        return function, args

    @utils.view_manager(True)
    def call_save_data(self, module):
        function = self._model.save_data
        args = {"path": module.parameters.path.text(),
                "dfs": [utils.get_data(n) for n in module.get_parent_names()]}
        return function, args

    @utils.view_manager(True)
    def call_merge(self, module):
        function = self._model.merge
        args = {"dfs": [utils.get_data(n) for n in module.get_parent_names()],
                "how": module.parameters.how.currentText(),
                "on": ceval(module.parameters.on.currentText()),
                "left_on": ceval(module.parameters.left_on.currentText()),
                "right_on": ceval(module.parameters.right_on.currentText()),
                "left_index": module.parameters.left_index.isChecked(),
                "right_index": module.parameters.right_index.isChecked(),
                "sort": ceval(module.parameters.suffixes.text())}
        return function, args
