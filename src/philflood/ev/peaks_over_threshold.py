"""Peak extraction and declustering for peaks‑over‑threshold (POT) analysis.

The peaks over threshold method requires careful treatment of dependence
in the original time series. This module provides a function to
extract independent exceedances from a pandas Series. The result is a
Series containing only the cluster maxima above the specified
threshold.

At present these functions are stubs; real implementations will
leverage external libraries such as ``pyextremes`` or custom code to
identify and decluster exceedances. The goal is to preserve a
consistent interface across the project.
"""

from __future__ import annotations

from typing import Optional

import pandas as pd


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
    This function is currently a placeholder. You will need to implement
    logic to identify contiguous clusters of exceedances separated by at
    least `run_length_days` below the threshold, then take the cluster
    maximum. In the interim, this function simply filters out values
    below the threshold without declustering.
    """
    # Placeholder implementation: no declustering
    exceedances = series[series > threshold].dropna()
    return exceedances