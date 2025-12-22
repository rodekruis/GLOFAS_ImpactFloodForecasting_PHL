#!/usr/bin/env python3
"""Scheduled monitoring runner.

This script demonstrates how you might schedule recurring trigger
evaluations, e.g. using cron or a simple loop.  For each run it
invokes ``run_monitoring_once.py`` with the current date.  In a
production system you would integrate this into an airflow DAG or
another orchestrator.
"""

import time
from datetime import date
from pathlib import Path
import subprocess


def schedule_monitoring(basin_dir: str, interval_hours: float = 24.0) -> None:
    """Run monitoring at a fixed interval.

    Parameters
    ----------
    basin_dir : str
        Directory containing basin YAML configurations.
    interval_hours : float, optional
        Time between runs, in hours.  Defaults to 24 hours.

    Notes
    -----
    This script simply sleeps between runs.  It is not robust to
    errors or overlaps.  Replace with a proper scheduler in
    production.
    """
    while True:
        today_str = date.today().isoformat()
        basin_files = list(Path(basin_dir).glob("*.yaml"))
        if not basin_files:
            print(f"No basins found in {basin_dir}")
        else:
            args = [
                "python",
                "ops/pipeline/run_monitoring_once.py",
                "--date",
                today_str,
                "--basins",
            ] + [str(b) for b in basin_files]
            subprocess.run(args, check=False)
        time.sleep(interval_hours * 3600)


if __name__ == "__main__":
    # Example usage: run once per day for all basins in ops/configs/basins/
    schedule_monitoring("ops/configs/basins", 24.0)