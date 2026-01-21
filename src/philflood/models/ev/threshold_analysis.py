"""Utilities for exploratory threshold analysis in peaks-over-threshold (POT) models.

This module defines helper functions to support the calibration
notebooks used to select a suitable threshold for POT analyses.  The
goal of these functions is twofold:

1. Provide reusable implementations of common diagnostics such as
   the **mean residual life** (MRL) plot and **parameter stability**
   curves.  These diagnostics help users judge where the tail of
   their discharge distribution begins and therefore which threshold
   is appropriate for extreme value modelling.
2. Offer a more robust **declustering** routine than the placeholder
   defined in :mod:`philflood.models.ev.peaks_over_threshold`.  The
   declustering routine identifies independent flood peaks by
   grouping exceedances into clusters separated by a minimum number
   of days below the threshold and retaining only the maximum of
   each cluster.

These functions depend only on ``pandas`` and ``scipy``, both of
which are available in this project.  They avoid pulling in heavy
external libraries such as ``pyextremes`` so that the repository
remains fully open source and reproducible without additional
dependencies.

Each helper is documented with usage notes so that analysts can
understand how to interpret the diagnostics.  See the calibration
notebooks under ``calibration/notebooks`` for examples.
"""

from __future__ import annotations

from typing import Iterable, List, Tuple

import numpy as np
import pandas as pd
from scipy import stats

def extract_declust_pot(
    series: pd.Series,
    threshold: float,
    run_length_days: int = 5,
) -> pd.Series:
    """Extract independent peaks above a threshold from a time series.

    This function implements declustering for peaks‑over‑threshold
    analyses.  It identifies clusters of threshold exceedances that
    occur within ``run_length_days`` of each other and returns only the
    maximum value from each cluster.  The result is a smaller
    time series of independent exceedances, suitable for fitting a
    Generalized Pareto Distribution (GPD).

    Parameters
    ----------
    series : pandas.Series
        Time series of discharge (or any hydrological variable) indexed
        by a datetime index.  Missing values (``NaN``) will be
        ignored.  The index must be monotonic increasing.
    threshold : float
        Threshold above which values are considered exceedances.
    run_length_days : int, optional
        Minimum number of days separating two exceedances to treat
        them as independent clusters.  For example, a value of
        ``5`` will merge all exceedances occurring within a 5‑day
        window into a single cluster.

    Returns
    -------
    pandas.Series
        A series containing the maximum value of each cluster of
        exceedances.  The index corresponds to the date of the
        cluster maximum.

    Notes
    -----
    The series is first filtered to retain only values strictly
    exceeding the threshold.  The index differences (in days) between
    consecutive exceedances are then used to identify new clusters
    whenever the gap exceeds ``run_length_days``.  Within each cluster
    the maximum is selected.  If no values exceed the threshold, an
    empty series is returned.
    """
    if series.empty:
        return series
    # Drop missing values
    s = series.dropna()
    # Filter to exceedances
    exceedances = s[s > threshold]
    if exceedances.empty:
        return pd.Series(dtype=float)
    # Compute time differences in days between consecutive exceedances
    diffs = exceedances.index.to_series().diff().dt.days.fillna(run_length_days + 1)
    # A new cluster starts where the gap exceeds run_length_days
    cluster_ids = diffs.gt(run_length_days).cumsum()
    # For each cluster, retain the index of the maximum value
    def cluster_max_idx(group: pd.Series) -> pd.Timestamp:
        return group.idxmax()
    max_indices = exceedances.groupby(cluster_ids).apply(cluster_max_idx)
    # Extract the corresponding values
    peaks = s.loc[max_indices]
    peaks = peaks.sort_index()
    return peaks


