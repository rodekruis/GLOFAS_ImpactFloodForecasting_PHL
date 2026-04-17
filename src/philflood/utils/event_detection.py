"""Event detection utilities for impact and discharge time series.

This module provides helper functions to detect peak events in a time
series and to automatically select a Peaks‑Over‑Threshold (POT)
threshold based on simple criteria.  These helpers are intentionally
lightweight and do not depend on the `pyextremes` package; they are
designed for use in notebook workflows and automated pipelines where
a full EVT calibration is not required.

Functions
---------
peak_pick(series, threshold, decluster_days)
    Identify local maxima above a threshold in a series with a simple
    declustering rule.

auto_select_threshold(series, q_candidates, decluster_days,
                      min_events, max_events)
    Choose a POT threshold (quantile) such that the number of
    declustered events falls within a specified range.

These functions were originally implemented inline in the calibration
notebooks.  They have been extracted into a reusable module to avoid
duplication and to support the forthcoming calibration and monitoring
pipelines.
"""

from __future__ import annotations

from typing import Iterable, List, Tuple

import numpy as np
import pandas as pd


def peak_pick(series: pd.Series, threshold: float, decluster_days: int) -> pd.DatetimeIndex:
    """Identify independent peaks above a threshold in a time series.

    The algorithm proceeds by finding local maxima (a point is a peak
    if it is greater than its immediate neighbours) that also exceed
    the specified threshold.  Peaks are sorted in descending order and
    a simple declustering rule is applied: once a peak is selected,
    all peaks within ±``decluster_days`` are removed from consideration.

    Parameters
    ----------
    series : pandas.Series
        Input time series with a datetime index.
    threshold : float
        Minimum value to qualify as a peak.
    decluster_days : int
        Number of days on either side of a peak to exclude when
        selecting independent events.

    Returns
    -------
    pandas.DatetimeIndex
        Sorted index of detected peak dates.

    Notes
    -----
    This function is designed for simplicity and speed.  It does not
    perform run‑length declustering (which accounts for hydrological
    recession time), but it provides a reasonable first pass for
    counting extreme events when a more sophisticated method is not
    available.
    """
    # Drop missing values and ensure chronological order
    s = series.dropna().sort_index()
    if s.empty:
        return pd.DatetimeIndex([])

    # Identify strict local maxima
    is_peak = (s.shift(1) < s) & (s.shift(-1) < s)
    peaks = s[is_peak & (s >= threshold)].copy()
    if peaks.empty:
        return pd.DatetimeIndex([])

    # Sort peaks by magnitude (descending) so that the highest peak in a
    # cluster is selected first
    peaks = peaks.sort_values(ascending=False)
    selected: List[pd.Timestamp] = []
    taken = pd.Series(False, index=s.index)
    for t, _ in peaks.items():
        # Skip if this timestamp has already been marked as belonging to
        # another cluster
        if taken.loc[t]:
            continue
        selected.append(t)
        # Mark the declustering window as taken
        win = (s.index >= t - pd.Timedelta(days=decluster_days)) & (
            s.index <= t + pd.Timedelta(days=decluster_days)
        )
        taken.loc[win] = True

    return pd.DatetimeIndex(sorted(selected))


def auto_select_threshold(
    series: pd.Series,
    q_candidates: Iterable[float],
    decluster_days: int,
    min_events: int,
    max_events: int,
) -> float:
    """Choose a POT threshold such that the number of events falls within a range.

    Given a list of candidate quantiles, this function computes the
    corresponding thresholds and counts the number of declustered peaks
    above each threshold.  It selects the highest threshold that
    produces between ``min_events`` and ``max_events`` events.  If no
    candidate satisfies the criteria, it falls back to the lowest or
    highest quantile depending on which side of the range the counts
    fall.

    Parameters
    ----------
    series : pandas.Series
        Input time series with a datetime index.
    q_candidates : Iterable[float]
        Sequence of quantile levels (0–1) to test as potential
        thresholds (e.g., [0.90, 0.92, 0.95]).
    decluster_days : int
        Number of days used for declustering in ``peak_pick``.
    min_events : int
        Minimum desired number of events.
    max_events : int
        Maximum desired number of events.

    Returns
    -------
    float
        Selected threshold (in the same units as ``series``).
    """
    s = series.dropna().sort_index()
    if s.empty:
        raise ValueError("Time series is empty after removing NaN values.")

    # Compute candidate thresholds from quantiles and ensure unique,
    # sorted values
    thresholds = sorted(set(float(s.quantile(q)) for q in q_candidates))
    threshold_counts: List[Tuple[float, int]] = []
    for thr in thresholds:
        peak_dates = peak_pick(s, threshold=thr, decluster_days=decluster_days)
        n = len(peak_dates)
        threshold_counts.append((thr, n))

    # Select the highest threshold whose event count is within the target range
    valid = [(thr, n) for (thr, n) in threshold_counts if min_events <= n <= max_events]
    if valid:
        # Choose the threshold that gives the fewest events within range (most
        # conservative) to maintain more independence among events
        thr_selected = max(valid, key=lambda x: x[0])[0]
        return thr_selected

    # If all candidates yield too many events, pick the highest threshold
    if all(n > max_events for (_, n) in threshold_counts):
        return thresholds[-1]

    # If all candidates yield too few events, pick the lowest threshold
    return thresholds[0]