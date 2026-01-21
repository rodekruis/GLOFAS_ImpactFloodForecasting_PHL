"""Peak extraction and declustering for peaks‑over‑threshold (POT) analysis.

The peaks over threshold method requires careful treatment of dependence
in the original time series. This module provides a function to
extract independent exceedances from a pandas Series. The result is a
Series containing only the cluster maxima above the specified
threshold.

This module provides a thin wrapper around the implementation in
``philflood.models.ev.threshold_analysis``.  The function defined here
delegates to :func:`philflood.models.ev.threshold_analysis.extract_declust_pot` to
perform declustering.  It is kept for backwards compatibility and
maintains the same signature.
"""

from __future__ import annotations

from typing import Optional

import pandas as pd

# Import the actual implementation from the threshold_analysis module.
from .threshold_analysis import extract_declust_pot as _impl


def extract_declust_pot(
    series: pd.Series,
    threshold: float,
    run_length_days: int = 5,
) -> pd.Series:
    """Extract independent peaks above a threshold from a time series.

    Parameters
    ----------
    series : pandas.Series
        A time series of discharge (or any hydrological variable) indexed
        by datetime. Missing values should be represented by NaN.
    threshold : float
        Values above this threshold will be considered exceedances.
    run_length_days : int, optional
        Minimum time separation between two exceedances for them to be
        considered independent. For example, a run length of 5 days
        merges all exceedances within a 5‑day window into one cluster.

    Returns
    -------
    pandas.Series
        A new Series containing only the maximum value of each cluster
        where the original series exceeds the threshold. The index of
        the returned Series corresponds to the dates of those maxima.

    Notes
    -----
    This function delegates its work to
    :func:`philflood.models.ev.threshold_analysis.extract_declust_pot`.  See
    that function for implementation details and additional
    documentation.
    """
    return _impl(series, threshold=threshold, run_length_days=run_length_days)