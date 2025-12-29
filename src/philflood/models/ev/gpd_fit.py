"""Fitting and diagnostics for the Generalized Pareto Distribution (GPD).

This module defines a simple wrapper over the underlying EVT library
(``pyextremes``) to fit a GPD to a set of threshold exceedances. It also
provides helpers to compute return levels for specified return periods.

During the calibration phase you should call these functions from
notebooks or scripts, then store the fitted parameters in the basin
configuration.  The operational code should **not** refit the GPD; it
should rely on the fixed parameters selected during calibration.
"""

from __future__ import annotations

from typing import Iterable, Sequence, Dict, Union

import numpy as np
import pandas as pd

# We avoid importing pyextremes here directly because the library may not be
# installed in all environments.  Instead we refer to it in our docstrings
# and load it lazily in functions when needed.


class GPDModel:
    """Simple container for GPD parameters and return levels.

    Parameters
    ----------
    threshold : float
        The threshold used for the exceedances.
    shape : float
        The fitted shape parameter :math:`\xi`.
    scale : float
        The fitted scale parameter :math:`\sigma`.
    rate : float
        Average number of exceedances per unit time (e.g. per year).
    """

    def __init__(self, threshold: float, shape: float, scale: float, rate: float) -> None:
        self.threshold = threshold
        self.shape = shape
        self.scale = scale
        self.rate = rate

    def return_level(self, return_period: float) -> float:
        """Compute the return level for a given return period using the GPD.

        Parameters
        ----------
        return_period : float
            Return period in units of the data (typically years).  For
            example, 5 means the level exceeded on average once every
            five years.

        Returns
        -------
        float
            The discharge level associated with the given return
            period, using the fitted GPD and rate parameters.

        Notes
        -----
        The formula for the return level in a POT model with Poisson
        exceedances is::

            z_T = u + (sigma / xi) * [(T * lambda_u * xi)^{xi} - 1]

        where ``u`` is the threshold, ``sigma`` and ``xi`` are the GPD
        parameters and ``lambda_u`` is the exceedance rate.
        """
        if self.shape == 0:
            # Exponential tail
            return self.threshold - self.scale * np.log(
                1 - 1 / (return_period * self.rate)
            )
        # Heavy or bounded tail
        return self.threshold + (
            self.scale
            / self.shape
            * ((return_period * self.rate) ** self.shape - 1)
        )


def fit_gpd_to_exceedances(
    exceedances: pd.Series,
    threshold: float,
    block_size: float = 1.0,
    method: str = "MLE",
) -> GPDModel:
    """Fit a GPD to threshold exceedances and estimate the exceedance rate.

    Parameters
    ----------
    exceedances : pandas.Series
        Independent exceedances above a threshold.  The index should
        represent dates; missing values should have been removed.
    threshold : float
        The threshold used to define exceedances (same as in
        ``extract_declust_pot``).
    block_size : float, optional
        The reference time span for the return period, expressed in
        years.  For daily data a full calendar year corresponds to
        ``block_size=1.0``.  If you use months or seasons, adjust
        accordingly.
    method : str, optional
        Fitting method, currently ``"MLE"`` for maximum likelihood
        estimation.  Additional methods (e.g. L‑moments) could be added.

    Returns
    -------
    GPDModel
        A model containing the fitted parameters and exceedance rate.

    Notes
    -----
    This function is a placeholder: it does not yet call
    ``pyextremes``.  You will need to import the necessary
    functionality and perform the fit.  For example, using
    ``pyextremes.EVD.fit_gpd()``.
    """
    # Placeholder: fit dummy parameters.  Replace with pyextremes code.
    n_ex = len(exceedances)
    # Estimate average number of exceedances per year based on the index
    if n_ex == 0:
        raise ValueError("No exceedances to fit GPD to.")
    # Compute observation period in years
    duration_years = (
        (exceedances.index[-1] - exceedances.index[0]).days / 365.25
    )
    rate = n_ex / duration_years
    # Dummy parameters – replace with real fit
    shape = 0.0
    scale = exceedances.mean() - threshold
    return GPDModel(threshold, shape, scale, rate)