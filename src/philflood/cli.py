from __future__ import annotations

import csv
import json
from datetime import date
from enum import Enum
from pathlib import Path
from typing import Optional

import typer

from philflood.domain.config import load_basin_config
from philflood.pipelines.monitoring import run_monitoring

app = typer.Typer(
    help="PhilFlood: Impact-Based Forecasting CLI for flood early action",
    no_args_is_help=True,
)

class OutputFormat(str, Enum):
    json = "json"
    csv = "csv"


def _resolve_basin_files(basins: list[Path], basin_dir: Optional[Path]) -> list[Path]:
    if basin_dir is not None:
        return sorted(basin_dir.glob("*.yaml"))
    return basins


@app.command()
def monitor(
    basins: list[Path] = typer.Argument(
        [],
        help="Basin YAML config files (space-separated). Optional if --basin-dir is provided.",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    date_str: Optional[str] = typer.Option(
        None, "--date", help="Forecast issue date (YYYY-MM-DD). Defaults to today."
    ),
    basin_dir: Optional[Path] = typer.Option(
        None,
        "--basin-dir",
        help="Directory containing basin configs (*.yaml).",
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", help="Output file path (JSON or CSV)."
    ),
    fmt: Optional[OutputFormat] = typer.Option(
        None, "--format", help="Output format. If omitted, inferred from --output suffix."
    ),
    strict: bool = typer.Option(False, "--strict", help="Exit on first error."),
) -> None:
    issue_date = date.fromisoformat(date_str) if date_str else date.today()

    basin_files = _resolve_basin_files(basins, basin_dir)

    if basin_dir is not None and not basin_files:
        typer.secho(f"❌ No basin configs found in {basin_dir}", err=True, fg=typer.colors.RED)
        raise typer.Exit(code=1)

    if not basin_files:
        typer.secho("❌ No basins specified. Provide BASINS... or use --basin-dir", err=True, fg=typer.colors.RED)
        raise typer.Exit(code=1)

    typer.echo(f"🔍 Running monitoring for {len(basin_files)} basin(s) on {issue_date}")
    results = []

    for basin_path in basin_files:
        try:
            cfg = load_basin_config(basin_path)
            decision = run_monitoring(cfg, issue_date)
            results.append(decision)

            status = "🚨 TRIGGERED" if decision.triggered else "✓ No trigger"
            typer.echo(f"\n{status} - {decision.basin_id}")
            typer.echo(f"  Probability: {decision.probability_exceed:.1%}")
            typer.echo(f"  Expected people affected: {decision.expected_people:,.0f}")
        except Exception as e:
            typer.secho(f"❌ Error processing {basin_path}: {e}", err=True, fg=typer.colors.RED)
            if strict:
                raise typer.Exit(code=1)

    if output:
        output.parent.mkdir(parents=True, exist_ok=True)

        if fmt is None:
            fmt = OutputFormat.json if output.suffix.lower() == ".json" else OutputFormat.csv

        if fmt == OutputFormat.json:
            output.write_text(json.dumps([r.to_dict() for r in results], indent=2), encoding="utf-8")
        else:
            with output.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=["basin_id", "issue_date", "probability_exceed", "expected_people", "triggered"],
                )
                writer.writeheader()
                writer.writerows([r.to_dict() for r in results])

        typer.echo(f"\n💾 Results saved to {output}")

@app.command()
def validate(
    basins: list[Path] = typer.Argument(
        [],
        help="Basin YAML config files (space-separated). Optional if --basin-dir is provided.",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    basin_dir: Optional[Path] = typer.Option(
        None,
        "--basin-dir",
        help="Directory containing basin configs (*.yaml).",
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
    ),
) -> None:

    from philflood.pipelines.validation import validate_basin_config

    basin_files = _resolve_basin_files(basins, basin_dir)

    if basin_dir is not None and not basin_files:
        typer.secho(f"❌ No basin configs found in {basin_dir}", err=True, fg=typer.colors.RED)
        raise typer.Exit(code=1)

    if not basin_files:
        typer.secho("❌ No basins specified. Provide BASINS... or use --basin-dir", err=True, fg=typer.colors.RED)
        raise typer.Exit(code=1)

    all_valid = True
    for basin_path in basin_files:
        typer.echo(f"\n🔍 Validating {basin_path}...")
        issues = validate_basin_config(basin_path)
        if not issues:
            typer.echo(f"✓ {basin_path.name} is valid")
        else:
            all_valid = False
            typer.secho(f"❌ {basin_path.name} has {len(issues)} issue(s):", fg=typer.colors.RED)
            for issue in issues:
                typer.echo(f"   - {issue}")

    raise typer.Exit(code=0 if all_valid else 1)


@app.command()
def calibrate(
    basin: Path = typer.Option(
        ...,
        "--basin",
        help="Basin YAML config file.",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    start: str = typer.Option(..., "--start", help="Start date (YYYY-MM-DD)."),
    end: str = typer.Option(..., "--end", help="End date (YYYY-MM-DD)."),
) -> None:
    from philflood.calibration.run_evt_calibration import calibrate_evt_for_basin

    try:
        calibrate_evt_for_basin(basin, start, end)
        typer.echo("\n✓ Calibration complete. Review outputs and update config.")
    except Exception as e:
        typer.secho(f"❌ Calibration failed: {e}", err=True, fg=typer.colors.RED)
        raise typer.Exit(code=1)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
