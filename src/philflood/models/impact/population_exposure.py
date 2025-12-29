"""Load and manipulate population exposure data.

Exposure functions in this module handle reading population rasters
(e.g. WorldPop, GHS‑POP) and sampling them onto the same grid as the
hazard maps.  This separation allows you to swap the exposure
dataset by editing the basin or country configuration without
changing the rest of the code.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import xarray as xr

from ..basin import BasinConfig


def load_population_grid(basin: BasinConfig) -> xr.DataArray:
    """Load a population grid for the basin.

    Parameters
    ----------
    basin : BasinConfig
        Basin configuration with a `data_root` pointing to population
        datasets.  You can define different exposure datasets at the
        country level and override them per basin if needed.

    Returns
    -------
    xarray.DataArray
        Population counts per raster cell.  Dimensions should match
        those of the hazard depths so that elementwise operations are
        possible.

    Notes
    -----
    This placeholder returns a small constant array.  In practice you
    should read a GeoTIFF or NetCDF file from
    ``<data_root>/exposure/population.tif`` or similar, reproject it
    and regrid it to match the hazard coordinates.  The calibration
    notebooks contain examples of how to use ``rasterio`` and
    ``xarray`` for this purpose.
    """
    # Placeholder: return a 100x100 array with uniform population
    data = np.ones((100, 100), dtype=np.int32)
    da = xr.DataArray(data, dims=["lat", "lon"])
    return da