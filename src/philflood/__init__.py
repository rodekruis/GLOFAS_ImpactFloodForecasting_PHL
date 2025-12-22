"""Top-level package for the Philippines Flood Trigger project.

This package contains modular code to support both calibration and operational
components of a riverine flood impact forecasting and trigger system. The
functions are organised by domain (EVT, hazard, impact, risk, etc.) to make
the library easy to extend and maintain.  Users of this package should import
from these modules rather than directly from the notebooks.

Example::

    from philflood.ev.peaks_over_threshold import extract_declust_pot
    from philflood.basin import BasinConfig

    # load a configured basin
    cfg = load_basin_config("ops/configs/basins/example_basin.yaml")

    # extract and decluster peaks
    peaks = extract_declust_pot(series, cfg.evt.threshold_m3s, cfg.evt.run_length_days)

"""

__all__ = [
    "config",
    "basin",
    "data",
    "ev",
    "hazard",
    "impact",
    "risk",
    "ops",
]