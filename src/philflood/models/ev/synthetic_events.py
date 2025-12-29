"""Generate synthetic flood events from fitted EVT models.

Synthetic event generation allows you to create long time series of
extreme discharge values beyond the length of the observed record.  In
conjunction with hazard and impact models, these synthetic events
produce the synthetic impact databases used to derive AEP/OEP curves
and AAPA metrics.

This module defines helper functions to sample event counts and
magnitudes from fitted GPD parameters and arrival rates.  It is
deliberately agnostic of the underlying hydrological variable; it
treats the EVT model as the interface.
"""

from __future__ import annotations

from typing import Iterable, List, Tuple

import numpy as np
import pandas as pd

from .gpd_fit import GPDModel


def simulate_event_year(
    model: GPDModel,
    random_state: np.random.Generator,
    basin_id: str,
    year: int,
) -> List[Tuple[str, int, float]]:
    """Simulate one synthetic year of flood events from a GPD model.

    Parameters
    ----------
    model : GPDModel
        Fitted GPD model containing the exceedance threshold, shape,
        scale and rate parameters.
    random_state : numpy.random.Generator
        Random number generator used to sample event counts and
        magnitudes.  Providing an explicit generator makes results
        reproducible when seeding it in calibration.
    basin_id : str
        Identifier for the basin; stored in the event tuple for
        downstream joins.
    year : int
        The synthetic year label (e.g. 1 through N).  Not a calendar
        year; used only for indexing synthetic events.

    Returns
    -------
    list of tuple
        A list of tuples ``(basin_id, year, discharge)`` for each
        simulated event in the given synthetic year.  The number of
        events is drawn from a Poisson distribution with mean
        ``model.rate``; each discharge is obtained by transforming a
        random sample from the GPD.

    Notes
    -----
    This is a basic implementation. In reality you might want to
    include additional attributes (e.g. event IDs, RP values) or
    produce event times as well.  You could also vectorise this for
    performance.
    """
    n_events = random_state.poisson(model.rate)
    events: List[Tuple[str, int, float]] = []
    for _ in range(n_events):
        # Sample a GPD exceedance
        u = random_state.random()
        if model.shape == 0:
            y = -model.scale * np.log(1 - u)
        else:
            y = model.scale / model.shape * ((1 - u) ** (-model.shape) - 1)
        discharge = model.threshold + y
        events.append((basin_id, year, float(discharge)))
    return events


def simulate_multiple_years(
    model: GPDModel,
    years: int,
    basin_id: str,
    seed: int = 42,
) -> pd.DataFrame:
    """Simulate many years of events and return as a DataFrame.

    Parameters
    ----------
    model : GPDModel
        Fitted GPD model.
    years : int
        Number of synthetic years to simulate.
    basin_id : str
        Basin identifier to tag each event.
    seed : int, optional
        Seed for the random number generator to ensure reproducibility.

    Returns
    -------
    pandas.DataFrame
        DataFrame with columns ``["basin_id", "year", "discharge"]``.

    Notes
    -----
    In practice you might also want to include the derived return
    period or event date.  You could compute return periods by
    inverting the GPD CDF or simply derive them post‑hoc from the
    synthetic catalogue.  These refinements can be added later.
    """
    rng = np.random.default_rng(seed)
    rows = []
    for yr in range(1, years + 1):
        rows.extend(simulate_event_year(model, rng, basin_id, yr))
    return pd.DataFrame(rows, columns=["basin_id", "year", "discharge"])