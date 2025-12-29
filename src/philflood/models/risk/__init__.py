"""Risk metrics and trigger logic.

This subpackage contains functions to build risk curves (AEP, OEP) from
synthetic impact databases and to derive operational trigger
thresholds.  These functions operate on pandas DataFrames or simple
data structures and avoid file I/O.  They can therefore be tested
independently of the data extraction and modelling layers.
"""

__all__ = ["aep_oep", "trigger_design"]