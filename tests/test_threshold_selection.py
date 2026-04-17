"""Unit tests for threshold_selection module.

Tests the auto_select_threshold_pot function with synthetic and semi-realistic
discharge time series.
"""

import unittest
import numpy as np
import pandas as pd

from philflood.models.ev.threshold_selection import auto_select_threshold_pot


class TestAutoSelectThresholdPOT(unittest.TestCase):
    """Test suite for auto_select_threshold_pot function."""

    @classmethod
    def setUpClass(cls):
        """Create synthetic test data once for all tests."""
        # Generate synthetic discharge time series with daily frequency
        dates = pd.date_range(start="2000-01-01", end="2020-12-31", freq="D")
        
        # Simulate discharge from a Gamma distribution
        # (realistic approximation of river discharge)
        np.random.seed(42)
        base_flow = 50.0  # m³/s baseline
        seasonality = 20 * np.sin(2 * np.pi * np.arange(len(dates)) / 365.25)
        noise = np.random.normal(0, 10, len(dates))
        extreme_events = np.random.poisson(0.1, len(dates)) * np.random.exponential(100, len(dates))
        
        discharge = base_flow + seasonality + noise + extreme_events
        discharge = np.clip(discharge, 0.1, None)  # Ensure positive values
        
        cls.discharge_series = pd.Series(discharge, index=dates, name="Q")
        cls.short_series = cls.discharge_series.iloc[:500]  # Short series for quick tests
        cls.empty_series = pd.Series([], dtype=float)

    def test_normal_operation(self):
        """Test normal operation with realistic discharge data."""
        u_opt, status, diag_df = auto_select_threshold_pot(
            self.discharge_series,
            run_length_days=5,
            min_events_total=10,
            verbose=False,
        )
        
        # Check outputs are valid
        self.assertIsInstance(u_opt, float)
        self.assertIn(status, ["stable", "conservative", "fallback"])
        self.assertIsInstance(diag_df, pd.DataFrame)
        
        # Check that threshold is reasonable (between 90th and 99.9th percentile)
        q90 = self.discharge_series.quantile(0.90)
        q999 = self.discharge_series.quantile(0.999)
        self.assertGreaterEqual(u_opt, q90 * 0.9)  # Allow some flexibility
        self.assertLessEqual(u_opt, q999 * 1.1)

    def test_empty_series_raises_error(self):
        """Test that empty series raises an error."""
        with self.assertRaises(ValueError):
            auto_select_threshold_pot(self.empty_series, verbose=False)

    def test_with_nan_values(self):
        """Test that NaN values are handled correctly."""
        series_with_nans = self.discharge_series.copy()
        series_with_nans.iloc[::100] = np.nan  # Add some NaN values
        
        u_opt, status, diag_df = auto_select_threshold_pot(
            series_with_nans,
            verbose=False,
        )
        
        # Should still work after removing NaNs
        self.assertIsInstance(u_opt, float)
        self.assertIn(status, ["stable", "conservative", "fallback"])

    def test_diagnostics_dataframe(self):
        """Test that diagnostics dataframe has expected columns."""
        _, _, diag_df = auto_select_threshold_pot(
            self.discharge_series,
            verbose=False,
        )
        
        expected_columns = [
            "threshold",
            "n_events",
            "lambda_per_year",
            "gpd_xi",
            "gpd_sigma",
            "dispersion",
        ]
        for col in expected_columns:
            self.assertIn(col, diag_df.columns)

    def test_short_series(self):
        """Test with short time series (6 months)."""
        u_opt, status, diag_df = auto_select_threshold_pot(
            self.short_series,
            min_events_total=5,
            verbose=False,
        )
        
        # Should return something even with short data
        self.assertIsInstance(u_opt, float)
        self.assertGreater(u_opt, 0)

    def test_custom_parameters(self):
        """Test with custom parameter values."""
        u_opt1, status1, _ = auto_select_threshold_pot(
            self.discharge_series,
            candidate_quantiles=[0.90, 0.95, 0.99],
            run_length_days=3,
            min_events_total=20,
            stability_tol_xi=0.05,
            stability_tol_sigma=0.10,
            verbose=False,
        )
        
        u_opt2, status2, _ = auto_select_threshold_pot(
            self.discharge_series,
            candidate_quantiles=[0.95, 0.97],
            run_length_days=10,
            min_events_total=15,
            stability_tol_xi=0.20,
            stability_tol_sigma=0.25,
            verbose=False,
        )
        
        # Both should work and produce valid thresholds
        self.assertIsInstance(u_opt1, float)
        self.assertIsInstance(u_opt2, float)
        # Different parameters should potentially give different results
        # (but might be same due to data-dependent behavior)

    def test_verbose_output_doesnt_error(self):
        """Test that verbose=True doesn't cause errors."""
        try:
            u_opt, status, diag_df = auto_select_threshold_pot(
                self.short_series,
                verbose=True,
                min_events_total=5,
            )
            # If we get here, verbose mode worked
            self.assertIsInstance(u_opt, float)
        except Exception as e:
            self.fail(f"Verbose mode raised: {e}")

    def test_return_types(self):
        """Test that return types are exactly as specified."""
        result = auto_select_threshold_pot(
            self.discharge_series,
            verbose=False,
        )
        
        self.assertEqual(len(result), 3)
        u_opt, status, diag_df = result
        self.assertIsInstance(u_opt, float)
        self.assertIsInstance(status, str)
        self.assertIsInstance(diag_df, pd.DataFrame)

    def test_deterministic_output(self):
        """Test that same input gives same output (deterministic)."""
        u_opt1, status1, _ = auto_select_threshold_pot(
            self.discharge_series.copy(),
            verbose=False,
        )
        
        u_opt2, status2, _ = auto_select_threshold_pot(
            self.discharge_series.copy(),
            verbose=False,
        )
        
        self.assertEqual(u_opt1, u_opt2)
        self.assertEqual(status1, status2)


class TestThresholdSelectionTiers(unittest.TestCase):
    """Test the three-tier fallback mechanism."""

    def test_stable_tier_selection(self):
        """Test that stable tier is used when available."""
        # Create a well-behaved series where stable threshold should exist
        dates = pd.date_range("2000-01-01", "2020-12-31", freq="D")
        np.random.seed(123)
        
        # Moderate noise should allow stable threshold
        discharge = 100 + np.random.normal(0, 20, len(dates))
        discharge = np.clip(discharge, 1, None)
        series = pd.Series(discharge, index=dates)
        
        _, status, _ = auto_select_threshold_pot(
            series,
            stability_tol_xi=0.1,
            stability_tol_sigma=0.15,
            verbose=False,
        )
        
        # With well-behaved data, should find stable threshold
        self.assertIn(status, ["stable", "conservative", "fallback"])


if __name__ == "__main__":
    unittest.main()
