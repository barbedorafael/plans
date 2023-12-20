"""
PLANS - Planning Nature-based Solutions

Module description:
This module stores all dataset objects of PLANS.

Copyright (C) 2022 Iporã Brito Possantti
"""
import os, glob
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
import warnings

warnings.filterwarnings("ignore")


# -----------------------------------------
# Utility functions
def dataframe_prepro(dataframe):
    """Utility function for dataframe pre-processing.

    :param dataframe: incoming dataframe
    :type dataframe: :class:`pandas.DataFrame`
    :return: prepared dataframe
    :rtype: :class:`pandas.DataFrame`
    """
    # fix headings
    dataframe.columns = dataframe.columns.str.strip()
    # strip string fields
    for i in range(len(dataframe.columns)):
        # if data type is string
        if str(dataframe.dtypes.iloc[i]) == "base_object":
            # strip all data
            dataframe[dataframe.columns[i]] = dataframe[
                dataframe.columns[i]
            ].str.strip()
    return dataframe


def get_random_colors(size=10, cmap="tab20"):
    """Utility function to get a list of random colors

    :param size: Size of list of colors
    :type size: int
    :param cmap: Name of matplotlib color map (cmap)
    :type cmap: str
    :return: list of random colors
    :rtype: list
    """
    import matplotlib.colors as mcolors

    # Choose a colormap from matplotlib
    _cmap = plt.get_cmap(cmap)
    # Generate a list of random numbers between 0 and 1
    _lst_rand_vals = np.random.rand(size)
    # Use the colormap to convert the random numbers to colors
    _lst_colors = [mcolors.to_hex(_cmap(x)) for x in _lst_rand_vals]
    return _lst_colors


# -----------------------------------------
# Series data structures


class Collection:
    """
    This is the primitive objects collection
    """

    def __init__(self, base_object, name="myCatalog"):
        dct_meta = base_object.get_metadata()
        self.catalog = pd.DataFrame(columns=dct_meta.keys())
        self.collection = dict()
        self.name = name

    def update(self, details=False):
        """Update the collection catalog

        :param details: option to update catalog details
        :type details: bool
        :return: None
        :rtype: none
        """
        # update details
        if details:
            # create new catalog
            df_new_catalog = pd.DataFrame(columns=self.catalog.columns)
            for name in self.collection:
                dct_meta = self.collection[name].get_metadata()
                lst_keys = dct_meta.keys()
                _dct = dict()
                for k in lst_keys:
                    _dct[k] = [dct_meta[k]]
                # set new information
                df_aux = pd.DataFrame(_dct)
                # append
                df_new_catalog = pd.concat([df_new_catalog, df_aux], ignore_index=True)

            self.catalog = df_new_catalog.copy()
            del df_new_catalog
        # basic updates
        self.catalog = self.catalog.drop_duplicates(subset="Name", keep="last")
        self.catalog = self.catalog.sort_values(by="Name").reset_index(drop=True)
        return None

    def append(self, new_object):
        """Append new object to collection. Object is expected to have a `.get_metadata()` method that returns a dict

        :param new_object: object to append
        :type new_object: object
        :return: None
        :rtype: None
        """
        # append to collection
        self.collection[new_object.name] = new_object
        # set
        dct_meta = new_object.get_metadata()
        dct_meta_df = dict()
        for k in dct_meta:
            dct_meta_df[k] = [dct_meta[k]]
        df_aux = pd.DataFrame(dct_meta_df)
        self.catalog = pd.concat([self.catalog, df_aux], ignore_index=True)
        self.update()
        return None

    def remove(self, name):
        """Remove base_object from collection.

        :param name: object name attribute to remove
        :type name: str
        """
        # delete raster base_object
        del self.collection[name]
        # delete from catalog
        self.catalog = self.catalog.drop(
            self.catalog[self.catalog["Name"] == name].index
        ).reset_index(drop=True)
        return None


class TimeSeries:
    """
    The primitive time series object

    """

    def __init__(self, name, varname, varfield, units):
        """Deploy time series object

        :param name: Name for the object
        :type name: str
        :param varname: variable name
        :type varname: str
        :param varfield: variable field alias
        :type varfield: str
        :param units: Units of the variable
        :type units: str
        """
        self.name = name
        self.varname = varname
        self.varfield = varfield
        self.units = units
        self.dtfield = "Datetime"
        self.data = None
        self.dtres = "minute"
        self.isstandard = False
        self.agg = "sum"
        self.epochs_stats = None
        self.gapsize = 3
        self._set_view_specs()

    def _set_view_specs(self):
        self.view_specs = {
            "title": "{} | {} ({})".format(self.name, self.varname, self.varfield),
            "width": 5 * 1.618,
            "height": 3,
            "xlabel": "Date",
            "ylabel": self.units,
            "vmin": 0,
            "vmax": None,
        }
        return None

    def load_data(
        self,
        input_file,
        input_varfield,
        input_dtres,
        input_dtfield="Datetime",
        sep=";",
    ):
        """Load data from file

        :param input_file: path to `csv` input file
        :type input_file: str
        :param input_varfield: name of incoming varfield
        :type input_varfield: str
        :param input_dtres: datetime resolution. Options: second, minute, hour, day, month and year
        :type input_dtres: str
        :param input_dtfield: name of incoming datetime field
        :type input_dtfield: str
        :param sep: string separator. Default: `;`
        :type sep: str
        :return: None
        :rtype: None
        """
        # load from csv
        df = pd.read_csv(input_file, sep=sep, usecols=[input_dtfield, input_varfield])

        # set data
        self.set_data(
            input_df=df,
            input_varfield=input_varfield,
            input_dtfield=input_dtfield,
            input_dtres=input_dtres,
        )
        # clear
        del df
        return None

    def set_data(self, input_df, input_dtfield, input_varfield, input_dtres="minute"):
        """Set the data from the incoming pandas DataFrame.

        :param input_df: :class:`pandas.DataFrame`
            Incoming DataFrame.
        :param input_dtfield: str
            Name of the incoming datetime field.
        :param input_varfield: str
            Name of the incoming variable field.
        :param input_dtres: str
            Datetime resolution. Options: second, minute, hour, day, month, and year.
        :return: None
        :rtype: None

        **Notes:**

        This function sets the time series data from an incoming DataFrame, applying a specified datetime resolution.

        **Examples:**

        >>> ts.set_data(df, "timestamp", "temperature", "hour")
        """
        # resolution dict
        s_std_time = "2020-01-01 12:00:00"
        dict_res = {
            "second": "",
            "minute": s_std_time[-3:],  # add seconds
            "hour": s_std_time[-6:],  # add minutes
            "day": s_std_time[-9:],  # add standard hour
            "month": s_std_time[-12:],  # add day
            "year": s_std_time[-16:],  # add month
        }
        # get copy
        df = input_df.copy()

        # drop nan values
        df = df.dropna()

        # rename columns to standard format
        df = df.rename(
            columns={input_dtfield: self.dtfield, input_varfield: self.varfield}
        )

        # datetime standard format
        df[self.dtfield] = pd.to_datetime(
            df[self.dtfield] + dict_res[input_dtres], format="%Y-%m-%d %H:%M:%S"
        )

        # set to attribute
        self.data = df.copy()
        self.dtres = input_dtres

        return None

    def standardize(self):
        """Standardize the data based on regular datetime steps and the time resolution.

        :return: None
        :rtype: None

        **Notes:**

        This function standardizes the time series data based on regular datetime steps and the specified time resolution.

        **Examples:**

        >>> ts.standardize()
        """
        dict_freq = {
            "second": ["20min", 15],
            "minute": ["20min", 15],
            "hour": ["H", 13],
            "day": ["D", 10],
            "month": ["MS", 7],
            "year": ["YS", 4],
        }
        # get a date range for all period
        dt_index = pd.date_range(
            start=self.data[self.dtfield].dt.date.values[0],
            end=self.data[self.dtfield].dt.date.values[-1],
            freq=dict_freq[self.dtres][0],
        )
        # set dataframe
        df = pd.DataFrame({self.dtfield: dt_index, "StEpoch": "-"})
        # insert Epochs
        df["StEpoch"] = df[self.dtfield].astype(str)
        df["StEpoch"] = df["StEpoch"].str.slice(0, dict_freq[self.dtres][1])

        # insert Epochs
        df2 = self.data.copy()
        df2["StEpoch"] = df2[self.dtfield].astype(str)
        df2["StEpoch"] = df2["StEpoch"].str.slice(0, dict_freq[self.dtres][1])

        # Group by 'Epochs' and calculate agg function
        result_df = df2.groupby("StEpoch")[self.varfield].agg([self.agg]).reset_index()
        # rename
        result_df = result_df.rename(columns={self.agg: self.varfield})

        # merge
        df = pd.merge(
            left=df, right=result_df, left_on="StEpoch", right_on="StEpoch", how="left"
        )
        # clear
        self.data = df.drop(columns="StEpoch").copy()

        # cut off edges
        self.cut_edges(inplace=True)

        self.isstandard = True
        return None

    def get_epochs(self, inplace=False):
        """Get Epochs (periods) for continuous time series (0 = gap epoch).

        :param inplace: bool, optional
            Option to set Epochs inplace. Default is False.
        :type inplace: bool
        :return: :class:`pandas.DataFrame` or None
            A DataFrame if inplace is False or None.
        :rtype: :class:`pandas.DataFrame`, None

        **Notes:**

        This function labels continuous chunks of data as Epochs, with Epoch 0 representing gaps in the time series.

        **Examples:**

        >>> df_epochs = ts.get_epochs()
        """
        df = self.data.copy()
        # Create a helper column to label continuous chunks of data
        df["CumSum"] = (
            df[self.varfield]
            .isna()
            .astype(int)
            .groupby(df[self.varfield].notna().cumsum())
            .cumsum()
        )

        # get skip hint
        skip_v = np.zeros(len(df))
        for i in range(len(df) - 1):
            n_curr = df["CumSum"].values[i]
            n_next = df["CumSum"].values[i + 1]
            if n_next < n_curr:
                if n_curr >= self.gapsize:
                    n_start = i - n_curr
                    if i <= n_curr:
                        n_start = 0
                    skip_v[n_start + 1 : i + 1] = 1
        df["Skip"] = skip_v

        # Set Epoch Field
        df["Epoch_Id"] = 0
        # counter epochs
        counter = 1
        for i in range(len(df) - 1):
            if df["Skip"].values[i] == 0:
                df["Epoch_Id"].values[i] = counter
            else:
                if df["Skip"].values[i + 1] == 0:
                    counter = counter + 1
        if df["Skip"].values[i + 1] == 0:
            df["Epoch_Id"].values[i] = counter

        df = df.drop(columns=["CumSum", "Skip"])

        if inplace:
            self.data = df.copy()
            del df
            return None
        else:
            return df

    def update_epochs_stats(self):
        """Update all epochs statistics.

        :return: None
        :rtype: None

        **Notes:**

        This function updates statistics for all epochs in the time series.

        **Examples:**

        >>> ts.update_epochs_stats()
        """
        # get epochs
        if self.isstandard:
            pass
        else:
            self.standardize()
        df = self.get_epochs(inplace=False)
        # remove epoch = 0
        df.drop(df[df["Epoch_Id"] == 0].index, inplace=True)
        df = df.rename(columns={"Epoch_Id": "Id"})
        # group by
        self.epochs_stats = (
            df.groupby("Id")
            .agg(
                Count=("Id", "count"),
                Start=(self.dtfield, "min"),
                End=(self.dtfield, "max"),
            )
            .reset_index()
        )
        # get colors
        self.epochs_stats["Color"] = get_random_colors(size=len(self.epochs_stats))
        return None

    def fill_gaps(self, method="linear", inplace=False):
        """Fill gaps in a time series by interpolating missing values. If the time series is not in standard form, it will be standardized before interpolation.

        :param method: str, optional
            Specifies the interpolation method. Default is "linear".
        :type method: str

        :param inplace: bool, optional
            If True, the interpolation will be performed in-place, and the original data will be modified.
            If False, a new DataFrame with interpolated values will be returned, and the original data will remain unchanged.
            Default is False.
        :type inplace: bool

        :return: :class:`pandas.DataFrame` or None
            If inplace is False, a new DataFrame with interpolated values.
            If inplace is True, returns None, and the original data is modified in-place.
        :rtype: :class:`pandas.DataFrame` or None

        **Notes:**

        The interpolation is performed for each unique epoch in the time series.
        The method supports linear interpolation and other interpolation methods provided by scipy.interpolate.interp1d.

        **Examples:**

        >>> ts.fill_gaps(method="linear", inplace=True)

        >>> interpolated_ts = ts.fill_gaps(method="linear", inplace=False)
        """
        from scipy.interpolate import interp1d

        if self.isstandard:
            pass
        else:
            self.standardize()
        # get epochs for interpolation
        df = self.get_epochs(inplace=False)
        epochs = df["Epoch_Id"].unique()
        list_dfs = list()
        for epoch in epochs:
            df_aux1 = df.query("Epoch_Id == {}".format(epoch)).copy()
            if epoch == 0:
                df_aux1["{}_interp".format(self.varfield)] = np.nan
            else:
                df_aux2 = df_aux1.dropna().copy()
                # Create an interpolation function without the datetimes
                interpolation_func = interp1d(
                    df_aux2[self.dtfield].astype(np.int64).values,
                    df_aux2[self.varfield].values,
                    kind=method,
                    fill_value="extrapolate",
                )
                # interpolate full values
                df_aux1["{}_interp".format(self.varfield)] = interpolation_func(
                    df_aux1[self.dtfield].astype(np.int64)
                )
            # append
            list_dfs.append(df_aux1)
        df_new = pd.concat(list_dfs, ignore_index=True)
        df_new = df_new.sort_values(by=self.dtfield).reset_index(drop=True)

        if inplace:
            self.data[self.varfield] = df_new["{}_interp".format(self.varfield)].values
            return None
        else:
            return df_new

    def cut_edges(self, inplace=False):
        """Cut off initial and final NaN records in a given time series.

        :param inplace: bool, optional
            If True, the operation will be performed in-place, and the original data will be modified.
            If False, a new DataFrame with cut edges will be returned, and the original data will remain unchanged.
            Default is False.
        :type inplace: bool

        :return: :class:`pandas.DataFrame` or None
            If inplace is False, a new DataFrame with cut edges.
            If inplace is True, returns None, and the original data is modified in-place.
        :rtype: :class:`pandas.DataFrame` or None

        **Notes:**

        This function removes leading and trailing rows with NaN values in the specified variable field.
        The operation is performed on a copy of the original data, and the original data remains unchanged.

        **Examples:**

        >>> ts.cut_edges(inplace=True)

        >>> trimmed_ts = ts.cut_edges(inplace=False)
        """
        # get dataframe
        in_df = self.data.copy()
        def_len = len(in_df)
        # drop first nan lines
        drop_ids = list()
        # loop to collect indexes in the start of series
        for def_i in range(def_len):
            aux = in_df[self.varfield].isnull().iloc[def_i]
            if aux:
                drop_ids.append(def_i)
            else:
                break
        # loop to collect indexes in the end of series
        for def_i in range(def_len - 1, -1, -1):
            aux = in_df[self.varfield].isnull().iloc[def_i]
            if aux:
                drop_ids.append(def_i)
            else:
                break
        # loop to drop rows:
        for def_i in range(len(drop_ids)):
            in_df.drop(drop_ids[def_i], inplace=True)
        # output
        if inplace:
            self.data = in_df.copy()
            del in_df
            return None
        else:
            return in_df

    def aggregate(self, freq, agg_funcs=None, bad_max=7):
        """Aggregate the time series data based on a specified frequency using various aggregation functions.

        :param freq: str
            Pandas-like alias frequency at which to aggregate the time series data, e.g., 'D' for daily, 'M' for monthly.
        :type freq: str

        :param agg_funcs: dict, optional
            A dictionary specifying customized aggregation functions for each variable.
            Default is None, which uses standard aggregation functions (sum, mean, median, min, max, std, var, percentiles).
        :type agg_funcs: dict

        :param bad_max: int, optional
            The maximum number of 'Bad' records allowed in a time window for aggregation. Records with more 'Bad' entries
            will be excluded from the aggregated result.
            Default is 7.
        :type bad_max: int

        :return: pandas.DataFrame
            A new DataFrame with aggregated values based on the specified frequency.
        :rtype: pandas.DataFrame

        **Notes:**

        This function resamples the time series data to the specified frequency and aggregates the values using the
        specified aggregation functions. It also counts the number of 'Bad' records in each time window and excludes
        time windows with more 'Bad' entries than the specified threshold.

        **Examples:**

        >>> agg_result = ts.aggregate(freq='D', agg_funcs={'sum': 'sum', 'mean': 'mean'}, bad_max=5)
        """

        def custom_percentile(series, percentile):
            return np.percentile(series, percentile)

        if agg_funcs is None:
            # Create a dictionary of standard and custom aggregation functions
            agg_funcs = {
                "sum": "sum",
                "mean": "mean",
                "median": "median",
                "min": "min",
                "max": "max",
                "std": "std",
                "var": "var",
            }
            # Add custom percentiles to the dictionary
            percentiles_to_compute = [1, 5, 10, 25, 50, 75, 90, 95, 99]
            for p in percentiles_to_compute:
                agg_funcs[f"p{p}"] = lambda x, p=p: np.percentile(x, p)

        # set list of tuples
        agg_funcs_list = [
            ("{}_{}".format(self.varfield, f), agg_funcs[f]) for f in agg_funcs
        ]

        # get data
        df = self.data.copy()
        df["Bad"] = df[self.varfield].isna().astype(int)
        # Set the 'datetime' column as the index
        df.set_index(self.dtfield, inplace=True)

        # Resample the time series to a frequency using aggregation functions
        agg_df1 = df.resample(freq)[self.varfield].agg(agg_funcs_list)
        agg_df2 = df.resample(freq)["Bad"].agg([("Bad_count", "sum")])

        # Reset the index to get 'Datetime' as a regular column
        agg_df1.reset_index(inplace=True)
        agg_df2.reset_index(inplace=True)

        # merge with bad dates
        agg_df = pd.merge(left=agg_df1, right=agg_df2, how="left", on=self.dtfield)

        # set new df
        agg_df_new = pd.DataFrame(
            {
                self.dtfield: pd.date_range(
                    start=agg_df[self.dtfield].values[0],
                    end=agg_df[self.dtfield].values[-1],
                    freq=freq,
                )
            }
        )
        # remove bad records
        agg_df.drop(agg_df[agg_df["Bad_count"] > bad_max].index, inplace=True)
        # remove bad column
        agg_df.drop(columns=["Bad_count"], inplace=True)

        # left join
        agg_df_new = pd.merge(
            left=agg_df_new, right=agg_df, on=self.dtfield, how="left"
        )

        return agg_df_new

    def view(
        self, show=True, folder="./output", filename=None, dpi=300, fig_format="jpg"
    ):
        """Visualize the time series data using a scatter plot with colored epochs.

        :param show: bool, optional
            If True, the plot will be displayed interactively.
            If False, the plot will be saved to a file.
            Default is True.
        :type show: bool

        :param folder: str, optional
            The folder where the plot file will be saved. Used only if show is False.
            Default is "./output".
        :type folder: str

        :param filename: str, optional
            The base name of the plot file. Used only if show is False. If None, a default filename is generated.
            Default is None.
        :type filename: str or None

        :param dpi: int, optional
            The dots per inch (resolution) of the plot file. Used only if show is False.
            Default is 300.
        :type dpi: int

        :param fig_format: str, optional
            The format of the plot file. Used only if show is False.
            Default is "jpg".
        :type fig_format: str

        :return: None
            If show is True, the plot is displayed interactively.
            If show is False, the plot is saved to a file.
        :rtype: None

        **Notes:**

        This function generates a scatter plot with colored epochs based on the epochs' start and end times.
        The plot includes data points within each epoch, and each epoch is labeled with its corresponding ID.

        **Examples:**

        >>> ts.view(show=True)

        >>> ts.view(show=False, folder="./output", filename="time_series_plot", dpi=300, fig_format="png")
        """
        specs = self.view_specs
        # Deploy figure
        fig = plt.figure(figsize=(specs["width"], specs["height"]))  # Width, Height

        self.update_epochs_stats()
        for i in range(len(self.epochs_stats)):
            start = self.epochs_stats["Start"].values[i]
            end = self.epochs_stats["End"].values[i]
            df_aux = self.data.query(
                "{} >= '{}' and {} < '{}'".format(
                    self.dtfield, start, self.dtfield, end
                )
            )
            epoch_c = self.epochs_stats["Color"].values[i]
            epoch_id = self.epochs_stats["Id"].values[i]
            plt.plot(
                df_aux[self.dtfield],
                df_aux[self.varfield],
                ".",
                color=epoch_c,
                label=f"Epoch_{epoch_id}",
            )
        plt.legend(frameon=True, ncol=2)
        plt.title(specs["title"])
        plt.ylabel(specs["ylabel"])
        plt.xlabel(specs["xlabel"])
        plt.xlim(self.data[self.dtfield].min(), self.data[self.dtfield].max())
        plt.ylim(0, 1.2 * self.data[self.varfield].max())

        # Adjust layout to prevent cutoff
        plt.tight_layout()

        # show or save
        if show:
            plt.show()
        else:
            if filename is None:
                filename = "{}_{}{}".format(self.varalias, self.name, suff)
            plt.savefig(
                "{}/{}{}.{}".format(folder, filename, suff, fig_format), dpi=dpi
            )
            plt.close(fig)
        return None


