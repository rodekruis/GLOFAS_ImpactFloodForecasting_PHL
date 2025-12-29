"""Configuration utilities for loading basin and country settings.

This module provides helper functions to read configuration YAML files
into structured dataclass objects. Configurations are divided into two
levels:

* **Country** configuration (`ops/configs/country.yaml`): high level
  metadata for the country, such as default exposure dataset or
  projection parameters.  The country file can also list multiple
  basins belonging to that country.

* **Basin** configuration (`ops/configs/basins/<basin_id>.yaml`):
  fully parameterised settings for one basin, including EVT
  parameters, vulnerability assumptions and trigger thresholds.  This
  file is created after the calibration phase and feeds the
  operational pipeline.

If you need to create additional configuration objects, extend the
dataclasses in :mod:`philflood.basin` and update the loader
accordingly.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Dict, Union

import yaml

from .basin import BasinConfig


def load_basin_config(path: Union[str, Path]) -> BasinConfig:
    """Load a basin configuration from a YAML file.

    Parameters
    ----------
    path : str or Path
        The path to a YAML file containing a serialized BasinConfig.  The
        file must define keys that correspond exactly to the fields
        defined in :class:`philflood.basin.BasinConfig`.

    Returns
    -------
    BasinConfig
        A dataclass instance populated with the values from the YAML file.

    Notes
    -----
    You should not modify the returned object directly in operational
    code.  To update parameters, edit the YAML file during calibration
    or use the helper script ``generate_basin_config_from_calibration.py``.
    """
    path = Path(path)
    with open(path, "r", encoding="utf-8") as f:
        data: Dict[str, Dict[str, str]] = yaml.safe_load(f)
    # Compose nested dataclass objects
    # Ensure nested dictionaries exist
    evt_data = data.get("evt", {})
    vulnerability_data = data.get("vulnerability", {})
    trigger_data = data.get("trigger", {})
    basin_data = {
        k: v
        for k, v in data.items()
        if k not in {"evt", "vulnerability", "trigger"}
    }
    cfg = BasinConfig.from_dict(basin_data, evt_data, vulnerability_data, trigger_data)
    issues = cfg.validate()
    if issues:
        raise ValueError(f"Invalid basin config {path}:\n- " + "\n- ".join(issues))
    return cfg




def dump_basin_config(cfg: BasinConfig, path: Union[str, Path]) -> None:
    """Write a basin configuration to a YAML file.

    Parameters
    ----------
    cfg : BasinConfig
        The configuration object to serialize.
    path : str or Path
        Destination path for the YAML file.  Intermediate directories
        will be created if they do not exist.

    Notes
    -----
    This function will overwrite any existing file at the given path.
    It serialises nested dataclasses into nested dictionaries before
    dumping to YAML.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(asdict(cfg), f, sort_keys=False)