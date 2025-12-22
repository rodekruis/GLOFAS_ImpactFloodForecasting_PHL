#!/usr/bin/env python3
"""Run the flood trigger once for one or more basins.

This command line script reads basin configurations from YAML files,
loads a forecast for a specified issue date and evaluates the trigger
for each basin.  The results are printed to stdout as a CSV table.

Usage::

    python ops/pipeline/run_monitoring_once.py --date 2025-12-19 \
        --basins ops/configs/basins/example_basin.yaml

You can pass multiple ``--basins`` arguments; the script will run
each basin sequentially.  In the future this script could be
extended to fetch data automatically and send notifications.
"""

import argparse
from datetime import date
import csv
from typing import List

from philflood.config import load_basin_config
from philflood.ops.monitoring import run_monitoring


def main(issue_date: str, basin_files: List[str]) -> None:
    issue = date.fromisoformat(issue_date)
    results = []
    for cfg_path in basin_files:
        cfg = load_basin_config(cfg_path)
        decision = run_monitoring(cfg, issue)
        results.append(decision.to_dict())
    # Print as CSV to stdout
    writer = csv.DictWriter(
        fp := __import__("sys").stdout,
        fieldnames=["basin_id", "issue_date", "probability_exceed", "expected_people", "triggered"],
    )
    writer.writeheader()
    writer.writerows(results)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the flood trigger once for specified basins")
    parser.add_argument("--date", required=True, help="Forecast issue date (YYYY-MM-DD)")
    parser.add_argument(
        "--basins",
        required=True,
        nargs="+",
        help="One or more basin YAML config files",
    )
    args = parser.parse_args()
    main(args.date, args.basins)