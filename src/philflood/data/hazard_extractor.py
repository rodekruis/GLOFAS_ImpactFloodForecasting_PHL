"""Helpers to load static hazard layers and catchment boundaries.

The hazard mapping process requires several inputs: HydroBASINS
geometries to delineate basins, global river flood hazard maps (e.g.
JRC GFM) and potentially other ancillary layers such as digital
elevation models or flood defences.  This module centralises access
to those resources so that the rest of the code can assume they are
available in a consistent format.

At minimum you will need to place a GeoJSON or shapefile for each
HydroBASINS level and the relevant flood hazard layers in a known
location under each basin's `data_root`.  You can adapt this to use
online services or remote storage when appropriate.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import geopandas as gpd
import xarray as xr

from ..basin import BasinConfig


def load_hydrobasins_geometry(
    basin: BasinConfig, level: Optional[int] = None
) -> gpd.GeoDataFrame:
    """Load the HydroBASINS geometry for the specified basin.

    Parameters
    ----------
    basin : BasinConfig
        Configuration containing the HydroBASINS identifier and level.
    level : int, optional
        HydroBASINS level to use.  If None, use the level defined in
        the basin configuration.

    Returns
    -------
    geopandas.GeoDataFrame
        A GeoDataFrame containing at least a geometry column
        representing the basin polygon.

    Notes
    -----
    The file path is assumed to be
    ``<data_root>/hydrobasins/level_<L>/hydrobasins_level_<L>.gpkg`` or
    similar.  You may need to adjust the pattern in your own
    implementation.
    """
    level = basin.hydrobasins_level if level is None else level
    # Placeholder path: adapt to your local storage scheme
    path = (
        Path(basin.data_root or ".")
        / "hydrobasins"
        / f"level_{level}"
        / f"hydrobasins_level_{level}.gpkg"
    )
    if not path.exists():
        raise FileNotFoundError(
            f"HydroBASINS file not found for level {level}: {path}"
        )
    gdf = gpd.read_file(path)
    # Filter by HydroBASINS ID
    return gdf[gdf["HYBAS_ID"] == basin.hydrobasins_id]


def load_jrc_flood_hazard_layer(
    basin: BasinConfig, return_period: int
) -> xr.DataArray:
    """Load a JRC Global Flood Model depth layer for a specific return period.

    Parameters
    ----------
    basin : BasinConfig
        Basin configuration with `data_root` pointing to hazard layers.
    return_period : int
        Return period (in years) for the depth layer (e.g. 10, 100).

    Returns
    -------
    xarray.DataArray
        A raster array of flood depths (metres) covering the basin.

    Notes
    -----
    The file naming convention is assumed to be
    ``<data_root>/hazard/jrc_gfm_depth_rp<RP>.nc``.  This should be
    updated to reflect your actual storage.  The function reads the
    entire file, but you could optimise to subset only the basin
    extent when needed.
    """
    path = (
        Path(basin.data_root or ".")
        / "hazard"
        / f"jrc_gfm_depth_rp{return_period}.nc"
    )
    if not path.exists():
        raise FileNotFoundError(
            f"JRC hazard file not found for RP{return_period}: {path}"
        )
    da = xr.open_dataarray(path)
    return da