"""Configuration validation utilities for operational deployment.

This module checks that basin configuration files are complete, consistent
and ready for operational use. It validates:
- Required fields are present and have sensible values
- Data paths exist and are accessible
- EVT parameters are physically reasonable
- Trigger thresholds are properly configured

Use this before deploying a new basin configuration to production.
"""

from pathlib import Path
from typing import List, Union

from philflood.domain.config import load_basin_config
from philflood.domain.basin import BasinConfig


def validate_basin_config(config_path: Union[str, Path]) -> List[str]:
    """Validate a basin configuration file.
    
    Parameters
    ----------
    config_path : str or Path
        Path to the basin YAML configuration file.
    
    Returns
    -------
    List[str]
        List of validation issues. Empty list means config is valid.
    
    Examples
    --------
    >>> issues = validate_basin_config("ops/configs/basins/example.yaml")
    >>> if issues:
    ...     for issue in issues:
    ...         print(f"⚠️ {issue}")
    """
    issues = []
    
    try:
        cfg = load_basin_config(config_path)
    except Exception as e:
        return [f"Failed to load config: {e}"]
    
    # Basic metadata validation
    if not cfg.basin_id or cfg.basin_id == "example_basin":
        issues.append("basin_id not set or still using placeholder value")
    
    if not cfg.country_iso3:
        issues.append("country_iso3 is required")
    
    if not cfg.glofas_point_ids or cfg.glofas_point_ids == ["PHL_00000"]:
        issues.append("glofas_point_ids not configured (still using placeholder)")
    
    # Data paths validation
    if cfg.data_root and cfg.data_root != "<path/to/basin/data>":
        data_path = Path(cfg.data_root)
        if not data_path.exists():
            issues.append(f"data_root path does not exist: {cfg.data_root}")
    else:
        issues.append("data_root not configured (placeholder value)")
    
    # EVT parameter validation
    if cfg.evt.threshold_m3s <= 0:
        issues.append("EVT threshold must be positive (still at placeholder 0.0)")
    
    if cfg.evt.run_length_days < 1:
        issues.append("run_length_days must be at least 1")
    
    if cfg.evt.gpd_scale_sigma <= 0:
        issues.append("GPD scale parameter must be positive")
    
    if cfg.evt.gpd_shape_xi < -1 or cfg.evt.gpd_shape_xi > 1:
        issues.append(f"GPD shape parameter {cfg.evt.gpd_shape_xi} is outside reasonable range [-1, 1]")
    
    if cfg.evt.event_rate_per_year <= 0:
        issues.append("event_rate_per_year must be positive (still at placeholder)")
    
    if cfg.evt.event_rate_per_year > 100:
        issues.append(f"event_rate_per_year {cfg.evt.event_rate_per_year} seems unreasonably high")
    
    # Vulnerability validation
    if cfg.vulnerability.depth_threshold_m < 0:
        issues.append("depth_threshold_m must be non-negative")
    
    if cfg.vulnerability.depth_threshold_m > 5:
        issues.append(f"depth_threshold_m {cfg.vulnerability.depth_threshold_m}m seems very high")
    
    if not (0 < cfg.vulnerability.impact_fraction <= 1):
        issues.append("impact_fraction must be between 0 and 1")
    
    # Trigger configuration validation
    if cfg.trigger.impact_threshold_people <= 0:
        issues.append("impact_threshold_people must be positive")
    
    if not (0 < cfg.trigger.probability_threshold <= 1):
        issues.append("probability_threshold must be between 0 and 1")
    
    if cfg.trigger.max_lead_time_days < 1:
        issues.append("max_lead_time_days must be at least 1")
    
    if cfg.trigger.max_lead_time_days > 30:
        issues.append(f"max_lead_time_days {cfg.trigger.max_lead_time_days} exceeds typical forecast horizon")
    
    return issues


def validate_all_basins(basin_dir: Union[str, Path]) -> dict:
    """Validate all basin configurations in a directory.
    
    Parameters
    ----------
    basin_dir : str or Path
        Directory containing basin YAML files.
    
    Returns
    -------
    dict
        Dictionary mapping basin file names to lists of validation issues.
    """
    basin_path = Path(basin_dir)
    results = {}
    
    for yaml_file in basin_path.glob("*.yaml"):
        issues = validate_basin_config(yaml_file)
        results[yaml_file.name] = issues
    
    return results


if __name__ == "__main__":
    # Quick command-line validation
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python -m philflood.ops.validation <basin_config.yaml>")
        sys.exit(1)
    
    config_file = sys.argv[1]
    issues = validate_basin_config(config_file)
    
    if not issues:
        print(f"✓ {config_file} is valid")
        sys.exit(0)
    else:
        print(f"❌ {config_file} has {len(issues)} issue(s):")
        for issue in issues:
            print(f"  - {issue}")
        sys.exit(1)