class DailySeries:
    """
    The basic daily time series base_object

    """

    def __init__(
        self,
        name,
        varname,
    ):
        """Deploy daily series base dataset

        :param name: name of series
        :type name: str
        :param varname: name of variable
        :type varname: str
        """
        # -------------------------------------
        # set basic attributes
        self.data = None  # start with no data
        self.name = name
        self.varname = varname
        self.datefield = "Date"
        self.file = None

    def set_data(self, dataframe, varfield, datefield="Date"):
        """Set the data from incoming class:`pandas.DataFrame`.

        :param dataframe: incoming :class:`pandas.DataFrame` base_object
        :type dataframe: :class:`pandas.DataFrame`
        :param varfield: name of variable field in the incoming :class:`pandas.DataFrame`
        :type varfield: str
        :param datefield: name of date field in the incoming :class:`pandas.DataFrame`
        :type datefield: str
        """
        # slice only interest fields
        df_aux = dataframe[[datefield, varfield]].copy()
        self.data = df_aux.rename(
            columns={datefield: self.datefield, varfield: self.varname}
        )
        # ensure datetime fig_format
        self.data[self.datefield] = pd.to_datetime(self.data[self.datefield])
        self.data = self.data.sort_values(by=self.datefield).reset_index(drop=True)

    def load_data(self, file, varfield, datefield="Date"):
        """Load data from ``csv`` file.

        :param file: path_main to ``csv`` file
        :type file:
        :param varfield:
        :type varfield:
        :param datefield:
        :type datefield:
        :return:
        :rtype:
        """

        self.file = file
        # -------------------------------------
        # import data
        df_aux = pd.read_csv(self.file, sep=";", parse_dates=[self.datefield])
        # set data
        self.set_data(dataframe=df_aux, varfield=varfield, datefield=datefield)

    def export_data(self, folder):
        """Export dataset to ``csv`` file

        :param folder: path_main to output directory
        :type folder: str
        :return: file path_main
        :rtype: str
        """
        s_filepath = "{}/{}_{}.txt".format(folder, self.varname, self.name)
        self.data.to_csv(s_filepath, sep=";", index=False)
        return s_filepath

    def resample_sum(self, period="MS"):
        """Resampler method for daily time series using the .sum() function

        :param period: pandas standard period code

        * `W-MON` -- weekly starting on mondays
        * `MS` --  monthly on start of month
        * `QS` -- quarterly on start of quarter
        * `YS` -- yearly on start of year

        :type period: str
        :return: resampled time series
        :rtype: :class:`pandas.DataFrame`
        """
        df_aux = self.data.set_index(self.datefield)
        df_aux = df_aux.resample(period).sum()[self.varname]
        df_aux = df_aux.reset_index()
        return df_aux

    def resample_mean(self, period="MS"):
        """Resampler method for daily time series using the .mean() function

        :param period: pandas standard period code

        * `W-MON` -- weekly starting on mondays
        * `MS` --  monthly on start of month
        * `QS` -- quarterly on start of quarter
        * `YS` -- yearly on start of year

        :type period: str
        :return: resampled time series
        :rtype: :class:`pandas.DataFrame`
        """
        df_aux = self.data.set_index(self.datefield)
        df_aux = df_aux.resample(period).mean()[self.varname]
        df_aux = df_aux.reset_index()
        return df_aux

    def view(
        self,
        show=True,
        folder="C:/data",
        filename=None,
        specs=None,
        dpi=150,
        fig_format="jpg",
    ):
        """Plot series basic view

        :type show: option to display plot. Default False
        :type show: bool
        :param folder: output folder
        :type folder: str
        :param filename: image file name
        :type filename: str
        :param specs: specification dictionary
        :type specs: dict
        :param dpi: image resolution (default = 96)
        :type dpi: int
        :param fig_format: image fig_format (ex: png or jpg). Default jpg
        :type fig_format: str
        """
        import matplotlib.ticker as mtick
        from plans.analyst import Univar

        # get univar base_object
        uni = Univar(data=self.data[self.varname].values)

        # get specs
        default_specs = {
            "color": "tab:grey",
            "suptitle": "Series Overview",
            "a_title": "Series",
            "b_title": "Histogram",
            "c_title": "CFC",
            "width": 5 * 1.618,
            "height": 5,
            "ylabel": "units",
            "ylim": (np.min(uni.data), np.max(uni.data)),
            "a_xlabel": "Date",
            "b_xlabel": "Frequency",
            "c_xlabel": "Probability",
            "a_data_label": "Data Series",
            "skip mavg": False,
            "a_mavg_label": "Moving Average",
            "mavg period": 10,
            "mavg color": "tab:blue",
            "nbins": uni.nbins_fd(),
            "series marker": "o",
            "series linestyle": "-",
            "series alpha": 1.0,
        }
        # handle input specs
        if specs is None:
            pass
        else:  # override default
            for k in specs:
                default_specs[k] = specs[k]
        specs = default_specs

        # Deploy figure
        fig = plt.figure(figsize=(specs["width"], specs["height"]))  # Width, Height
        gs = mpl.gridspec.GridSpec(
            4, 5, wspace=0.5, hspace=0.9, left=0.075, bottom=0.1, top=0.9, right=0.95
        )
        fig.suptitle(specs["suptitle"])

        # plot Series
        plt.subplot(gs[0:3, :3])
        plt.title("a. {}".format(specs["a_title"]), loc="left")
        plt.plot(
            self.data[self.datefield],
            self.data[self.varname],
            linestyle=specs["series linestyle"],
            marker=specs["series marker"],
            label="Data Series",
            color=specs["color"],
            alpha=specs["series alpha"],
        )
        if specs["skip mavg"]:
            pass
        else:
            plt.plot(
                self.data[self.datefield],
                self.data[self.varname]
                .rolling(specs["mavg period"], min_periods=2)
                .mean(),
                label=specs["a_mavg_label"],
                color=specs["mavg color"],
            )
        plt.ylim(specs["ylim"])
        plt.xlim(self.data[self.datefield].min(), self.data[self.datefield].max())
        plt.ylabel(specs["ylabel"])
        plt.xlabel(specs["a_xlabel"])
        plt.legend(frameon=True, loc=(0.0, -0.35), ncol=1)

        # plot Hist
        plt.subplot(gs[0:3, 3:4])
        plt.title("b. {}".format(specs["b_title"]), loc="left")
        plt.hist(
            x=self.data[self.varname],
            bins=specs["nbins"],
            orientation="horizontal",
            color=specs["color"],
            weights=np.ones(len(self.data)) / len(self.data),
        )
        plt.ylim(specs["ylim"])
        # plt.ylabel(specs["ylabel"])
        plt.xlabel(specs["b_xlabel"])

        # Set the x-axis formatter as percentages
        xticks = mtick.PercentFormatter(xmax=1, decimals=1, symbol="%", is_latex=False)
        ax = plt.gca()
        ax.xaxis.set_major_formatter(xticks)

        # plot CFC
        df_freq = uni.assess_frequency()
        plt.subplot(gs[0:3, 4:5])
        plt.title("c. {}".format(specs["c_title"]), loc="left")
        plt.plot(df_freq["Exceedance"] / 100, df_freq["Values"])
        plt.ylim(specs["ylim"])
        # plt.ylabel(specs["ylabel"])
        plt.xlabel(specs["c_xlabel"])
        plt.xlim(0, 1)
        # Set the x-axis formatter as percentages
        xticks = mtick.PercentFormatter(xmax=1, decimals=0, symbol="%", is_latex=False)
        ax = plt.gca()
        ax.xaxis.set_major_formatter(xticks)

        # show or save
        if show:
            plt.show()
        else:
            if filename is None:
                filename = self.name
            plt.savefig("{}/{}.{}".format(folder, filename, fig_format), dpi=dpi)
            plt.close(fig)
        return None


class PrecipSeries(DailySeries):
    """The precipitation daily time series base_object

    Example of using this base_object:

    """

    def __init__(self, name, file, varfield, datefield, location):
        # ---------------------------------------------------
        # use superior initialization
        super().__init__(name, file, "P", varfield, datefield, location)
        # override varfield
        self.data = self.data.rename(columns={varfield: "P"})


class RatingCurve:
    """
    This is the Rating Curve base_object
    """

    def __init__(self, name="MyRatingCurve"):
        """Initiate Rating Curve

        :param name: name of rating curve
        :type name: str
        """
        self.name = name
        self.date_start = None
        self.date_end = None
        self.n = None
        self.hmax = None
        self.hmin = None
        self.field_hobs = "Hobs"
        self.field_qobs = "Qobs"
        self.field_h = "H"
        self.field_q = "Q"
        self.name_h0 = "h0"
        self.name_a = "a"
        self.name_b = "b"
        self.field_ht = "Hobs - h0"
        self.field_htt = "ln(Hobs - h0)"
        self.field_qt = "ln(Qobs)"
        self.field_date = "Date"
        self.units_h = "m"
        self.units_q = "m3/s"
        self.source_data = None
        self.description = None

        # data attribute
        self.data = None
        self.a = 1
        self.b = 1
        self.h0 = 0
        self.rmse = None
        self.e_mean = None
        self.e_sd = None
        self.et_mean = None
        self.et_sd = None

    def __str__(self):
        dct_meta = self.get_metadata()
        lst_ = list()
        lst_.append("\n")
        lst_.append("Object: {}".format(type(self)))
        lst_.append("Metadata:")
        for k in dct_meta:
            lst_.append("\t{}: {}".format(k, dct_meta[k]))
        return "\n".join(lst_)

    def run(self, h):
        """Run the model Q = a * (H - h0)^b

        :param h: vector of H
        :type h: :class:`numpy.ndarray` or float
        :return: computed Q
        :rtype: :class:`numpy.ndarray` or float
        """
        return self.a * (np.power((h - self.h0), self.b))

    def extrapolate(self, hmin=None, hmax=None, n_samples=100):
        """Extrapolate Rating Curve model. Data is expected to be loaded.

        :param hmin: lower bound
        :type hmin: float
        :param hmax: upper bound
        :type hmax: float
        :param n_samples: number of evenly spaced samples between bounds
        :type n_samples: int
        :return: dataframe of extrapolated data
        :rtype: :class:`pandas.DataFrame`
        """
        # handle bounds
        if hmin is None:
            if self.hmin is None:
                hmin = 0
            else:
                hmin = self.hmin
        if hmax is None:
            if self.hmax is None:
                hmax = 100
            else:
                hmax = self.hmax
        # set h vector
        vct_h = np.linspace(hmin, hmax, n_samples)
        # run
        vct_q = self.run(h=vct_h)
        return pd.DataFrame({self.field_h: vct_h, self.field_q: vct_q})

    def update(self, h0=None, a=None, b=None):
        """Update rating curve model

        :param h0: h0 parameter
        :type h0: float or None
        :param a: a parameter
        :type a: float or None
        :param b: b parameter
        :type b: float or None
        :return: None
        :rtype: None
        """

        # set up parameters
        if h0 is not None:
            self.h0 = h0
        if a is not None:
            self.a = a
        if b is not None:
            self.b = b
        # data model setup
        if self.data is None:
            pass
        else:
            from plans.analyst import Bivar

            # sort values by H
            self.data = self.data.sort_values(by=self.field_hobs).reset_index(drop=True)

            # get model values (reverse transform)
            self.data[self.field_qobs + "_Mean"] = self.run(
                h=self.data[self.field_hobs].values
            )
            # compute the model error
            self.data["e"] = (
                self.data[self.field_qobs] - self.data[self.field_qobs + "_Mean"]
            )

            # get first transform on H
            self.data[self.field_ht] = self.data[self.field_hobs] - self.h0
            # get second transform on H
            self.data[self.field_htt] = np.log(self.data[self.field_ht])
            # get transform on Q
            self.data[self.field_qt] = np.log(self.data[self.field_qobs])

            # get transformed Linear params
            c0t = np.log(self.a)
            c1t = self.b

            # now compute the tranformed model
            s_qt_model = self.field_qt + "_Mean"
            self.data[s_qt_model] = c0t + (c1t * self.data[self.field_htt])
            # compute the transformed error
            self.data["eT"] = self.data[self.field_qt] - self.data[s_qt_model]

            # update attributes
            self.rmse = np.sqrt(np.mean(np.square(self.data["e"])))
            self.e_mean = np.mean(self.data["e"])
            self.e_sd = np.std(self.data["e"])
            # get transformed attributes
            self.et_mean = np.mean(self.data["eT"])
            self.et_sd = np.std(self.data["eT"])

        return None

    def get_metadata(self):
        """Get all metadata from base_object

        :return: metadata
        :rtype: dict
        """
        return {
            "Name": self.name,
            "Date_Start": self.date_start,
            "Date_End": self.date_end,
            "N": self.n,
            "h0": self.h0,
            "a": self.a,
            "b": self.b,
            "RMSE": self.rmse,
            "Error_Mean": self.e_mean,
            "Error_SD": self.e_sd,
            "ErrorT_Mean": self.et_mean,
            "ErrorT_SD": self.et_sd,
            "H_max": self.hmax,
            "H_min": self.hmin,
            "H_units": self.units_h,
            "Q_units": self.units_q,
            "Source": self.source_data,
            "Description": self.description,
        }

    def load(
        self,
        table_file,
        hobs_field,
        qobs_field,
        date_field="Date",
        units_q="m3/s",
        units_h="m",
    ):
        """Load data from CSV file

        :param table_file: path_main to CSV file
        :type table_file: str
        :param hobs_field: name of observed Stage field
        :type hobs_field: str
        :param qobs_field: name of observed Discharge field
        :type qobs_field: str
        :param date_field: name of Date field
        :type date_field: str
        :param units_q: units of streamflow
        :type units_q: str
        :param units_h: units of stage
        :type units_h: str
        :return: None
        :rtype: None
        """
        _df = pd.read_csv(table_file, sep=";", parse_dates=[date_field])
        _df = dataframe_prepro(dataframe=_df)
        # select fields
        _df = _df[[date_field, hobs_field, qobs_field]].copy()
        # rename columns
        dct_rename = {
            date_field: self.field_date,
            hobs_field: self.field_hobs,
            qobs_field: self.field_qobs,
        }
        _df = _df.rename(columns=dct_rename)
        # set data
        self.data = _df.sort_values(by=self.field_date).reset_index(drop=True)
        # set attributes
        self.n = len(self.data)
        self.units_h = units_h
        self.units_q = units_q
        self.hmax = self.data[self.field_hobs].max()
        self.hmin = self.data[self.field_hobs].min()
        self.date_start = self.data[self.field_date].min()
        self.date_end = self.data[self.field_date].max()
        return None

    def fit(self, n_grid=20):
        """Fit Rating Curve method. Q = a * (H - h0)^b

        :param n_grid: number of intervals for h0 iteration
        :type n_grid: int
        :return: None
        :rtype: None
        """
        from plans.analyst import Bivar

        # estimate h0
        _h0_max = self.data[self.field_hobs].min()
        # get range of h0
        _h0_values = np.linspace(0, 0.99 * _h0_max, n_grid)
        # set fit dataframe
        _df_fits = pd.DataFrame(
            {
                "h0": _h0_values,
                "b": np.zeros(n_grid),
                "a": np.zeros(n_grid),
                "RMSE": np.zeros(n_grid),
            }
        )
        _df_fits.insert(0, "Model", "")
        # search loop
        for i in range(len(_df_fits)):
            # get h0
            n_h0 = _df_fits["h0"].values[i]
            # get transformed variables
            self.update(h0=n_h0)

            # set Bivar base_object for tranformed linear model
            biv = Bivar(df_data=self.data, x_name=self.field_htt, y_name=self.field_qt)
            # fit linear model
            biv.fit(model_type="Linear")
            ###biv.view()
            # retrieve re-transformed values
            _df_fits["a"].values[i] = np.exp(
                biv.models["Linear"]["Setup"]["Mean"].values[0]
            )
            _df_fits["b"].values[i] = biv.models["Linear"]["Setup"]["Mean"].values[1]
            _df_fits["RMSE"].values[i] = biv.models["Linear"]["RMSE"]

        # sort by metric
        _df_fits = _df_fits.sort_values(by="RMSE").reset_index(drop=True)

        self.h0 = _df_fits["h0"].values[0]
        self.a = _df_fits["a"].values[0]
        self.b = _df_fits["b"].values[0]
        self.update()
        return None

    def get_bands(self, extrap_f=2, n_samples=100, runsize=100, seed=None, talk=False):
        """Get uncertainty bands from Rating Curve model using Monte Carlo sampling on the transformed error

        :param extrap_f: extrapolation factor over upper bound
        :type extrap_f: float
        :param n_samples: number of extrapolation samples
        :type n_samples: int
        :param runsize: number of monte carlo simulations
        :type runsize: int
        :param seed: reproducibility seed
        :type seed: int or None
        :param talk: option for printing messages
        :type talk: bool
        :return: dictionary with output dataframes
        :rtype: dict
        """
        from plans.analyst import Univar

        # random state setup
        if seed is None:
            from datetime import datetime

            np.random.seed(int(datetime.now().timestamp()))
        else:
            np.random.seed(seed)

        # ensure model is up-to-date
        self.update()

        # resample error

        # get the transform error datasets:
        grd_et = np.random.normal(
            loc=0, scale=self.et_sd, size=(runsize, len(self.data))
        )
        # re-calc qobs_t for all error realizations
        grd_qt = grd_et + np.array([self.data["{}_Mean".format(self.field_qt)].values])
        # re-calc qobs
        grd_qobs = np.exp(grd_qt)

        # setup of montecarlo dataframe
        mc_models_df = pd.DataFrame(
            {
                "Id": [
                    "MC{}".format(str(i + 1).zfill(int(np.log10(runsize)) + 1))
                    for i in range(runsize)
                ],
                self.name_h0: np.zeros(runsize),
                self.name_a: np.zeros(runsize),
                self.name_b: np.zeros(runsize),
            }
        )
        # set up simulation data
        grd_qsim = np.zeros(shape=(runsize, n_samples))

        # for each error realization, fit model and extrapolate
        if talk:
            print("Processing models...")
        for i in range(runsize):
            # set new qobs
            self.data[self.field_qobs] = grd_qobs[i]
            # update
            self.update()
            # fit
            self.fit(n_grid=10)
            # extrapolate
            hmax = self.hmax * extrap_f
            _df_ex = self.extrapolate(hmin=0, hmax=hmax, n_samples=n_samples)
            # store results
            grd_qsim[i] = _df_ex[self.field_q].values
            mc_models_df[self.name_h0].values[i] = self.h0
            mc_models_df[self.name_a].values[i] = self.a
            mc_models_df[self.name_b].values[i] = self.b

        # extract h values
        vct_h = _df_ex[self.field_h].values
        # transpose data
        grd_qsim_t = np.transpose(grd_qsim)

        # set simulation dataframe
        mc_sim_df = pd.DataFrame(
            data=grd_qsim_t,
            columns=[
                "Q_{}".format(mc_models_df["Id"].values[i]) for i in range(runsize)
            ],
        )
        mc_sim_df.insert(0, value=vct_h, column=self.field_h)
        mc_sim_df = mc_sim_df.dropna(how="any").reset_index(drop=True)

        # clear up memory
        del grd_qsim
        del grd_qsim_t

        # set up stats data
        df_sts_dumm = Univar(data=np.ones(10)).assess_basic_stats()
        grd_stats = np.zeros(shape=(len(mc_sim_df), len(df_sts_dumm)))

        # retrieve stats from simulation
        if talk:
            print("Processing bands...")
        for i in range(len(mc_sim_df)):
            vct_data = mc_sim_df.values[i][1:]
            uni = Univar(data=vct_data)
            _df_stats = uni.assess_basic_stats()
            grd_stats[i] = _df_stats["Value"].values

        # set up stats dataframe
        mc_stats_df = pd.DataFrame(
            columns=[
                "Q_{}".format(df_sts_dumm["Statistic"].values[i])
                for i in range(len(df_sts_dumm))
            ],
            data=grd_stats,
        )
        mc_stats_df.insert(0, column=self.field_h, value=mc_sim_df[self.field_h])
        del grd_stats

        # return objects
        return {
            "Models": mc_models_df,
            "Simulation": mc_sim_df,
            "Statistics": mc_stats_df,
        }

    def view(
        self, show=True, folder="C:/data", filename=None, dpi=150, fig_format="jpg"
    ):
        """View Rating Curve

        :param show: boolean to show plot instead of saving, defaults to False
        :type show: bool
        :param folder: path_main to output folder, defaults to ``./output``
        :type folder: str
        :param filename: name of file, defaults to None
        :type filename: str
        :param specs: specifications dictionary, defaults to None
        :type specs: dict
        :param dpi: image resolution, defaults to 96
        :type dpi: int
        :param fig_format: image fig_format (ex: png or jpg). Default jpg
        :type fig_format: str
        :return: None
        :rtype: None
        """
        from plans.analyst import Bivar

        biv = Bivar(
            df_data=self.data,
            x_name=self.field_hobs,
            y_name=self.field_qobs,
            name="{} Rating Curve".format(self.name),
        )
        specs = {
            "xlabel": "{} ({})".format(self.field_hobs, self.units_h),
            "ylabel": "{} ({})".format(self.field_qobs, self.units_q),
            "xlim": (0, 1.1 * self.data[self.field_hobs].max()),
            "ylim": (0, 1.1 * self.data[self.field_qobs].max()),
        }
        biv.view(
            show=show,
            folder=folder,
            filename=filename,
            specs=specs,
            dpi=dpi,
            fig_format=fig_format,
        )
        del biv
        return None

    def view_model(
        self,
        transform=False,
        show=True,
        folder="C:/data",
        filename=None,
        dpi=150,
        fig_format="jpg",
    ):
        """View model Rating Curve

        :param transform: option for plotting transformed variables
        :type transform: bool
        :param show: boolean to show plot instead of saving, defaults to False
        :type show: bool
        :param folder: path_main to output folder, defaults to ``./output``
        :type folder: str
        :param filename: name of file, defaults to None
        :type filename: str
        :param specs: specifications dictionary, defaults to None
        :type specs: dict
        :param dpi: image resolution, defaults to 96
        :type dpi: int
        :param fig_format: image fig_format (ex: png or jpg). Default jpg
        :type fig_format: str
        :return: None
        :rtype: None
        """
        from plans.analyst import Bivar

        self.update()

        s_xfield = self.field_hobs
        s_yfield = self.field_qobs
        model_type = "Power"
        if transform:
            s_xfield = self.field_htt
            s_yfield = self.field_qt
            model_type = "Linear"

        # create Bivar base_object
        biv = Bivar(
            df_data=self.data,
            x_name=s_xfield,
            y_name=s_yfield,
            name="{} Rating Curve".format(self.name),
        )

        specs = {
            "xlabel": "{} ({})".format(s_xfield, self.units_h),
            "ylabel": "{} ({})".format(s_yfield, self.units_q),
            "xlim": (0, 1.1 * self.data[s_xfield].max()),
            "ylim": (0, 1.1 * self.data[s_yfield].max()),
        }

        # set Power model parameters
        params_model = [-self.h0, self.b, self.a]
        if transform:
            # get transformed Linear params
            c0t = np.log(self.a)
            c1t = self.b
            params_model = [c0t, c1t]
        biv.update_model(params_mean=params_model, model_type=model_type)

        biv.view_model(
            model_type=model_type,
            show=show,
            folder=folder,
            filename=filename,
            specs=specs,
            dpi=dpi,
            fig_format=fig_format,
        )
        del biv
        return None


