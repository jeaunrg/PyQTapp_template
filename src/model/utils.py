import sqlite3
import pandas as pd


def protector(foo):
    """
    function used as decorator to avoid the app to crash because of basic errors
    """
    def inner(*args, **kwargs):
        try:
            return foo(*args, **kwargs)
        except Exception as e:
            return e
    return inner


def to_datetime(arg, formats):
    res = []
    for v in arg:
        fit_format = False
        for format in formats:
            try:
                res.append(pd.to_datetime(v, format=format))
                fit_format = True
                break
            except ValueError:
                continue
        if not fit_format:
            raise ValueError("time data {} does not match any format".format(v))
    return res


class PySQL:
    def __init__(self, path):
        self.path = path
        self.bdd = sqlite3.connect(path)

    def initialize(self, table_name, dataframe):
        dataframe.to_sql(table_name, con=self.bdd, if_exists="replace")

    def feed(self, table_name, dataframe):
        dataframe.to_sql(table_name, con=self.bdd, if_exists="append")

    def execute(self, cmd):
        out = pd.read_sql_query(cmd, con=self.bdd)
        return out

    def close(self):
        self.bdd.close()
