#!/usr/bin/env python3
"""Run the flood trigger once for one or more basins.

This command line script reads basin configurations from YAML files,
loads a forecast for a specified issue date and evaluates the trigger
for each basin. Results can be output as CSV or JSON.

Usage::

    python ops/pipeline/run_monitoring_once.py --date 2025-12-19 \
        --basins ops/configs/basins/example_basin.yaml

    python ops/pipeline/run_monitoring_once.py --date 2025-12-19 \
        --basins ops/configs/basins/*.yaml --output results.json --format json

You can pass multiple ``--basins`` arguments; the script will run
each basin sequentially. For production use, consider the philflood CLI
which provides better error handling and logging.
"""

import argparse
import csv
import json
import sys
from datetime import date
from pathlib import Path
from typing import List

from philflood.domain.config import load_basin_config
from philflood.pipelines.monitoring import run_monitoring
from philflood.ops.logging_config import get_logger

logger = get_logger(__name__)


def main(issue_date: str, basin_files: List[str], output_file: str = None, 
         output_format: str = "csv", strict: bool = False) -> int:
    """Run monitoring for specified basins.
    
    Returns
    -------
    int
        Exit code (0 = success, 1 = error)
    """
    try:
        issue = date.fromisoformat(issue_date)
    except ValueError as e:
        logger.error(f"Invalid date format: {issue_date}. Use YYYY-MM-DD")
        return 1
    
    logger.info(f"Running monitoring for {len(basin_files)} basin(s) on {issue}")
    
    results = []
    errors = []
    
    for cfg_path in basin_files:
        try:
            logger.info(f"Processing {cfg_path}")
            cfg = load_basin_config(cfg_path)
            decision = run_monitoring(cfg, issue)
            results.append(decision.to_dict())
            
            if decision.triggered:
                logger.warning(
                    f"TRIGGER ACTIVATED for {decision.basin_id}: "
                    f"P={decision.probability_exceed:.1%}, "
                    f"People={decision.expected_people:,.0f}"
                )
        except Exception as e:
            error_msg = f"Error processing {cfg_path}: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
            if strict:
                return 1
    
    # Output results
    if output_file:
        output_path = Path(output_file)
        try:
            if output_format == "json":
                output_path.write_text(json.dumps(results, indent=2))
            else:  # CSV
                with open(output_path, "w", newline="") as f:
                    if results:
                        writer = csv.DictWriter(
                            f, 
                            fieldnames=["basin_id", "issue_date", "probability_exceed", 
                                       "expected_people", "triggered"]
                        )
                        writer.writeheader()
                        writer.writerows(results)
            logger.info(f"Results written to {output_path}")
        except Exception as e:
            logger.error(f"Failed to write output: {e}")
            return 1
    else:
        # Print as CSV to stdout
        if results:
            writer = csv.DictWriter(
                sys.stdout,
                fieldnames=["basin_id", "issue_date", "probability_exceed", 
                           "expected_people", "triggered"],
            )
            writer.writeheader()
            writer.writerows(results)
    
    # Summary
    triggered_count = sum(1 for r in results if r["triggered"])
    logger.info(
        f"Monitoring complete: {len(results)} basins processed, "
        f"{triggered_count} triggers, {len(errors)} errors"
    )
    
    return 0 if not errors or not strict else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run the flood trigger once for specified basins",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python ops/pipeline/run_monitoring_once.py --date 2025-12-29 --basins basin1.yaml basin2.yaml
  python ops/pipeline/run_monitoring_once.py --date 2025-12-29 --basins ops/configs/basins/*.yaml --output results.json --format json
""",
    )
    parser.add_argument("--date", required=True, help="Forecast issue date (YYYY-MM-DD)")
    parser.add_argument(
        "--basins",
        required=True,
        nargs="+",
        help="One or more basin YAML config files",
    )
    parser.add_argument("--output", help="Output file (optional, prints to stdout if omitted)")
    parser.add_argument(
        "--format", 
        choices=["csv", "json"], 
        default="csv",
        help="Output format (default: csv)"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit on first error (default: continue processing)"
    )
    args = parser.parse_args()
    sys.exit(main(args.date, args.basins, args.output, args.format, args.strict))