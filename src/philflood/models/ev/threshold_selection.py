"""Threshold selection for Peaks-Over-Threshold (POT) analysis.

This module provides automated and manual threshold selection methods for
identifying extreme value events in hydrological time series. It uses the
Generalized Pareto Distribution (GPD) fitting and parameter stability
diagnostics to recommend optimal thresholds.

The workflow supports both interactive selection (for calibration) and
batch automated selection (for operational processing).
"""

from __future__ import annotations

from typing import Tuple, Dict, List, Any, Optional
import warnings

import numpy as np
import pandas as pd
from scipy import stats
from pyextremes import EVA


def compute_mrl(
    series: pd.Series,
    candidate_thresholds: List[float],
) -> pd.DataFrame:
    """Compute Mean Residual Life (mean excess) for a set of candidate thresholds.

    The MRL function e(u) = E[X - u | X > u] should be approximately linear and
    increasing in u when the tail follows a GPD. Linearity over a range of u
    is the classical graphical diagnostic for threshold validity.

    Parameters
    ----------
    series : pd.Series
        Discharge time series (no NaNs required by caller).
    candidate_thresholds : list of float
        Threshold values to evaluate. Typically the same grid used in threshold selection.

    Returns
    -------
    pd.DataFrame
        Columns: threshold, n_exceed, mrl, mrl_se, mrl_linear_ok.
        - mrl: mean excess E[X - u | X > u]
        - mrl_se: standard error of the mean excess = std / sqrt(n_exceed)
        - mrl_linear_ok: True if this threshold lies in a linearly-increasing MRL region.
          Computed by fitting a line to all (threshold, mrl) pairs and checking that
          the residual for this point is within 1.5 * median absolute residual of the fit.
    """
    vals = series.dropna().values
    rows = []
    for u in sorted(candidate_thresholds):
        exceedances = vals[vals > u] - u
        n = len(exceedances)
        if n >= 2:
            mrl = float(exceedances.mean())
            mrl_se = float(exceedances.std(ddof=1) / np.sqrt(n))
        else:
            mrl = np.nan
            mrl_se = np.nan
        rows.append({"threshold": float(u), "n_exceed": int(n), "mrl": mrl, "mrl_se": mrl_se})

    df = pd.DataFrame(rows)

    # Linearity flag: fit linear model to valid (threshold, mrl) pairs; flag outliers
    valid = df.dropna(subset=["mrl"])
    df["mrl_linear_ok"] = True  # default True when insufficient data to test
    if len(valid) >= 3:
        x = valid["threshold"].values
        y = valid["mrl"].values
        # Least-squares linear fit
        coeffs = np.polyfit(x, y, 1)
        y_pred = np.polyval(coeffs, x)
        residuals = np.abs(y - y_pred)
        mad = float(np.median(residuals))
        threshold_val = 1.5 * mad if mad > 0 else np.inf
        linear_ok = residuals <= threshold_val
        for i, idx in enumerate(valid.index):
            df.at[idx, "mrl_linear_ok"] = bool(linear_ok[i])

    return df


