"""Data access layer.

This subpackage contains helper functions for retrieving datasets used in
the calibration and operational phases. By encapsulating file I/O here,
the rest of the code remains clean and easy to test. If you need to
support other storage backends (e.g. S3, Google Cloud Storage), you
should extend these modules accordingly.
"""

__all__ = [
    "glofas_extractor",
    "hazard_extractor",
]