class RatingCurveCollection(Collection):
    def __init__(self, name="MyRatingCurveCollection"):
        obj_aux = RatingCurve()
        super().__init__(base_object=obj_aux, name=name)
        # set up date fields and special attributes
        self.catalog["Date_Start"] = pd.to_datetime(self.catalog["Date_Start"])
        self.catalog["Date_End"] = pd.to_datetime(self.catalog["Date_End"])

    def load(
        self,
        name,
        table_file,
        hobs_field,
        qobs_field,
        date_field="Date",
        units_q="m3/s",
        units_h="m",
    ):
        """Load rating curve to colletion from CSV file

        :param name: Rating Curve name
        :type name: str
        :param table_file: path to CSV file
        :type table_file: str
        :param hobs_field: name of observed Stage field
        :type hobs_field: str
        :param qobs_field: name of observed Discharge field
        :type qobs_field: str
        :param date_field: name of Date field
        :type date_field: str
        :param units_q: units of streamflow
        :type units_q: str
        :param units_h: units of stage
        :type units_h: str
        :return: None
        :rtype: None
        """
        rc_aux = RatingCurve(name=name)
        rc_aux.load(
            table_file=table_file,
            hobs_field=hobs_field,
            qobs_field=qobs_field,
            date_field=date_field,
            units_q=units_q,
            units_h=units_h,
        )
        self.append(new_object=rc_aux)
        # delete aux
        del rc_aux
        return None

    def view(
        self,
        show=True,
        folder="./output",
        filename=None,
        specs=None,
        dpi=150,
        fig_format="jpg",
    ):
        lst_colors = get_random_colors(size=len(self.catalog))

        # get specs
        default_specs = {
            "suptitle": "Rating Curves Collection | {}".format(self.name),
            "width": 5 * 1.618,
            "height": 5,
            "xmin": 0,
            "xmax": 1.5 * self.catalog["H_max"].max(),
        }
        # handle input specs
        if specs is None:
            pass
        else:  # override default
            for k in specs:
                default_specs[k] = specs[k]
        specs = default_specs

        # Deploy figure
        fig = plt.figure(figsize=(specs["width"], specs["height"]))  # Width, Height
        fig.suptitle(specs["suptitle"])

        self.update(details=True)
        for i in range(len(self.catalog)):
            s_name = self.catalog["Name"].values[i]
            _df = self.collection[s_name].data
            _hfield = self.collection[s_name].field_hobs
            _qfield = self.collection[s_name].field_qobs
            plt.scatter(_df[_hfield], _df[_qfield], marker=".", color=lst_colors[i])

        plt.xlim(specs["xmin"], specs["xmax"])

        # show or save
        if show:
            plt.show()
        else:
            if filename is None:
                filename = "{}_{}".format(self.varalias, self.name)
            plt.savefig("{}/{}.{}".format(folder, filename, fig_format), dpi=dpi)
            plt.close(fig)
        return None


class Streamflow:
    """
    The Streamflow (Discharge) base_object
    """

    def __init__(self, name, code):
        # -------------------------------------
        # set basic attributes
        self.name = name
        self.code = code
        self.source_data = None
        self.latitude = None
        self.longitude = None
        self.stage_series = None
        self.rating_curves = None

    # todo implement StreamFlow


# -----------------------------------------
# Base raster data structures


