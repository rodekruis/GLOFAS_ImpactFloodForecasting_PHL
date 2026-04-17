"""Compatibility validation helpers for basin YAML files.

This module is intentionally lightweight and kept for backwards
compatibility with existing imports from ``philflood.cli`` and smoke
tests.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Union

from philflood.domain.config import load_basin_config


def validate_basin_config(config_path: Union[str, Path]) -> List[str]:
    """Validate a basin configuration file and return human-readable issues."""
    issues: List[str] = []

    try:
        cfg = load_basin_config(config_path)
    except Exception as exc:
        return [f"Failed to load config: {exc}"]

    if not cfg.basin_id or cfg.basin_id == "example_basin":
        issues.append("basin_id not set or still using placeholder value")

    if not cfg.country_iso3:
        issues.append("country_iso3 is required")

    if not cfg.glofas_point_ids or cfg.glofas_point_ids == ["PHL_00000"]:
        issues.append("glofas_point_ids not configured (still using placeholder)")

    if not cfg.data_root:
        issues.append("data_root not configured")
    else:
        data_path = Path(cfg.data_root)
        if not data_path.exists():
            issues.append(f"data_root path does not exist: {cfg.data_root}")

    if cfg.evt.threshold_m3s <= 0:
        issues.append("EVT threshold must be positive (still at placeholder 0.0)")

    if cfg.evt.run_length_days < 1:
        issues.append("run_length_days must be at least 1")

    if cfg.evt.gpd_scale_sigma <= 0:
        issues.append("GPD scale parameter must be positive")

    if cfg.evt.gpd_shape_xi < -1 or cfg.evt.gpd_shape_xi > 1:
        issues.append(
            f"GPD shape parameter {cfg.evt.gpd_shape_xi} is outside reasonable range [-1, 1]"
        )

    if cfg.evt.event_rate_per_year <= 0:
        issues.append("event_rate_per_year must be positive (still at placeholder)")

    if cfg.evt.event_rate_per_year > 100:
        issues.append(f"event_rate_per_year {cfg.evt.event_rate_per_year} seems unreasonably high")

    if cfg.vulnerability.depth_threshold_m < 0:
        issues.append("depth_threshold_m must be non-negative")

    if cfg.vulnerability.depth_threshold_m > 5:
        issues.append(f"depth_threshold_m {cfg.vulnerability.depth_threshold_m}m seems very high")

    if not (0 < cfg.vulnerability.impact_fraction <= 1):
        issues.append("impact_fraction must be between 0 and 1")

    return issues
