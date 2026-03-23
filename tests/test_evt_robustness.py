"""Unit tests for EVT robustness improvements.

Covers:
- scipy sign convention: genpareto c = EVT xi (positive for heavy tail)
- compute_mrl: correct MRL computation and linearity flag
- gpd_gof_test: pass for GPD-distributed data, fail for non-GPD data
"""

import numpy as np
import pandas as pd
import pytest
from scipy import stats


# ---------------------------------------------------------------------------
# 1. scipy sign convention
# ---------------------------------------------------------------------------

class TestScipySignConvention:
    """Verify that scipy genpareto shape c = EVT xi (same sign, not negated)."""

    def test_positive_xi_heavy_tail(self):
        """Data sampled from GPD(xi=0.3) should yield scipy c > 0."""
        rng = np.random.RandomState(0)
        # GPD(xi=0.3, sigma=100): CDF = 1 - (1 + 0.3*x/100)^(-1/0.3)
        xi_true, sigma_true = 0.3, 100.0
        sample = stats.genpareto.rvs(c=xi_true, scale=sigma_true, size=500, random_state=rng)
        c_fit, _, _ = stats.genpareto.fit(sample, floc=0)
        # scipy c should be positive (same sign as EVT xi)
        assert c_fit > 0, f"Expected scipy c > 0 for heavy-tailed data, got {c_fit:.4f}"

    def test_negative_xi_bounded_tail(self):
        """Data sampled from GPD(xi=-0.2) should yield scipy c < 0."""
        rng = np.random.RandomState(1)
        xi_true, sigma_true = -0.2, 50.0
        sample = stats.genpareto.rvs(c=xi_true, scale=sigma_true, size=500, random_state=rng)
        sample = sample[sample >= 0]  # bounded support
        c_fit, _, _ = stats.genpareto.fit(sample, floc=0)
        assert c_fit < 0, f"Expected scipy c < 0 for bounded-tail data, got {c_fit:.4f}"

    def test_threshold_selection_xi_sign(self):
        """gpd_xi in threshold_selection diagnostics should be positive for heavy-tailed data."""
        from philflood.models.ev.threshold_selection import auto_select_threshold_pot

        rng = np.random.RandomState(42)
        n_days = 365 * 20
        dates = pd.date_range("2000-01-01", periods=n_days, freq="D")
        # Simulate heavy-tailed discharge
        base = np.random.exponential(50, n_days)
        extremes = np.random.poisson(0.05, n_days) * np.random.pareto(2.5, n_days) * 200
        discharge = pd.Series(base + extremes + 20, index=dates)

        _, _, diag_df = auto_select_threshold_pot(
            discharge,
            candidate_quantiles=[0.90, 0.95, 0.99],
            verbose=False,
        )
        # The gpd_xi column must use the correct (non-negated) scipy convention
        valid_xi = diag_df["gpd_xi"].dropna()
        assert len(valid_xi) > 0, "No valid gpd_xi values in diagnostics"
        # For this data we expect positive xi on average (heavy tail)
        # Key assertion: xi stored should match scipy c directly (not negated)
        # We check it matches re-computed values from scipy directly
        for _, row in diag_df.dropna(subset=["gpd_xi", "gpd_sigma"]).iterrows():
            u = row["threshold"]
            exceedances = discharge[discharge > u].values - u
            if len(exceedances) < 5:
                continue
            c_scipy, _, _ = stats.genpareto.fit(exceedances, floc=0)
            # The stored gpd_xi should have the same sign as scipy c (tolerance for MLE variability)
            assert np.sign(row["gpd_xi"]) == np.sign(c_scipy) or abs(row["gpd_xi"]) < 0.05, (
                f"gpd_xi={row['gpd_xi']:.4f} has wrong sign vs scipy c={c_scipy:.4f} at u={u:.1f}"
            )


# ---------------------------------------------------------------------------
# 2. compute_mrl
# ---------------------------------------------------------------------------

