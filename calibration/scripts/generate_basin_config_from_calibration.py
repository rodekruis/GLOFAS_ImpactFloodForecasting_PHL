#!/usr/bin/env python3
"""Generate a BasinConfig YAML file from calibration results.

This script takes the outputs of the calibration notebooks or scripts
(e.g. fitted EVT parameters, vulnerability settings and chosen trigger
thresholds) and writes them into a YAML file conforming to the schema
defined by :class:`philflood.basin.BasinConfig`.  Use this after you
have run the calibration notebooks and made decisions about
parameters.

The script expects a JSON or YAML file containing a dictionary with
keys ``basin``, ``evt``, ``vulnerability`` and ``trigger``.  You can
create this manually or export it from a notebook.

Example::

    python calibration/scripts/generate_basin_config_from_calibration.py \
        --input calibration/output/agusan_calibration.yaml \
        --output ops/configs/basins/phl_agusan.yaml

This script is currently a stub.  You will need to implement the
parsing of your calibration output format and call
``philflood.config.dump_basin_config``.  See the documentation for
details on the expected structure.
"""

import argparse
from pathlib import Path
import json
import yaml

from philflood.domain.config import dump_basin_config
from philflood.domain.basin import BasinConfig, EVTConfig, VulnerabilityConfig, TriggerConfig


def generate_basin_yaml(input_path: str, output_path: str) -> None:
    with open(input_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    # Build BasinConfig from nested dicts
    basin_data = {
        k: v
        for k, v in data.items()
        if k not in {"evt", "vulnerability", "trigger"}
    }
    evt_cfg = EVTConfig(**data.get("evt", {}))
    vuln_cfg = VulnerabilityConfig(**data.get("vulnerability", {}))
    trig_cfg = TriggerConfig(**data.get("trigger", {}))
    cfg = BasinConfig(
        evt=evt_cfg,
        vulnerability=vuln_cfg,
        trigger=trig_cfg,
        **basin_data,
    )
    dump_basin_config(cfg, output_path)
    print(f"Written BasinConfig to {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate BasinConfig YAML from calibration output")
    parser.add_argument("--input", required=True, help="Path to calibration output YAML/JSON")
    parser.add_argument("--output", required=True, help="Destination YAML config file")
    args = parser.parse_args()
    generate_basin_yaml(args.input, args.output)