def auto_select_threshold_pot(
    time_series: pd.Series,
    candidate_quantiles: List[float] = None,
    run_length_days: int = 5,
    min_events_total: int = 10,
    stability_tol_xi: float = 0.1,
    stability_tol_sigma: float = 0.15,
    dispersion_range: Tuple[float, float] = (0.5, 2.5),
    verbose: bool = False,
) -> Tuple[float, str, pd.DataFrame]:
    """Automatically select an optimal POT threshold using stability criteria.

    This function implements a 3-tier fallback strategy:
    
    **Tier 1 (Recommended):** Lowest threshold that maintains stable GPD parameters
    across adjacent quantiles (ξ and σ changes < tolerance).
    
    **Tier 2 (Conservative):** If no stable threshold found, use lowest quantile
    with sufficient events and reasonable dispersion.
    
    **Tier 3 (Last resort):** If all else fails, use 95th percentile.

    Parameters
    ----------
    time_series : pd.Series
        Time series of discharge values with datetime index. Must be sorted
        in time and contain sufficient data (ideally >10 years).
    candidate_quantiles : list of float, optional
        Quantile levels (0-1) to test as potential thresholds.
        Default: [0.80, 0.85, 0.90, 0.92, 0.95, 0.97, 0.99, 0.995].
    run_length_days : int, optional
        Minimum days between independent events (run-length declustering).
        Default: 5 days (typical for river hydrographs).
    min_events_total : int, optional
        Minimum number of events required across entire period to consider
        a threshold viable. Default: 10 events.
    stability_tol_xi : float, optional
        Tolerance for shape parameter (ξ) stability between adjacent thresholds.
        Recommended: 0.05-0.15. Default: 0.1.
    stability_tol_sigma : float, optional
        Tolerance for scale parameter (σ) stability between adjacent thresholds.
        Recommended: 0.10-0.20. Default: 0.15.
    dispersion_range : tuple of float, optional
        Acceptable range for the annual dispersion index (variance/mean).
        Outside this range suggests under/over-dispersion (clustering).
        Default: (0.5, 2.5).
    verbose : bool, optional
        If True, print detailed diagnostic information. Default: False.

    Returns
    -------
    tuple
        A tuple of (threshold, status_str, diagnostics_df) where:
        
        - **threshold** (float): Selected POT threshold (m³/s or native units)
        - **status_str** (str): Labels the tier used: "stable", "conservative", or "fallback"
        - **diagnostics_df** (pd.DataFrame): Detailed diagnostics for all candidate
          thresholds, useful for manual inspection and override decisions

    Notes
    -----
    The function prints detailed step-by-step logic if `verbose=True`, helping
    practitioners understand which tier was triggered and why. This is useful
    for building trust in automated decisions during calibration workshops.

    Examples
    --------
    >>> import pandas as pd
    >>> from philflood.models.ev.threshold_selection import auto_select_threshold_pot
    >>> # Load discharge time series (datetime index, sorted)
    >>> discharge = pd.read_csv('discharge.csv', index_col='date', parse_dates=True)['Q']
    >>> u_opt, tier, diagnostics = auto_select_threshold_pot(
    ...     discharge,
    ...     run_length_days=5,
    ...     min_events_total=15,
    ...     verbose=True
    ... )
    >>> print(f"Selected threshold: {u_opt:.2f} (Tier: {tier})")
    >>> print(diagnostics)
    """
    if candidate_quantiles is None:
        candidate_quantiles = [0.80, 0.85, 0.90, 0.92, 0.95, 0.97, 0.99, 0.995]

    # === PREPROCESSING ===
    ts_clean = time_series.dropna().sort_index()
    if len(ts_clean) == 0:
        raise ValueError("Time series is empty after removing NaN values")

    if verbose:
        print(f"[auto_select_threshold_pot] Received parameters:")
        print(f"  time_series length: {len(ts_clean)} samples")
        print(f"  candidate_quantiles: {candidate_quantiles}")
        print(f"  run_length_days: {run_length_days}")
        print(f"  min_events_total: {min_events_total}")
        print(f"  stability_tol_xi: {stability_tol_xi}, stability_tol_sigma: {stability_tol_sigma}")
        print(f"  dispersion_range: {dispersion_range}\n")

    # === COMPUTE THRESHOLD CANDIDATES ===
    candidate_thresholds = sorted(set(float(ts_clean.quantile(q)) for q in candidate_quantiles))
    
    # === EVALUATE EACH THRESHOLD ===
    diagnostics = []
    for u in candidate_thresholds:
        diag = _evaluate_threshold(ts_clean, u, run_length_days)
        diagnostics.append(diag)

    diag_df = pd.DataFrame(diagnostics).sort_values("threshold").reset_index(drop=True)

    # === TIER 1: STABLE THRESHOLD ===
    if verbose:
        print("=" * 70)
        print("TIER 1: Finding STABLE threshold (both ξ and σ stable across range)")
        print("=" * 70)

    stable_thresholds = []
    for idx in range(len(diag_df) - 1):
        u_curr = diag_df.loc[idx, "threshold"]
        u_next = diag_df.loc[idx + 1, "threshold"]
        
        xi_curr = diag_df.loc[idx, "gpd_xi"]
        xi_next = diag_df.loc[idx + 1, "gpd_xi"]
        sigma_curr = diag_df.loc[idx, "gpd_sigma"]
        sigma_next = diag_df.loc[idx + 1, "gpd_sigma"]
        n_events_curr = diag_df.loc[idx, "n_events"]

        # Check both parameters and event count
        if (n_events_curr >= min_events_total and
            np.isfinite(xi_curr) and np.isfinite(xi_next) and
            np.isfinite(sigma_curr) and np.isfinite(sigma_next)):
            
            xi_stable = abs(xi_next - xi_curr) < stability_tol_xi
            sigma_stable = abs(sigma_next - sigma_curr) < stability_tol_sigma

            if xi_stable and sigma_stable:
                stable_thresholds.append(u_curr)
                if verbose:
                    print(f"  ✓ u={u_curr:.2f}: Δξ={abs(xi_next-xi_curr):.4f}, Δσ={abs(sigma_next-sigma_curr):.4f} (STABLE)")
            else:
                if verbose:
                    print(f"  ✗ u={u_curr:.2f}: Δξ={abs(xi_next-xi_curr):.4f}, Δσ={abs(sigma_next-sigma_curr):.4f} (unstable)")

    if stable_thresholds:
        pick_u = min(stable_thresholds)  # Prefer lowest stable threshold
        pick_status = "stable"
        if verbose:
            print(f"\n✓ TIER 1 SUCCESS: Picked u*={pick_u:.2f} (lowest stable threshold)")
        return pick_u, pick_status, diag_df

    # === TIER 2: CONSERVATIVE FALLBACK ===
    if verbose:
        print("\n" + "=" * 70)
        print("TIER 2: No stable threshold found, using CONSERVATIVE fallback")
        print("=" * 70)

    conservative_candidates = diag_df[
        (diag_df["n_events"] >= min_events_total) &
        (diag_df["dispersion"] >= dispersion_range[0]) &
        (diag_df["dispersion"] <= dispersion_range[1])
    ]

    if len(conservative_candidates) > 0:
        pick_u = float(conservative_candidates["threshold"].iloc[0])  # Lowest
        pick_status = "conservative"
        if verbose:
            print(f"✓ TIER 2 SUCCESS: Picked u*={pick_u:.2f} (lowest with sufficient events)")
            print(f"  n_events={float(conservative_candidates['n_events'].iloc[0]):.0f}, "
                  f"dispersion={float(conservative_candidates['dispersion'].iloc[0]):.3f}")
        return pick_u, pick_status, diag_df

    # === TIER 3: LAST RESORT ===
    if verbose:
        print("\n" + "=" * 70)
        print("TIER 3: Fallback to 95th percentile (last resort)")
        print("=" * 70)

    pick_u = float(ts_clean.quantile(0.95))
    pick_status = "fallback"
    if verbose:
        print(f"✓ TIER 3 FALLBACK: Using u*={pick_u:.2f} (95th percentile)")
        print("  Warning: Threshold selection did not converge to stable parameters.")
        print("  Consider manual review or longer data period.")

    return pick_u, pick_status, diag_df