class Raster:
    """
    The basic raster map dataset.
    """

    def __init__(self, name="myRasterMap", dtype="float32"):
        """Deploy a basic raster map object.

        :param name: Map name, defaults to "myRasterMap"
        :type name: str
        :param dtype: Data type of raster cells. Options: byte, uint8, int16, int32, float32, etc., defaults to "float32"
        :type dtype: str

        **Attributes:**

        - `grid` (None): Main grid of the raster.
        - `backup_grid` (None): Backup grid for AOI operations.
        - `isaoi` (False): Flag indicating whether an AOI mask is applied.
        - `asc_metadata` (dict): Metadata dictionary with keys: ncols, nrows, xllcorner, yllcorner, cellsize, NODATA_value.
        - `nodatavalue` (None): NODATA value from asc_metadata.
        - `cellsize` (None): Cell size from asc_metadata.
        - `name` (str): Name of the raster map.
        - `dtype` (str): Data type of raster cells.
        - `cmap` ("jet"): Default color map for visualization.
        - `varname` ("Unknown variable"): Variable name associated with the raster.
        - `varalias` ("Var"): Variable alias.
        - `description` (None): Description of the raster map.
        - `units` ("units"): Measurement units of the raster values.
        - `date` (None): Date associated with the raster map.
        - `source_data` (None): Source data information.
        - `prj` (None): Projection information.
        - `path_ascfile` (None): Path to the .asc raster file.
        - `path_prjfile` (None): Path to the .prj projection file.
        - `view_specs` (None): View specifications for visualization.

        **Examples:**

        >>> # Create a raster map with default settings
        >>> raster = Raster()

        >>> # Create a raster map with custom name and data type
        >>> custom_raster = Raster(name="CustomRaster", dtype="int16")
        """
        # -------------------------------------
        # set basic attributes
        self.grid = None  # main grid
        self.backup_grid = None
        self.isaoi = False
        self.asc_metadata = {
            "ncols": None,
            "nrows": None,
            "xllcorner": None,
            "yllcorner": None,
            "cellsize": None,
            "NODATA_value": None,
        }
        self.nodatavalue = self.asc_metadata["NODATA_value"]
        self.cellsize = self.asc_metadata["cellsize"]
        self.name = name
        self.dtype = dtype
        self.cmap = "jet"
        self.varname = "Unknown variable"
        self.varalias = "Var"
        self.description = None
        self.units = "units"
        self.date = None  # "2020-01-01"
        self.source_data = None
        self.prj = None
        self.path_ascfile = None
        self.path_prjfile = None
        # get view specs
        self.view_specs = None
        self._set_view_specs()

    def __str__(self):
        dct_meta = self.get_metadata()
        lst_ = list()
        lst_.append("\n")
        lst_.append("Object: {}".format(type(self)))
        lst_.append("Metadata:")
        for k in dct_meta:
            lst_.append("\t{}: {}".format(k, dct_meta[k]))
        return "\n".join(lst_)

    def set_grid(self, grid):
        """Set the data grid for the raster object.

        This function allows setting the data grid for the raster object. The incoming grid should be a NumPy array.

        :param grid: :class:`numpy.ndarray`
            The data grid to be set for the raster.
        :type grid: :class:`numpy.ndarray`

        **Notes:**

        - The function overwrites the existing data grid in the raster object with the incoming grid, ensuring that the data type matches the raster's dtype.
        - Nodata values are masked after setting the grid.

        **Examples:**

        >>> # Example of setting a new grid
        >>> new_grid = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]])
        >>> raster.set_grid(new_grid)
        """
        # overwrite incoming dtype
        self.grid = grid.astype(self.dtype)
        # mask nodata values
        self.mask_nodata()
        return None

    def set_asc_metadata(self, metadata):
        """Set metadata for the raster object based on incoming metadata.

        This function allows setting metadata for the raster object from an incoming metadata dictionary. The metadata should include information such as the number of columns, number of rows, corner coordinates, cell size, and nodata value.

        :param metadata: dict
            A dictionary containing metadata for the raster. Example metadata for a '.asc' file raster:

            .. code-block:: python

                meta = {
                    'ncols': 366,
                    'nrows': 434,
                    'xllcorner': 559493.08,
                    'yllcorner': 6704832.2,
                    'cellsize': 30,
                    'NODATA_value': -1
                }

        :type metadata: dict

        **Notes:**

        - The function updates the raster object's metadata based on the provided dictionary, ensuring that existing metadata keys are preserved.
        - It specifically updates nodata value and cell size attributes in the raster object.

        **Examples:**

        >>> # Example of setting metadata
        >>> metadata_dict = {'ncols': 200, 'nrows': 300, 'xllcorner': 500000.0, 'yllcorner': 6000000.0, 'cellsize': 25, 'NODATA_value': -9999}
        >>> raster.set_asc_metadata(metadata_dict)
        """
        for k in self.asc_metadata:
            if k in metadata:
                self.asc_metadata[k] = metadata[k]
        # update nodata value and cellsize
        self.nodatavalue = self.asc_metadata["NODATA_value"]
        self.cellsize = self.asc_metadata["cellsize"]
        return None

    def load(self, asc_file, prj_file=None):
        """Load data from files to the raster object.

        This function loads data from '.asc' raster and '.prj' projection files into the raster object.

        :param asc_file: str
            The path to the '.asc' raster file.
        :type asc_file: str

        :param prj_file: str, optional
            The path to the '.prj' projection file. If not provided, an attempt is made to use the same path and name as the '.asc' file with the '.prj' extension.
        :type prj_file: str

        :return: None
        :rtype: None

        **Notes:**

        - The function first loads the raster data from the '.asc' file using the `load_asc_raster` method.
        - If a '.prj' file is not explicitly provided, the function attempts to use a '.prj' file with the same path and name as the '.asc' file.
        - The function then loads the projection information from the '.prj' file using the `load_prj_file` method.

        **Examples:**

        >>> # Example of loading data
        >>> raster.load(asc_file="path/to/raster.asc")

        >>> # Example of loading data with a specified projection file
        >>> raster.load(asc_file="path/to/raster.asc", prj_file="path/to/raster.prj")
        """
        self.load_asc_raster(file=asc_file)
        if prj_file is None:
            # try to use the same path and name
            prj_file = asc_file.split(".")[0] + ".prj"
            if os.path.isfile(prj_file):
                self.load_prj_file(file=prj_file)
        else:
            self.load_prj_file(file=prj_file)
        return None

    def load_tif_raster(self, file):
        """Load data from '.tif' raster files.

        This function loads data from '.tif' raster files into the raster object. Note that metadata may be provided from other sources.

        :param file: str
            The file path of the '.tif' raster file.
        :type file: str

        :return: None
        :rtype: None

        **Notes:**

        - The function uses the Pillow (PIL) library to open the '.tif' file and converts it to a NumPy array.
        - Metadata may need to be provided separately, as this function focuses on loading raster data.
        - The loaded data grid is set using the `set_grid` method of the raster object.

        **Examples:**

        >>> # Example of loading data from a '.tif' file
        >>> raster.load_tif_raster(file="path/to/raster.tif")
        """
        from PIL import Image

        # Open the TIF file
        img_data = Image.open(file)
        # Convert the PIL image to a NumPy array
        grd_data = np.array(img_data)
        # set grid
        self.set_grid(grid=grd_data)
        return None

    def load_asc_raster(self, file):
        """Load data and metadata from '.asc' raster files.

        This function loads both data and metadata from '.asc' raster files into the raster object.

        :param file: str
            The file path to the '.asc' raster file.
        :type file: str

        :return: None
        :rtype: None

        **Notes:**

        - The function reads the content of the '.asc' file, extracts metadata, and constructs the data grid.
        - The metadata includes information such as the number of columns, number of rows, corner coordinates, cell size, and nodata value.
        - The data grid is constructed from the array information provided in the '.asc' file.
        - The function depends on the existence of a properly formatted '.asc' file.
        - No additional dependencies beyond standard Python libraries are required.

        **Examples:**

        >>> # Example of loading data and metadata from a '.asc' file
        >>> raster.load_asc_raster(file="path/to/raster.asc")
        """
        # get file
        self.path_ascfile = file
        f_file = open(file)
        lst_file = f_file.readlines()
        f_file.close()
        #
        # get metadata constructor loop
        tpl_meta_labels = (
            "ncols",
            "nrows",
            "xllcorner",
            "yllcorner",
            "cellsize",
            "NODATA_value",
        )
        tpl_meta_format = ("int", "int", "float", "float", "float", "float")
        dct_meta = dict()
        for i in range(6):
            lcl_lst = lst_file[i].split(" ")
            lcl_meta_str = lcl_lst[len(lcl_lst) - 1].split("\n")[0]
            if tpl_meta_format[i] == "int":
                dct_meta[tpl_meta_labels[i]] = int(lcl_meta_str)
            else:
                dct_meta[tpl_meta_labels[i]] = float(lcl_meta_str)
        #
        # array constructor loop:
        lst_grid = list()
        for i in range(6, len(lst_file)):
            lcl_lst = lst_file[i].split(" ")[1:]
            lcl_lst[len(lcl_lst) - 1] = lcl_lst[len(lcl_lst) - 1].split("\n")[0]
            lst_grid.append(lcl_lst)
        # create grid file
        grd_data = np.array(lst_grid, dtype=self.dtype)
        #
        self.set_asc_metadata(metadata=dct_meta)
        self.set_grid(grid=grd_data)
        return None

    def load_asc_metadata(self, file):
        """Load only metadata from '.asc' raster files.

        This function extracts metadata from '.asc' raster files and sets it as attributes in the raster object.

        :param file: str
            The file path to the '.asc' raster file.
        :type file: str

        :return: None
        :rtype: None

        **Notes:**

        - The function reads the first six lines of the '.asc' file to extract metadata.
        - Metadata includes information such as the number of columns, number of rows, corner coordinates, cell size, and nodata value.
        - The function sets the metadata as attributes in the raster object using the `set_asc_metadata` method.
        - This function is useful when only metadata needs to be loaded without the entire data grid.

        **Examples:**

        >>> # Example of loading metadata from a '.asc' file
        >>> raster.load_asc_metadata(file="path/to/raster.asc")
        """
        with open(file) as f:
            def_lst = []
            for i, line in enumerate(f):
                if i >= 6:
                    break
                def_lst.append(line.strip())  # append each line to the list
        #
        # get metadata constructor loop
        meta_lbls = (
            "ncols",
            "nrows",
            "xllcorner",
            "yllcorner",
            "cellsize",
            "NODATA_value",
        )
        meta_format = ("int", "int", "float", "float", "float", "float")
        meta_dct = dict()
        for i in range(6):
            lcl_lst = def_lst[i].split(" ")
            lcl_meta_str = lcl_lst[len(lcl_lst) - 1].split("\n")[0]
            if meta_format[i] == "int":
                meta_dct[meta_lbls[i]] = int(lcl_meta_str)
            else:
                meta_dct[meta_lbls[i]] = float(lcl_meta_str)
        # set attribute
        self.set_asc_metadata(metadata=meta_dct)
        return None

    def load_prj_file(self, file):
        """Load '.prj' auxiliary file to the 'prj' attribute.

        This function loads the content of a '.prj' auxiliary file and sets it as the 'prj' attribute in the raster object.

        :param file: str
            The file path to the '.prj' auxiliary file.
        :type file: str

        :return: None
        :rtype: None

        **Notes:**

        - The function reads the content of the '.prj' file and assigns it to the 'prj' attribute.
        - The 'prj' attribute typically contains coordinate system information in Well-Known Text (WKT) format.
        - This function is useful for associating coordinate system information with raster data.

        **Examples:**

        >>> # Example of loading coordinate system information from a '.prj' file
        >>> raster.load_prj_file(file="path/to/raster.prj")
        """
        self.path_prjfile = file
        with open(file) as f:
            self.prj = f.readline().strip("\n")
        return None

    def copy_structure(self, raster_ref, n_nodatavalue=None):
        """Copy structure (asc_metadata and prj file) from another raster object.

        This function copies the structure, including asc_metadata and prj, from another raster object to the current raster object.

        :param raster_ref: :class:`datasets.Raster`
            The reference incoming raster object from which to copy asc_metadata and prj.
        :type raster_ref: :class:`datasets.Raster`

        :param n_nodatavalue: float, optional
            The new nodata value for different raster objects. If None, the nodata value remains unchanged.
        :type n_nodatavalue: float

        :return: None
        :rtype: None

        **Notes:**

        - The function copies the asc_metadata and prj attributes from the reference raster object to the current raster object.
        - If a new nodata value is provided, it updates the 'NODATA_value' in the copied asc_metadata.
        - This function is useful for ensuring consistency in metadata and coordinate system information between raster objects.

        **Examples:**

        >>> # Example of copying structure from a reference raster object
        >>> new_raster.copy_structure(raster_ref=reference_raster, n_nodatavalue=-9999.0)
        """
        dict_meta = raster_ref.asc_metadata.copy()
        # handle new nodatavalue
        if n_nodatavalue is None:
            pass
        else:
            dict_meta["NODATA_value"] = n_nodatavalue
        self.set_asc_metadata(metadata=dict_meta)
        self.prj = raster_ref.prj[:]
        return None

    def export(self, folder, filename=None):
        """Export raster data to a folder.

        This function exports raster data, including the '.asc' raster file and '.prj' projection file, to the specified folder.

        :param folder: str
            The directory path to export the raster data.
        :type folder: str

        :param filename: str, optional
            The name of the exported files without extension. If None, the name of the raster object is used.
        :type filename: str

        :return: None
        :rtype: None

        **Notes:**

        - The function exports the raster data to the specified folder, creating '.asc' and '.prj' files.
        - If a filename is not provided, the function uses the name of the raster object.
        - The exported files will have the same filename with different extensions ('.asc' and '.prj').
        - This function is useful for saving raster data to a specified directory.

        **Examples:**

        >>> # Example of exporting raster data to a folder
        >>> raster.export(folder="path/to/export_folder", filename="exported_raster")
        """
        if filename is None:
            filename = self.name
        self.export_asc_raster(folder=folder, filename=filename)
        self.export_prj_file(folder=folder, filename=filename)
        return None

    def export_asc_raster(self, folder, filename=None):
        """Export an '.asc' raster file.

        This function exports the raster data as an '.asc' file to the specified folder.

        :param folder: str
            The directory path to export the '.asc' raster file.
        :type folder: str

        :param filename: str, optional
            The name of the exported file without extension. If None, the name of the raster object is used.
        :type filename: str

        :return: str
            The full file name (path and extension) of the exported '.asc' raster file.
        :rtype: str

        **Notes:**

        - The function exports the raster data to an '.asc' file in the specified folder.
        - If a filename is not provided, the function uses the name of the raster object.
        - The exported '.asc' file contains metadata and data information.
        - This function is useful for saving raster data in ASCII format.

        **Examples:**

        >>> # Example of exporting an '.asc' raster file to a folder
        >>> raster.export_asc_raster(folder="path/to/export_folder", filename="exported_raster")
        """
        if self.grid is None or self.asc_metadata is None:
            pass
        else:
            meta_lbls = (
                "ncols",
                "nrows",
                "xllcorner",
                "yllcorner",
                "cellsize",
                "NODATA_value",
            )
            ndv = float(self.asc_metadata["NODATA_value"])
            exp_lst = list()
            for i in range(len(meta_lbls)):
                line = "{}    {}\n".format(
                    meta_lbls[i], self.asc_metadata[meta_lbls[i]]
                )
                exp_lst.append(line)

            # ----------------------------------
            # data constructor loop:
            self.insert_nodata()  # insert nodatavalue

            def_array = np.array(self.grid, dtype=self.dtype)
            for i in range(len(def_array)):
                # replace np.nan to no data values
                lcl_row_sum = np.sum((np.isnan(def_array[i])) * 1)
                if lcl_row_sum > 0:
                    # print('Yeas')
                    for j in range(len(def_array[i])):
                        if np.isnan(def_array[i][j]):
                            def_array[i][j] = int(ndv)
                str_join = " " + " ".join(np.array(def_array[i], dtype="str")) + "\n"
                exp_lst.append(str_join)

            if filename is None:
                filename = self.name
            flenm = folder + "/" + filename + ".asc"
            fle = open(flenm, "w+")
            fle.writelines(exp_lst)
            fle.close()

            # mask again
            self.mask_nodata()

            return flenm

    def export_prj_file(self, folder, filename=None):
        """Export a '.prj' file.

        This function exports the coordinate system information to a '.prj' file in the specified folder.

        :param folder: str
            The directory path to export the '.prj' file.
        :type folder: str

        :param filename: str, optional
            The name of the exported file without extension. If None, the name of the raster object is used.
        :type filename: str

        :return: str or None
            The full file name (path and extension) of the exported '.prj' file, or None if no coordinate system information is available.
        :rtype: str or None

        **Notes:**

        - The function exports the coordinate system information to a '.prj' file in the specified folder.
        - If a filename is not provided, the function uses the name of the raster object.
        - The exported '.prj' file contains coordinate system information in Well-Known Text (WKT) format.
        - This function is useful for saving coordinate system information associated with raster data.

        **Examples:**

        >>> # Example of exporting a '.prj' file to a folder
        >>> raster.export_prj_file(folder="path/to/export_folder", filename="exported_prj")
        """
        if self.prj is None:
            return None
        else:
            if filename is None:
                filename = self.name

            flenm = folder + "/" + filename + ".prj"
            fle = open(flenm, "w+")
            fle.writelines([self.prj])
            fle.close()
            return flenm

    def mask_nodata(self):
        """Mask grid cells as NaN where data is NODATA.

        :return: None
        :rtype: None

        **Notes:**

        - The function masks grid cells as NaN where the data is equal to the specified NODATA value.
        - If NODATA value is not set, no masking is performed.
        """
        if self.nodatavalue is None:
            pass
        else:
            if self.grid.dtype.kind in ["i", "u"]:
                # for integer grid
                self.grid = np.ma.masked_where(self.grid == self.nodatavalue, self.grid)
            else:
                # for floating point grid:
                self.grid[self.grid == self.nodatavalue] = np.nan
        return None

    def insert_nodata(self):
        """Insert grid cells as NODATA where data is NaN.

        :return: None
        :rtype: None

        **Notes:**

        - The function inserts NODATA values into grid cells where the data is NaN.
        - If NODATA value is not set, no insertion is performed.
        """
        if self.nodatavalue is None:
            pass
        else:
            if self.grid.dtype.kind in ["i", "u"]:
                # for integer grid
                self.grid = np.ma.filled(self.grid, fill_value=self.nodatavalue)
            else:
                # for floating point grid:
                self.grid = np.nan_to_num(self.grid, nan=self.nodatavalue)
        return None

    def rebase_grid(self, base_raster, inplace=False, method="linear_model"):
        """Rebase the grid of a raster.

        This function creates a new grid based on a provided reference raster. Both rasters are expected to be in the same coordinate system and have overlapping bounding boxes.

        :param base_raster: :class:`datasets.Raster`
            The reference raster used for rebase. It should be in the same coordinate system and have overlapping bounding boxes.
        :type base_raster: :class:`datasets.Raster`

        :param inplace: bool, optional
            If True, the rebase operation will be performed in-place, and the original raster's grid will be modified. If False, a new rebased grid will be returned, and the original data will remain unchanged. Default is False.
        :type inplace: bool

        :param method: str, optional
            Interpolation method for rebasing the grid. Options include "linear_model," "nearest," and "cubic." Default is "linear_model."
        :type method: str

        :return: :class:`numpy.ndarray` or None
            If inplace is False, a new rebased grid as a NumPy array.
            If inplace is True, returns None, and the original raster's grid is modified in-place.
        :rtype: :class:`numpy.ndarray` or None

        **Notes:**

        - The rebase operation involves interpolating the values of the original grid to align with the reference raster's grid.
        - The method parameter specifies the interpolation method and can be "linear_model," "nearest," or "cubic."
        - The rebase assumes that both rasters are in the same coordinate system and have overlapping bounding boxes.

        **Examples:**

        >>> # Example with inplace=True
        >>> raster.rebase_grid(base_raster=reference_raster, inplace=True)

        >>> # Example with inplace=False
        >>> rebased_grid = raster.rebase_grid(base_raster=reference_raster, inplace=False)
        """
        from scipy.interpolate import griddata

        # get data points
        _df = self.get_grid_datapoints(drop_nan=True)
        # get base grid data points
        _dfi = base_raster.get_grid_datapoints(drop_nan=False)
        # set data points
        grd_points = np.array([_df["x"].values, _df["y"].values]).transpose()
        grd_new_points = np.array([_dfi["x"].values, _dfi["y"].values]).transpose()
        _dfi["zi"] = griddata(
            points=grd_points, values=_df["z"].values, xi=grd_new_points, method=method
        )
        grd_zi = np.reshape(_dfi["zi"].values, newshape=base_raster.grid.shape)
        if inplace:
            # set
            self.set_grid(grid=grd_zi)
            self.set_asc_metadata(metadata=base_raster.asc_metadata)
            self.prj = base_raster.prj
            return None
        else:
            return grd_zi

    def apply_aoi_mask(self, grid_aoi, inplace=False):
        """Apply AOI (area of interest) mask to the raster map.

        This function applies an AOI (area of interest) mask to the raster map, replacing values outside the AOI with the NODATA value.

        :param grid_aoi: :class:`numpy.ndarray`
            Map of AOI (masked array or pseudo-boolean). Expected to have the same grid shape as the raster.
        :type grid_aoi: :class:`numpy.ndarray`

        :param inplace: bool, optional
            If True, overwrite the main grid with the masked values. If False, create a backup and modify a copy of the grid.
            Default is False.
        :type inplace: bool

        :return: None
        :rtype: None

        **Notes:**

        - The function replaces values outside the AOI (where grid_aoi is 0) with the NODATA value.
        - If NODATA value is not set, no replacement is performed.
        - If inplace is True, the main grid is modified. If False, a backup of the grid is created before modification.
        - This function is useful for focusing analysis or visualization on a specific area within the raster map.

        **Examples:**

        >>> # Example of applying an AOI mask to the raster map
        >>> raster.apply_aoi_mask(grid_aoi=aoi_mask, inplace=True)
        """
        if self.nodatavalue is None or self.grid is None:
            pass
        else:
            # ensure fill on masked values
            grid_aoi = np.ma.filled(grid_aoi, fill_value=0)
            # replace
            grd_mask = np.where(grid_aoi == 0, self.nodatavalue, self.grid)

            if inplace:
                pass
            else:
                # pass a copy to backup grid
                self.backup_grid = self.grid.copy()
            # set main grid
            self.set_grid(grid=grd_mask)
            self.isaoi = True
        return None

    def release_aoi_mask(self):
        """Release AOI mask from the main grid. Backup grid is restored.

        This function releases the AOI (area of interest) mask from the main grid, restoring the original values from the backup grid.

        :return: None
        :rtype: None

        **Notes:**

        - If an AOI mask has been applied, this function restores the original values to the main grid from the backup grid.
        - If no AOI mask has been applied, the function has no effect.
        - After releasing the AOI mask, the backup grid is set to None, and the raster object is no longer considered to have an AOI mask.

        **Examples:**

        >>> # Example of releasing the AOI mask from the main grid
        >>> raster.release_aoi_mask()
        """
        if self.isaoi:
            self.set_grid(grid=self.backup_grid)
            self.backup_grid = None
            self.isaoi = False
        return None

    def cut_edges(self, upper, lower, inplace= False):
        """Cutoff upper and lower values of the raster grid.

        :param upper: float or int
            The upper value for the cutoff.
        :type upper: float or int

        :param lower: float or int
            The lower value for the cutoff.
        :type lower: float or int

        :param inplace: bool, optional
            If True, modify the main grid in-place. If False, create a processed copy of the grid.
            Default is False.
        :type inplace: bool

        :return: :class:`numpy.ndarray` or None
            The processed grid if inplace is False. If inplace is True, returns None.
        :rtype: Union[None, np.ndarray]

        **Notes:**

        - Values in the raster grid below the lower value are set to the lower value.
        - Values in the raster grid above the upper value are set to the upper value.
        - If inplace is False, a processed copy of the grid is returned, leaving the original grid unchanged.
        - This function is useful for clipping extreme values in the raster grid.

        **Examples:**

        >>> # Example of cutting off upper and lower values in the raster grid
        >>> processed_grid = raster.cut_edges(upper=100, lower=0, inplace=False)
        >>> # Alternatively, modify the main grid in-place
        >>> raster.cut_edges(upper=100, lower=0, inplace=True)
        """
        if self.grid is None:
            return None
        else:
            new_grid = self.grid
            new_grid[new_grid < lower] = lower
            new_grid[new_grid > upper] = upper

            if inplace:
                self.set_grid(grid=new_grid)
                return None
            else:
                return new_grid

    def get_metadata(self):
        """Get all metadata from the base object.

        :return: Metadata dictionary.

            - "Name" (str): Name of the raster.
            - "Variable" (str): Variable name.
            - "VarAlias" (str): Variable alias.
            - "Units" (str): Measurement units.
            - "Date" (str): Date information.
            - "Source" (str): Data source.
            - "Description" (str): Description of the raster.
            - "cellsize" (float): Cell size of the raster.
            - "ncols" (int): Number of columns in the raster grid.
            - "nrows" (int): Number of rows in the raster grid.
            - "xllcorner" (float): X-coordinate of the lower-left corner.
            - "yllcorner" (float): Y-coordinate of the lower-left corner.
            - "NODATA_value" (Union[float, None]): NODATA value in the raster.
            - "Prj" (str): Projection information.
            - "Path_ASC" (str): File path to the ASC raster file.
            - "Path_PRJ" (str): File path to the PRJ projection file.
        :rtype: dict
        """
        return {
            "Name": self.name,
            "Variable": self.varname,
            "VarAlias": self.varalias,
            "Units": self.units,
            "Date": self.date,
            "Source": self.source_data,
            "Description": self.description,
            "cellsize": self.cellsize,
            "ncols": self.asc_metadata["ncols"],
            "nrows": self.asc_metadata["nrows"],
            "xllcorner": self.asc_metadata["xllcorner"],
            "yllcorner": self.asc_metadata["yllcorner"],
            "NODATA_value": self.nodatavalue,
            "Prj": self.prj,
            "Path_ASC": self.path_ascfile,
            "Path_PRJ": self.path_prjfile,
        }

    def get_bbox(self):
        """Get the Bounding Box of the map.

        :return: Dictionary of xmin, xmax, ymin, and ymax.

            - "xmin" (float): Minimum x-coordinate.
            - "xmax" (float): Maximum x-coordinate.
            - "ymin" (float): Minimum y-coordinate.
            - "ymax" (float): Maximum y-coordinate.
        :rtype: dict
        """
        return {
            "xmin": self.asc_metadata["xllcorner"],
            "xmax": self.asc_metadata["xllcorner"]
            + (self.asc_metadata["ncols"] * self.cellsize),
            "ymin": self.asc_metadata["yllcorner"],
            "ymax": self.asc_metadata["yllcorner"]
            + (self.asc_metadata["nrows"] * self.cellsize),
        }

    def get_grid_datapoints(self, drop_nan=False):
        """Get flat and cleared grid data points (x, y, and z).

        :param drop_nan: Option to ignore nan values.
        :type drop_nan: bool

        :return: DataFrame of x, y, and z fields.
        :rtype: :class:`pandas.DataFrame` or None
            If the grid is None, returns None.

        **Notes:**

        - This function extracts coordinates (x, y, and z) from the raster grid.
        - The x and y coordinates are determined based on the grid cell center positions.
        - If drop_nan is True, nan values are ignored in the resulting DataFrame.
        - The resulting DataFrame includes columns for x, y, z, i, and j coordinates.

        **Examples:**

        >>> # Get grid data points with nan values included
        >>> datapoints_df = raster.get_grid_datapoints(drop_nan=False)
        >>> # Get grid data points with nan values ignored
        >>> clean_datapoints_df = raster.get_grid_datapoints(drop_nan=True)
        """
        if self.grid is None:
            return None
        else:
            # get coordinates
            vct_i = np.zeros(self.grid.shape[0] * self.grid.shape[1])
            vct_j = vct_i.copy()
            vct_z = vct_i.copy()
            _c = 0
            for i in range(len(self.grid)):
                for j in range(len(self.grid[i])):
                    vct_i[_c] = i
                    vct_j[_c] = j
                    vct_z[_c] = self.grid[i][j]
                    _c = _c + 1

            # transform
            n_height = self.grid.shape[0] * self.cellsize
            vct_y = (
                self.asc_metadata["yllcorner"]
                + (n_height - (vct_i * self.cellsize))
                - (self.cellsize / 2)
            )
            vct_x = (
                self.asc_metadata["xllcorner"]
                + (vct_j * self.cellsize)
                + (self.cellsize / 2)
            )

            # drop nan or masked values:
            if drop_nan:
                vct_j = vct_j[~np.isnan(vct_z)]
                vct_i = vct_i[~np.isnan(vct_z)]
                vct_x = vct_x[~np.isnan(vct_z)]
                vct_y = vct_y[~np.isnan(vct_z)]
                vct_z = vct_z[~np.isnan(vct_z)]
            # built dataframe
            _df = pd.DataFrame(
                {
                    "x": vct_x,
                    "y": vct_y,
                    "z": vct_z,
                    "i": vct_i,
                    "j": vct_j,
                }
            )
            return _df

    def get_grid_data(self):
        """Get flat and cleared grid data.

        :return: 1D vector of cleared data.
        :rtype: :class:`numpy.ndarray` or None
            If the grid is None, returns None.

        **Notes:**

        - This function extracts and flattens the grid data, removing any masked or NaN values.
        - For integer grids, the masked values are ignored.
        - For floating-point grids, both masked and NaN values are ignored.

        **Examples:**

        >>> # Get flattened and cleared grid data
        >>> data_vector = raster.get_grid_data()
        """
        if self.grid is None:
            return None
        else:
            if self.grid.dtype.kind in ["i", "u"]:
                # for integer grid
                _grid = self.grid[~self.grid.mask]
                return _grid
            else:
                # for floating point grid:
                _grid = self.grid.ravel()[~np.isnan(self.grid.ravel())]
                return _grid

    def get_grid_stats(self):
        """Get basic statistics from flat and cleared data.

        :return: DataFrame of basic statistics.
        :rtype: :class:`pandas.DataFrame` or None
            If the grid is None, returns None.

        **Notes:**

        - This function computes basic statistics from the flattened and cleared grid data.
        - Basic statistics include measures such as mean, median, standard deviation, minimum, and maximum.
        - Requires the 'plans.analyst' module for statistical analysis.

        **Examples:**

        >>> # Get basic statistics from the raster grid
        >>> stats_dataframe = raster.get_grid_stats()
        """
        if self.grid is None:
            return None
        else:
            from plans.analyst import Univar

            return Univar(data=self.get_grid_data()).assess_basic_stats()

    def get_aoi(self, by_value_lo, by_value_hi):
        """Get the AOI map from an interval of values (values are expected to exist in the raster).

        :param by_value_lo: Number for the lower bound (inclusive).
        :type by_value_lo: float
        :param by_value_hi: Number for the upper bound (inclusive).
        :type by_value_hi: float

        :return: AOI map.
        :rtype: :class:`AOI` object

        **Notes:**

        - This function creates an AOI (Area of Interest) map based on a specified value range.
        - The AOI map is constructed as a binary grid where values within the specified range are set to 1, and others to 0.

        **Examples:**

        >>> # Get AOI map for values between 10 and 20
        >>> aoi_map = raster.get_aoi(by_value_lo=10, by_value_hi=20)
        """
        map_aoi = AOI(name="{} {}-{}".format(self.varname, by_value_lo, by_value_hi))
        map_aoi.set_asc_metadata(metadata=self.asc_metadata)
        map_aoi.prj = self.prj
        # set grid
        self.insert_nodata()
        map_aoi.set_grid(
            grid=1 * (self.grid >= by_value_lo) * (self.grid <= by_value_hi)
        )
        self.mask_nodata()
        return map_aoi

    def _set_view_specs(self):
        """Set default view specs.

        :return: None
        :rtype: None

        **Notes:**

        - This private method sets default view specifications for visualization.
        - The view specs include color, colormap, titles, dimensions, and other parameters for visualization.
        - These default values can be adjusted based on specific requirements.

        **Examples:**

        >>> # Set default view specifications
        >>> obj._set_view_specs()
        """
        self.view_specs = {
            "color": "tab:grey",
            "cmap": self.cmap,
            "suptitle": "{} | {}".format(self.varname, self.name),
            "a_title": "{} ({})".format(self.varalias, self.units),
            "b_title": "Histogram",
            "c_title": "Metadata",
            "d_title": "Statistics",
            "width": 5 * 1.618,
            "height": 5,
            "b_ylabel": "percentage",
            "b_xlabel": self.units,
            "nbins": 100,
            "vmin": None,
            "vmax": None,
            "hist_vmax": None,
            "suffix": None,
        }
        return None

    def view(
        self,
        accum=True,
        show=True,
        folder="./output",
        filename=None,
        dpi=300,
        fig_format="jpg",
    ):
        """Plot a basic panel of the raster map.

        :param accum: boolean to include an accumulated probability plot, defaults to True
        :type accum: bool
        :param show: boolean to show the plot instead of saving, defaults to True
        :type show: bool
        :param folder: path to the output folder, defaults to "./output"
        :type folder: str
        :param filename: name of the file, defaults to None
        :type filename: str
        :param dpi: image resolution, defaults to 300
        :type dpi: int
        :param fig_format: image format (e.g., jpg or png), defaults to "jpg"
        :type fig_format: str

        **Notes:**

        - This function generates a basic panel for visualizing the raster map, including the map itself, a histogram,
          metadata, and basic statistics.
        - The panel includes various customization options such as color, titles, dimensions, and more.
        - The resulting plot can be displayed or saved based on the specified parameters.

        **Examples:**

        >>> # Show the plot without saving
        >>> raster.view()

        >>> # Save the plot to a file
        >>> raster.view(show=False, folder="./output", filename="raster_plot", dpi=300, fig_format="png")
        """
        import matplotlib.ticker as mtick
        from plans.analyst import Univar

        # get univar base_object
        uni = Univar(data=self.get_grid_data())

        specs = self.view_specs

        if specs["vmin"] is None:
            specs["vmin"] = np.min(self.grid)
        if specs["vmax"] is None:
            specs["vmax"] = np.max(self.grid)

        if specs["suffix"] is None:
            suff = ""
        else:
            suff = "_{}".format(specs["suffix"])

        # Deploy figure
        fig = plt.figure(figsize=(specs["width"], specs["height"]))  # Width, Height
        gs = mpl.gridspec.GridSpec(
            4, 5, wspace=0.8, hspace=0.1, left=0.05, bottom=0.1, top=0.85, right=0.95
        )
        fig.suptitle(specs["suptitle"] + suff)

        # plot map
        plt.subplot(gs[:3, :3])
        plt.title("a. {}".format(specs["a_title"]), loc="left")
        im = plt.imshow(
            self.grid, cmap=specs["cmap"], vmin=specs["vmin"], vmax=specs["vmax"]
        )
        fig.colorbar(im, shrink=0.5)
        plt.axis("off")

        # plot Hist
        plt.subplot(gs[:2, 3:])
        plt.title("b. {}".format(specs["b_title"]), loc="left")
        vct_result = plt.hist(
            x=uni.data,
            bins=specs["nbins"],
            color=specs["color"],
            weights=np.ones(len(uni.data)) / len(uni.data)
            # orientation="horizontal"
        )

        # get upper limit if none
        if specs["hist_vmax"] is None:
            specs["hist_vmax"] = 1.2 * np.max(vct_result[0])
        # plot mean line
        n_mean = np.mean(uni.data)
        plt.vlines(
            x=n_mean,
            ymin=0,
            ymax=specs["hist_vmax"],
            colors="tab:orange",
            linestyles="--",
            # label="mean ({:.2f})".fig_format(n_mean)
        )
        plt.text(
            x=n_mean - 32 * (specs["vmax"] - specs["vmin"]) / 100,
            y=0.9 * specs["hist_vmax"],
            s="{:.2f} (mean)".format(n_mean),
        )

        plt.ylim(0, specs["hist_vmax"])
        plt.xlim(specs["vmin"], specs["vmax"])

        # plt.ylabel(specs["b_ylabel"])
        plt.xlabel(specs["b_xlabel"])

        # Set the y-axis formatter as percentages
        yticks = mtick.PercentFormatter(xmax=1, decimals=1, symbol="%", is_latex=False)
        ax = plt.gca()
        ax.yaxis.set_major_formatter(yticks)

        # --------
        # plot accumulated probability
        if accum:
            ax2 = ax.twinx()
            vct_cump = np.cumsum(a=vct_result[0]) / np.sum(vct_result[0])
            plt.plot(vct_result[1][1:], vct_cump, color="darkred")
            ax2.grid(False)

        # ------------------------------------------------------------------
        # plot metadata

        # get datasets
        df_stats = self.get_grid_stats()
        lst_meta = []
        lst_value = []
        for k in self.asc_metadata:
            lst_value.append(self.asc_metadata[k])
            lst_meta.append(k)
        df_meta = pd.DataFrame({"Raster": lst_meta, "Value": lst_value})
        # metadata
        n_y = 0.25
        n_x = 0.08
        plt.text(
            x=n_x,
            y=n_y,
            s="c. {}".format(specs["c_title"]),
            fontsize=12,
            transform=fig.transFigure,
        )
        n_y = n_y - 0.01
        n_step = 0.025
        for i in range(len(df_meta)):
            s_head = df_meta["Raster"].values[i]
            if s_head == "cellsize":
                s_value = self.cellsize
                s_line = "{:>15}: {:<10.5f}".format(s_head, s_value)
            else:
                s_value = df_meta["Value"].values[i]
                s_line = "{:>15}: {:<10.2f}".format(s_head, s_value)
            n_y = n_y - n_step
            plt.text(
                x=n_x,
                y=n_y,
                s=s_line,
                fontsize=9,
                fontdict={"family": "monospace"},
                transform=fig.transFigure,
            )

        # stats
        n_y_base = 0.25
        n_x = 0.62
        plt.text(
            x=n_x,
            y=n_y_base,
            s="d. {}".format(specs["d_title"]),
            fontsize=12,
            transform=fig.transFigure,
        )
        n_y = n_y_base - 0.01
        n_step = 0.025
        for i in range(7):
            s_head = df_stats["Statistic"].values[i]
            s_value = df_stats["Value"].values[i]
            s_line = "{:>10}: {:<10.2f}".format(s_head, s_value)
            n_y = n_y - n_step
            plt.text(
                x=n_x,
                y=n_y,
                s=s_line,
                fontsize=9,
                fontdict={"family": "monospace"},
                transform=fig.transFigure,
            )
        n_y = n_y_base - 0.01
        for i in range(7, len(df_stats)):
            s_head = df_stats["Statistic"].values[i]
            s_value = df_stats["Value"].values[i]
            s_line = "{:>10}: {:<10.2f}".format(s_head, s_value)
            n_y = n_y - n_step
            plt.text(
                x=n_x + 0.15,
                y=n_y,
                s=s_line,
                fontsize=9,
                fontdict={"family": "monospace"},
                transform=fig.transFigure,
            )
        # show or save
        if show:
            plt.show()
        else:
            if filename is None:
                filename = "{}_{}{}".format(self.varalias, self.name, suff)
            plt.savefig(
                "{}/{}{}.{}".format(folder, filename, suff, fig_format), dpi=dpi
            )
            plt.close(fig)
        return None


