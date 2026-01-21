#!/usr/bin/env python3
"""Quick script to run EVT threshold diagnostics for a basin.

This script demonstrates how to drive the pyextremes library to
produce diagnostic plots for the peaks‑over‑threshold method.  It
should be run during the calibration phase.  The results can be
inspected interactively in a notebook or saved to disk.  After
selecting a threshold and fitting a GPD, you can store the parameters
in the basin configuration using `generate_basin_config_from_calibration.py`.

Usage::

    python calibration/scripts/run_evt_calibration.py --config ops/configs/basins/example_basin.yaml \
        --start 1980-01-01 --end 2020-12-31

This script is a placeholder.  You need to implement the actual
interaction with pyextremes inside the `calibrate_evt_for_basin`
function.  See the calibration notebooks for guidance.
"""

import argparse
from datetime import datetime
import sys

from philflood.domain.config import load_basin_config
from philflood.adapters.glofas import load_glofas_reanalysis_for_basin
from philflood.ev.peaks_over_threshold import extract_declust_pot
from philflood.ev.gpd_fit import fit_gpd_to_exceedances


def calibrate_evt_for_basin(cfg_path: str, start: str, end: str) -> None:
    cfg = load_basin_config(cfg_path)
    # Load discharge time series
    series = load_glofas_reanalysis_for_basin(cfg, start, end)
    # For now, take the first station only
    station = cfg.glofas_point_ids[0]
    ts = series[station].dropna()
    # Extract exceedances (no declustering yet)
    exceed = extract_declust_pot(ts, cfg.evt.threshold_m3s, cfg.evt.run_length_days)
    # Fit GPD (placeholder)
    model = fit_gpd_to_exceedances(exceed, cfg.evt.threshold_m3s)
    print(f"Fitted model for {cfg.basin_id}: xi={model.shape}, sigma={model.scale}, rate={model.rate}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run EVT calibration for a basin")
    parser.add_argument("--config", required=True, help="Path to basin YAML config")
    parser.add_argument("--start", required=True, help="Start date of calibration period (YYYY-MM-DD)")
    parser.add_argument("--end", required=True, help="End date of calibration period (YYYY-MM-DD)")
    args = parser.parse_args()
    calibrate_evt_for_basin(args.config, args.start, args.end)