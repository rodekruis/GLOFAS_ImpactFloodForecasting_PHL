"""Impact modelling utilities.

Functions in this subpackage convert flood hazard maps into estimates
of people affected.  They handle exposure data loading, application of
vulnerability curves and aggregation to spatial units (e.g. sub‑
catchments or administrative boundaries).  These functions should be
pure, meaning they do not perform file I/O; instead they accept
inputs (depth rasters, exposure grids, configuration objects) and
return data structures ready for further analysis.
"""

__all__ = [
    "population_exposure",
    "vulnerability",
]