# -----------------------------------------
# Derived Raster data structures


class Elevation(Raster):
    """
    Elevation (DEM) raster map dataset.
    """

    def __init__(self, name="DEM"):
        """Initialize dataset

        :param name: name of map
        :type name: str
        """
        super().__init__(name=name, dtype="float32")
        self.cmap = "BrBG_r"
        self.varname = "Elevation"
        self.varalias = "DEM"
        self.description = "Height above sea level"
        self.units = "m"
        self._set_view_specs()

    def get_tpi(self, cell_radius):
        print("ah shit")

    def get_tpi_landforms(self, radius_micro, radius_macro):
        print("ah shit")


class Slope(Raster):
    """
    Slope raster map dataset.
    """

    def __init__(self, name="Slope"):
        """Initialize dataset

        :param name: name of map
        :type name: str
        """
        super().__init__(name=name, dtype="float32")
        self.cmap = "OrRd"
        self.varname = "Slope"
        self.varalias = "SLP"
        self.description = "Slope of terrain"
        self.units = "deg."
        self._set_view_specs()


class TWI(Raster):
    """
    TWI raster map dataset.
    """

    def __init__(self, name="TWI"):
        """Initialize dataset

        :param name: name of map
        :type name: str
        """
        super().__init__(name=name, dtype="float32")
        self.cmap = "YlGnBu"
        self.varname = "TWI"
        self.varalias = "TWI"
        self.description = "Topographical Wetness Index"
        self.units = "index units"
        self._set_view_specs()


class HAND(Raster):
    """
    HAND raster map dataset.
    """

    def __init__(self, name="HAND"):
        """Initialize dataset

        :param name: name of map
        :type name: str
        """
        super().__init__(name=name, dtype="float32")
        self.cmap = "YlGnBu_r"
        self.varname = "HAND"
        self.varalias = "HAND"
        self.description = "Height Above the Nearest Drainage"
        self.units = "m"
        self._set_view_specs()


class DTO(Raster):
    """
    Distance to outlet raster map dataset.
    """

    def __init__(self, name="DTO"):
        """Initialize dataset

        :param name: name of map
        :type name: str
        """
        super().__init__(name=name, dtype="float32")
        self.cmap = "rainbow"  # "gist_rainbow_r"
        self.varname = "DTO"
        self.varalias = "DTO"
        self.description = "Distance To Outlet"
        self.units = "meters"
        self._set_view_specs()


class NDVI(Raster):
    """
    NDVI raster map dataset.
    """

    def __init__(self, name, date):
        """Initialize dataset.

        :param name: name of map
        :type name: str
        :param date: date of map in ``yyyy-mm-dd``
        :type date: str
        """
        super().__init__(name=name, dtype="float32")
        self.cmap = "RdYlGn"
        self.varname = "NDVI"
        self.varalias = "NDVI"
        self.description = "Normalized difference vegetation index"
        self.units = "index units"
        self.date = date
        self._set_view_specs()
        self.view_specs["vmin"] = -1
        self.view_specs["vmax"] = 1

    def set_grid(self, grid):
        super().set_grid(grid)
        self.cut_edges(upper=1, lower=-1)
        return None


class ET24h(Raster):
    """
    ET 24h raster map dataset.
    """

    def __init__(self, name, date):
        """Initialize dataset.

        :param name: name of map
        :type name: str
        :param date: date of map in ``yyyy-mm-dd``
        :type date: str
        """
        import matplotlib as mpl
        from matplotlib.colors import ListedColormap

        super().__init__(name=name, dtype="float32")
        self.varname = "Daily Evapotranspiration"
        self.varalias = "ET24h"
        self.description = "Daily Evapotranspiration"
        self.units = "mm"
        # set custom cmap
        jet_big = mpl.colormaps["jet_r"]
        self.cmap = ListedColormap(jet_big(np.linspace(0.3, 0.75, 256)))
        self.date = date
        # view specs
        self._set_view_specs()
        self.view_specs["vmin"] = 0
        self.view_specs["vmax"] = 15

    def set_grid(self, grid):
        super().set_grid(grid)
        self.cut_edges(upper=100, lower=0)
        return None


class Hydrology(Raster):
    """
    Primitive hydrology raster map dataset.
    """

    def __init__(self, name, varalias):
        """Initialize dataset

        :param name: name of map
        :type name: str
        """
        import matplotlib as mpl
        from matplotlib.colors import ListedColormap

        dict_cmaps = {
            "flow surface": "gist_earth_r",
            "flow vapor": ListedColormap(
                mpl.colormaps["jet_r"](np.linspace(0.3, 0.75, 256))
            ),
            "flow subsurface": "gist_earth_r",
            "stock surface": "",
            "stock subsurface": "",
            "deficit": "",
        }
        # evaluate load this from csv
        dict_flows = {
            "r": {
                "varname": "Runoff",
                "description": "Combined overland flows",
                "type": "flow",
                "subtype": "surface",
            },
            "rie": {
                "varname": "Runoff by Infiltration Excess",
                "description": "Hortonian overland flow",
                "type": "flow",
                "subtype": "surface",
            },
            "rse": {
                "varname": "Runoff by Saturation Excess",
                "description": "Dunnean overland flow",
                "type": "flow",
                "subtype": "surface",
            },
            "ptf": {
                "varname": "Throughfall",
                "description": "Effective precipitation at the surface",
                "type": "flow",
                "subtype": "surface",
            },
            "inf": {
                "varname": "Infiltration",
                "description": "Water infiltration in soil",
                "type": "flow",
                "subtype": "subsurface",
            },
            "qv": {
                "varname": "Recharge",
                "description": "Recharge of groundwater",
                "type": "flow",
                "subtype": "subsurface",
            },
            "et": {
                "varname": "Evapotranspiration",
                "description": "Combined Evaporation and Transpiration flows",
                "type": "flow",
                "subtype": "vapor",
            },
            "evc": {
                "varname": "Canopy evaporation",
                "description": "Direct evaporation from canopy",
                "type": "flow",
                "subtype": "vapor",
            },
            "evs": {
                "varname": "Surface evaporation",
                "description": "Direct evaporation from soil surface",
                "type": "flow",
                "subtype": "vapor",
            },
            "tun": {
                "varname": "Soil tranpiration",
                "description": "Transpiration from the water moisture in the soil",
                "type": "flow",
                "subtype": "vapor",
            },
            "tgw": {
                "varname": "Groundwater transpiration",
                "description": "Transpiration from the saturated water zone",
                "type": "flow",
                "subtype": "vapor",
            },
        }

        super().__init__(name=name, dtype="float32")
        self.varalias = varalias.lower()
        str_cmap_id = "{} {}".format(
            dict_flows[self.varalias]["type"], dict_flows[self.varalias]["subtype"]
        )
        self.cmap = dict_cmaps[str_cmap_id]
        self.varname = dict_flows[self.varalias]["varname"]
        self.description = dict_flows[self.varalias]["description"]
        self.units = "mm"
        self.timescale = "annual"
        self._set_view_specs()


class HabQuality(Raster):
    """
    Habitat Quality raster map dataset.
    """

    def __init__(self, name, date):
        """Initialize dataset.

        :param name: name of map
        :type name: str
        :param date: date of map in ``yyyy-mm-dd``
        :type date: str
        """
        super().__init__(name=name, dtype="float32")
        self.varname = "Habitat Quality"
        self.varalias = "HQ"
        self.description = "Habitat Quality from the InVEST model"
        self.units = "index units"
        self.cmap = "RdYlGn"
        self.date = date
        # view specs
        self._set_view_specs()
        # customize
        self.view_specs["vmin"] = 0
        self.view_specs["vmax"] = 1

    def get_biodiversity_area(self, b_a: float = 1.0) -> Raster:
        """
        Get a raster of Biodiversity Area
        :param b_a: model parameter
        :type b_a: float
        :return: Raster object of biodiversity area
        :rtype: Raster
        """
        s = self.cellsize
        grid_ba = b_a * np.square(s) * self.grid / 10000
        # instantiate output
        output_raster = BiodiversityArea(name=self.name, date=self.date, q_a=b_a)
        # set raster
        output_raster.set_asc_metadata(metadata=self.asc_metadata)
        output_raster.prj = self.prj
        # set grid
        output_raster.set_grid(grid=grid_ba)
        return output_raster


class HabDegradation(Raster):
    """
    Habitat Degradation raster map dataset.
    """

    def __init__(self, name, date):
        """Initialize dataset.

        :param name: name of map
        :type name: str
        :param date: date of map in ``yyyy-mm-dd``
        :type date: str
        """
        super().__init__(name=name, dtype="float32")
        self.varname = "Habitat Degradation"
        self.varalias = "HDeg"
        self.description = "Habitat Degradation from the InVEST model"
        self.units = "index units"
        self.cmap = "YlOrRd"
        self.date = date
        self._set_view_specs()
        self.view_specs["vmin"] = 0
        self.view_specs["vmax"] = 0.7


class BiodiversityArea(Raster):
    """
    Biodiversity Area raster map dataset.
    """

    def __init__(self, name, date, q_a=1.0):
        """Initialize dataset.

        :param name: name of map
        :type name: str
        :param date: date of map in ``yyyy-mm-dd``
        :type date: str
        :param q_a: habitat quality reference
        :type q_a: float
        """
        super().__init__(name=name, dtype="float32")
        self.cmap = "YlGn"
        self.varname = "Biodiversity Area"
        self.varalias = "Ba"
        self.description = "Biodiversity area in ha equivalents"
        self.units = "ha"
        self.date = date
        self.ba_total = None
        self._set_view_specs()

    def set_grid(self, grid):
        super(BiodiversityArea, self).set_grid(grid)
        self.ba_total = np.sum(grid)
        return None


# -----------------------------------------
# Quali Raster data structures


class QualiRaster(Raster):
    """
    Basic qualitative raster map dataset.

    Attributes dataframe must at least have:
    * :class:`Id` field
    * :class:`Name` field
    * :class:`Alias` field

    """

    def __init__(self, name="QualiMap", dtype="uint8"):
        """Initialize dataset.

        :param name: name of map
        :type name: str
        :param dtype: data type of raster cells, defaults to uint8
        :type dtype: str
        """
        # prior setup
        self.path_csvfile = None
        self.table = None
        self.idfield = "Id"
        self.namefield = "Name"
        self.aliasfield = "Alias"
        self.colorfield = "Color"
        self.areafield = "Area"
        # call superior
        super().__init__(name=name, dtype=dtype)
        # overwrite
        self.cmap = "tab20"
        self.varname = "Unknown variable"
        self.varalias = "Var"
        self.description = "Unknown"
        self.units = "category ID"
        self.path_csvfile = None
        self._overwrite_nodata()
        # NOTE: view specs is set by setting table

    def _overwrite_nodata(self):
        """No data in QualiRaster is set by default to 0"""
        self.nodatavalue = 0
        self.asc_metadata["NODATA_value"] = self.nodatavalue
        return None

    def set_asc_metadata(self, metadata):
        super().set_asc_metadata(metadata)
        self._overwrite_nodata()
        return None

    def rebase_grid(self, base_raster, inplace=False):
        out = super().rebase_grid(base_raster, inplace, method="nearest")
        return out

    def reclassify(self, dict_ids, df_new_table, talk=False):
        """Reclassify QualiRaster Ids in grid and table

        :param dict_ids: dictionary to map from "Old_Id" to "New_id"
        :type dict_ids: dict
        :param df_new_table: new table for QualiRaster
        :type df_new_table: :class:`pandas.DataFrame`
        :param talk: option for printing messages
        :type talk: bool
        :return: None
        :rtype: None
        """
        grid_new = self.grid.copy()
        for i in range(len(dict_ids["Old_Id"])):
            n_old_id = dict_ids["Old_Id"][i]
            n_new_id = dict_ids["New_Id"][i]
            if talk:
                print(">> reclassify Ids from {} to {}".format(n_old_id, n_new_id))
            grid_new = (grid_new * (grid_new != n_old_id)) + (
                n_new_id * (grid_new == n_old_id)
            )
        # set new grid
        self.set_grid(grid=grid_new)
        # reset table
        self.set_table(dataframe=df_new_table)
        return None

    def load(self, asc_file, prj_file, table_file):
        """
        Load data from files to raster
        :param asc_file: path_main to ``.asc`` raster file
        :type asc_file: str
        :param prj_file: path_main to ``.prj`` projection file
        :type prj_file: str
        :param table_file: path_main to ``.txt`` table file
        :type table_file: str
        :return: None
        :rtype: None
        """
        super().load(asc_file=asc_file, prj_file=prj_file)
        self.load_table(file=table_file)
        return None

    def load_table(self, file):
        """Load attributes dataframe from ``csv`` ``.txt`` file (separator must be ;).

        :param file: path_main to file
        :type file: str
        """
        self.path_csvfile = file
        # read raw file
        df_aux = pd.read_csv(file, sep=";")
        # set to self
        self.set_table(dataframe=df_aux)
        return None

    def export(self, folder, filename=None):
        """
        Export raster data
        param folder: string of directory path_main,
        :type folder: str
        :param filename: string of file without extension, defaults to None
        :type filename: str
        :return: None
        :rtype: None
        """
        super().export(folder=folder, filename=filename)
        self.export_table(folder=folder, filename=filename)
        return None

    def export_table(self, folder, filename=None):
        """Export a CSV ``.txt``  file.

        :param folder: string of directory path_main
        :type folder: str
        :param filename: string of file without extension
        :type filename: str
        :return: full file name (path_main and extension) string
        :rtype: str
        """
        if filename is None:
            filename = self.name
        flenm = folder + "/" + filename + ".txt"
        self.table.to_csv(flenm, sep=";", index=False)
        return flenm

    def set_table(self, dataframe):
        """Set attributes dataframe from incoming :class:`pandas.DataFrame`.

        :param dataframe: incoming pandas dataframe
        :type dataframe: :class:`pandas.DataFrame`
        """
        self.table = dataframe_prepro(dataframe=dataframe.copy())
        self.table = self.table.sort_values(by=self.idfield).reset_index(drop=True)
        # set view specs
        self._set_view_specs()
        return None

    def clear_table(self):
        """Clear the unfound values in the map from the table."""
        if self.grid is None:
            pass
        else:
            # found values:
            lst_ids = np.unique(self.grid)
            # filter dataframe
            filtered_df = self.table[self.table[self.idfield].isin(lst_ids)]
            # reset table
            self.set_table(dataframe=filtered_df.reset_index(drop=True))
        return None

    def set_random_colors(self):
        """Set random colors to attribute table."""
        if self.table is None:
            pass
        else:
            self.table[self.colorfield] = get_random_colors(
                size=len(self.table), cmap=self.cmap
            )
            # reaload table for reset viewspecs
            self.set_table(dataframe=self.table)
        return None

    def get_areas(self, merge=False):
        """Get areas in map of each category in table.

        :param merge: option to merge data with raster table
        :type merge: bool, defaults to False
        :return: areas dataframe
        :rtype: :class:`pandas.DataFrame`
        """
        if self.table is None or self.grid is None or self.prj is None:
            return None
        else:
            # get unit area in meters
            _cell_size = self.cellsize
            if self.prj[:6] == "GEOGCS":
                _cell_size = self.cellsize * 111111  # convert degrees to meters
            _n_unit_area = np.square(_cell_size)
            # get aux dataframe
            df_aux = self.table[["Id", "Name", "Alias"]].copy()
            _lst_count = []
            # iterate categories
            for i in range(len(df_aux)):
                _n_id = df_aux[self.idfield].values[i]
                _n_count = np.sum(1 * (self.grid == _n_id))
                _lst_count.append(_n_count)
            # set area fields
            lst_area_fields = []
            # Count
            s_count_field = "Cell_count"
            df_aux[s_count_field] = _lst_count
            lst_area_fields.append(s_count_field)

            # m2
            s_field = "{}_m2".format(self.areafield)
            lst_area_fields.append(s_field)
            df_aux[s_field] = df_aux[s_count_field].values * _n_unit_area

            # ha
            s_field = "{}_ha".format(self.areafield)
            lst_area_fields.append(s_field)
            df_aux[s_field] = df_aux[s_count_field].values * _n_unit_area / (100 * 100)

            # km2
            s_field = "{}_km2".format(self.areafield)
            lst_area_fields.append(s_field)
            df_aux[s_field] = (
                df_aux[s_count_field].values * _n_unit_area / (1000 * 1000)
            )

            # fraction
            s_field = "{}_f".format(self.areafield)
            lst_area_fields.append(s_field)
            df_aux[s_field] = df_aux[s_count_field] / df_aux[s_count_field].sum()
            # %
            s_field = "{}_%".format(self.areafield)
            lst_area_fields.append(s_field)
            df_aux[s_field] = 100 * df_aux[s_count_field] / df_aux[s_count_field].sum()
            df_aux[s_field] = df_aux[s_field].round(2)

            # handle merge
            if merge:
                for k in lst_area_fields:
                    self.table[k] = df_aux[k].values

            return df_aux

    def get_zonal_stats(self, raster_sample, merge=False, skip_count=False):
        """Get zonal stats from other raster map to sample.

        :param raster_sample: raster map to sample
        :type raster_sample: :class:`datasets.Raster`
        :param merge: option to merge data with raster table, defaults to False
        :type merge: bool
        :param skip_count: set True to skip count, defaults to False
        :type skip_count: bool
        :return: dataframe of zonal stats
        :rtype: :class:`pandas.DataFrame`
        """
        from plans.analyst import Univar

        # deploy dataframe
        df_aux1 = self.table.copy()
        self.clear_table()  # clean
        df_aux = self.table.copy()  # get copy
        df_aux = df_aux[["Id", "Name", "Alias"]].copy()  # filter
        self.set_table(dataframe=df_aux1)  # restore uncleaned table
        ##### df_aux = self.table[["Id", "Name", "Alias"]].copy()

        # store copy of raster
        grid_raster = raster_sample.grid
        varname = raster_sample.varname
        # collect statistics
        lst_stats = []
        for i in range(len(df_aux)):
            n_id = df_aux["Id"].values[i]
            # apply mask
            grid_aoi = 1 * (self.grid == n_id)
            raster_sample.apply_aoi_mask(grid_aoi=grid_aoi, inplace=True)
            # get basic stats
            raster_uni = Univar(data=raster_sample.get_grid_data(), name=varname)
            df_stats = raster_uni.assess_basic_stats()
            lst_stats.append(df_stats.copy())
            # restore
            raster_sample.grid = grid_raster

        # create empty fields
        lst_stats_field = []
        for k in df_stats["Statistic"]:
            s_field = "{}_{}".format(varname, k)
            lst_stats_field.append(s_field)
            df_aux[s_field] = 0.0

        # fill values
        for i in range(len(df_aux)):
            df_aux.loc[i, lst_stats_field[0] : lst_stats_field[-1]] = lst_stats[i][
                "Value"
            ].values

        # handle count
        if skip_count:
            df_aux = df_aux.drop(columns=["{}_count".format(varname)])
            lst_stats_field.remove("{}_count".format(varname))

        # handle merge
        if merge:
            for k in lst_stats_field:
                self.table[k] = df_aux[k].values

        return df_aux

    def get_aoi(self, by_value_id):
        """
        Get the AOI map from a specific value id (value is expected to exist in the raster)
        :param by_value_id: category id value
        :type by_value_id: int
        :return: AOI map
        :rtype: :class:`AOI` object
        """
        map_aoi = AOI(name="{} {}".format(self.varname, by_value_id))
        map_aoi.set_asc_metadata(metadata=self.asc_metadata)
        map_aoi.prj = self.prj
        # set grid
        self.insert_nodata()
        map_aoi.set_grid(grid=1 * (self.grid == by_value_id))
        self.mask_nodata()
        return map_aoi

    def get_metadata(self):
        """Get all metadata from base_object

        :return: metadata
        :rtype: dict
        """
        _dict = super().get_metadata()
        _dict["Path_CSV"] = self.path_csvfile
        return _dict

    def _set_view_specs(self):
        """
        Get default view specs
        :return: None
        :rtype: None
        """
        if self.table is None:
            pass
        else:
            from matplotlib.colors import ListedColormap

            # handle no color field in table:
            if self.colorfield in self.table.columns:
                pass
            else:
                self.set_random_colors()

            # hack for non-continuous ids:
            _all_ids = np.arange(0, self.table[self.idfield].max() + 1)
            _lst_colors = []
            for i in range(0, len(_all_ids)):
                _df = self.table.query("{} >= {}".format(self.idfield, i)).copy()
                _color = _df[self.colorfield].values[0]
                _lst_colors.append(_color)
            # setup
            self.view_specs = {
                "color": "tab:grey",
                "cmap": ListedColormap(_lst_colors),
                "suptitle": "{} ({}) | {}".format(
                    self.varname, self.varalias, self.name
                ),
                "a_title": "{} Map ({})".format(self.varalias, self.units),
                "b_title": "{} Prevalence".format(self.varalias),
                "c_title": "Metadata",
                "width": 8,
                "height": 5,
                "b_area": "km2",
                "b_xlabel": "Area",
                "b_xmax": None,
                "bars_alias": True,
                "vmin": 0,
                "vmax": self.table[self.idfield].max(),
                "gs_rows": 7,
                "gs_cols": 5,
                "gs_b_rowlim": 4,
                "legend_x": 0.4,
                "legend_y": 0.3,
                "legend_ncol": 1,
                "suffix": None,
            }
        return None

    def view(
        self,
        show=True,
        folder="./output",
        filename=None,
        dpi=150,
        fig_format="jpg",
        filter=False,
        n_filter=6,
    ):
        """Plot a basic pannel of qualitative raster map.

        :param show: option to show plot instead of saving, defaults to False
        :type show: bool
        :param folder: path_main to output folder, defaults to ``./output``
        :type folder: str
        :param filename: name of file, defaults to None
        :type filename: str
        :param dpi: image resolution, defaults to 96
        :type dpi: int
        :param fig_format: image fig_format (ex: png or jpg). Default jpg
        :type fig_format: str
        :param filter: option for collapsing to n classes max (create "other" class)
        :type filter: bool
        :param n_filter: number of total classes + others
        :type n_filter: int
        :return: None
        :rtype: None
        """
        from matplotlib.patches import Patch

        # pass specs
        specs = self.view_specs

        if specs["suffix"] is None:
            suff = ""
        else:
            suff = "_{}".format(specs["suffix"])

        # -----------------------------------------------
        # ensure areas are computed
        df_aux = pd.merge(
            self.table[["Id", "Color"]], self.get_areas(), how="left", on="Id"
        )
        df_aux = df_aux.sort_values(by="{}_m2".format(self.areafield), ascending=True)
        if filter:
            if len(df_aux) > n_filter:
                n_limit = df_aux["{}_m2".format(self.areafield)].values[-n_filter]
                df_aux2 = df_aux.query("{}_m2 < {}".format(self.areafield, n_limit))
                df_aux2 = pd.DataFrame(
                    {
                        "Id": [0],
                        "Color": ["tab:grey"],
                        "Name": ["Others"],
                        "Alias": ["etc"],
                        "Cell_count": [df_aux2["Cell_count"].sum()],
                        "{}_m2".format(self.areafield): [
                            df_aux2["{}_m2".format(self.areafield)].sum()
                        ],
                        "{}_ha".format(self.areafield): [
                            df_aux2["{}_ha".format(self.areafield)].sum()
                        ],
                        "{}_km2".format(self.areafield): [
                            df_aux2["{}_km2".format(self.areafield)].sum()
                        ],
                        "{}_f".format(self.areafield): [
                            df_aux2["{}_f".format(self.areafield)].sum()
                        ],
                        "{}_%".format(self.areafield): [
                            df_aux2["{}_%".format(self.areafield)].sum()
                        ],
                    }
                )
                df_aux = df_aux.query("{}_m2 >= {}".format(self.areafield, n_limit))
                df_aux = pd.concat([df_aux, df_aux2])
                df_aux = df_aux.drop_duplicates(subset="Id")
                df_aux = df_aux.sort_values(by="{}_m2".format(self.areafield))
                df_aux = df_aux.reset_index(drop=True)

        # -----------------------------------------------
        # Deploy figure
        fig = plt.figure(figsize=(specs["width"], specs["height"]))  # Width, Height
        gs = mpl.gridspec.GridSpec(
            specs["gs_rows"],
            specs["gs_cols"],
            wspace=0.8,
            hspace=0.05,
            left=0.05,
            bottom=0.1,
            top=0.85,
            right=0.95,
        )
        fig.suptitle(specs["suptitle"] + suff)

        # plot map
        plt.subplot(gs[:5, :3])
        plt.title("a. {}".format(specs["a_title"]), loc="left")
        im = plt.imshow(
            self.grid, cmap=specs["cmap"], vmin=specs["vmin"], vmax=specs["vmax"]
        )
        plt.axis("off")

        # place legend
        legend_elements = []
        for i in range(len(df_aux)):
            _color = df_aux[self.colorfield].values[i]
            _label = "{} ({})".format(
                df_aux[self.namefield].values[i],
                df_aux[self.aliasfield].values[i],
            )
            legend_elements.append(
                Patch(
                    facecolor=_color,
                    label=_label,
                )
            )
        plt.legend(
            frameon=True,
            fontsize=9,
            markerscale=0.8,
            handles=legend_elements,
            bbox_to_anchor=(specs["legend_x"], specs["legend_y"]),
            bbox_transform=fig.transFigure,
            ncol=specs["legend_ncol"],
        )

        # -----------------------------------------------
        # plot horizontal bar of areas
        plt.subplot(gs[: specs["gs_b_rowlim"], 3:])
        plt.title("b. {}".format(specs["b_title"]), loc="left")
        if specs["bars_alias"]:
            s_bar_labels = self.aliasfield
        else:
            s_bar_labels = self.namefield
        plt.barh(
            df_aux[s_bar_labels],
            df_aux["{}_{}".format(self.areafield, specs["b_area"])],
            color=df_aux[self.colorfield],
        )

        # Add labels for each bar
        if specs["b_xmax"] is None:
            specs["b_xmax"] = df_aux[
                "{}_{}".format(self.areafield, specs["b_area"])
            ].max()
        for i in range(len(df_aux)):
            v = df_aux["{}_{}".format(self.areafield, specs["b_area"])].values[i]
            p = df_aux["{}_%".format(self.areafield)].values[i]
            plt.text(
                v + specs["b_xmax"] / 50,
                i - 0.3,
                "{:.1f} ({:.1f}%)".format(v, p),
                fontsize=9,
            )
        plt.xlim(0, 1.5 * specs["b_xmax"])
        plt.xlabel("{} (km$^2$)".format(specs["b_xlabel"]))
        plt.grid(axis="y")

        # -----------------------------------------------
        # plot metadata
        lst_meta = []
        lst_value = []
        for k in self.asc_metadata:
            lst_value.append(self.asc_metadata[k])
            lst_meta.append(k)
        df_meta = pd.DataFrame({"Raster": lst_meta, "Value": lst_value})
        # metadata
        n_y = 0.25
        n_x = 0.62
        plt.text(
            x=n_x,
            y=n_y,
            s="c. {}".format(specs["c_title"]),
            fontsize=12,
            transform=fig.transFigure,
        )
        n_y = n_y - 0.01
        n_step = 0.025
        for i in range(len(df_meta)):
            s_head = df_meta["Raster"].values[i]
            if s_head == "cellsize":
                s_value = self.cellsize
                s_line = "{:>15}: {:<10.5f}".format(s_head, s_value)
            else:
                s_value = df_meta["Value"].values[i]
                s_line = "{:>15}: {:<10.2f}".format(s_head, s_value)
            n_y = n_y - n_step
            plt.text(
                x=n_x,
                y=n_y,
                s=s_line,
                fontsize=9,
                fontdict={"family": "monospace"},
                transform=fig.transFigure,
            )

        # show or save
        if show:
            plt.show()
        else:
            if filename is None:
                filename = "{}_{}{}".format(self.varalias, self.name, suff)
            plt.savefig(
                "{}/{}{}.{}".format(folder, filename, suff, fig_format), dpi=dpi
            )
            plt.close(fig)
        return None


