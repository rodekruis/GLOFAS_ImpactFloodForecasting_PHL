"""Operational trigger evaluation.

This subpackage contains minimal code to run the calibrated trigger in
near real time.  The code here should avoid heavy computation and
should never modify calibration parameters.  It reads basin
configuration files, fetches forecast data via the data extractors,
computes hazard and impact using the calibrated settings, and applies
the trigger rule.  Results can then be formatted for dashboards or
messages.
"""

__all__ = ["monitoring"]