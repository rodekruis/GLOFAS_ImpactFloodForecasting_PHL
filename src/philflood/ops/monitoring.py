"""Run the operational flood trigger for one or more basins.

This module ties together the EVT model, hazard mapping, impact
calculation and trigger evaluation for a given forecast input.  It
exposes a `run_monitoring` function that accepts a basin
configuration and a date or forecast object, and returns a decision
record.  In a production setting this could be scheduled to run daily
or multiple times per day.

Only the high‑level workflow is shown here; individual steps call
functions from other modules.  A proper implementation should also
include logging, error handling and caching of intermediate results.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Dict

import numpy as np
import pandas as pd

from ..basin import BasinConfig
from ..config import load_basin_config
from ..data.glofas_extractor import load_glofas_forecast_for_basin
from ..hazard.climada_driver import run_flood_hazard
from ..impact.population_exposure import load_population_grid
from ..impact.vulnerability import compute_people_affected


@dataclass
class TriggerDecision:
    basin_id: str
    issue_date: date
    probability_exceed: float
    expected_people: float
    triggered: bool

    def to_dict(self) -> Dict[str, object]:
        """Serialise decision to a dict for JSON or CSV output."""
        return {
            "basin_id": self.basin_id,
            "issue_date": self.issue_date.isoformat(),
            "probability_exceed": self.probability_exceed,
            "expected_people": self.expected_people,
            "triggered": self.triggered,
        }


def run_monitoring(
    basin_cfg: BasinConfig,
    issue_date: date,
    forecast: pd.DataFrame | None = None,
) -> TriggerDecision:
    """Evaluate the flood trigger for a single basin on a given date.

    Parameters
    ----------
    basin_cfg : BasinConfig
        Calibrated configuration for the basin.
    issue_date : date
        Date of the forecast issuance.  Lead times are counted from
        this date.
    forecast : pandas.DataFrame or None, optional
        Pre‑loaded forecast impact table.  If None, the function
        fetches the GloFAS forecast and computes hazards and impacts
        on the fly.  Passing a pre‑computed DataFrame allows you to
        decouple data fetching from trigger evaluation.

    Returns
    -------
    TriggerDecision
        Decision record containing the probability of exceeding the
        impact threshold and whether the trigger criteria were met.

    Notes
    -----
    This function is currently a skeleton.  It does not implement
    ensemble aggregation, hazard mapping or impact calculation.  Those
    steps should call the corresponding functions in the `data`,
    `hazard`, `impact` and `risk` modules.  It returns placeholder
    results for now.
    """
    # If no forecast data passed, load from GloFAS (placeholder)
    if forecast is None:
        # ds = load_glofas_forecast_for_basin(basin_cfg, issue_date)
        # For each ensemble member: compute hazard depth map, then impacts
        # Then derive a distribution of impacts across the ensemble
        expected_people = 0.0
        prob = 0.0
    else:
        # Derive probability of exceedance and expected impact from the DataFrame
        expected_people = forecast["people_affected"].mean()
        prob = (
            (forecast["people_affected"] >= basin_cfg.trigger.impact_threshold_people).mean()
        )
    triggered = (
        prob >= basin_cfg.trigger.probability_threshold
        and expected_people >= basin_cfg.trigger.impact_threshold_people
    )
    return TriggerDecision(
        basin_id=basin_cfg.basin_id,
        issue_date=issue_date,
        probability_exceed=prob,
        expected_people=expected_people,
        triggered=triggered,
    )