class LULC(QualiRaster):
    """
    Land Use and Land Cover map dataset
    """

    def __init__(self, name, date):
        """Initialize :class:`LULC` map

        :param name: name of map
        :type name: str
        :param date: date of map in ``yyyy-mm-dd``
        :type date: str
        """
        super().__init__(name, dtype="uint8")
        self.cmap = "tab20b"
        self.varname = "Land Use and Land Cover"
        self.varalias = "LULC"
        self.description = "Classes of Land Use and Land Cover"
        self.units = "classes ID"
        self.date = date


class LULCChange(QualiRaster):
    """
    Land Use and Land Cover Change map dataset
    """

    def __init__(self, name, date_start, date_end, name_lulc):
        """Initialize :class:`LULCChange` map

        :param name: name of map
        :type name: str
        :param date_start: date of map in ``yyyy-mm-dd``
        :type date_start: str
        :param date_end: date of map in ``yyyy-mm-dd``
        :type date_end: str
        :param name_lulc: name of lulc incoming map
        :type name_lulc: str
        """
        super().__init__(name, dtype="uint8")
        self.cmap = "tab20b"
        self.varname = "LULC Change"
        self.varalias = "LULCC"
        self.description = "Change of Land Use and Land Cover"
        self.units = "Change ID"
        self.date_start = date_start
        self.date_end = date_end
        self.date = date_end
        df_aux = pd.DataFrame(
            {
                self.idfield: [
                    1,
                    2,
                    3,
                ],
                self.namefield: ["Retraction", "Stable", "Expansion"],
                self.aliasfield: ["Rtr", "Stb", "Exp"],
                self.colorfield: ["tab:purple", "tab:orange", "tab:red"],
            }
        )
        self.set_table(dataframe=df_aux)


class Lithology(QualiRaster):
    """
    Lithology map dataset
    """

    def __init__(self, name="LitoMap"):
        """Initialize :class:`Lithology` map

        :param name:
        :type name:
        """
        super().__init__(name, dtype="uint8")
        self.cmap = "tab20c"
        self.varname = "Litological Domains"
        self.varalias = "Lito"
        self.description = "Litological outgcrop domains"
        self.units = "types ID"


class Soils(QualiRaster):
    """Soils map dataset"""

    def __init__(self, name="SoilsMap"):
        super().__init__(name, dtype="uint8")
        self.cmap = "tab20c"
        self.varname = "Soil Types"
        self.varalias = "Soils"
        self.description = "Types of Soils and Substrate"
        self.units = "types ID"

    def set_hydro_soils(self, map_lito, map_hand, map_slope, n_hand=2, n_slope=10):
        """Set hydrological soils based on lithology, Hand and Slope maps.

        :param map_lito: Lithology raster map
        :type map_lito: :class:`datasets.Lithology`
        :param map_hand: HAND raster map
        :type map_hand: :class:`datasets.HAND`
        :param map_slope: Slope raster map
        :type map_slope: :class:`datasets.Slope`
        :param n_hand: HAND threshold for alluvial definition
        :type n_hand: float
        :param n_slope: Slope threshold for colluvial definition
        :type n_slope: float
        :return: None
        :rtype: None
        """
        # process grid
        grd_soils = map_lito.grid.copy()
        # this assumes that there is less than 10 lito classes:
        grd_slopes = 10 * (map_slope.grid > n_slope)
        # append colluvial (+10)
        grd_soils = grd_soils + grd_slopes
        # append alluvial
        grd_soils = grd_soils * (map_hand.grid > n_hand)
        n_all_id = np.max(grd_soils) + 1
        grd_alluvial = n_all_id * (map_hand.grid <= n_hand)
        grd_soils = grd_soils + grd_alluvial
        self.set_grid(grid=grd_soils)

        # edit table
        # get table copy from lito
        df_table_res = map_lito.table[["Id", "Alias", "Name", "Color"]].copy()
        df_table_col = map_lito.table[["Id", "Alias", "Name", "Color"]].copy()
        #
        df_table_res["Name"] = "Residual " + df_table_res["Name"]
        df_table_res["Alias"] = "R" + df_table_res["Alias"]
        #
        df_table_col["Name"] = "Colluvial " + df_table_col["Name"]
        df_table_col["Alias"] = "C" + df_table_col["Alias"]
        df_table_col["Id"] = 10 + df_table_col["Id"].values
        # new soil table
        df_table_all = pd.DataFrame(
            {"Id": [n_all_id], "Alias": ["Alv"], "Name": ["Alluvial"], "Color": ["tan"]}
        )
        # append
        df_new = pd.concat([df_table_res, df_table_col], ignore_index=True)
        df_new = pd.concat([df_new, df_table_all], ignore_index=True)
        # set table
        self.set_table(dataframe=df_new)
        # set colors
        self.set_random_colors()
        # set more attributes
        self.prj = map_lito.prj
        self.set_asc_metadata(metadata=map_lito.asc_metadata)

        # reclassify
        df_new_table = self.table.copy()
        df_new_table["Id"] = [i for i in range(1, len(df_new_table) + 1)]
        dict_ids = {
            "Old_Id": self.table["Id"].values,
            "New_Id": df_new_table["Id"].values,
        }
        self.reclassify(dict_ids=dict_ids, df_new_table=df_new_table)
        return None


class QualiHard(QualiRaster):
    """
    A Quali-Hard is a hard-coded qualitative map (that is, the table is pre-set)
    """

    def __init__(self, name="qualihard"):
        super().__init__(name, dtype="uint8")
        self.varname = "QualiRasterHard"
        self.varalias = "QRH"
        self.description = "Preset Classes"
        self.units = "classes ID"
        self.set_table(dataframe=self.get_table())

    def get_table(self):
        df_aux = pd.DataFrame(
            {
                "Id": [1, 2, 3],
                "Alias": ["A", "B", "C"],
                "Name": ["Class A", "Class B", "Class C"],
                "Color": ["red", "green", "blue"],
            }
        )
        return df_aux

    def load(self, asc_file, prj_file=None):
        """Load data from files to raster

        :param asc_file: path_main to ``.asc`` raster file
        :type asc_file: str
        :param prj_file: path_main to ``.prj`` projection file
        :type prj_file: str
        :return: None
        :rtype: None
        """
        self.load_asc_raster(file=asc_file)
        if prj_file is None:
            # try to use the same path and name
            prj_file = asc_file.split(".")[0] + ".prj"
            if os.path.isfile(prj_file):
                self.load_prj_file(file=prj_file)
        else:
            self.load_prj_file(file=prj_file)
        return None


class AOI(QualiHard):
    """
    AOI map dataset
    """

    def __init__(self, name="AOIMap"):
        super().__init__(name)
        self.varname = "Area Of Interest"
        self.varalias = "AOI"
        self.description = "Boolean map an Area of Interest"
        self.units = "classes ID"
        self.set_table(dataframe=self.get_table())

    def get_table(self):
        df_aux = pd.DataFrame(
            {
                "Id": [1, 2],
                "Alias": ["AOI", "EZ"],
                "Name": ["Area of Interest", "Exclusion Zone"],
                "Color": ["magenta", "silver"],
            }
        )
        return df_aux

    def view(
        self,
        show=True,
        folder="./output",
        filename=None,
        dpi=150,
        fig_format="jpg",
    ):
        """Plot a basic pannel of raster map.

        :param show: boolean to show plot instead of saving, defaults to False
        :type show: bool
        :param folder: path_main to output folder, defaults to ``./output``
        :type folder: str
        :param filename: name of file, defaults to None
        :type filename: str
        :param dpi: image resolution, defaults to 96
        :type dpi: int
        :param fig_format: image fig_format (ex: png or jpg). Default jpg
        :type fig_format: str
        """
        map_aoi_aux = QualiRaster(name=self.name)

        # set up
        map_aoi_aux.varname = self.varname
        map_aoi_aux.varalias = self.varalias
        map_aoi_aux.units = self.units
        map_aoi_aux.set_table(dataframe=self.table)
        map_aoi_aux.view_specs = self.view_specs
        map_aoi_aux.set_asc_metadata(metadata=self.asc_metadata)
        map_aoi_aux.prj = self.prj

        # process grid
        self.insert_nodata()
        grd_new = 2 * np.ones(shape=self.grid.shape, dtype="byte")
        grd_new = grd_new - (1 * (self.grid == 1))
        self.mask_nodata()
        map_aoi_aux.set_grid(grid=grd_new)
        # this will call the view
        map_aoi_aux.view(
            show=show,
            folder=folder,
            filename=filename,
            dpi=dpi,
            fig_format=fig_format,
        )
        del map_aoi_aux
        return None


class LDD(QualiHard):
    """
    LDD - Local Drain Direction map dataset
    convention:

    7   8   9
    4   5   6
    1   2   3
    """

    def __init__(self, name="LDDMap"):
        super().__init__(name)
        self.varname = "Local Drain Direction"
        self.varalias = "LDD"
        self.description = "Direction of flux"
        self.units = "direction ID"
        self.set_table(dataframe=self.get_table())
        self.view_specs["legend_ncol"] = 2
        self.view_specs["legend_x"] = 0.5

    def get_table(self):
        df_aux = pd.DataFrame(
            {
                "Id": [1, 2, 3, 4, 5, 6, 7, 8, 9],
                "Alias": [
                    "1-SW",
                    "2-S",
                    "3-SE",
                    "4-W",
                    "5-C",
                    "6-E",
                    "7-NW",
                    "8-N",
                    "9-NE",
                ],
                "Name": [
                    "South-west",
                    "South",
                    "South-east",
                    "West",
                    "Center",
                    "East",
                    "North-west",
                    "North",
                    "North-east",
                ],
                "Color": [
                    "#8c564b",
                    "#9edae5",
                    "#98df8a",
                    "#dbdb8d",
                    "#d62728",
                    "#ff7f0e",
                    "#1f77b4",
                    "#f7b6d2",
                    "#98df8a",
                ],
            }
        )
        return df_aux


class Zones(QualiRaster):
    """
    Zones map dataset
    """

    def __init__(self, name="ZonesMap"):
        super().__init__(name, dtype="uint32")
        self.varname = "Zone"
        self.varalias = "ZN"
        self.description = "Ids map of zones"
        self.units = "zones ID"
        self.table = None

    def set_table(self):
        if self.grid is None:
            self.table = None
        else:
            self.insert_nodata()
            # get unique values
            vct_unique = np.unique(self.grid)
            # reapply mask
            self.mask_nodata()
            # set table
            self.table = pd.DataFrame(
                {
                    "Id": vct_unique,
                    "Alias": [
                        "{}{}".format(self.varalias, vct_unique[i])
                        for i in range(len(vct_unique))
                    ],
                    "Name": [
                        "{} {}".format(self.varname, vct_unique[i])
                        for i in range(len(vct_unique))
                    ],
                }
            )
            self.table = self.table.drop(
                self.table[self.table["Id"] == self.asc_metadata["NODATA_value"]].index
            )
            self.table["Id"] = self.table["Id"].astype(int)
            self.table = self.table.sort_values(by="Id")
            self.table = self.table.reset_index(drop=True)
            self.set_random_colors()
            # set view specs
            self._set_view_specs()
            # fix some view_specs:
            self.view_specs["b_xlabel"] = "zones ID"
            del vct_unique
            return None

    def set_grid(self, grid):
        super().set_grid(grid)
        self.set_table()
        return None

    def load(self, asc_file, prj_file):
        """
        Load data from files to raster
        :param asc_file: path_main to ``.asc`` raster file
        :type asc_file: str
        :param prj_file: path_main to ``.prj`` projection file
        :type prj_file: str
        :return: None
        :rtype: None
        """
        self.load_asc_raster(file=asc_file)
        self.load_prj_file(file=prj_file)
        return None

    def get_aoi(self, zone_id):
        """
        Get the AOI map from a zone id
        :param zone_id: number of zone ID
        :type zone_id: int
        :return: AOI map
        :rtype: :class:`AOI` object
        """
        map_aoi = AOI(name="{} {}".format(self.varname, zone_id))
        map_aoi.set_asc_metadata(metadata=self.asc_metadata)
        map_aoi.prj = self.prj
        # set grid
        self.insert_nodata()
        map_aoi.set_grid(grid=1 * (self.grid == zone_id))
        self.mask_nodata()
        return map_aoi

    def view(
        self,
        show=True,
        folder="./output",
        filename=None,
        specs=None,
        dpi=150,
        fig_format="jpg",
    ):
        """Plot a basic pannel of raster map.

        :param show: boolean to show plot instead of saving, defaults to False
        :type show: bool
        :param folder: path_main to output folder, defaults to ``./output``
        :type folder: str
        :param filename: name of file, defaults to None
        :type filename: str
        :param specs: specifications dictionary, defaults to None
        :type specs: dict
        :param dpi: image resolution, defaults to 96
        :type dpi: int
        :param fig_format: image fig_format (ex: png or jpg). Default jpg
        :type fig_format: str
        """
        # set Raster map for plotting
        map_zones_aux = Raster(name=self.name)
        # set up
        map_zones_aux.varname = self.varname
        map_zones_aux.varalias = self.varalias
        map_zones_aux.units = self.units
        map_zones_aux.set_asc_metadata(metadata=self.asc_metadata)
        map_zones_aux.prj = self.prj
        map_zones_aux.cmap = "tab20"

        # grid setup
        self.insert_nodata()
        map_zones_aux.set_grid(grid=self.grid)
        self.mask_nodata()
        map_zones_aux._set_view_specs()
        map_zones_aux.view_specs["vmin"] = self.table["Id"].min()
        map_zones_aux.view_specs["vmax"] = self.table["Id"].max()
        # update extra view specs:
        for k in self.view_specs:
            map_zones_aux.view_specs[k] = self.view_specs[k]
        # call view
        map_zones_aux.view(
            accum=False,
            show=show,
            folder=folder,
            filename=filename,
            dpi=dpi,
            fig_format=fig_format,
        )
        del map_zones_aux
        return None


