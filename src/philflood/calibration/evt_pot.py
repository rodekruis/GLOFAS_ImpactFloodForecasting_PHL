from __future__ import annotations

import gc
from dataclasses import dataclass
from typing import Optional, Tuple

import pandas as pd

try:
    from pyextremes import EVA
except Exception:  # pragma: no cover
    EVA = None


@dataclass(frozen=True)
class POTResult:
    threshold_m3s: float
    run_length_days: int
    lambda_events_per_year: float
    coverage_years: float
    events: pd.DataFrame  # columns: date, discharge_m3s
    annual_counts: pd.DataFrame  # year, n_events


def _require_pyextremes():
    if EVA is None:
        raise ImportError(
            "pyextremes is required for POT extraction. Install with: pip install pyextremes"
        )


def _cleanup_eva_memory(eva: EVA) -> None:
    """Clear memory-heavy EVA attributes after use to prevent accumulation."""
    if eva is None:
        return
    
    # Clear internal EVA model and cache data
    for attr in ['model', 'extremes', '_extremes', '_samples']:
        if hasattr(eva, attr):
            try:
                setattr(eva, attr, None)
            except Exception:
                # Some EVA attributes may be read-only or have restrictive setters;
                # continue cleanup of remaining attributes even if one fails
                pass
    
    # Force garbage collection
    gc.collect()



def _build_eva(series: pd.Series) -> EVA:
    """Construct an EVA instance compatible with older/newer pyextremes APIs."""
    try:
        return EVA(series, extremes_type="high")  # pyextremes<=2.4
    except TypeError:
        return EVA(series)  # pyextremes>=2.5


def _get_pot_extremes(eva: EVA, threshold_m3s: float, r: str) -> pd.Series:
    """Extract POT extremes and return them (pyextremes stores them on eva.extremes)."""
    last_err = None
    for kwargs in (
        {"extremes_type": "high"},
        {"extremes": "high"},
        {},
    ):
        try:
            eva.get_extremes(method="POT", threshold=float(threshold_m3s), r=r, **kwargs)
            return eva.extremes  # <-- key fix: pyextremes returns None, stores here
        except TypeError as e:
            last_err = e
            continue
    # surface the last signature error if none worked
    if last_err is not None:
        raise last_err
    raise RuntimeError("Failed to extract POT extremes with all parameter combinations")


def pot_extract(
    discharge_series: pd.Series,
    threshold_m3s: float,
    run_length_days: int = 5,
) -> POTResult:
    """Extract declustered POT extremes using pyextremes EVA.

    Uses EVA.get_extremes(method='POT', threshold=..., r='5D').
    
    Note: EVA model objects are cleaned up after use to prevent memory accumulation.
    """
    _require_pyextremes()

    if discharge_series is None or len(discharge_series) == 0:
        raise ValueError("discharge_series is empty")

    s = discharge_series.dropna().copy()
    s = s.sort_index()
    if not isinstance(s.index, pd.DatetimeIndex):
        raise TypeError("discharge_series must have a DatetimeIndex")

    r = f"{int(run_length_days)}D"

    eva = _build_eva(s)
    try:
        extremes = _get_pot_extremes(eva, threshold_m3s=threshold_m3s, r=r)

        if extremes is None or len(extremes) == 0:
            # No events above threshold
            coverage_years = float(len(s) / 365.25)
            annual = pd.DataFrame({"year": [], "n_events": []})
            return POTResult(
                threshold_m3s=float(threshold_m3s),
                run_length_days=int(run_length_days),
                lambda_events_per_year=0.0,
                coverage_years=coverage_years,
                events=pd.DataFrame({"date": [], "discharge_m3s": []}),
                annual_counts=annual,
            )

        # Normalize extremes to a clean two-column DataFrame: date, discharge_m3s
        if isinstance(extremes, pd.Series):
            ev_series = extremes.copy()
            ev_series.index = pd.to_datetime(ev_series.index)
            ev = pd.DataFrame({"date": ev_series.index, "discharge_m3s": ev_series.values})
        else:
            ev = extremes.copy()
        ev.index = pd.to_datetime(ev.index)
        discharge_col = "discharge_m3s" if "discharge_m3s" in ev.columns else ev.columns[0]
        ev = pd.DataFrame({"date": ev.index, "discharge_m3s": ev[discharge_col].values})

        ev = ev.sort_values("date")

        # Coverage years (based on observed days with data)
        coverage_years = float(len(s) / 365.25)
        if coverage_years <= 0:
            raise RuntimeError("coverage_years computed as 0; check time series length")

        ev["year"] = ev["date"].dt.year
        annual_counts = ev.groupby("year").size().rename("n_events").reset_index()

        lambda_hat = float(len(ev) / coverage_years)

        return POTResult(
            threshold_m3s=float(threshold_m3s),
            run_length_days=int(run_length_days),
            lambda_events_per_year=lambda_hat,
            coverage_years=coverage_years,
            events=ev[["date", "discharge_m3s"]].copy(),
            annual_counts=annual_counts,
        )
    finally:
        # Clean up EVA model to prevent memory accumulation
        _cleanup_eva_memory(eva)


def fit_gpd_to_pot(
    discharge_series: pd.Series,
    threshold_m3s: float,
    run_length_days: int = 5,
) -> Optional[Tuple[float, float]]:
    """Fit a GPD model to POT extremes and return (xi, sigma).

    This is optional and mainly for reporting; the locked requirement is to output
    threshold + declustered events + lambda.

    Returns None if fitting fails.
    
    Note: EVA model objects are cleaned up after use to prevent memory accumulation.
    """
    _require_pyextremes()

    s = discharge_series.dropna().copy()
    s = s.sort_index()
    r = f"{int(run_length_days)}D"

    eva = _build_eva(s)
    try:
        _get_pot_extremes(eva, threshold_m3s=threshold_m3s, r=r)
        eva.fit_model(distribution="genpareto")
        # pyextremes stores fit params on eva.model; expose in a stable way.
        params = getattr(eva, "model", None)
        if params is None:
            return None
        # Most scipy-like parameterizations: shape (c/xi), loc, scale (sigma)
        # We fix loc at 0 (because threshold is applied), but different versions may store.
        dist_params = getattr(params, "params", None)
        if dist_params is None:
            dist_params = getattr(params, "fit_parameters", None)
        if dist_params is None:
            return None

        # Attempt to extract keys
        if isinstance(dist_params, dict):
            xi = float(dist_params.get("shape", dist_params.get("c", 0.0)))
            sigma = float(dist_params.get("scale", 0.0))
            return xi, sigma

        # Fallback: tuple/list
        if isinstance(dist_params, (tuple, list)) and len(dist_params) >= 3:
            xi = float(dist_params[0])
            sigma = float(dist_params[2])
            return xi, sigma

        return None
    except Exception:
        return None
    finally:
        # Clean up EVA model to prevent memory accumulation
        _cleanup_eva_memory(eva)
