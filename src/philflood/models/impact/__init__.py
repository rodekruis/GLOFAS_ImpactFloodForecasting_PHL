"""Impact modelling subpackage.

This package contains modules for computing flood impacts on
populations and fitting impact‑based extreme value models.  These
modules were extracted from the calibration notebooks to provide
reusable building blocks for the calibration and monitoring pipelines.

Submodules
----------
impact_evt
    Functions for fitting Peaks‑Over‑Threshold (POT) models to impact
    severity data and mapping impact values to return periods.

population_exposure
    Utilities for aggregating affected population by administrative
    regions given flood depth rasters and population maps.
"""

from . import impact_evt  # noqa: F401
from . import population_exposure  # noqa: F401