def _evaluate_threshold(
    time_series: pd.Series,
    threshold: float,
    run_length_days: int,
) -> Dict[str, Any]:
    """Evaluate GPD fit and dispersion for a single threshold.

    Helper function for auto_select_threshold_pot. Returns a dict of
    diagnostics that are aggregated into a diagnostic DataFrame.

    Parameters
    ----------
    time_series : pd.Series
        Clean discharge time series (no NaNs, sorted).
    threshold : float
        POT threshold to evaluate.
    run_length_days : int
        Run-length declustering window in days.

    Returns
    -------
    dict
        Diagnostics including: threshold, n_events, lambda_per_year,
        gpd_xi (shape), gpd_sigma (scale), dispersion, etc.
    """
    try:
        # Extract events using POT with declustering
        eva = EVA(time_series)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            eva.get_extremes(
                method="POT",
                threshold=float(threshold),
                r=f"{int(run_length_days)}D",
                extremes_type="high",
            )
        events = eva.extremes

        if len(events) == 0:
            return {
                "threshold": float(threshold),
                "n_events": 0,
                "lambda_per_year": 0.0,
                "gpd_xi": np.nan,
                "gpd_sigma": np.nan,
                "dispersion": np.nan,
            }

        # Compute annual frequency
        years = np.arange(time_series.index.min().year, time_series.index.max().year + 1)
        annual_counts = events.groupby(events.index.year).size().reindex(years, fill_value=0)
        lambda_events = annual_counts.mean()
        
        # Compute dispersion (variance/mean of annual counts)
        if lambda_events > 0:
            dispersion = float(annual_counts.var(ddof=1) / lambda_events)
        else:
            dispersion = np.nan

        # Fit GPD to excesses
        excesses = (events - threshold).values
        try:
            # Use scipy stats for GPD fit (shape, loc, scale)
            # scipy genpareto uses the same sign convention as EVT:
            #   CDF = 1 - (1 + c*x/scale)^(-1/c)  matches  1 - (1 + ξ*y/σ)^(-1/ξ)
            # so scipy shape c = EVT ξ directly (no negation needed).
            params = stats.genpareto.fit(excesses, floc=0)
            xi = params[0]       # EVT shape ξ: positive → heavy tail (Fréchet)
            gpd_scale = params[2]
        except Exception:
            xi = np.nan
            gpd_scale = np.nan

        return {
            "threshold": float(threshold),
            "n_events": int(len(events)),
            "lambda_per_year": float(lambda_events),
            "gpd_xi": float(xi),
            "gpd_sigma": float(gpd_scale),
            "dispersion": float(dispersion),
        }

    except Exception as e:
        # If fitting fails, return NaN diagnostics
        return {
            "threshold": float(threshold),
            "n_events": 0,
            "lambda_per_year": 0.0,
            "gpd_xi": np.nan,
            "gpd_sigma": np.nan,
            "dispersion": np.nan,
            "error": str(e),
        }
