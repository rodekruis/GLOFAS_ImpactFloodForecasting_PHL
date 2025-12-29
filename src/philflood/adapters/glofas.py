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

from ..domain.basin import BasinConfig


def load_glofas_reanalysis_for_basin(
    basin: BasinConfig,
    start_date: str | dt.date,
    end_date: str | dt.date,
    source: str = "local",
) -> pd.DataFrame:
    """Load GloFAS reanalysis discharge time series for the given basin.

    This helper attempts to read pre‑extracted discharge time series for
    the stations listed in ``basin.glofas_point_ids``.  The preferred
    workflow is to first convert the raw GloFAS GRIB/NetCDF files into
    a tidy table (e.g. Parquet or CSV) during calibration.  The
    resulting file should be stored under ``<basin.data_root>/glofas/timeseries/``
    with a name like ``<basin_id>__discharge.parquet``.  During
    operational monitoring, you should not recompute the time series
    from scratch on the fly.  If no pre‑extracted file is available the
    function falls back to the legacy behaviour of returning an empty
    DataFrame with the appropriate index.

    Parameters
    ----------
    basin : BasinConfig
        Basin configuration specifying which GloFAS point IDs to use and
        where to find the data (``basin.data_root``).
    start_date, end_date : str or date
        Start and end of the time period to load.  Strings will be
        parsed by ``pandas.to_datetime``.  The start date must not
        exceed the end date.
    source : str, optional
        Currently only ``"local"`` is supported.  Future versions may
        implement remote downloads via the Copernicus API.

    Returns
    -------
    pandas.DataFrame
        DataFrame indexed by datetime with one column per GloFAS
        station.  If data are not available for a given station the
        column contains NaNs.  If no extracted file is found an
        empty DataFrame with the correct date index is returned.
    """
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)
    if start > end:
        raise ValueError("start_date must be before end_date")
    # Build an empty date index covering the requested period
    index = pd.date_range(start=start, end=end, freq="D")
    # Prepare empty DataFrame with all stations
    df = pd.DataFrame(index=index)
    for station in basin.glofas_point_ids:
        df[station] = np.nan
    # Only support local source at present
    if source != "local":
        raise NotImplementedError(
            f"Unsupported source '{source}'. Only 'local' is implemented."
        )
    # Determine the data root.  If not set in the config, default to the
    # current working directory.  Accept both strings and Path objects.
    data_root = basin.data_root or Path(".")
    data_root = Path(data_root)
    # Construct the expected path for the pre‑extracted time series
    # The file name convention is <basin_id>__discharge.parquet
    ts_dir = data_root / "glofas" / "timeseries"
    ts_path_parquet = ts_dir / f"{basin.basin_id}__discharge.parquet"
    ts_path_csv = ts_dir / f"{basin.basin_id}__discharge.csv"
    # Try to load a Parquet file first
    if ts_path_parquet.is_file():
        try:
            ts_df = pd.read_parquet(ts_path_parquet)
        except Exception:
            ts_df = None
    elif ts_path_csv.is_file():
        try:
            ts_df = pd.read_csv(ts_path_csv, parse_dates=True, index_col=0)
        except Exception:
            ts_df = None
    else:
        ts_df = None
    if ts_df is not None:
        # Ensure the index is datetime and sorted
        if not isinstance(ts_df.index, pd.DatetimeIndex):
            ts_df.index = pd.to_datetime(ts_df.index)
        ts_df = ts_df.sort_index()
        # Subset to the requested date range
        ts_subset = ts_df.loc[(ts_df.index >= start) & (ts_df.index <= end)]
        # Reindex onto the full daily index to fill any missing days
        ts_subset = ts_subset.reindex(index)
        # If the file contains more stations than requested, filter
        for col in ts_subset.columns:
            if col not in df.columns:
                df[col] = np.nan
        df.update(ts_subset)
        return df
    # No extracted file found; return empty DataFrame with NaNs
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