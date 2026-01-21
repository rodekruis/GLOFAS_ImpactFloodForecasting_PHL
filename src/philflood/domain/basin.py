"""Dataclasses representing configuration for basins and related sub‑objects.

The :class:`BasinConfig` hierarchy holds the parameters that define a
specific watershed for both calibration and operational purposes.  Each
configuration file should correspond to one instance of `BasinConfig`.
The nested dataclasses allow easy deserialization from YAML and
provide type hints for IDEs and static checkers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional


@dataclass
class EVTConfig:
    """Configuration for the extreme value analysis of a basin.

    Parameters
    ----------
    method : str
        The type of EVT model applied (e.g. ``"POT-GPD"``).  For
        partial duration series we always use peaks‑over‑threshold with
        a Generalised Pareto Distribution.
    threshold_m3s : float
        The discharge threshold (in cubic metres per second) above
        which peaks are considered extreme.  Selected during
        calibration using diagnostics such as mean residual life and
        parameter stability plots.
    run_length_days : int
        The minimum time separation between two exceedances for them to
        be considered independent events.  This accounts for the
        hydrological response time of the catchment.
    gpd_shape_xi : float
        The estimated shape parameter :math:`\\xi` of the GPD,
        describing tail heaviness.  Positive values indicate a heavy
        tail, values near zero indicate an exponential tail.
    gpd_scale_sigma : float
        The scale parameter :math:`\\sigma_u` of the GPD (in the same
        units as the excesses), controlling the spread of exceedances.
    event_rate_per_year : float
        The average number of independent exceedances per year.  This
        determines the Poisson arrival rate in synthetic event
        generation.
    """

    method: str = "POT-GPD"
    threshold_m3s: float = 0.0
    run_length_days: int = 5
    gpd_shape_xi: float = 0.0
    gpd_scale_sigma: float = 1.0
    event_rate_per_year: float = 0.0


@dataclass
class VulnerabilityConfig:
    """Parameters defining how flood depth translates to affected people.

    Parameters
    ----------
    depth_threshold_m : float
        Water depth (in metres) above which people are counted as
        affected.  This is a coarse step function; more complex
        vulnerability curves can be added later.
    impact_fraction : float
        The fraction of the population exposed to water depths
        exceeding the threshold that are considered affected.  For
        example, ``0.8`` means 80% of people living in a flooded cell
        will be counted as affected.
    """

    depth_threshold_m: float = 0.3
    impact_fraction: float = 1.0


@dataclass
class TriggerConfig:
    """Definition of an operational trigger for early action.

    Parameters
    ----------
    impact_threshold_people : int
        The minimum number of people affected required to consider
        activation.  This value will be compared to modelled impacts.
    probability_threshold : float
        The minimum probability (between 0 and 1) that the impact
        threshold will be exceeded before a trigger is activated.  For
        example, ``0.3`` corresponds to a 30% probability.
    max_lead_time_days : int
        The maximum forecast lead time (in days) to consider when
        evaluating the trigger.  Forecasts beyond this horizon are
        ignored.
    """

    impact_threshold_people: int = 100_000
    probability_threshold: float = 0.3
    max_lead_time_days: int = 10


@dataclass
class BasinConfig:
    """Configuration for a single watershed or catchment.

    Parameters
    ----------
    basin_id : str
        An identifier for the basin, used in file names and plots.
    country_iso3 : str
        ISO 3166‑1 alpha‑3 code of the country containing the basin.
    hydrobasins_level : int
        HydroBASINS level (1–12) used to delineate the basin.  Higher
        levels correspond to smaller sub‑basins.
    hydrobasins_id : int
        HydroBASINS ID of the catchment polygon.
    glofas_point_ids : list of str
        List of GloFAS station identifiers or grid cell identifiers
        associated with this basin.
    evt : EVTConfig
        Nested configuration for extreme value modelling.
    vulnerability : VulnerabilityConfig
        Nested configuration for converting depth to affected people.
    trigger : TriggerConfig
        Nested configuration for the operational early action trigger.
    data_root : pathlib.Path or str
        Path to the root directory where data for this basin are stored
        (e.g. GloFAS files, hazard maps).  This can be set at runtime
        through environment variables or the configuration file.
    """

    basin_id: str
    country_iso3: str
    hydrobasins_level: int
    hydrobasins_id: int
    glofas_point_ids: List[str] = field(default_factory=list)
    evt: EVTConfig = field(default_factory=EVTConfig)
    vulnerability: VulnerabilityConfig = field(default_factory=VulnerabilityConfig)
    trigger: TriggerConfig = field(default_factory=TriggerConfig)
    data_root: Optional[Path] = None

    @staticmethod
    def from_dict(
        basin_data: Dict[str, object],
        evt_data: Dict[str, object],
        vulnerability_data: Dict[str, object],
        trigger_data: Dict[str, object],
    ) -> "BasinConfig":
        """Factory method to construct a BasinConfig from nested dicts.

        This helper is used by the YAML loader in :mod:`philflood.config`.
        """
        evt_cfg = EVTConfig(**evt_data)
        vuln_cfg = VulnerabilityConfig(**vulnerability_data)
        trigger_cfg = TriggerConfig(**trigger_data)
        return BasinConfig(
            evt=evt_cfg,
            vulnerability=vuln_cfg,
            trigger=trigger_cfg,
            **basin_data,
        )
    
    def validate(self) -> List[str]:
        """Validate the basin configuration and return a list of issues.

        This method checks that required fields are present and that
        numerical parameters fall within sensible bounds.  It returns a
        list of error messages; if the list is empty the configuration
        is considered valid.
        """
        issues: List[str] = []

        if not self.basin_id:
            issues.append("basin_id is required")

        if not (0.0 <= self.trigger.probability_threshold <= 1.0):
            issues.append("trigger.probability_threshold must be between 0 and 1")

        if self.trigger.impact_threshold_people <= 0:
            issues.append("trigger.impact_threshold_people must be > 0")

        if self.vulnerability.depth_threshold_m < 0:
            issues.append("vulnerability.depth_threshold_m must be >= 0")

        if not (0.0 <= self.vulnerability.impact_fraction <= 1.0):
            issues.append("vulnerability.impact_fraction must be between 0 and 1")

        if self.hydrobasins_level < 1 or self.hydrobasins_level > 12:
            issues.append("hydrobasins_level must be between 1 and 12")

        return issues

