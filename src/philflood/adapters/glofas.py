#!/usr/bin/env python3
"""Download GloFAS historical discharge data via the Copernicus Data API.

This utility wraps the ``cdsapi`` client to automate downloading of
yearly subsets from the ``cems-glofas-historical`` dataset.  It is
designed to simplify bulk retrieval of the GloFAS v4.0 hydrological
reanalysis for a particular spatial bounding box.  Files are stored
under a deterministic directory structure and extracted on the fly to
facilitate subsequent processing.

**Important prerequisites**

* Install the ``cdsapi`` Python package (``pip install cdsapi``).
* Create a ``.cdsapirc`` file with your Copernicus Data Store API key
  and ensure it points to the EWDS endpoint:

  .. code-block:: yaml

     url: https://ewds.climate.copernicus.eu/api
     key: <uid>:<api-key>

  By default the cdsapi will look for this file in your home directory.
  You can override this by setting the ``CDSAPI_RC`` environment
  variable.
* Accept the licence for ``cems-glofas-historical`` via the CDS web
  interface (https://cds.climate.copernicus.eu) before running.

Example
-------

.. code-block:: bash

    python -m philflood.scripts.download_glofas_historical \
        --area "18.7,120.6,15.6,122.6" \
        --start-year 1979 --end-year 2025 \
        --output data/raw

This will download discharge data for the Cagayan basin bounding box
into ``data/raw/glofas/historical/version_4_0/consolidated/discharge/grib2/``.

"""
from __future__ import annotations
import argparse
import random
import time
import zipfile
from pathlib import Path
from typing import List

import cdsapi


def parse_bbox(area_str: str) -> List[float]:
    """Parse a bounding box string of the form "N,W,S,E".

    Parameters
    ----------
    area_str : str
        Comma‑separated list of four numbers in the order north, west,
        south, east.  Note that the Copernicus API uses this order.

    Returns
    -------
    list of float
        Parsed values as a list ``[north, west, south, east]``.
    """
    parts = [p.strip() for p in area_str.split(",")]
    if len(parts) != 4:
        raise ValueError(
            f"Area must have four comma‑separated values (got {len(parts)})"
        )
    return [float(p) for p in parts]


def is_valid_zip(path: Path) -> bool:
    """Check whether a path exists and is a valid ZIP archive."""
    if not path.exists() or path.stat().st_size == 0:
        return False
    try:
        with zipfile.ZipFile(path, "r") as zf:
            # Attempt to list a few entries to verify structure
            _ = zf.namelist()[:1]
        return True
    except Exception:
        return False


