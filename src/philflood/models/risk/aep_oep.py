"""Functions to compute AEP, OEP and AAPA risk metrics.

After generating a synthetic impact database (list or DataFrame of
events with year labels and numbers of people affected), the next
step is to summarise the distribution of impacts.  Two key curves
are used:

* **Aggregate Exceedance Probability (AEP)** – the probability that
  the *annual sum* of impacts exceeds a given threshold.
* **Occurrence Exceedance Probability (OEP)** – the probability that
  the *largest single event* impact in a year exceeds a given
  threshold.

This module defines functions to compute these curves and the Annual
Average People Affected (AAPA) metric.  It does not perform any
statistical fitting; it uses empirical ranking.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def compute_aep_oep(
    impacts: pd.DataFrame,
    value_col: str = "people_affected",
    year_col: str = "year",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compute AEP and OEP curves from a synthetic impact database.

    Parameters
    ----------
    impacts : pandas.DataFrame
        DataFrame containing at least two columns: a ``year`` identifier
        and a numerical column with impact values (e.g. people
        affected).  Each row represents one event.
    value_col : str, optional
        Name of the column in ``impacts`` containing the numerical
        impact values.  Default is ``"people_affected"``.
    year_col : str, optional
        Name of the column containing the year label.  Default is
        ``"year"``.

    Returns
    -------
    (AEP, OEP) : tuple of pandas.DataFrame
        Two DataFrames where the index is the rank (1..N years) and
        columns ``"impact"`` and ``"probability"``.  The AEP DataFrame
        ranks the annual sums descending; the OEP DataFrame ranks the
        annual maxima descending.  ``probability`` is defined as
        ``rank / (N + 1)`` to give a plotting position consistent with
        exceedance probability definitions.

    Notes
    -----
    The returned DataFrames can be used to plot exceedance probability
    curves.  You can interpolate between points or fit parametric
    curves if desired, but for many humanitarian applications the
    empirical curves are sufficiently descriptive.
    """
    # Aggregate impacts per year
    yearly_sum = impacts.groupby(year_col)[value_col].sum()
    yearly_max = impacts.groupby(year_col)[value_col].max()
    n_years = len(yearly_sum)
    # Rank annual sums descending
    aep = yearly_sum.sort_values(ascending=False).reset_index(drop=True)
    aep_prob = (aep.index + 1) / (n_years + 1)
    aep_df = pd.DataFrame({"impact": aep.values, "probability": aep_prob})
    # Rank annual maxima descending
    oep = yearly_max.sort_values(ascending=False).reset_index(drop=True)
    oep_prob = (oep.index + 1) / (n_years + 1)
    oep_df = pd.DataFrame({"impact": oep.values, "probability": oep_prob})
    return aep_df, oep_df


def compute_aapa(
    impacts: pd.DataFrame,
    value_col: str = "people_affected",
    year_col: str = "year",
) -> float:
    """Compute the Annual Average People Affected (AAPA).

    The AAPA is the mean of the annual aggregate impacts over the
    synthetic catalogue.  It represents the long‑term expected number
    of people affected per year.

    Parameters
    ----------
    impacts : pandas.DataFrame
        Synthetic impact database with columns ``year`` and ``value_col``.
    value_col : str, optional
        Column containing impact values.  Default ``"people_affected"``.
    year_col : str, optional
        Column containing year labels.  Default ``"year"``.

    Returns
    -------
    float
        The AAPA value.
    """
    yearly_sum = impacts.groupby(year_col)[value_col].sum()
    return float(yearly_sum.mean())