# -----------------------------------------
# Raster Collection data structures


class RasterCollection(Collection):
    """
    The raster collection base dataset.
    This data strucute is designed for holding and comparing :class:`Raster` objects.
    """

    def __init__(self, name="myRasterCollection"):
        """Deploy the raster collection data structure.

        :param name: name of raster collection
        :type name: str
        """
        obj_aux = Raster()
        super().__init__(base_object=obj_aux, name=name)
        # set up date fields and special attributes
        self.catalog["Date"] = pd.to_datetime(self.catalog["Date"])

    def load(
        self,
        name,
        asc_file,
        prj_file=None,
        varname=None,
        varalias=None,
        units=None,
        date=None,
        dtype="float32",
        skip_grid=False,
    ):
        """Load a :class:`Raster` base_object from a ``.asc`` raster file.

        :param name: :class:`Raster.name` name attribute
        :type name: str
        :param asc_file: path_main to ``.asc`` raster file
        :type asc_file: str
        :param varname: :class:`Raster.varname` variable name attribute, defaults to None
        :type varname: str
        :param varalias: :class:`Raster.varalias` variable alias attribute, defaults to None
        :type varalias: str
        :param units: :class:`Raster.units` units attribute, defaults to None
        :type units: str
        :param date: :class:`Raster.date` date attribute, defaults to None
        :type date: str
        :param skip_grid: option for loading only the metadata
        :type skip_grid: bool
        """
        # create raster
        rst_aux = Raster(name=name, dtype=dtype)
        # set attributes
        rst_aux.varname = varname
        rst_aux.varalias = varalias
        rst_aux.units = units
        rst_aux.date = date
        # load prj file
        if prj_file is None:
            pass
        else:
            rst_aux.load_prj_file(file=prj_file)
        # read asc file
        if skip_grid:
            rst_aux.load_asc_metadata(file=asc_file)
        else:
            rst_aux.load_asc_raster(file=asc_file)
        # append to collection
        self.append(new_object=rst_aux)
        # delete aux
        del rst_aux
        return None

    def issamegrid(self):
        u_cols = len(self.catalog["ncols"].unique())
        u_rows = len(self.catalog["nrows"].unique())
        if u_cols == 1 and u_rows == 1:
            return True
        else:
            return False

    def reducer(
        self,
        reducer_function,
        reduction_name,
        extra_arg=None,
        skip_nan=False,
        talk=False,
    ):
        """This method reduces the collection by applying a numpy broadcasting function (example: np.mean)

        :param reducer_function: reducer numpy function (example: np.mean)
        :type reducer_function: numpy function
        :param reduction_name: name for the output raster
        :type reduction_name: str
        :param extra_arg: extra argument for function (example: np.percentiles) - Default: None
        :type extra_arg: any
        :param skip_nan: Option for skipping NaN values in map
        :type skip_nan: bool
        :param talk: option for printing messages
        :type talk: bool
        :return: raster object based on the first object found in the collection
        :rtype: :class:`Raster`
        """
        import copy

        # return None if there is different grids
        if self.issamegrid():
            # get shape parameters
            n = len(self.catalog)
            _first = self.catalog["Name"].values[0]
            n_flat = (
                self.collection[_first].grid.shape[0]
                * self.collection[_first].grid.shape[1]
            )

            # create the merged grid
            grd_merged = np.zeros(shape=(n, n_flat))
            # insert the flat arrays
            for i in range(n):
                _name = self.catalog["Name"].values[i]
                _vct_flat = self.collection[_name].grid.flatten()
                grd_merged[i] = _vct_flat
            # transpose
            grd_merged_T = grd_merged.transpose()

            # setup stats vector
            vct_stats = np.zeros(n_flat)
            # fill vector
            for i in range(n_flat):
                _vct = grd_merged_T[i]
                # remove NaN
                if skip_nan:
                    _vct = _vct[~np.isnan(_vct)]
                    # handle void vector
                    if len(_vct) == 0:
                        _vct = np.nan
                if extra_arg is None:
                    vct_stats[i] = reducer_function(_vct)
                else:
                    vct_stats[i] = reducer_function(_vct, extra_arg)

            # reshape
            grd_stats = np.reshape(
                a=vct_stats, newshape=self.collection[_first].grid.shape
            )
            # return set up
            output_raster = copy.deepcopy(self.collection[_first])
            output_raster.set_grid(grd_stats)
            output_raster.name = reduction_name
            return output_raster
        else:
            if talk:
                print("Warning: different grids found")
            return None

    def mean(self, skip_nan=False, talk=False):
        """Reduce Collection to the Mean raster

        :param skip_nan: Option for skipping NaN values in map
        :type skip_nan: bool
        :param talk: option for printing messages
        :type talk: bool
        :return: raster object based on the first object found in the collection
        :rtype: :class:`Raster`
        """
        output_raster = self.reducer(
            reducer_function=np.mean,
            reduction_name="{} Mean".format(self.name),
            skip_nan=skip_nan,
            talk=talk,
        )
        return output_raster

    def std(self, skip_nan=False, talk=False):
        """Reduce Collection to the Standard Deviation raster

        :param skip_nan: Option for skipping NaN values in map
        :type skip_nan: bool
        :param talk: option for printing messages
        :type talk: bool
        :return: raster object based on the first object found in the collection
        :rtype: :class:`Raster`
        """
        output_raster = self.reducer(
            reducer_function=np.std,
            reduction_name="{} SD".format(self.name),
            skip_nan=skip_nan,
            talk=talk,
        )
        return output_raster

    def min(self, skip_nan=False, talk=False):
        """Reduce Collection to the Min raster

        :param skip_nan: Option for skipping NaN values in map
        :type skip_nan: bool
        :param talk: option for printing messages
        :type talk: bool
        :return: raster object based on the first object found in the collection
        :rtype: :class:`Raster`
        """
        output_raster = self.reducer(
            reducer_function=np.min,
            reduction_name="{} Min".format(self.name),
            skip_nan=skip_nan,
            talk=talk,
        )
        return output_raster

    def max(self, skip_nan=False, talk=False):
        """Reduce Collection to the Max raster

        :param skip_nan: Option for skipping NaN values in map
        :type skip_nan: bool
        :param talk: option for printing messages
        :type talk: bool
        :return: raster object based on the first object found in the collection
        :rtype: :class:`Raster`
        """
        output_raster = self.reducer(
            reducer_function=np.max,
            reduction_name="{} Max".format(self.name),
            skip_nan=skip_nan,
            talk=talk,
        )
        return output_raster

    def sum(self, skip_nan=False, talk=False):
        """Reduce Collection to the Sum raster

        :param skip_nan: Option for skipping NaN values in map
        :type skip_nan: bool
        :param talk: option for printing messages
        :type talk: bool
        :return: raster object based on the first object found in the collection
        :rtype: :class:`Raster`
        """
        output_raster = self.reducer(
            reducer_function=np.sum,
            reduction_name="{} Sum".format(self.name),
            skip_nan=skip_nan,
            talk=talk,
        )
        return output_raster

    def percentile(self, percentile, skip_nan=False, talk=False):
        """Reduce Collection to the Nth Percentile raster

        :param percentile: Nth percentile (from 0 to 100)
        :type percentile: float
        :param skip_nan: Option for skipping NaN values in map
        :type skip_nan: bool
        :param talk: option for printing messages
        :type talk: bool
        :return: raster object based on the first object found in the collection
        :rtype: :class:`Raster`
        """
        output_raster = self.reducer(
            reducer_function=np.percentile,
            reduction_name="{} {}th percentile".format(self.name, str(percentile)),
            skip_nan=skip_nan,
            talk=talk,
            extra_arg=percentile,
        )
        return output_raster

    def median(self, skip_nan=False, talk=False):
        """Reduce Collection to the Median raster

        :param skip_nan: Option for skipping NaN values in map
        :type skip_nan: bool
        :param talk: option for printing messages
        :type talk: bool
        :return: raster object based on the first object found in the collection
        :rtype: :class:`Raster`
        """
        output_raster = self.reducer(
            reducer_function=np.median,
            reduction_name="{} Median".format(self.name),
            skip_nan=skip_nan,
            talk=talk,
        )
        return output_raster

    def get_collection_stats(self):
        """Get basic statistics from collection.

        :return: statistics data
        :rtype: :class:`pandas.DataFrame`
        """
        # deploy dataframe
        df_aux = self.catalog[["Name"]].copy()
        lst_stats = []
        for i in range(len(self.catalog)):
            s_name = self.catalog["Name"].values[i]
            print(s_name)
            df_stats = self.collection[s_name].get_grid_stats()
            lst_stats.append(df_stats.copy())
        # deploy fields
        for k in df_stats["Statistic"]:
            df_aux[k] = 0.0

        # fill values
        for i in range(len(df_aux)):
            df_aux.loc[i, "Count":"Max"] = lst_stats[i]["Value"].values
        # convert to integer
        df_aux["Count"] = df_aux["Count"].astype(dtype="uint32")
        return df_aux

    def get_views(self, show=True, folder="./output", dpi=300, fig_format="jpg"):
        """Plot all basic pannel of raster maps in collection.

        :param show: boolean to show plot instead of saving,
        :type show: bool
        :param folder: path_main to output folder, defaults to ``./output``
        :type folder: str
        :param dpi: image resolution, defaults to 96
        :type dpi: int
        :param fig_format: image fig_format (ex: png or jpg). Default jpg
        :type fig_format: str
        :return: None
        :rtype: None
        """

        # plot loop
        for k in self.collection:
            rst_lcl = self.collection[k]
            s_name = rst_lcl.name
            rst_lcl.view(
                show=show,
                folder=folder,
                filename=s_name,
                dpi=dpi,
                fig_format=fig_format,
            )
        return None

    def view_bboxes(
        self,
        colors=None,
        datapoints=False,
        show=True,
        folder="./output",
        filename=None,
        dpi=150,
        fig_format="jpg",
    ):
        """View Bounding Boxes of Raster collection

        :param colors: list of colors for plotting. expected to be the same runsize of catalog
        :type colors: list
        :param datapoints: option to plot datapoints as well, defaults to False
        :type datapoints: bool
        :param show: option to show plot instead of saving, defaults to False
        :type show: bool
        :param folder: path_main to output folder, defaults to ``./output``
        :type folder: str
        :param filename: name of file, defaults to None
        :type filename: str
        :param dpi: image resolution, defaults to 96
        :type dpi: int
        :param fig_format: image fig_format (ex: png or jpg). Default jpg
        :type fig_format: str
        :return: None
        :rtype: none
        """
        plt.style.use("seaborn-v0_8")
        fig = plt.figure(figsize=(5, 5))
        # get colors
        lst_colors = colors
        if colors is None:
            lst_colors = get_random_colors(size=len(self.catalog))
        # colect names and bboxes
        lst_x_values = list()
        lst_y_values = list()
        dct_bboxes = dict()
        dct_colors = dict()
        _c = 0
        for name in self.collection:
            dct_colors[name] = lst_colors[_c]
            lcl_bbox = self.collection[name].get_bbox()
            dct_bboxes[name] = lcl_bbox
            # append coordinates
            lst_x_values.append(lcl_bbox["xmin"])
            lst_x_values.append(lcl_bbox["xmax"])
            lst_y_values.append(lcl_bbox["ymin"])
            lst_y_values.append(lcl_bbox["ymax"])
            _c = _c + 1
        # get min and max
        n_xmin = np.min(lst_x_values)
        n_xmax = np.max(lst_x_values)
        n_ymin = np.min(lst_y_values)
        n_ymax = np.max(lst_y_values)
        # get ranges
        n_x_range = np.abs(n_xmax - n_xmin)
        n_y_range = np.abs(n_ymax - n_ymin)

        # plot loop
        for name in dct_bboxes:
            plt.scatter(
                dct_bboxes[name]["xmin"],
                dct_bboxes[name]["ymin"],
                marker="^",
                color=dct_colors[name],
            )
            if datapoints:
                df_dpoints = self.collection[name].get_grid_datapoints(drop_nan=False)
                plt.scatter(
                    df_dpoints["x"], df_dpoints["y"], color=dct_colors[name], marker="."
                )
            _w = dct_bboxes[name]["xmax"] - dct_bboxes[name]["xmin"]
            _h = dct_bboxes[name]["ymax"] - dct_bboxes[name]["ymin"]
            rect = plt.Rectangle(
                xy=(dct_bboxes[name]["xmin"], dct_bboxes[name]["ymin"]),
                width=_w,
                height=_h,
                alpha=0.5,
                label=name,
                color=dct_colors[name],
            )
            plt.gca().add_patch(rect)
        plt.ylim(n_ymin - (n_y_range / 3), n_ymax + (n_y_range / 3))
        plt.xlim(n_xmin - (n_x_range / 3), n_xmax + (n_x_range / 3))
        plt.gca().set_aspect("equal")
        plt.legend()

        # show or save
        if show:
            plt.show()
        else:
            if filename is None:
                filename = "bboxes"
            plt.savefig("{}/{}.{}".format(folder, filename, fig_format), dpi=dpi)
        plt.close(fig)
        return None


class QualiRasterCollection(RasterCollection):
    """
    The raster collection base dataset.

    This data strucute is designed for holding and comparing :class:`QualiRaster` objects.
    """

    def __init__(self, name):
        """Deploy Qualitative Raster Series

        :param name: :class:`RasterSeries.name` name attribute
        :type name: str
        :param varname: :class:`Raster.varname` variable name attribute, defaults to None
        :type varname: str
        :param varalias: :class:`Raster.varalias` variable alias attribute, defaults to None
        :type varalias: str
        """
        super().__init__(name=name)

    def load(self, name, asc_file, prj_file=None, table_file=None):
        """Load a :class:`QualiRaster` base_object from ``.asc`` raster file.

        :param name: :class:`Raster.name` name attribute
        :type name: str
        :param asc_file: path_main to ``.asc`` raster file
        :type asc_file: str
        :param prj_file: path_main to ``.prj`` projection file
        :type prj_file: str
        :param table_file: path_main to ``.txt`` table file
        :type table_file: str
        """
        # create raster
        rst_aux = QualiRaster(name=name)
        # read file
        rst_aux.load_asc_raster(file=asc_file)
        # load prj
        if prj_file is None:
            pass
        else:
            rst_aux.load_prj_file(file=prj_file)
        # set table
        if table_file is None:
            pass
        else:
            rst_aux.load_table(file=table_file)
        # append to collection
        self.append(new_object=rst_aux)
        # delete aux
        del rst_aux
        return None


class RasterSeries(RasterCollection):
    """A :class:`RasterCollection` where date matters and all maps in collections are
    expected to be the same variable, same projection and same grid.
    """

    def __init__(self, name, varname, varalias, units, dtype="float32"):
        """Deploy RasterSeries

        :param name: :class:`RasterSeries.name` name attribute
        :type name: str
        :param varname: :class:`Raster.varname` variable name attribute, defaults to None
        :type varname: str
        :param varalias: :class:`Raster.varalias` variable alias attribute, defaults to None
        :type varalias: str
        :param units: :class:`Raster.units` units attribute, defaults to None
        :type units: str
        """
        super().__init__(name=name)
        self.varname = varname
        self.varalias = varalias
        self.units = units
        self.dtype = dtype

    def load(self, name, date, asc_file, prj_file=None):
        """Load a :class:`Raster` base_object from a ``.asc`` raster file.

        :param name: :class:`Raster.name` name attribute
        :type name: str
        :param date: :class:`Raster.date` date attribute, defaults to None
        :type date: str
        :param asc_file: path_main to ``.asc`` raster file
        :type asc_file: str
        :param prj_file: path_main to ``.prj`` projection file
        :type prj_file: str
        :return: None
        :rtype: None
        """
        # create raster
        rst_aux = Raster(name=name, dtype=self.dtype)
        # set attributes
        rst_aux.varname = self.varname
        rst_aux.varalias = self.varalias
        rst_aux.units = self.units
        rst_aux.date = date
        # read file
        rst_aux.load_asc_raster(file=asc_file)
        # append to collection
        self.append(new_object=rst_aux)
        # load prj file
        if prj_file is None:
            pass
        else:
            rst_aux.load_prj_file(file=prj_file)
        # delete aux
        del rst_aux
        return None

    def load_folder(self, folder, name_pattern="map_*", talk=False):
        """Load all rasters from a folder by following a name pattern. Date is expected to be at the end of name before file extension.

        :param folder: path_main to folder
        :type folder: str
        :param name_pattern: name pattern. example map_*
        :type name_pattern: str
        :param talk: option for printing messages
        :type talk: bool
        :return: None
        :rtype: None
        """
        #
        lst_maps = glob.glob("{}/{}.asc".format(folder, name_pattern))
        lst_prjs = glob.glob("{}/{}.prj".format(folder, name_pattern))
        if talk:
            print("loading folder...")
        for i in range(len(lst_maps)):
            asc_file = lst_maps[i]
            prj_file = lst_prjs[i]
            # get name
            s_name = os.path.basename(asc_file).split(".")[0]
            # get dates
            s_date_map = asc_file.split("_")[-1].split(".")[0]
            s_date_prj = prj_file.split("_")[-1].split(".")[0]
            # load
            self.load(
                name=s_name,
                date=s_date_map,
                asc_file=asc_file,
                prj_file=prj_file,
            )
        self.update(details=True)
        return None

    def apply_aoi_masks(self, grid_aoi, inplace=False):
        """Batch method to apply AOI mask over all maps in collection

        :param grid_aoi: aoi grid
        :type grid_aoi: :class:`numpy.ndarray`
        :param inplace: overwrite the main grid if True, defaults to False
        :type inplace: bool
        :return: None
        :rtype: None
        """
        for name in self.collection:
            self.collection[name].apply_aoi_mask(grid_aoi=grid_aoi, inplace=inplace)
        return None

    def release_aoi_masks(self):
        """Batch method to release the AOI mask over all maps in collection

        :return: None
        :rtype: None
        """
        for name in self.collection:
            self.collection[name].release_aoi_mask()
        return None

    def rebase_grids(self, base_raster, talk=False):
        """Batch method for rebase all maps in collection

        :param base_raster: base raster for rebasing
        :type base_raster: :class:`datasets.Raster`
        :param talk: option for print messages
        :type talk: bool
        :return: None
        :rtype: None
        """
        if talk:
            print("rebase grids...")
        for name in self.collection:
            self.collection[name].rebase_grid(base_raster=base_raster, inplace=True)
        self.update(details=True)
        return None

    def get_series_stats(self):
        """Get the raster series statistics

        :return: dataframe of raster series statistics
        :rtype: :class:`pandas.DataFrame`
        """
        df_stats = self.get_collection_stats()
        df_series = pd.merge(
            self.catalog[["Name", "Date"]], df_stats, how="left", on="Name"
        )
        return df_series

    def get_views(
        self,
        show=True,
        folder="./output",
        view_specs=None,
        dpi=300,
        fig_format="jpg",
        talk=False,
    ):
        """Plot all basic pannel of raster maps in collection.

        :param show: boolean to show plot instead of saving, defaults to False
        :type show: bool
        :param folder: path_main to output folder, defaults to ``./output``
        :type folder: str
        :param view_specs: specifications dictionary, defaults to None
        :type view_specs: dict
        :param dpi: image resolution, defaults to 96
        :type dpi: int
        :param fig_format: image fig_format (ex: png or jpg). Default jpg
        :type fig_format: str
        :param talk: option for print messages
        :type talk: bool
        :return: None
        :rtype: None
        """

        # get stats
        df_stats = self.get_collection_stats()
        n_vmin = df_stats["Min"].max()
        n_vmax = df_stats["Max"].max()

        # plot loop
        for k in self.collection:
            rst_lcl = self.collection[k]
            s_name = rst_lcl.name
            if talk:
                print("plotting view of {}...".format(s_name))

            # handle specs
            rst_lcl.view_specs["vmin"] = n_vmin
            rst_lcl.view_specs["vmax"] = n_vmax
            rst_lcl.view_specs["hist_vmax"] = 0.05
            if view_specs is None:
                pass
            else:
                # overwrite incoming specs
                for k in view_specs:
                    rst_lcl.view_specs[k] = view_specs[k]
            # plot
            rst_lcl.view(
                show=show,
                folder=folder,
                filename=s_name,
                dpi=dpi,
                fig_format=fig_format,
            )
        return None

    def view_series_stats(
        self,
        statistic="Mean",
        folder="./output",
        filename=None,
        specs=None,
        show=True,
        dpi=150,
        fig_format="jpg",
    ):
        """View raster series statistics

        :param statistic: statistc to view. Default mean
        :type statistic: str
        :param show: option to show plot instead of saving, defaults to False
        :type show: bool
        :param folder: path_main to output folder, defaults to ``./output``
        :type folder: str
        :param filename: name of file, defaults to None
        :type filename: str
        :param specs: specifications dictionary, defaults to None
        :type specs: dict
        :param dpi: image resolution, defaults to 96
        :type dpi: int
        :param fig_format: image fig_format (ex: png or jpg). Default jpg
        :type fig_format: str
        :return: None
        :rtype: None
        """
        df_series = self.get_series_stats()
        ts = DailySeries(
            name=self.name, varname="{}_{}".format(self.varname, statistic)
        )
        ts.set_data(dataframe=df_series, varfield=statistic, datefield="Date")
        default_specs = {
            "suptitle": "{} | {} {} series".format(self.name, self.varname, statistic),
            "ylabel": self.units,
        }
        if specs is None:
            specs = default_specs
        else:
            # overwrite incoming specs
            for k in default_specs:
                specs[k] = default_specs[k]
        ts.view(
            show=show,
            folder=folder,
            filename=filename,
            specs=specs,
            dpi=dpi,
            fig_format=fig_format,
        )
        return None


