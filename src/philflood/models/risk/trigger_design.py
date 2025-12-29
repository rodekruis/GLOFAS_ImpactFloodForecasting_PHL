"""Trigger design and evaluation functions.

This module provides helpers to derive candidate trigger levels from
AEP/OEP curves and to evaluate those candidates against historical
impact data.  Candidate triggers are defined as pairs
``(return_period, impact_threshold)`` or equivalently as fixed
probability and impact thresholds for the operational rule.

Functions in this file operate purely on in‑memory data structures
(pandas DataFrames, dictionaries). They do not fetch or process
forecasts – that happens in the operations layer.
"""

from __future__ import annotations

from typing import List, Dict, Iterable, Tuple, Optional

import numpy as np
import pandas as pd


def propose_candidate_triggers(
    aep_curve: pd.DataFrame,
    return_periods: Iterable[float],
) -> List[Dict[str, float]]:
    """Identify candidate trigger levels on an AEP curve.

    Parameters
    ----------
    aep_curve : pandas.DataFrame
        DataFrame with columns ``"impact"`` and ``"probability"`` as
        returned by :func:`philflood.risk.aep_oep.compute_aep_oep` for
        the AEP curve.  ``impact`` should be sorted descending.
    return_periods : iterable of float
        Target return periods (in years) for which to find the
        corresponding impact values.  A 1‑in‑10‑year event has RP=10.

    Returns
    -------
    list of dict
        Each dict has keys ``"return_period"`` and
        ``"impact_threshold"`` indicating that the annual sum of
        impacts exceeds ``impact_threshold`` with annual probability
        ``1/return_period``.

    Notes
    -----
    The mapping from return period to impact threshold is done by
    finding the closest probability in the AEP curve.  If the target
    probability is between two empirical points, linear interpolation
    is used.  You could extend this to use parametric fits or smooth
    the curve before interpolation.
    """
    # Ensure the curve is sorted by probability ascending
    curve = aep_curve.sort_values("probability").reset_index(drop=True)
    results: List[Dict[str, float]] = []
    probs = curve["probability"].values
    impacts = curve["impact"].values
    for rp in return_periods:
        p = 1.0 / rp  # AEP is 1/RP
        # Interpolate impact at this probability
        impact_val = np.interp(p, probs, impacts)
        results.append({"return_period": rp, "impact_threshold": impact_val})
    return results


def evaluate_trigger_against_catalogue(
    impacts: pd.DataFrame,
    threshold_people: float,
    p0: float,
    year_col: str = "year",
    value_col: str = "people_affected",
    impact_catalogue: Optional[pd.DataFrame] = None,
) -> Dict[str, float]:
    """Evaluate a candidate trigger using POD and FAR metrics.

    Parameters
    ----------
    impacts : pandas.DataFrame
        Synthetic impact database (ensemble or synthetic events) used
        to estimate probabilities that events exceed the threshold.
    threshold_people : float
        Impact threshold in number of people.  A forecast event is
        considered potentially triggering if the predicted impact
        exceeds this threshold.
    p0 : float
        Probability threshold.  A trigger is activated if the
        probability that an event exceeds ``threshold_people`` is
        greater than or equal to ``p0``.
    year_col, value_col : str, optional
        Column names for year and impact in the synthetic impact
        database.  Defaults assume impacts have been aggregated.
    impact_catalogue : pandas.DataFrame, optional
        Historical impact catalogue with at least a ``year`` column
        indicating which years had impactful floods.  Additional
        columns can be present but are not used here.

    Returns
    -------
    dict
        Dictionary with keys ``"POD"`` (probability of detection)
        and ``"FAR"`` (false alarm ratio).  If ``impact_catalogue``
        is None or empty, both metrics are returned as NaN.

    Notes
    -----
    The evaluation is simplified: it assumes that the synthetic
    database approximates the true distribution of impacts.  A more
    rigorous approach would require matching synthetic years to
    historical years and using actual hindcasts.
    """
    if impact_catalogue is None or impact_catalogue.empty:
        return {"POD": float("nan"), "FAR": float("nan")}
    # Identify years with catalogue impacts above threshold
    impacted_years = set(impact_catalogue[year_col])
    # Compute probability that annual sum exceeds threshold in each synthetic year
    yearly_sum = impacts.groupby(year_col)[value_col].sum()
    exceed_years = set(yearly_sum[yearly_sum >= threshold_people].index)
    hits = len(exceed_years.intersection(impacted_years))
    misses = len(impacted_years - exceed_years)
    false_alarms = len(exceed_years - impacted_years)
    # Avoid division by zero
    pod = hits / (hits + misses) if (hits + misses) > 0 else float("nan")
    far = false_alarms / (hits + false_alarms) if (hits + false_alarms) > 0 else float("nan")
    return {"POD": pod, "FAR": far}