def retrieve_with_retries(
    client: cdsapi.Client, dataset: str, request: dict, target: Path, max_attempts: int = 5
) -> None:
    """Perform a CDS API request with simple retry/backoff logic.

    In case of transient network errors or server overload, the CDS API
    may fail sporadically.  This helper wraps ``client.retrieve`` and
    retries the request a few times with exponential backoff and jitter.

    Parameters
    ----------
    client : cdsapi.Client
        The CDS API client to use for retrieval.
    dataset : str
        Identifier of the dataset (e.g. ``"cems-glofas-historical"``).
    request : dict
        The request payload as defined in the CDS API documentation.
    target : Path
        Local path to write the downloaded file to.
    max_attempts : int, optional
        Maximum number of retrieval attempts.  Defaults to 5.
    """
    last_err: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            client.retrieve(dataset, request, str(target))
            return
        except Exception as exc:
            last_err = exc
            sleep_seconds = min(120, 5 * attempt) + random.uniform(0.0, 2.0)
            print(
                f"[Attempt {attempt}/{max_attempts}] CDS API error: {exc}\n"
                f"Retrying in {sleep_seconds:.1f} seconds..."
            )
            time.sleep(sleep_seconds)
    # If we exit the loop without returning, raise the last error
    raise last_err  # type: ignore[arg-type]


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Download GloFAS historical discharge data for a bounding box and year range "
            "from the cems-glofas-historical dataset."
        )
    )
    parser.add_argument(
        "--area",
        required=True,
        help="Bounding box in 'north,west,south,east' order (degrees).",
    )
    parser.add_argument(
        "--start-year",
        type=int,
        required=True,
        help="First year of data to download (inclusive).",
    )
    parser.add_argument(
        "--end-year",
        type=int,
        required=True,
        help="Last year of data to download (inclusive).",
    )
    parser.add_argument(
        "--output",
        default="data/raw",
        type=str,
        help=(
            "Root directory into which downloads should be placed.  Files will "
            "be organised under <output>/glofas/historical/<version>/<product_type>/discharge/grib2/"
        ),
    )
    parser.add_argument(
        "--system-version",
        default="version_4_0",
        type=str,
        help="GloFAS system version (e.g. 'version_4_0').",
    )
    parser.add_argument(
        "--product-type",
        default="consolidated",
        type=str,
        help="Product type (e.g. 'consolidated').",
    )
    parser.add_argument(
        "--hydrological-model",
        default="lisflood",
        type=str,
        help="Hydrological model (e.g. 'lisflood').",
    )
    parser.add_argument(
        "--variable",
        default="river_discharge_in_the_last_24_hours",
        type=str,
        help="Variable name to request (default: river discharge).",
    )
    parser.add_argument(
        "--dataset",
        default="cems-glofas-historical",
        type=str,
        help="Dataset identifier (default: cems-glofas-historical).",
    )
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=5,
        help="Maximum number of retries for each file download.",
    )
    parser.add_argument(
        "--extract",
        action="store_true",
        help="If set, extract the ZIP file into a year‑specific subdirectory after download."
        ,
    )
    args = parser.parse_args()

    # Parse bounding box
    area = parse_bbox(args.area)

    # Determine output directory
    base_dir = Path(args.output) / "glofas" / "historical" / args.system_version / args.product_type / "discharge" / "grib2" / (
        f"area_{area[0]}_{area[1]}_{area[2]}_{area[3]}"
    )
    base_dir.mkdir(parents=True, exist_ok=True)

    # Instantiate CDS API client
    client = cdsapi.Client()

    # Precompute months and days for the request (1..12 and 1..31)
    months = [f"{m:02d}" for m in range(1, 13)]
    days = [f"{d:02d}" for d in range(1, 32)]

    # Loop over years
    for year in range(args.start_year, args.end_year + 1):
        target_zip = base_dir / (
            f"glofas_historical_{args.system_version}_{args.product_type}_{args.variable}_{year}.zip"
        )
        # Skip if a valid ZIP file already exists
        if is_valid_zip(target_zip):
            print(f"✓ {year} already downloaded; skipping")
            continue

        # If an invalid or partial file exists, remove it before retrying
        if target_zip.exists():
            print(f"⚠ Removing incomplete or corrupt file for {year}: {target_zip.name}")
            try:
                target_zip.unlink()
            except Exception:
                pass

        # Build the CDS request for this year
        request = {
            "system_version": [args.system_version],
            "hydrological_model": [args.hydrological_model],
            "product_type": [args.product_type],
            "variable": [args.variable],
            "hyear": [str(year)],
            "hmonth": months,
            "hday": days,
            "data_format": "grib2",
            "download_format": "zip",
            "area": area,
        }
        print(f"↓ Downloading {year} to {target_zip.name}")
        try:
            retrieve_with_retries(
                client=client,
                dataset=args.dataset,
                request=request,
                target=target_zip,
                max_attempts=args.max_attempts,
            )
        except Exception as err:
            print(f"❌ Failed to download {year}: {err}")
            continue
        print(
            f"✓ Downloaded {year} ({target_zip.stat().st_size / 1e6:.1f} MB)"
        )
        # Optionally extract the archive
        if args.extract:
            extract_dir = base_dir / str(year)
            extract_dir.mkdir(parents=True, exist_ok=True)
            try:
                with zipfile.ZipFile(target_zip, "r") as zf:
                    zf.extractall(extract_dir)
                print(f"↳ Extracted {year} to {extract_dir}")
            except Exception as exc:
                print(f"⚠ Failed to extract {target_zip.name}: {exc}")


if __name__ == "__main__":
    main()

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