def mean_residual_life(
    series: pd.Series,
    thresholds: Iterable[float],
    run_length_days: int = 5,
) -> pd.DataFrame:
    """Compute the mean residual life (MRL) for a range of thresholds.

    The mean residual life function (also known as the mean excess
    function) is defined as

    .. math:: \text{MRL}(u) = \mathbb{E}[X - u \mid X > u]

    where :math:`X` denotes the discharge.  For a suitable threshold
    ``u`` the MRL should increase approximately linearly; abrupt
    departures from linearity indicate the threshold may be too high or
    too low.  Plotting the MRL against ``u`` helps analysts choose a
    threshold beyond which the tail behaviour is well approximated by
    a Generalized Pareto Distribution.

    Parameters
    ----------
    series : pandas.Series
        Time series of discharge indexed by datetime.  Missing values
        should have been removed.  The series can contain multiple
        columns if it has a hierarchical index; this function expects
        a simple Series.
    thresholds : iterable of float
        Sequence of candidate thresholds at which to compute the MRL.
    run_length_days : int, optional
        Declustering window.  The series will be declustered at each
        threshold before computing the MRL.  This ensures that
        dependence between peaks does not bias the estimate of the
        mean excess.

    Returns
    -------
    pandas.DataFrame
        A table with columns ``['threshold', 'mean_excess', 'n_exceedances']``.
        The ``mean_excess`` is NaN if there are no exceedances above
        the threshold after declustering.  ``n_exceedances`` counts
        how many independent peaks exceed the threshold.
    """
    thresholds = list(thresholds)
    records: List[Tuple[float, float, int]] = []
    for u in thresholds:
        peaks = extract_declust_pot(series, u, run_length_days)
        # Compute excesses relative to the threshold
        excesses = peaks - u
        n = len(excesses)
        mean_excess = excesses.mean() if n > 0 else np.nan
        records.append((u, mean_excess, n))
    df = pd.DataFrame(records, columns=["threshold", "mean_excess", "n_exceedances"])
    return df


def gpd_parameter_stability(
    series: pd.Series,
    thresholds: Iterable[float],
    run_length_days: int = 5,
) -> pd.DataFrame:
    """Fit a GPD at multiple thresholds to assess parameter stability.

    For each candidate threshold the series is declustered, the
    excesses (values above the threshold minus the threshold) are
    computed, and a Generalized Pareto Distribution (GPD) is fitted
    using maximum likelihood estimation (MLE) via ``scipy.stats.genpareto``.
    The fitted shape (\\xi\\) and scale (\\sigma\\) parameters are
    returned as a function of the threshold.  A flat profile of the
    shape parameter across a range of thresholds is indicative of a
    suitable threshold region.

    Parameters
    ----------
    series : pandas.Series
        Time series of discharge indexed by datetime.  The data
        should already be cleaned of missing values.  Values must be
        strictly positive; if not, you may need to add a constant
        offset before fitting.
    thresholds : iterable of float
        Thresholds at which to fit the GPD.
    run_length_days : int, optional
        Declustering window.

    Returns
    -------
    pandas.DataFrame
        Table with columns ``['threshold', 'shape', 'scale', 'n_exceedances']``.
        ``n_exceedances`` counts the number of independent peaks used
        in each fit.  If there are fewer than three exceedances the
        fit is skipped and the parameters are set to NaN.

    Notes
    -----
    We fix the location parameter of the GPD at zero by fitting to
    the excesses (``values - threshold``).  This is standard when
    working in a peaks-over-threshold framework.
    """
    thresholds = list(thresholds)
    results: List[Tuple[float, float, float, int]] = []
    for u in thresholds:
        peaks = extract_declust_pot(series, u, run_length_days)
        excesses = peaks - u
        n = len(excesses)
        if n < 3:
            shape = np.nan
            scale = np.nan
        else:
            # Fit GPD to excesses with fixed location=0
            # scipy returns (shape, loc, scale)
            try:
                shape, loc, scale = stats.genpareto.fit(excesses, floc=0)
            except Exception:
                shape, scale = np.nan, np.nan
            # Sometimes the MLE fails or returns degenerate values
        results.append((u, shape, scale, n))
    df = pd.DataFrame(
        results, columns=["threshold", "shape", "scale", "n_exceedances"]
    )
    return df


def suggest_threshold_range(
    series: pd.Series,
    lower_quantile: float = 0.9,
    upper_quantile: float = 0.99,
    num: int = 20,
) -> np.ndarray:
    """Suggest an array of candidate thresholds based on quantiles.

    This utility constructs a sequence of thresholds between two
    quantiles of the input series.  Analysts typically explore
    thresholds from a high quantile (e.g. 90th percentile) up to a
    very high quantile (e.g. 99th percentile).  The returned
    thresholds can then be passed to :func:`mean_residual_life` or
    :func:`gpd_parameter_stability`.

    Parameters
    ----------
    series : pandas.Series
        Data from which to compute quantiles.  Missing values are
        ignored.
    lower_quantile : float, optional
        Lower bound of the quantile range (e.g. 0.9).
    upper_quantile : float, optional
        Upper bound of the quantile range (e.g. 0.99).
    num : int, optional
        Number of equally spaced thresholds between the quantiles.

    Returns
    -------
    numpy.ndarray
        Array of threshold values.
    """
    clean = series.dropna().values
    q_low = np.quantile(clean, lower_quantile)
    q_high = np.quantile(clean, upper_quantile)
    # Ensure strictly increasing thresholds
    if num <= 1:
        return np.array([q_high])
    return np.linspace(q_low, q_high, num=num)
