"""Utility functions to load GloFAS discharge data for calibration and monitoring.

These helpers hide the details of file formats and storage locations. For
calibration, you will typically load a long historical time series of
daily discharge at one or more GloFAS locations. For monitoring, you
will load forecast ensembles at multiple lead times. Currently these
functions assume that NetCDF files are stored locally under
``<basin.data_root>/glofas/``; you can adapt them to fetch data from
remote APIs if needed.

Example usage::

    from philflood.data.glofas_extractor import load_glofas_reanalysis_for_basin
    from philflood.config import load_basin_config

    cfg = load_basin_config("ops/configs/basins/example_basin.yaml")
    series = load_glofas_reanalysis_for_basin(cfg, "1980-01-01", "2020-12-31")

"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import xarray as xr

from ..basin import BasinConfig


def load_glofas_reanalysis_for_basin(
    basin: BasinConfig,
    start_date: str | dt.date,
    end_date: str | dt.date,
    source: str = "local",
) -> pd.DataFrame:
    """Load GloFAS reanalysis discharge time series for the given basin.

    Parameters
    ----------
    basin : BasinConfig
        Basin configuration specifying which GloFAS point IDs to use and
        where to find the data.
    start_date, end_date : str or date
        Start and end of the time period to load.  Should span the
        calibration period (decades).
    source : str, optional
        Data source, currently only ``"local"`` is supported.  If you
        implement a remote download, add options here.

    Returns
    -------
    pandas.DataFrame
        DataFrame indexed by datetime with one column per
        ``glofas_point_id``.  Missing data are represented by NaN.

    Notes
    -----
    This function currently expects that NetCDF files follow a naming
    convention like ``<data_root>/glofas/reanalysis_<point_id>.nc``.  You
    will need to adapt this function to your local file organisation.  For
    examples of NetCDF operations with xarray, see the calibration
    notebooks.
    """
    # Parse dates
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)
    if start > end:
        raise ValueError("start_date must be before end_date")
    # Placeholder: currently returns an empty DataFrame with correct index
    index = pd.date_range(start=start, end=end, freq="D")
    df = pd.DataFrame(index=index)
    for station in basin.glofas_point_ids:
        # In a real implementation, open the NetCDF file and extract the
        # discharge time series.  Use xarray to read and convert to pandas.
        # ds = xr.open_dataset(path_to_file)
        # ts = ds['discharge'].sel(time=slice(start, end)).to_pandas()
        # df[station] = ts
        df[station] = np.nan  # placeholder column
    return df


def load_glofas_forecast_for_basin(
    basin: BasinConfig,
    issue_date: str | dt.date,
    lead_days: int = 15,
    source: str = "local",
) -> xr.Dataset:
    """Load GloFAS ensemble forecast for a given basin and issue date.

    Parameters
    ----------
    basin : BasinConfig
        Basin configuration with point IDs and data_root set.
    issue_date : str or date
        Date on which the forecast was issued.  Forecast lead times are
        counted forward from this date.
    lead_days : int, optional
        Number of lead days to load.  The default of 15 days matches
        typical Start Ready horizons.  Extend if needed.
    source : str, optional
        Data source, currently only ``"local"`` is supported.

    Returns
    -------
    xarray.Dataset
        Dataset with dimensions (ensemble_member, time, station).

    Notes
    -----
    A complete implementation should read ensemble forecasts from
    NetCDF files or call the GloFAS API.  The returned dataset should
    be ready for use in the hazard module without further processing.
    """
    # Placeholder: return an empty xarray dataset
    dates = pd.date_range(
        pd.to_datetime(issue_date), periods=lead_days, freq="D"
    )
    stations = basin.glofas_point_ids
    # Example: 51 ensemble members as used in ECMWF forecasts
    n_members = 51
    data = np.full((n_members, len(dates), len(stations)), np.nan)
    ds = xr.Dataset(
        {"discharge": ("ensemble", "time", "station", data)},
        coords={
            "ensemble": np.arange(n_members),
            "time": dates,
            "station": stations,
        },
    )
    return ds