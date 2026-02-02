from __future__ import annotations

import gc
from dataclasses import dataclass, field
from typing import Optional, Tuple, Union

import numpy as np
import pandas as pd

try:
    from pyextremes import EVA
except Exception:  # pragma: no cover
    EVA = None

try:
    from scipy import stats
except Exception:  # pragma: no cover
    stats = None


@dataclass(frozen=True)
class POTResult:
    threshold_m3s: float
    run_length_days: int
    lambda_events_per_year: float
    coverage_years: float
    events: pd.DataFrame  # columns: date, discharge_m3s
    annual_counts: pd.DataFrame  # year, n_events
    extraction_method: str = "pour_point"  # "pour_point" or "cell_level"
    extraction_metadata: dict = field(default_factory=dict)  # Optional: additional metadata


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
    extraction_method: str = "pour_point",
    extraction_metadata: Optional[dict] = None,
) -> POTResult:
    """Extract declustered POT extremes using pyextremes EVA.

    Uses EVA.get_extremes(method='POT', threshold=..., r='5D').
    
    Args:
        discharge_series: Time series of discharge values
        threshold_m3s: POT threshold
        run_length_days: Declustering interval (days)
        extraction_method: "pour_point" or "cell_level"
        extraction_metadata: Optional dict with additional context (e.g., n_cells, coordinates)
    
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
                extraction_method=extraction_method,
                extraction_metadata=extraction_metadata or {},
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
            extraction_method=extraction_method,
            extraction_metadata=extraction_metadata or {},
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


def return_period_to_discharge_pot(
    T: Union[float, np.ndarray],
    u: float,
    xi: float,
    sigma: float,
    lambda_u: float,
    tol_exponential: float = 1e-6,
) -> Union[float, np.ndarray]:
    """Convert return period to discharge using POT formula.
    
    Formula:
        - If |ξ| > tol_exponential:
          q_T = u + (σ/ξ) * ((λ*T)^ξ - 1)
        - If |ξ| ≤ tol_exponential (exponential limit):
          q_T = u + σ * ln(λ*T)
    
    Parameters
    ----------
    T : float or np.ndarray
        Return period(s) in years.
    u : float
        POT threshold (m³/s).
    xi : float
        GPD shape parameter (dimensionless).
    sigma : float
        GPD scale parameter (m³/s).
    lambda_u : float
        Poisson event rate (events/year).
    tol_exponential : float, optional
        Tolerance for treating ξ as zero (exponential case). Default 1e-6.
    
    Returns
    -------
    float or np.ndarray
        Discharge value(s) in m³/s.
    
    Raises
    ------
    ValueError
        If sigma <= 0, lambda_u <= 0, or T <= 0.
    
    Examples
    --------
    >>> return_period_to_discharge_pot(T=10, u=100, xi=0.1, sigma=50, lambda_u=2)
    >>> return_period_to_discharge_pot(T=[2, 10, 100], u=100, xi=0, sigma=50, lambda_u=2)
    """
    # Input validation
    if sigma <= 0:
        raise ValueError(f"sigma must be > 0, got {sigma}")
    if lambda_u <= 0:
        raise ValueError(f"lambda_u must be > 0, got {lambda_u}")
    
    T_arr = np.atleast_1d(T)
    if np.any(T_arr <= 0):
        raise ValueError("All return periods must be > 0")
    
    # Check for exponential limit
    if np.abs(xi) <= tol_exponential:
        # Exponential case: q = u + σ * ln(λ*T)
        q = u + sigma * np.log(lambda_u * T_arr)
    else:
        # GPD case: q = u + (σ/ξ) * ((λ*T)^ξ - 1)
        q = u + (sigma / xi) * (np.power(lambda_u * T_arr, xi) - 1.0)
    
    # Return scalar if input was scalar
    if np.isscalar(T):
        return float(q[0])
    return q


def discharge_to_return_period_pot(
    q: Union[float, np.ndarray],
    u: float,
    xi: float,
    sigma: float,
    lambda_u: float,
    tol_exponential: float = 1e-6,
) -> Union[float, np.ndarray]:
    """Convert discharge to return period using POT inverse formula.
    
    Formula:
        - If |ξ| > tol_exponential:
          T(q) = (1/λ) * [1 + ξ*(q-u)/σ]^(1/ξ)
        - If |ξ| ≤ tol_exponential (exponential limit):
          T(q) = (1/λ) * exp[(q-u)/σ]
    
    Parameters
    ----------
    q : float or np.ndarray
        Discharge value(s) in m³/s.
    u : float
        POT threshold (m³/s).
    xi : float
        GPD shape parameter (dimensionless).
    sigma : float
        GPD scale parameter (m³/s).
    lambda_u : float
        Poisson event rate (events/year).
    tol_exponential : float, optional
        Tolerance for treating ξ as zero (exponential case). Default 1e-6.
    
    Returns
    -------
    float or np.ndarray
        Return period(s) in years. Returns np.nan for q < u.
    
    Raises
    ------
    ValueError
        If sigma <= 0 or lambda_u <= 0.
    
    Examples
    --------
    >>> discharge_to_return_period_pot(q=150, u=100, xi=0.1, sigma=50, lambda_u=2)
    >>> discharge_to_return_period_pot(q=[120, 150, 200], u=100, xi=0, sigma=50, lambda_u=2)
    """
    # Input validation
    if sigma <= 0:
        raise ValueError(f"sigma must be > 0, got {sigma}")
    if lambda_u <= 0:
        raise ValueError(f"lambda_u must be > 0, got {lambda_u}")
    
    q_arr = np.atleast_1d(q).astype(float)
    
    # Initialize result array
    T_arr = np.full_like(q_arr, np.nan, dtype=float)
    
    # Only compute for q >= u
    valid_mask = q_arr >= u
    q_valid = q_arr[valid_mask]
    
    if len(q_valid) == 0:
        if np.isscalar(q):
            return np.nan
        return T_arr
    
    # Check for exponential limit
    if np.abs(xi) <= tol_exponential:
        # Exponential case: T = (1/λ) * exp[(q-u)/σ]
        T_valid = (1.0 / lambda_u) * np.exp((q_valid - u) / sigma)
    else:
        # GPD case: T = (1/λ) * [1 + ξ*(q-u)/σ]^(1/ξ)
        bracket = 1.0 + xi * (q_valid - u) / sigma
        
        # Check for valid bracket (must be > 0 for positive ξ, always valid for ξ < 0 when q > u)
        if xi > 0:
            # For positive xi, bracket must be positive
            bracket_valid_mask = bracket > 0
            if not np.all(bracket_valid_mask):
                # Some values are beyond the GPD support
                T_valid_temp = np.full_like(q_valid, np.nan, dtype=float)
                T_valid_temp[bracket_valid_mask] = (1.0 / lambda_u) * np.power(
                    bracket[bracket_valid_mask], 1.0 / xi
                )
                T_valid = T_valid_temp
            else:
                T_valid = (1.0 / lambda_u) * np.power(bracket, 1.0 / xi)
        else:
            # For negative xi, all q >= u are valid (bounded support is below u, not above)
            T_valid = (1.0 / lambda_u) * np.power(bracket, 1.0 / xi)
    
    T_arr[valid_mask] = T_valid
    
    # Return scalar if input was scalar
    if np.isscalar(q):
        return float(T_arr[0])
    return T_arr


def bootstrap_pot_return_levels(
    exceedances: np.ndarray,
    threshold: float,
    lambda_u: float,
    return_periods: Union[list, np.ndarray],
    n_bootstrap: int = 20,
    random_state: int = 42,
    tol_exponential: float = 1e-6,
) -> pd.DataFrame:
    """Compute return levels with bootstrap uncertainty using POT formulas.
    
    This function uses uniform resampling of exceedances (inspired by CLIMADA's
    return_period_resample approach but adapted for EVT-GPD instead of Gumbel).
    
    Parameters
    ----------
    exceedances : np.ndarray
        Array of exceedances above threshold (i.e., discharge - threshold values).
        These should be positive values representing excess over threshold.
    threshold : float
        POT threshold value (m³/s).
    lambda_u : float
        Poisson event rate (events/year).
    return_periods : list or np.ndarray
        Return periods to compute (years), e.g., [2, 5, 10, 20, 50, 100, 200, 500, 1000].
    n_bootstrap : int, optional
        Number of bootstrap iterations. Default 20.
    random_state : int, optional
        Random seed for reproducibility. Default 42.
    tol_exponential : float, optional
        Tolerance for treating ξ as zero (exponential case). Default 1e-6.
    
    Returns
    -------
    pd.DataFrame
        DataFrame with columns:
        - return_period_years: Return period (years)
        - mean_m3s: Mean discharge across bootstrap samples
        - std_m3s: Standard deviation of discharge
        - q05_m3s: 5th percentile
        - q95_m3s: 95th percentile
        - n_bootstrap_success: Number of successful bootstrap iterations
        - xi_mean: Mean GPD shape parameter
        - xi_std: Std of GPD shape parameter
        - sigma_mean: Mean GPD scale parameter
        - sigma_std: Std of GPD scale parameter
    
    Raises
    ------
    ImportError
        If scipy is not available.
    ValueError
        If exceedances is empty or invalid inputs.
    
    Examples
    --------
    >>> exceedances = np.array([10, 20, 30, 40, 50])  # excesses above threshold
    >>> result = bootstrap_pot_return_levels(
    ...     exceedances, threshold=100, lambda_u=2.5, 
    ...     return_periods=[2, 5, 10, 100]
    ... )
    """
    if stats is None:
        raise ImportError("scipy is required for bootstrap. Install with: pip install scipy")
    
    # Input validation
    exceedances = np.asarray(exceedances).flatten()
    if len(exceedances) == 0:
        raise ValueError("exceedances array is empty")
    if np.any(exceedances < 0):
        raise ValueError("All exceedances must be >= 0 (they represent excess above threshold)")
    if threshold < 0:
        raise ValueError("threshold must be >= 0")
    if lambda_u <= 0:
        raise ValueError("lambda_u must be > 0")
    
    return_periods = np.atleast_1d(return_periods)
    if np.any(return_periods <= 0):
        raise ValueError("All return periods must be > 0")
    
    rng = np.random.RandomState(random_state)
    n_exceedances = len(exceedances)
    
    # Storage for bootstrap results
    bootstrap_discharges = np.full((n_bootstrap, len(return_periods)), np.nan, dtype=float)
    bootstrap_xi = np.full(n_bootstrap, np.nan, dtype=float)
    bootstrap_sigma = np.full(n_bootstrap, np.nan, dtype=float)
    
    for i in range(n_bootstrap):
        # Resample exceedances with replacement
        resampled = rng.choice(exceedances, size=n_exceedances, replace=True)
        
        try:
            # Fit GPD to resampled exceedances (floc=0 fixes location at zero)
            # Returns shape, loc, scale
            fit_result = stats.genpareto.fit(resampled, floc=0)
            xi_boot = float(fit_result[0])  # shape parameter (c in scipy)
            sigma_boot = float(fit_result[2])  # scale parameter
            
            # Store parameters
            bootstrap_xi[i] = xi_boot
            bootstrap_sigma[i] = sigma_boot
            
            # Compute return levels for this bootstrap sample
            q_boot = return_period_to_discharge_pot(
                T=return_periods,
                u=threshold,
                xi=xi_boot,
                sigma=sigma_boot,
                lambda_u=lambda_u,
                tol_exponential=tol_exponential,
            )
            bootstrap_discharges[i, :] = q_boot
            
        except Exception:
            # Skip this bootstrap iteration if fitting fails
            continue
    
    # Count successful iterations (non-NaN)
    success_mask = ~np.isnan(bootstrap_discharges[:, 0])
    n_success = int(np.sum(success_mask))
    
    if n_success == 0:
        raise RuntimeError(
            f"All {n_bootstrap} bootstrap iterations failed. "
            "Check exceedances data quality and GPD fitting."
        )
    
    # Compute statistics across successful bootstrap samples
    # Use nanmean/nanstd to handle any remaining NaNs gracefully
    mean_discharge = np.nanmean(bootstrap_discharges, axis=0)
    std_discharge = np.nanstd(bootstrap_discharges, axis=0, ddof=1)
    q05_discharge = np.nanpercentile(bootstrap_discharges, 5, axis=0)
    q95_discharge = np.nanpercentile(bootstrap_discharges, 95, axis=0)
    
    # Parameter statistics
    xi_mean = np.nanmean(bootstrap_xi)
    xi_std = np.nanstd(bootstrap_xi, ddof=1)
    sigma_mean = np.nanmean(bootstrap_sigma)
    sigma_std = np.nanstd(bootstrap_sigma, ddof=1)
    
    # Build result DataFrame
    result_df = pd.DataFrame({
        'return_period_years': return_periods,
        'mean_m3s': mean_discharge,
        'std_m3s': std_discharge,
        'q05_m3s': q05_discharge,
        'q95_m3s': q95_discharge,
        'n_bootstrap_success': n_success,
        'xi_mean': xi_mean,
        'xi_std': xi_std,
        'sigma_mean': sigma_mean,
        'sigma_std': sigma_std,
    })
    
    return result_df
