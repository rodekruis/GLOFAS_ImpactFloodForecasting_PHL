"""Interface for running CLIMADA's fluvial flood model.

This module defines a single high‑level function that takes event
discharge values (and their associated return periods) and produces
flood depth rasters over the basin using the CLIMADA fluvial flood
module. You will need to install and configure CLIMADA separately –
this repository does not ship the CLIMADA library. See the
documentation of CLIMADA for details.

This file does not implement the flood model itself; it wraps
CLIMADA's existing functions and ensures that inputs and outputs
conform to our project's data structures.  For now, the function
returns placeholder objects and logs what it would do.

Example::

    from philflood.hazard.climada_driver import run_flood_hazard
    depths = run_flood_hazard(discharge, return_period, basin_cfg)

"""

from __future__ import annotations

from typing import Any

import logging
import numpy as np
import xarray as xr

from ..basin import BasinConfig
from ..data.hazard_extractor import load_jrc_flood_hazard_layer

logger = logging.getLogger(__name__)


def run_flood_hazard(
    discharge: float,
    return_period: float,
    basin: BasinConfig,
) -> xr.DataArray:
    """Run the CLIMADA fluvial flood module for a single event.

    Parameters
    ----------
    discharge : float
        Peak discharge (m³/s) for the event at the representative
        GloFAS point of the basin.
    return_period : float
        Return period (years) corresponding to the event discharge.  If
        you compute return periods via the EVT model, you should pass
        the appropriate value here.
    basin : BasinConfig
        Basin configuration specifying where data are stored.

    Returns
    -------
    xarray.DataArray
        Raster of flood depths (metres) across the basin.  When
        CLIMADA is not available, a placeholder DataArray of zeros is
        returned.

    Notes
    -----
    A typical implementation will call CLIMADA's hazard interface::

        from climada.engine import RiverFlood
        hazard = RiverFlood().from_discharge(discharge, return_period, ...)

    Then convert the hazard into an xarray.DataArray.  Here we leave
    that part unimplemented and return an empty array with the same
    shape as the JRC hazard layer for the requested return period.
    """
    # Attempt to load a JRC hazard layer to get dimensions
    try:
        base_layer = load_jrc_flood_hazard_layer(basin, int(return_period))
        shape = base_layer.shape
        coords = base_layer.coords
    except Exception as exc:
        logger.warning("Failed to load JRC hazard layer: %s", exc)
        shape = (100, 100)
        coords = {
            "lat": np.linspace(0, 1, shape[0]),
            "lon": np.linspace(0, 1, shape[1]),
        }
    # Placeholder: zero depths everywhere
    data = np.zeros(shape, dtype=np.float32)
    da = xr.DataArray(data, coords=coords, dims=list(coords.keys()))
    logger.info(
        "run_flood_hazard called with discharge=%.2f, RP=%.2f for basin %s",
        discharge,
        return_period,
        basin.basin_id,
    )
    return da