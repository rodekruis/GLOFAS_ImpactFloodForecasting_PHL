"""Impact‑based Peaks‑Over‑Threshold (POT) fitting and return‑period mapping.

This module implements simple functions to fit a Generalized Pareto
Distribution (GPD) model to exceedances of an impact metric (e.g.,
number of people affected) and to convert new impact values into
return periods.  It parallels the discharge‑based EVT functionality
implemented in :mod:`philflood.calibration.evt_pot` but operates in
impact space.

The functions defined here are intentionally lightweight and do not
depend on the `pyextremes` library.  They are suitable for
integration into both manual notebooks and automated monitoring
pipelines.

Examples
--------

>>> import pandas as pd
>>> from philflood.models.impact.impact_evt import fit_gpd_pot, impact_to_return_period
>>> # Suppose `sev_series` is a pandas.Series of historical event severities
>>> fit = fit_gpd_pot(sev_series, q_candidates=[0.8, 0.9, 0.95], min_exceedances=20)
>>> rp = impact_to_return_period([1000, 5000], fit)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, Tuple, Union

import numpy as np
import pandas as pd
from scipy import stats


@dataclass
class ImpactGPD:
    """Holds parameters of an impact‑based GPD fit.

    Attributes
    ----------
    threshold : float
        POT threshold above which exceedances are used for fitting.
    xi : float
        GPD shape parameter (ξ).
    sigma : float
        GPD scale parameter (σ).
    lam : float
        Annual exceedance rate (λ) estimated from exceedances.
    """

    threshold: float
    xi: float
    sigma: float
    lam: float


def _fit_gpd(exceedances: np.ndarray) -> Optional[Tuple[float, float]]:
    """Fit a GPD to exceedances using maximum likelihood.

    Returns (xi, sigma) if successful, otherwise None.
    """
    if len(exceedances) == 0:
        return None
    try:
        c, loc, scale = stats.genpareto.fit(exceedances, floc=0)
        return float(c), float(scale)
    except Exception:
        return None


def fit_gpd_pot(
    series: pd.Series,
    q_candidates: Iterable[float],
    min_exceedances: int = 20,
) -> ImpactGPD:
    """Fit a GPD to a time series of impact severities using POT.

    This function tries a range of quantile thresholds and selects the
    lowest threshold that produces at least ``min_exceedances``.  It
    then fits a GPD to the exceedances (values exceeding the threshold)
    using maximum likelihood estimation via SciPy.  The annual
    exceedance rate (λ) is estimated as the number of exceedances
    divided by the number of years covered by the series.

    Parameters
    ----------
    series : pandas.Series
        Series of impact severities with a datetime index.
    q_candidates : iterable of float
        Candidate quantiles (0–1) to test as POT thresholds.
    min_exceedances : int, optional
        Minimum number of exceedances required to perform a fit.

    Returns
    -------
    ImpactGPD
        Object containing the selected threshold and fitted
        parameters.

    Raises
    ------
    ValueError
        If no candidate threshold yields the required number of
        exceedances.
    """
    s = series.dropna().sort_index()
    if s.empty:
        raise ValueError("Series is empty; cannot fit impact EVT.")

    thresholds = sorted(set(float(s.quantile(q)) for q in q_candidates))
    duration_days = (s.index.max() - s.index.min()).days
    years = duration_days / 365.25 if duration_days > 0 else 1.0

    best_fit: Optional[ImpactGPD] = None
    for u in thresholds:
        exceedances = (s[s > u] - u).to_numpy()
        if len(exceedances) < min_exceedances:
            continue
        params = _fit_gpd(exceedances)
        if params is None:
            continue
        xi, sigma = params
        lam = len(exceedances) / years
        best_fit = ImpactGPD(threshold=u, xi=xi, sigma=sigma, lam=lam)
        break

    if best_fit is None:
        raise ValueError(
            "Unable to fit impact GPD: no candidate threshold produced enough exceedances."
        )
    return best_fit


def _gpd_exceedance_rate(
    x: np.ndarray,
    u: float,
    sigma: float,
    xi: float,
    lam: float,
) -> np.ndarray:
    """Compute the annual exceedance rate for impact values x."""
    x = np.asarray(x, dtype=float)
    y = (x - u) / sigma
    y = np.maximum(y, 0.0)
    near0 = np.isclose(xi, 0.0)
    surv = np.empty_like(y, dtype=float)
    surv[near0] = np.exp(-y[near0])
    surv[~near0] = np.power(1.0 + xi * y[~near0], -1.0 / xi)
    rate = lam * surv
    return rate


def impact_to_return_period(x: Union[float, Iterable[float]], fit: ImpactGPD) -> np.ndarray:
    """Convert impact values to return periods using a fitted ImpactGPD."""
    x_arr = np.atleast_1d(np.asarray([x] if np.isscalar(x) else list(x), dtype=float))
    rates = _gpd_exceedance_rate(
        x_arr, u=fit.threshold, sigma=fit.sigma, xi=fit.xi, lam=fit.lam
    )
    rp = 1.0 / rates
    rp = np.clip(rp, 1.0, 1e12)
    return rp