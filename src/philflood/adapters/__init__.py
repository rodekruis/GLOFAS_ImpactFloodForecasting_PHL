"""Data access layer.

This subpackage contains helper functions for retrieving datasets used in
the calibration and operational phases. By encapsulating file I/O here,
the rest of the code remains clean and easy to test. If you need to
support other storage backends (e.g. S3, Google Cloud Storage), you
should extend these modules accordingly.

Note: Legacy adapters (glofas.py, climada_river.py, hazard_maps.py) have been
archived in _archive/. Use glofas_grib_v4 for current GloFAS data access.
The streaming helper is available as glofas_grib_streaming for low-memory runs.
"""

__all__ = [
    "glofas_grib_v4",
    "glofas_grib_streaming",
]