"""Test configuration and fixtures for PhilFlood.

This module provides test utilities and sample data for verifying
that the installation works correctly.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def generate_test_discharge_series(
    start_date: str = "2020-01-01",
    end_date: str = "2020-12-31",
    baseline_flow: float = 500.0,
    num_peaks: int = 5,
) -> pd.DataFrame:
    """Generate synthetic discharge time series for testing.
    
    Parameters
    ----------
    start_date : str
        Start date (YYYY-MM-DD)
    end_date : str
        End date (YYYY-MM-DD)
    baseline_flow : float
        Baseline discharge in m³/s
    num_peaks : int
        Number of flood peaks to inject
    
    Returns
    -------
    pd.DataFrame
        DataFrame with DatetimeIndex and 'discharge' column
    """
    dates = pd.date_range(start_date, end_date, freq="D")
    n = len(dates)
    
    # Generate baseline with some noise
    discharge = baseline_flow + np.random.gamma(2, 50, n)
    
    # Add synthetic flood peaks
    peak_indices = np.random.choice(n, size=num_peaks, replace=False)
    for idx in peak_indices:
        # Create a peak with rise and recession
        peak_magnitude = np.random.uniform(1500, 3000)
        duration = 15
        peak_shape = np.concatenate([
            np.linspace(0, 1, duration // 2),
            np.linspace(1, 0, duration // 2)
        ])
        start_idx = max(0, idx - duration // 2)
        end_idx = min(n, start_idx + duration)
        actual_shape = peak_shape[:end_idx - start_idx]
        discharge[start_idx:end_idx] += peak_magnitude * actual_shape
    
    return pd.DataFrame({"discharge": discharge}, index=dates)


def generate_test_forecast_ensemble(
    issue_date: str = "2025-12-29",
    lead_days: int = 10,
    num_members: int = 51,
    baseline: float = 800.0,
    triggered: bool = False,
) -> pd.DataFrame:
    """Generate synthetic ensemble forecast for testing.
    
    Parameters
    ----------
    issue_date : str
        Forecast issue date
    lead_days : int
        Number of forecast lead days
    num_members : int
        Number of ensemble members
    baseline : float
        Baseline discharge
    triggered : bool
        If True, inject a triggering event
    
    Returns
    -------
    pd.DataFrame
        DataFrame with columns [member, lead_day, discharge]
    """
    issue = pd.to_datetime(issue_date)
    data = []
    
    for member in range(num_members):
        for day in range(lead_days):
            valid_date = issue + timedelta(days=day)
            
            # Baseline with ensemble spread
            discharge = baseline + np.random.gamma(2, 100)
            
            # If triggered, some members show high flow at medium lead times
            if triggered and 3 <= day <= 7 and member < num_members * 0.4:
                discharge += np.random.uniform(1200, 2500)
            
            data.append({
                "member": member,
                "lead_day": day,
                "valid_date": valid_date,
                "discharge": discharge,
            })
    
    return pd.DataFrame(data)


if __name__ == "__main__":
    # Generate sample data for testing
    import os
    from pathlib import Path
    
    test_dir = Path(__file__).parent
    
    # Generate historical discharge
    discharge = generate_test_discharge_series("2015-01-01", "2020-12-31")
    discharge.to_csv(test_dir / "test_discharge_historical.csv")
    print(f"✓ Created test_discharge_historical.csv ({len(discharge)} days)")
    
    # Generate forecast ensemble (no trigger)
    forecast_normal = generate_test_forecast_ensemble(triggered=False)
    forecast_normal.to_csv(test_dir / "test_forecast_normal.csv", index=False)
    print(f"✓ Created test_forecast_normal.csv ({len(forecast_normal)} rows)")
    
    # Generate forecast ensemble (with trigger)
    forecast_trigger = generate_test_forecast_ensemble(triggered=True)
    forecast_trigger.to_csv(test_dir / "test_forecast_triggered.csv", index=False)
    print(f"✓ Created test_forecast_triggered.csv ({len(forecast_trigger)} rows)")
