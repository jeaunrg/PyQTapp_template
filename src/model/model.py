from src.model import utils
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import copy
import matplotlib
import matplotlib.pyplot as plt


class Model():

    @utils.protector
    def request_database(self, url, cmd=None):
        pysql = utils.PySQL(url)
        pysql.connect()
        if cmd is not None:
            outdf = pysql.execute(cmd)
        pysql.close()
        return outdf

    @utils.protector
    def describe_database(self, url):
        cmd = "SELECT * FROM sqlite_master WHERE type='table'"
        return self.request_database(url, cmd)

    @utils.protector
    def describe_table(self, url, table_name):
        cmd = "PRAGMA table_info({})".format(table_name)
        return self.request_database(url, cmd)

    @utils.protector
    def extract_from_database(self, url, table, columns):
        if table is None:
            raise ValueError("Empty table")
        cmd = "SELECT [{0}] FROM {1}".format("], [".join(columns), table)
        return self.request_database(url, cmd)

    @utils.protector
    def computeTransfusion(self, df, groupby, time_colname, value_colname, normalize_time=True, time_format=None):
        # df = df[[groupby, time_colname, value_colname]]
        df = self.standardize(df, {time_colname: ('time', time_format), value_colname: 'float'})
        if isinstance(df, Exception):
            return df
        if normalize_time:
            min_time = self.compute_stats(df, time_colname, groupBy=[groupby], statistics=["minimum"],
                                          ignore_nan=True, out_as_dict=False)
            if isinstance(min_time, Exception):
                return min_time
            df = self.merge([df, min_time], on=groupby)
            if isinstance(df, Exception):
                return df
            df["delay from earliest date"] = df[time_colname] - df["minimum"]
            time_colname = "delay from earliest date"

        # plot(df, x=time_colname, y=value_colname, groupby=groupby)
        return df

    @utils.protector
    def plot(self, df, X, Y, Z, xlabel, ylabel, zlabel, xlim, ylim, zlim, groupby):
        fig = plt.figure()
        ax = fig.add_subplot(111)
        df = df.set_index(groupby[0])
        df = df.sort_values(by=X)
        for i, ind in enumerate(np.unique(df.index)):
            x, y = df.loc[ind, X], df.loc[ind, Y]
            if not isinstance(x, pd.Series):
                x, y = [x], [y]

            ax.plot([i.total_seconds() for i in x], y)

        def timeTicks(x, pos):
            d = datetime.timedelta(seconds=x)
            return str(d)
        formatter = matplotlib.ticker.FuncFormatter(timeTicks)
        ax.xaxis.set_major_formatter(formatter)
        fig.autofmt_xdate()

        return ax

    @utils.protector
    def merge(self, dfs, *args, **kwargs):
        outdf = copy.copy(dfs[0])
        for df in dfs[1:]:
            outdf = outdf.merge(df, *args, **kwargs)
        return outdf

    @utils.protector
    def reform(self, df, colname_as_index, colname_as_header, colname_as_values):
        indexes = np.unique(df[colname_as_index])
        headers = np.unique(df[colname_as_header])
        df = df.set_index([colname_as_index, colname_as_header])
        new_df = pd.DataFrame(index=indexes, columns=headers)
        for i, h in df.index:
            values = df.loc[(i, h), colname_as_values]

            try:
                v = np.unique(values.values)
            except Exception:
                v = [values]
            if len(v) == 1:
                v = v[0]
            else:
                v = str(list(v))
            new_df.loc[i, h] = v
        # new_df = new_df.fillna("")
        new_df = new_df.reset_index()
        return new_df

    @utils.protector
    def load_data(self, path, separator="\t", decimal=",", header=None, encoding="latin-1", clean=True, sort=False):
        df = pd.read_csv(path, sep=separator, decimal=decimal, encoding=encoding, index_col=None, header=header)
        if clean:
            df = self.clean_dataframe(df)
        df = df.convert_dtypes()
        if sort:
            df = df.sort_index()
        return df

    def clean_dataframe(self, df):
        df = df.dropna(axis=0, how="all")
        df = df.dropna(axis=1, how="all")
        df = df.drop_duplicates()
        return df

    @utils.protector
    def rearrange(self, df, value_colname, new_colname=None, new_indname=None, out_as_dict=False):
        if new_indname is not None:
            df = df.set_index(new_indname)

        d = {}
        for ind in np.unique(df.index):
            d[ind] = {}
            colnames, values = df.loc[ind, new_colname], df.loc[ind, value_colname]
            if isinstance(colnames, (pd.Series, pd.DataFrame)):
                colnames, values = colnames.values, values.values
            else:
                colnames, values = [colnames], [values]
            for colname, value in zip(colnames, values):
                if isinstance(colname, np.ndarray):
                    colname = tuple(colname)
                if colname not in d[ind].keys():
                    d[ind][colname] = value
                elif isinstance(d[ind][colname], list):
                    d[ind][colname].append(value)
                else:
                    d[ind][colname] = [d[ind][colname], value]
        if not out_as_dict:
            d = pd.DataFrame.from_dict(d).T
            d = d.reset_index()
        return d

    @utils.protector
    def standardize(self, df, type_dict, format_dict={}, unit_dict={}):
        types = {'': None, 'integer': np.int64, 'float': np.float64, 'boolean': bool,
                 'string': str, 'datetime': datetime, 'timedelta': timedelta}
        for colname in type_dict:
            t = type_dict[colname]
            if types[t]:
                if t == 'datetime':
                    if ' OR ' in format_dict[colname]:
                        df[colname] = utils.to_datetime(df[colname], formats=format_dict[colname].split(' OR '))
                    else:
                        df[colname] = pd.to_datetime(df[colname], format=format_dict[colname])
                elif t == 'timedelta':
                    df[colname] = pd.to_timedelta(df[colname], unit=unit_dict[colname])
                else:
                    df[colname] = df[colname].astype(types[t])
        return df

    @utils.protector
    def apply_formula(self, df, formula, formula_name):
        formula = formula.replace("[", "df['")
        formula = formula.replace("]", "']")
        formula = formula.replace(" x ", " * ")
        try:
            df[formula_name] = eval(formula)
        except SyntaxError:
            raise SyntaxError("incorrect formula")
        return df

    @utils.protector
    def compute_stats(self, df, column, groupBy=None,
                      statistics=["count", "minimum", "maximum", "mean", "sum", "median", "std"],
                      ignore_nan=True, out_as_dict=False):
        """
        compute stats (recursively) if 'by' argument is set
        """
        if groupBy is None:
            if column is None:
                arr = df
            else:
                arr = df[column]
            if isinstance(arr, float):
                arr = [arr]
            else:
                arr = arr.values

            # compute statistics for and array
            d = {}
            for stat in statistics:
                if stat == "minimum":
                    d[stat] = np.min(arr)
                elif stat == "maximum":
                    d[stat] = np.max(arr)
                elif stat == "mean":
                    d[stat] = np.mean(arr)
                elif stat == "std":
                    d[stat] = np.std(arr)
                elif stat == "sum":
                    d[stat] = np.sum(arr)
                elif stat == "median":
                    d[stat] = np.median(arr)
                elif stat == "count":
                    d[stat] = len(arr)

            if not out_as_dict:
                d = pd.DataFrame.from_dict({"total": d}).T
            return d
        else:
            # compute stats recursively for each 'by'
            d = {}
            df = df.set_index(groupBy)
            for ind in np.unique(df.index):
                out = self.compute_stats(df.loc[[ind]], column, statistics=statistics,
                                         ignore_nan=ignore_nan, out_as_dict=True)
                if isinstance(out, type):
                    return out
                d[ind] = out
            if not out_as_dict:
                d = pd.DataFrame.from_dict(d).T
            d = d.reset_index()
            return d

    def get_selections(self, data, equal_to=None, different_from=None, higher_than=None, lower_than=None):
        selections = []
        if equal_to is not None:
            if not isinstance(equal_to, list):
                equal_to = [equal_to]
            preselection = []
            for et in equal_to:
                preselection.append(list((data == et).values))
            selections.append(list(np.logical_or.reduce(np.array(preselection))))
        if different_from is not None:
            if not isinstance(different_from, list):
                different_from = [different_from]
            preselection = []
            for df in different_from:
                preselection.append(list((data != df).values))
            selections.append(list(np.logical_and.reduce(np.array(preselection))))
        if higher_than is not None:
            selections.append(list((data >= higher_than).values))
        if lower_than is not None:
            selections.append(list((data <= lower_than).values))
        selections = np.array(selections)

        return selections

    @utils.protector
    def select_rows(self, df, column, equal_to=None, different_from=None,
                    higher_than=None, lower_than=None, logical="or"):
        selections = self.get_selections(df[column], equal_to, different_from, higher_than, lower_than)
        if logical == "and":
            selection = np.logical_and.reduce(selections)
        elif logical == "or":
            selection = np.logical_or.reduce(selections)
        if isinstance(selection, np.ndarray):
            df = df.loc[selection]
        return df

    @utils.protector
    def select_columns(self, df, columns):
        return df[columns]

    @utils.protector
    def save_data(self, dfs, path):
        if not isinstance(dfs, list):
            dfs = [dfs]
        for i, df in enumerate(dfs):
            if i > 0:
                df.to_csv(path+"_{}".format(i), sep='\t', decimal=",", encoding="latin-1")
            else:
                df.to_csv(path, sep='\t', decimal=",", encoding="latin-1")

    @utils.protector
    def fit_closest_event(self, ref, ref_datetime_colname, ref_param_colname, data, datetime_colname, value_colname,
                          on, delta=['before', 'after'], groupby=None, column_prefix=""):
        left_on, right_on = on, on
        if groupby is not None:
            outdf = pd.DataFrame()
            data = data.set_index(groupby)
            params = np.unique(data.index)
            for param in params:
                out = self.fit_closest_event(ref, ref_datetime_colname, ref_param_colname, data.loc[param],
                                             datetime_colname, value_colname, on, delta, column_prefix=param)
                outdf = pd.concat([outdf, out], axis=1)
        else:
            outdf = {}

            data_names = np.unique(data[right_on])

            ref = ref.set_index(left_on)
            ref = ref[[ref_datetime_colname, ref_param_colname]]

            data = data.set_index([right_on, datetime_colname])
            data = data[value_colname]

            for name in np.unique(ref.index):
                if name not in data_names:
                    continue
                subref = ref.loc[[name]]
                subdata = data.loc[name]
                subdata = subdata[~subdata.index.duplicated(keep='first')].sort_index()

                for i in range(len(subref.index)):
                    refdate, refparam = subref.iloc[i]
                    d = {}
                    if 'before' in delta:
                        try:
                            ind_before = subdata.index.get_loc(refdate, method='ffill')
                            d["_".join([column_prefix, "value before"])] = subdata.iloc[ind_before]
                            d["_".join([column_prefix, "delay before"])] = refdate - subdata.index[ind_before]
                        except KeyError:
                            pass
                    if 'after' in delta:
                        try:
                            ind_after = subdata.index.get_loc(refdate, method='backfill')
                            d["_".join([column_prefix, "value after"])] = subdata.iloc[ind_after]
                            d["_".join([column_prefix, "delay after"])] = subdata.index[ind_after] - refdate
                        except KeyError:
                            pass
                    outdf[(name, refparam, refdate)] = d

            outdf = pd.DataFrame.from_dict(outdf, orient='index')

        return outdf