class NDVISeries(RasterSeries):
    def __init__(self, name):
        # instantiate raster sample
        rst_aux = NDVI(name="dummy", date=None)
        super().__init__(
            name=name,
            varname=rst_aux.varname,
            varalias=rst_aux.varalias,
            units=rst_aux.units,
            dtype=rst_aux.dtype,
        )
        # remove
        del rst_aux

    def load(self, name, date, asc_file, prj_file):
        """Load a :class:`NDVI` base_object from a ``.asc`` raster file.

        :param name: :class:`Raster.name` name attribute
        :type name: str
        :param date: :class:`Raster.date` date attribute, defaults to None
        :type date: str
        :param asc_file: path_main to ``.asc`` raster file
        :type asc_file: str
        :param prj_file: path_main to ``.prj`` projection file
        :type prj_file: str
        :return: None
        :rtype: None
        """
        # create raster
        rst_aux = NDVI(name=name, date=date)
        # read file
        rst_aux.load_asc_raster(file=asc_file)
        # append to collection
        self.append(new_object=rst_aux)
        # load prj file
        rst_aux.load_prj_file(file=prj_file)
        # delete aux
        del rst_aux
        return None


class ETSeries(RasterSeries):
    def __init__(self, name):
        # instantiate raster sample
        rst_aux = ET24h(name="dummy", date=None)
        super().__init__(
            name=name,
            varname=rst_aux.varname,
            varalias=rst_aux.varalias,
            units=rst_aux.units,
            dtype=rst_aux.dtype,
        )
        # remove
        del rst_aux

    def load(self, name, date, asc_file, prj_file):
        """Load a :class:`ET24h` base_object from a ``.asc`` raster file.

        :param name: :class:`Raster.name` name attribute
        :type name: str
        :param date: :class:`Raster.date` date attribute, defaults to None
        :type date: str
        :param asc_file: path_main to ``.asc`` raster file
        :type asc_file: str
        :param prj_file: path_main to ``.prj`` projection file
        :type prj_file: str
        :return: None
        :rtype: None
        """
        # create raster
        rst_aux = ET24h(name=name, date=date)
        # read file
        rst_aux.load_asc_raster(file=asc_file)
        # append to collection
        self.append(new_object=rst_aux)
        # load prj file
        rst_aux.load_prj_file(file=prj_file)
        # delete aux
        del rst_aux
        return None


class QualiRasterSeries(RasterSeries):
    """A :class:`RasterSeries` where date matters and all maps in collections are
    expected to be :class:`QualiRaster` with the same variable, same projection and same grid.
    """

    def __init__(self, name, varname, varalias, dtype="uint8"):
        """Deploy Qualitative Raster Series

        :param name: :class:`RasterSeries.name` name attribute
        :type name: str
        :param varname: :class:`Raster.varname` variable name attribute, defaults to None
        :type varname: str
        :param varalias: :class:`Raster.varalias` variable alias attribute, defaults to None
        :type varalias: str
        """
        super().__init__(
            name=name, varname=varname, varalias=varalias, dtype=dtype, units="ID"
        )
        self.table = None

    def update_table(self, clear=True):
        """Update series table (attributes)
        :param clear: option for clear table from unfound values. default: True
        :type clear: bool
        :return: None
        :rtype: None
        """
        if len(self.catalog) == 0:
            pass
        else:
            for i in range(len(self.catalog)):
                _name = self.catalog["Name"].values[i]
                # clear table from unfound values
                if clear:
                    self.collection[_name].clear_table()
                # concat all tables
                if i == 0:
                    self.table = self.collection[_name].table.copy()
                else:
                    self.table = pd.concat(
                        [self.table, self.collection[_name].table.copy()]
                    )
        # clear from duplicates
        self.table = self.table.drop_duplicates(subset="Id", keep="last")
        self.table = self.table.reset_index(drop=True)
        return None

    def append(self, raster):
        """Append a :class:`Raster` base_object to collection. Pre-existing objects with the same :class:`Raster.name` attribute are replaced

        :param raster: incoming :class:`Raster` to append
        :type raster: :class:`Raster`
        """
        super().append(new_object=raster)
        self.update_table()
        return None

    def load(self, name, date, asc_file, prj_file=None, table_file=None):
        """Load a :class:`QualiRaster` base_object from ``.asc`` raster file.

        :param name: :class:`Raster.name` name attribute
        :type name: str
        :param date: :class:`Raster.date` date attribute
        :type date: str
        :param asc_file: path_main to ``.asc`` raster file
        :type asc_file: str
        :param prj_file: path_main to ``.prj`` projection file
        :type prj_file: str
        :param table_file: path_main to ``.txt`` table file
        :type table_file: str
        """
        # create raster
        rst_aux = QualiRaster(name=name)
        # set attributes
        rst_aux.date = date
        # read file
        rst_aux.load_asc_raster(file=asc_file)
        # load prj
        if prj_file is None:
            pass
        else:
            rst_aux.load_prj_file(file=prj_file)
        # set table
        if table_file is None:
            pass
        else:
            rst_aux.load_table(file=table_file)
        # append to collection
        self.append(new_object=rst_aux)
        # delete aux
        del rst_aux

    def load_folder(self, folder, table_file, name_pattern="map_*", talk=False):
        """Load all rasters from a folder by following a name pattern. Date is expected to be at the end of name before file extension.

        :param folder: path_main to folder
        :type folder: str
        :param table_file: path_main to table file
        :type table_file: str
        :param name_pattern: name pattern. example map_*
        :type name_pattern: str
        :param talk: option for printing messages
        :type talk: bool
        :return: None
        :rtype: None
        """
        #
        lst_maps = glob.glob("{}/{}.asc".format(folder, name_pattern))
        lst_prjs = glob.glob("{}/{}.prj".format(folder, name_pattern))
        if talk:
            print("loading folder...")
        for i in range(len(lst_maps)):
            asc_file = lst_maps[i]
            prj_file = lst_prjs[i]
            # get name
            s_name = os.path.basename(asc_file).split(".")[0]
            # get dates
            s_date_map = asc_file.split("_")[-1].split(".")[0]
            s_date_prj = prj_file.split("_")[-1].split(".")[0]
            # load
            self.load(
                name=s_name,
                date=s_date_map,
                asc_file=asc_file,
                prj_file=prj_file,
                table_file=table_file,
            )
        return None

    def get_series_areas(self):
        """Get areas prevalance for all series

        :return: dataframe of series areas
        :rtype: :class:`pandas.DataFrame`
        """
        # compute areas for each raster
        for i in range(len(self.catalog)):
            s_raster_name = self.catalog["Name"].values[i]
            s_raster_date = self.catalog["Date"].values[i]
            # compute
            df_areas = self.collection[s_raster_name].get_areas()
            # insert name and date fields
            df_areas.insert(loc=0, column="Name_raster", value=s_raster_name)
            df_areas.insert(loc=1, column="Date", value=s_raster_date)
            # concat dataframes
            if i == 0:
                df_areas_full = df_areas.copy()
            else:
                df_areas_full = pd.concat([df_areas_full, df_areas])
        df_areas_full["Name"] = df_areas_full["Name"].astype("category")
        df_areas_full["Date"] = pd.to_datetime(df_areas_full["Date"])
        return df_areas_full

    def view_series_areas(
        self,
        specs=None,
        show=True,
        folder="./output",
        filename=None,
        dpi=150,
        fig_format="jpg",
    ):
        """View series areas

        :param specs: specifications dictionary, defaults to None
        :type specs: dict
        :param show: option to show plot instead of saving, defaults to False
        :type show: bool
        :param folder: path_main to output folder, defaults to ``./output``
        :type folder: str
        :param filename: name of file, defaults to None
        :type filename: str
        :param dpi: image resolution, defaults to 96
        :type dpi: int
        :param fig_format: image fig_format (ex: png or jpg). Default jpg
        :type fig_format: str
        :return: None
        :rtype: None
        """
        plt.style.use("seaborn-v0_8")
        # get specs
        default_specs = {
            "suptitle": "{} | Area Series".format(self.name),
            "width": 5 * 1.618,
            "height": 5,
            "ylabel": "Area prevalence (%)",
            "ylim": (0, 100),
            "legend_x": 0.85,
            "legend_y": 0.33,
            "legend_ncol": 3,
            "filter_by_id": None,  # list of ids
        }
        # handle input specs
        if specs is None:
            pass
        else:  # override default
            for k in specs:
                default_specs[k] = specs[k]
        specs = default_specs

        # compute areas
        df_areas = self.get_series_areas()

        # Deploy figure
        fig = plt.figure(figsize=(specs["width"], specs["height"]))  # Width, Height
        gs = mpl.gridspec.GridSpec(
            3, 1, wspace=0.5, hspace=0.9, left=0.1, bottom=0.1, top=0.9, right=0.95
        )
        fig.suptitle(specs["suptitle"])

        # start plotting
        plt.subplot(gs[0:2, 0])
        for i in range(len(self.table)):
            # get attributes
            _id = self.table["Id"].values[i]
            _name = self.table["Name"].values[i]
            _alias = self.table["Alias"].values[i]
            _color = self.table["Color"].values[i]
            if specs["filter_by_id"] == None:
                # filter series
                _df = df_areas.query("Id == {}".format(_id)).copy()
                plt.plot(_df["Date"], _df["Area_%"], color=_color, label=_name)
            else:
                if _id in specs["filter_by_id"]:
                    # filter series
                    _df = df_areas.query("Id == {}".format(_id)).copy()
                    plt.plot(_df["Date"], _df["Area_%"], color=_color, label=_name)
                else:
                    pass
        plt.legend(
            frameon=True,
            fontsize=9,
            markerscale=0.8,
            bbox_to_anchor=(specs["legend_x"], specs["legend_y"]),
            bbox_transform=fig.transFigure,
            ncol=specs["legend_ncol"],
        )
        plt.xlim(df_areas["Date"].min(), df_areas["Date"].max())
        plt.ylabel(specs["ylabel"])
        plt.ylim(specs["ylim"])

        # show or save
        if show:
            plt.show()
        else:
            if filename is None:
                filename = "{}_{}".format(self.varalias, self.name)
            plt.savefig("{}/{}.{}".format(folder, filename, fig_format), dpi=dpi)
        plt.close(fig)
        return None

    def get_views(
        self,
        show=True,
        filter=False,
        n_filter=6,
        folder="./output",
        view_specs=None,
        dpi=300,
        fig_format="jpg",
        talk=False,
    ):
        """Plot all basic pannel of raster maps in collection.

        :param show: boolean to show plot instead of saving, defaults to False
        :type show: bool
        :param folder: path_main to output folder, defaults to ``./output``
        :type folder: str
        :param view_specs: specifications dictionary, defaults to None
        :type view_specs: dict
        :param dpi: image resolution, defaults to 96
        :type dpi: int
        :param fig_format: image fig_format (ex: png or jpg). Default jpg
        :type fig_format: str
        :param talk: option for print messages
        :type talk: bool
        :return: None
        :rtype: None
        """

        # plot loop
        for k in self.collection:
            rst_lcl = self.collection[k]
            s_name = rst_lcl.name
            if talk:
                print("plotting view of {}...".format(s_name))
            if view_specs is None:
                pass
            else:
                # overwrite incoming specs
                for k in view_specs:
                    rst_lcl.view_specs[k] = view_specs[k]
            # plot
            rst_lcl.view(
                show=show,
                folder=folder,
                filename=s_name,
                dpi=dpi,
                fig_format=fig_format,
                filter=filter,
                n_filter=n_filter,
            )
        return None


class LULCSeries(QualiRasterSeries):
    """
    A :class:`QualiRasterSeries` for holding Land Use and Land Cover maps
    """

    def __init__(self, name):
        # instantiate raster sample
        rst_aux = LULC(name="dummy", date=None)
        super().__init__(
            name=name,
            varname=rst_aux.varname,
            varalias=rst_aux.varalias,
            dtype=rst_aux.dtype,
        )
        # remove
        del rst_aux

    def load(self, name, date, asc_file, prj_file=None, table_file=None):
        """Load a :class:`LULCRaster` base_object from ``.asc`` raster file.

        :param name: :class:`Raster.name` name attribute
        :type name: str
        :param date: :class:`Raster.date` date attribute
        :type date: str
        :param asc_file: path_main to ``.asc`` raster file
        :type asc_file: str
        :param prj_file: path_main to ``.prj`` projection file
        :type prj_file: str
        :param table_file: path_main to ``.txt`` table file
        :type table_file: str
        :return: None
        :rtype: None
        """
        # create raster
        rst_aux = LULC(name=name, date=date)
        # read file
        rst_aux.load_asc_raster(file=asc_file)
        # load prj
        if prj_file is None:
            pass
        else:
            rst_aux.load_prj_file(file=prj_file)
        # set table
        if table_file is None:
            pass
        else:
            rst_aux.load_table(file=table_file)
        # append to collection
        self.append(raster=rst_aux)
        # delete aux
        del rst_aux
        return None

    def get_lulcc(self, date_start, date_end, by_lulc_id):
        """Get the :class:`LULCChange` of a given time interval and LULC class Id

        :param date_start: start date of time interval
        :type date_start: str
        :param date_end: end date of time interval
        :type date_end: str
        :param by_lulc_id: LULC class Id
        :type by_lulc_id: int
        :return: map of LULC Change
        :rtype: :class:`LULCChange`
        """
        # set up
        s_name_start = self.catalog.loc[self.catalog["Date"] == date_start][
            "Name"
        ].values[
            0
        ]  #
        s_name_end = self.catalog.loc[self.catalog["Date"] == date_end]["Name"].values[
            0
        ]

        # compute lulc change grid
        grd_lulcc = (1 * (self.collection[s_name_end].grid == by_lulc_id)) - (
            1 * (self.collection[s_name_start].grid == by_lulc_id)
        )
        grd_all = (1 * (self.collection[s_name_end].grid == by_lulc_id)) + (
            1 * (self.collection[s_name_start].grid == by_lulc_id)
        )
        grd_all = 1 * (grd_all > 0)
        grd_lulcc = (grd_lulcc + 2) * grd_all

        # get names
        s_name = self.name
        s_name_lulc = self.table.loc[self.table["Id"] == by_lulc_id]["Name"].values[0]
        # instantiate
        map_lulc_change = LULCChange(
            name="{} of {} from {} to {}".format(
                s_name, s_name_lulc, date_start, date_end
            ),
            name_lulc=s_name_lulc,
            date_start=date_start,
            date_end=date_end,
        )
        map_lulc_change.set_grid(grid=grd_lulcc)
        map_lulc_change.set_asc_metadata(
            metadata=self.collection[s_name_start].asc_metadata
        )
        map_lulc_change.prj = self.collection[s_name_start].prj

        return map_lulc_change

    def get_lulcc_series(self, by_lulc_id):
        """Get the :class:`QualiRasterSeries` of LULC Change for the entire LULC series for a given LULC Id

        :param by_lulc_id: LULC class Id
        :type by_lulc_id: int
        :return: Series of LULC Change
        :rtype: :class:`QualiRasterSeries`
        """
        series_lulcc = QualiRasterSeries(
            name="{} - Change Series".format(self.name),
            varname="Land Use and Land Cover Change",
            varalias="LULCC",
        )
        # loop in catalog
        for i in range(1, len(self.catalog)):
            raster = self.get_lulcc(
                date_start=self.catalog["Date"].values[i - 1],
                date_end=self.catalog["Date"].values[i],
                by_lulc_id=by_lulc_id,
            )
            series_lulcc.append(raster=raster)
        return series_lulcc

    def get_conversion_matrix(self, date_start, date_end, talk=False):
        """Compute the conversion matrix, expansion matrix and retraction matrix for a given interval

        :param date_start: start date of time interval
        :type date_start: str
        :param date_end: end date of time interval
        :type date_end: str
        :param talk: option for printing messages
        :type talk: bool
        :return: dict of outputs
        :rtype: dict
        """
        # get dates
        s_date_start = date_start
        s_date_end = date_end
        # get raster names
        s_name_start = self.catalog.loc[self.catalog["Date"] == date_start][
            "Name"
        ].values[
            0
        ]  #
        s_name_end = self.catalog.loc[self.catalog["Date"] == date_end]["Name"].values[
            0
        ]

        # compute areas
        df_areas_start = self.collection[s_name_start].get_areas()
        df_areas_end = self.collection[s_name_end].get_areas()
        # deploy variables
        df_conv = self.table.copy()
        df_conv["Date_start"] = s_date_start
        df_conv["Date_end"] = s_date_end
        df_conv["Area_f_start"] = df_areas_start["Area_f"].values
        df_conv["Area_f_end"] = df_areas_end["Area_f"].values
        df_conv["Area_km2_start"] = df_areas_start["Area_km2"].values
        df_conv["Area_km2_end"] = df_areas_end["Area_km2"].values

        lst_cols = list()
        for i in range(len(df_conv)):
            _alias = df_conv["Alias"].values[i]
            s_field = "to_{}_f".format(_alias)
            df_conv[s_field] = 0.0
            lst_cols.append(s_field)

        if talk:
            print("processing...")

        grd_conv = np.zeros(shape=(len(df_conv), len(df_conv)))
        for i in range(len(df_conv)):
            _id = df_conv["Id"].values[i]
            #
            # instantiate new LULC map
            map_lulc = LULC(name="Conversion", date=s_date_end)
            map_lulc.set_grid(grid=self.collection[s_name_end].grid)
            map_lulc.set_asc_metadata(
                metadata=self.collection[s_name_start].asc_metadata
            )
            map_lulc.set_table(dataframe=self.collection[s_name_start].table)
            map_lulc.prj = self.collection[s_name_start].prj
            #
            # apply aoi
            grd_aoi = 1 * (self.collection[s_name_start].grid == _id)
            map_lulc.apply_aoi_mask(grid_aoi=grd_aoi, inplace=True)
            #
            # bypass all-masked aois
            if np.sum(map_lulc.grid) is np.ma.masked:
                grd_conv[i] = np.zeros(len(df_conv))
            else:
                df_areas = map_lulc.get_areas()
                grd_conv[i] = df_areas["{}_f".format(map_lulc.areafield)].values

        # append to dataframe
        grd_conv = grd_conv.transpose()
        for i in range(len(df_conv)):
            df_conv[lst_cols[i]] = grd_conv[i]

        # get expansion matrix
        grd_exp = np.zeros(shape=grd_conv.shape)
        for i in range(len(grd_exp)):
            grd_exp[i] = df_conv["Area_f_start"].values * df_conv[lst_cols[i]].values
        np.fill_diagonal(grd_exp, 0)

        # get retraction matrix
        grd_rec = np.zeros(shape=grd_conv.shape)
        for i in range(len(grd_rec)):
            grd_rec[i] = df_conv["Area_f_start"].values[i] * grd_conv.transpose()[i]
        np.fill_diagonal(grd_rec, 0)

        return {
            "Dataframe": df_conv,
            "Conversion_Matrix": grd_conv,
            "Conversion_index": np.prod(np.diagonal(grd_conv)),
            "Expansion_Matrix": grd_exp,
            "Retraction_Matrix": grd_rec,
            "Date_start": date_start,
            "Date_end": date_end,
        }


if __name__ == "__main__":
    plt.style.use("seaborn-v0_8")
    # f = "C:/data/p_1.csv"
    # df = pd.read_csv(f, sep=";", parse_dates=["Date"])
    # df = df.query("Date >= '2017-01-01'")
    # df.to_csv(f, sep=";", index=False)

    dict_f = {
        0: ["C:/data/p_1.csv", "second"],
        1: ["C:/data/p_2.csv", "minute"],
        2: ["C:/data/p_3.csv", "day"],
    }
    f = 0

    ts = TimeSeries(name="MyTS", varname="Precipitation", varfield="P", units="mm")
    ts.load_data(
        input_file=dict_f[f][0],
        input_dtfield="Date",
        input_varfield="P_PVG42_mm",
        input_dtres=dict_f[f][1],
    )

    ts.standardize()
    print(ts.data.head(10))

    ts.fill_gaps(method="linear", inplace=True)
    print(ts.data.head(10))

    ts.view(show=True)
