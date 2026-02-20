"""Run the operational flood trigger for one or more basins.

⚠️ **v1.0 PLACEHOLDER - NOT YET IMPLEMENTED**

This module is a placeholder for v1.0 functionality (Q2 2026).
The operational monitoring pipeline requires:
- CLIMADA hazard integration (in progress)
- Population impact models (in progress)
- Real-time GloFAS forecast ingestion (in progress)

For v0.3.0, use the calibration notebooks for basin setup and 
impact estimation.

See CHANGELOG.md for full roadmap and migration timeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Dict

from ..domain.basin import BasinConfig


@dataclass
class TriggerDecision:
    """Placeholder for v1.0 trigger decision output."""
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
    forecast = None,
) -> TriggerDecision:
    """Evaluate the flood trigger for a single basin on a given date.
    
    ⚠️ **NOT IMPLEMENTED - v1.0 Feature**
    
    This function is a placeholder for operational monitoring that will be 
    completed in v1.0 (Q2 2026). It requires:
    
    - CLIMADA hazard integration (climada_river.py - in development)
    - Population impact models (models/impact/ - in development)  
    - Real-time GloFAS forecast ingestion (adapters/glofas_forecast.py - planned)
    
    **For v0.3.0 users:**
    - Use calibration notebooks for basin setup and historical analysis
    - See docs/user-guides/notebook01-calibration-guide.md for workflow
    - See CHANGELOG.md for v1.0 roadmap
    
    Parameters
    ----------
    basin_cfg : BasinConfig
        Calibrated configuration for the basin.
    issue_date : date
        Date of the forecast issuance.
    forecast : optional
        Pre-loaded forecast data (not yet implemented).

    Raises
    ------
    NotImplementedError
        This function is not yet implemented in v0.3.0.
    """
    raise NotImplementedError(
        "Operational monitoring is a v1.0 feature (planned Q2 2026). "
        "For v0.3.0, use the calibration notebooks for basin analysis. "
        "See docs/user-guides/notebook01-calibration-guide.md or "
        "CHANGELOG.md for the roadmap."
    )