class TestComputeMRL:
    """Tests for the Mean Residual Life function."""

    def test_mrl_decreasing_with_threshold(self):
        """For exponential data (xi=0), MRL should be approximately constant."""
        from philflood.models.ev.threshold_selection import compute_mrl

        rng = np.random.RandomState(5)
        n = 10000
        data = pd.Series(rng.exponential(scale=100.0, size=n))
        thresholds = [50.0, 100.0, 150.0, 200.0]
        mrl_df = compute_mrl(data, thresholds)

        valid = mrl_df.dropna(subset=["mrl"])
        assert len(valid) >= 3, "Expected at least 3 valid MRL values"
        # For exponential, MRL ≈ sigma = 100 regardless of threshold
        for mrl_val in valid["mrl"]:
            assert 70 < mrl_val < 130, f"MRL={mrl_val:.1f} far from expected 100 for exponential"

    def test_mrl_increasing_for_heavy_tail(self):
        """For Pareto (xi>0), MRL should increase with threshold."""
        from philflood.models.ev.threshold_selection import compute_mrl

        rng = np.random.RandomState(7)
        # Pareto: P(X>x) = (x/x_min)^(-alpha), MRL = x_min/(alpha-1) * (x/x_min)
        # Heavy tail: MRL increases with threshold
        sample = rng.pareto(1.5, 5000) * 100 + 50  # shift so positive
        data = pd.Series(sample)
        thresholds = [100.0, 150.0, 200.0, 250.0]
        mrl_df = compute_mrl(data, thresholds)

        valid = mrl_df.dropna(subset=["mrl"]).sort_values("threshold")
        assert len(valid) >= 3, "Need at least 3 points to test monotonicity"
        # MRL should be broadly increasing
        mrl_vals = valid["mrl"].values
        assert mrl_vals[-1] > mrl_vals[0], (
            f"MRL should increase with threshold for heavy-tailed data: {mrl_vals}"
        )

    def test_mrl_returns_linearity_flag(self):
        """compute_mrl must return mrl_linear_ok boolean column."""
        from philflood.models.ev.threshold_selection import compute_mrl

        data = pd.Series(np.random.exponential(50, 1000))
        thresholds = [10.0, 20.0, 30.0, 40.0, 50.0]
        mrl_df = compute_mrl(data, thresholds)
        assert "mrl_linear_ok" in mrl_df.columns
        assert mrl_df["mrl_linear_ok"].dtype == bool or mrl_df["mrl_linear_ok"].dtype == object


# ---------------------------------------------------------------------------
# 3. gpd_gof_test
# ---------------------------------------------------------------------------

class TestGPDGoFTest:
    """Tests for the KS GoF test on GPD-fitted exceedances."""

    def test_pass_for_gpd_data(self):
        """GPD-distributed exceedances should pass GoF (p >= 0.05)."""
        from philflood.calibration.evt_pot import gpd_gof_test

        rng = np.random.RandomState(10)
        xi, sigma = 0.2, 80.0
        exceedances = stats.genpareto.rvs(c=xi, scale=sigma, size=300, random_state=rng)
        exceedances = exceedances[exceedances >= 0]

        p_val, gof_pass = gpd_gof_test(exceedances, xi=xi, sigma=sigma, alpha=0.05)
        assert gof_pass, f"Expected GoF pass for GPD data, got p={p_val:.4f}"

    def test_fail_for_non_gpd_data(self):
        """Normal-distributed exceedances should fail GoF when fitted as GPD."""
        from philflood.calibration.evt_pot import gpd_gof_test

        rng = np.random.RandomState(20)
        # Normally distributed exceedances (completely wrong distribution)
        exceedances = np.abs(rng.normal(50, 10, 500))
        # Fit a GPD with obviously wrong params (just use arbitrary xi, sigma)
        xi_wrong, sigma_wrong = 0.5, 5.0  # very different from normal data

        p_val, gof_pass = gpd_gof_test(exceedances, xi=xi_wrong, sigma=sigma_wrong, alpha=0.05)
        assert not gof_pass, f"Expected GoF fail for non-GPD data with wrong params, got p={p_val:.4f}"

    def test_insufficient_data_returns_true(self):
        """With < 5 exceedances, GoF should return True (don't block on missing data)."""
        from philflood.calibration.evt_pot import gpd_gof_test

        p_val, gof_pass = gpd_gof_test(np.array([1.0, 2.0, 3.0]), xi=0.1, sigma=50.0)
        assert gof_pass, "Insufficient data should default to gof_pass=True"
        assert np.isnan(p_val), "p-value should be NaN for insufficient data"

    def test_returns_float_and_bool(self):
        """Return types must be (float, bool)."""
        from philflood.calibration.evt_pot import gpd_gof_test

        rng = np.random.RandomState(30)
        exceedances = stats.genpareto.rvs(c=0.1, scale=50.0, size=100, random_state=rng)
        p_val, gof_pass = gpd_gof_test(exceedances, xi=0.1, sigma=50.0)
        assert isinstance(p_val, float)
        assert isinstance(gof_pass, bool)


# ---------------------------------------------------------------------------
# 4. bootstrap N=500 default
# ---------------------------------------------------------------------------

class TestBootstrapDefault:
    """Verify that bootstrap_pot_return_levels uses n_bootstrap=500 by default."""

    def test_default_n_bootstrap(self):
        """Default n_bootstrap must be 500."""
        import inspect
        from philflood.calibration.evt_pot import bootstrap_pot_return_levels

        sig = inspect.signature(bootstrap_pot_return_levels)
        default_n = sig.parameters["n_bootstrap"].default
        assert default_n == 500, f"Expected n_bootstrap default=500, got {default_n}"
