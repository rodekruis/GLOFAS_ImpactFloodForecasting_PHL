"""PhilFlood utilities for impact-based flood triggers.

This patch adds a reproducible EVT/POT calibration workflow (GloFAS v4 GRIB -> daily discharge
-> virtual gauges -> POT extraction -> Poisson rate lambda).

All geometry is assumed to be in EPSG:4326 (WGS84).
"""

__all__ = [
    "utils",
    "geo",
    "adapters",
    "calibration",
    "qc",
]
