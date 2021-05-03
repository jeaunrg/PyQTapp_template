from PyQt5 import QtWidgets


def dict_from_list(dict_to_complete, element_list):
    """
    convert a list of elements into a one-branch dictionary

    Parameters
    ----------
    dict_to_complete
    element_list: list

    """
    if element_list:
        element = element_list.pop(0)
        dict_to_complete.setdefault(element, {})
    if element_list:
        dict_from_list(dict_to_complete.get(element), element_list)


def menu_from_dict(acts, activation_function=None, menu=None):
    """
    create a menu on right-click, based on 'acts' dictionnary

    Parameters
    ----------
    acts: dict
        actions to insert in menu
    activation_function: function, optionnal
        function that takes a QAction as argument and apply the requested action
    menu: QMenu, optionnal
        menu to fill

    Return
    ------
    menu: QMenu

    """
    if menu is None:
        menu = QtWidgets.QMenu()
    for a, subacts in acts.items():
        if not subacts:
            act = menu.addAction(a)
            if activation_function is not None:
                def connect(action):
                    action.triggered.connect(lambda: activation_function(action))
                connect(act)
        else:
            submenu = menu.addMenu(a)
            menu_from_dict(subacts, activation_function, submenu)
    return menu
