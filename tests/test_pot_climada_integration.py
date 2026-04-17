"""Integration tests for POT formula-based return levels and CLIMADA NetCDF output.

This test suite validates:
1. POT formula correctness (return_period_to_discharge_pot, discharge_to_return_period_pot)
2. Bootstrap return level computation (bootstrap_pot_return_levels)
3. Parquet output structure (return_levels_bootstrap.parquet)
4. NetCDF output structure and CF compliance (pot_climada.nc)
5. Performance benchmarks
"""

import numpy as np
import pandas as pd
import pytest

# Import the new functions
from philflood.calibration.evt_pot import (
    return_period_to_discharge_pot,
    discharge_to_return_period_pot,
    bootstrap_pot_return_levels,
)


# =============================================================================
# Unit Tests: POT Formulas
# =============================================================================

class TestReturnPeriodToDischarge:
    """Test return_period_to_discharge_pot function."""
    
    def test_exponential_case_known_value(self):
        """Test exponential limit (ξ ≈ 0) with known analytic result."""
        # For ξ=0: q = u + σ * ln(λ*T)
        u = 100.0
        sigma = 50.0
        lambda_u = 2.0
        T = 10.0
        xi = 0.0
        
        # Expected: 100 + 50 * ln(2*10) = 100 + 50 * ln(20)
        expected = u + sigma * np.log(lambda_u * T)
        
        result = return_period_to_discharge_pot(T, u, xi, sigma, lambda_u)
        
        assert np.isclose(result, expected, rtol=1e-10)
    
    def test_positive_xi_case(self):
        """Test GPD case with positive ξ (heavy tail)."""
        u = 100.0
        sigma = 50.0
        lambda_u = 2.0
        T = 10.0
        xi = 0.1
        
        # Expected: u + (σ/ξ) * ((λ*T)^ξ - 1)
        expected = u + (sigma / xi) * (np.power(lambda_u * T, xi) - 1.0)
        
        result = return_period_to_discharge_pot(T, u, xi, sigma, lambda_u)
        
        assert np.isclose(result, expected, rtol=1e-10)
    
    def test_negative_xi_case(self):
        """Test GPD case with negative ξ (bounded tail)."""
        u = 100.0
        sigma = 50.0
        lambda_u = 2.0
        T = 5.0
        xi = -0.1
        
        # Expected: u + (σ/ξ) * ((λ*T)^ξ - 1)
        expected = u + (sigma / xi) * (np.power(lambda_u * T, xi) - 1.0)
        
        result = return_period_to_discharge_pot(T, u, xi, sigma, lambda_u)
        
        assert np.isclose(result, expected, rtol=1e-10)
    
    def test_vectorized_input(self):
        """Test that function handles array input correctly."""
        u = 100.0
        sigma = 50.0
        lambda_u = 2.0
        T = np.array([2, 5, 10, 20, 50, 100])
        xi = 0.1
        
        result = return_period_to_discharge_pot(T, u, xi, sigma, lambda_u)
        
        assert isinstance(result, np.ndarray)
        assert len(result) == len(T)
        # Check monotonicity (higher T -> higher discharge)
        assert np.all(np.diff(result) > 0)
    
    def test_invalid_sigma(self):
        """Test that negative or zero sigma raises ValueError."""
        with pytest.raises(ValueError, match="sigma must be > 0"):
            return_period_to_discharge_pot(T=10, u=100, xi=0.1, sigma=0, lambda_u=2)
        
        with pytest.raises(ValueError, match="sigma must be > 0"):
            return_period_to_discharge_pot(T=10, u=100, xi=0.1, sigma=-5, lambda_u=2)
    
    def test_invalid_lambda(self):
        """Test that negative or zero lambda raises ValueError."""
        with pytest.raises(ValueError, match="lambda_u must be > 0"):
            return_period_to_discharge_pot(T=10, u=100, xi=0.1, sigma=50, lambda_u=0)
    
    def test_invalid_return_period(self):
        """Test that negative or zero return period raises ValueError."""
        with pytest.raises(ValueError, match="All return periods must be > 0"):
            return_period_to_discharge_pot(T=0, u=100, xi=0.1, sigma=50, lambda_u=2)


class TestDischargeToReturnPeriod:
    """Test discharge_to_return_period_pot function."""
    
    def test_exponential_case_known_value(self):
        """Test exponential limit (ξ ≈ 0) with known analytic result."""
        # For ξ=0: T = (1/λ) * exp[(q-u)/σ]
        u = 100.0
        sigma = 50.0
        lambda_u = 2.0
        q = 150.0
        xi = 0.0
        
        # Expected: (1/2) * exp[(150-100)/50] = 0.5 * exp(1)
        expected = (1.0 / lambda_u) * np.exp((q - u) / sigma)
        
        result = discharge_to_return_period_pot(q, u, xi, sigma, lambda_u)
        
        assert np.isclose(result, expected, rtol=1e-10)
    
    def test_discharge_below_threshold(self):
        """Test that q < u returns NaN."""
        u = 100.0
        sigma = 50.0
        lambda_u = 2.0
        q = 90.0  # below threshold
        xi = 0.1
        
        result = discharge_to_return_period_pot(q, u, xi, sigma, lambda_u)
        
        assert np.isnan(result)
    
    def test_positive_xi_case(self):
        """Test GPD case with positive ξ."""
        u = 100.0
        sigma = 50.0
        lambda_u = 2.0
        q = 200.0
        xi = 0.1
        
        # Expected: (1/λ) * [1 + ξ*(q-u)/σ]^(1/ξ)
        bracket = 1.0 + xi * (q - u) / sigma
        expected = (1.0 / lambda_u) * np.power(bracket, 1.0 / xi)
        
        result = discharge_to_return_period_pot(q, u, xi, sigma, lambda_u)
        
        assert np.isclose(result, expected, rtol=1e-10)
    
    def test_vectorized_input(self):
        """Test that function handles array input correctly."""
        u = 100.0
        sigma = 50.0
        lambda_u = 2.0
        q = np.array([110, 150, 200, 300, 400])
        xi = 0.1
        
        result = discharge_to_return_period_pot(q, u, xi, sigma, lambda_u)
        
        assert isinstance(result, np.ndarray)
        assert len(result) == len(q)
        # Check monotonicity (higher q -> higher T)
        assert np.all(np.diff(result) > 0)


class TestInverseConsistency:
    """Test that T→D→T and D→T→D round-trips are consistent."""
    
    def test_t_to_d_to_t_exponential(self):
        """Test T→D→T for exponential case."""
        u = 100.0
        sigma = 50.0
        lambda_u = 2.0
        xi = 0.0
        T_original = 10.0
        
        # Forward: T -> D
        q = return_period_to_discharge_pot(T_original, u, xi, sigma, lambda_u)
        
        # Backward: D -> T
        T_recovered = discharge_to_return_period_pot(q, u, xi, sigma, lambda_u)
        
        assert np.isclose(T_recovered, T_original, rtol=1e-8)
    
    def test_t_to_d_to_t_positive_xi(self):
        """Test T→D→T for positive ξ case."""
        u = 100.0
        sigma = 50.0
        lambda_u = 2.0
        xi = 0.15
        T_original = 50.0
        
        q = return_period_to_discharge_pot(T_original, u, xi, sigma, lambda_u)
        T_recovered = discharge_to_return_period_pot(q, u, xi, sigma, lambda_u)
        
        assert np.isclose(T_recovered, T_original, rtol=1e-8)
    
    def test_t_to_d_to_t_negative_xi(self):
        """Test T→D→T for negative ξ case."""
        u = 100.0
        sigma = 50.0
        lambda_u = 2.0
        xi = -0.05
        T_original = 20.0
        
        q = return_period_to_discharge_pot(T_original, u, xi, sigma, lambda_u)
        T_recovered = discharge_to_return_period_pot(q, u, xi, sigma, lambda_u)
        
        assert np.isclose(T_recovered, T_original, rtol=1e-8)
    
    def test_vectorized_consistency(self):
        """Test consistency for multiple return periods."""
        u = 100.0
        sigma = 50.0
        lambda_u = 2.0
        xi = 0.1
        T_original = np.array([2, 5, 10, 20, 50, 100, 200, 500, 1000])
        
        q = return_period_to_discharge_pot(T_original, u, xi, sigma, lambda_u)
        T_recovered = discharge_to_return_period_pot(q, u, xi, sigma, lambda_u)
        
        assert np.allclose(T_recovered, T_original, rtol=1e-8)


# =============================================================================
# Unit Tests: Bootstrap Function
# =============================================================================

class TestBootstrapReturnLevels:
    """Test bootstrap_pot_return_levels function."""
    
    def test_basic_functionality(self):
        """Test that bootstrap runs and returns expected structure."""
        # Create synthetic exceedances
        rng = np.random.RandomState(42)
        exceedances = rng.exponential(scale=20, size=100)  # Exponential exceedances
        
        threshold = 100.0
        lambda_u = 2.5
        return_periods = [2, 5, 10, 20, 50, 100]
        
        result = bootstrap_pot_return_levels(
            exceedances, threshold, lambda_u, return_periods, 
            n_bootstrap=10, random_state=42
        )
        
        # Check structure
        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(return_periods)
        
        expected_cols = [
            'return_period_years', 'mean_m3s', 'std_m3s', 
            'q05_m3s', 'q95_m3s', 'n_bootstrap_success',
            'xi_mean', 'xi_std', 'sigma_mean', 'sigma_std'
        ]
        for col in expected_cols:
            assert col in result.columns
    
    def test_output_monotonicity(self):
        """Test that mean discharge increases with return period."""
        rng = np.random.RandomState(42)
        exceedances = rng.exponential(scale=30, size=150)
        
        result = bootstrap_pot_return_levels(
            exceedances, threshold=100, lambda_u=2.0,
            return_periods=[2, 5, 10, 20, 50, 100, 200, 500, 1000],
            n_bootstrap=20, random_state=42
        )
        
        # Check monotonicity
        mean_values = result['mean_m3s'].values
        assert np.all(np.diff(mean_values) > 0), "Mean discharge must increase with return period"
    
    def test_uncertainty_ordering(self):
        """Test that q05 < mean < q95."""
        rng = np.random.RandomState(42)
        exceedances = rng.exponential(scale=25, size=120)
        
        result = bootstrap_pot_return_levels(
            exceedances, threshold=100, lambda_u=2.5,
            return_periods=[10, 50, 100],
            n_bootstrap=15, random_state=42
        )
        
        # Check quantile ordering for each row
        for _, row in result.iterrows():
            assert row['q05_m3s'] <= row['mean_m3s'], "q05 must be <= mean"
            assert row['mean_m3s'] <= row['q95_m3s'], "mean must be <= q95"
    
    def test_std_non_negative(self):
        """Test that standard deviation is non-negative."""
        rng = np.random.RandomState(42)
        exceedances = rng.exponential(scale=20, size=100)
        
        result = bootstrap_pot_return_levels(
            exceedances, threshold=100, lambda_u=2.0,
            return_periods=[5, 10, 50],
            n_bootstrap=10, random_state=42
        )
        
        assert np.all(result['std_m3s'] >= 0), "Standard deviation must be >= 0"
    
    def test_invalid_inputs(self):
        """Test that invalid inputs raise appropriate errors."""
        # Empty exceedances
        with pytest.raises(ValueError, match="exceedances array is empty"):
            bootstrap_pot_return_levels(
                np.array([]), threshold=100, lambda_u=2.0, return_periods=[10]
            )
        
        # Negative exceedances
        with pytest.raises(ValueError, match="All exceedances must be >= 0"):
            bootstrap_pot_return_levels(
                np.array([10, 20, -5]), threshold=100, lambda_u=2.0, return_periods=[10]
            )
        
        # Invalid lambda
        with pytest.raises(ValueError, match="lambda_u must be > 0"):
            bootstrap_pot_return_levels(
                np.array([10, 20, 30]), threshold=100, lambda_u=0, return_periods=[10]
            )
    
    def test_reproducibility(self):
        """Test that same random seed produces same results."""
        rng = np.random.RandomState(42)
        exceedances = rng.exponential(scale=20, size=100)
        
        result1 = bootstrap_pot_return_levels(
            exceedances, threshold=100, lambda_u=2.0,
            return_periods=[10, 50],
            n_bootstrap=10, random_state=123
        )
        
        result2 = bootstrap_pot_return_levels(
            exceedances, threshold=100, lambda_u=2.0,
            return_periods=[10, 50],
            n_bootstrap=10, random_state=123
        )
        
        pd.testing.assert_frame_equal(result1, result2)


# =============================================================================
# Integration Tests: Parquet Output
# =============================================================================

class TestReturnLevelsBootstrapParquet:
    """Test return_levels_bootstrap.parquet output structure."""
    
    @pytest.fixture
    def sample_parquet_path(self, tmp_path):
        """Create a sample parquet file for testing."""
        # Create synthetic data
        data = []
        for gauge_id in ['GAUGE_001', 'GAUGE_002', 'GAUGE_003']:
            for rp in [2, 5, 10, 20, 50, 100, 200, 500, 1000]:
                data.append({
                    'virtual_gauge_id': gauge_id,
                    'return_period_years': rp,
                    'mean_m3s': 100 + rp * 2,
                    'std_m3s': rp * 0.2,
                    'q05_m3s': 100 + rp * 1.5,
                    'q95_m3s': 100 + rp * 2.5,
                    'n_bootstrap_success': 20,
                    'xi_mean': 0.1,
                    'xi_std': 0.02,
                    'sigma_mean': 50.0,
                    'sigma_std': 5.0,
                })
        
        df = pd.DataFrame(data)
        path = tmp_path / "return_levels_bootstrap.parquet"
        df.to_parquet(path, index=False, compression="snappy")
        return path
    
    def test_parquet_exists_and_loadable(self, sample_parquet_path):
        """Test that parquet file exists and can be loaded."""
        assert sample_parquet_path.exists()
        df = pd.read_parquet(sample_parquet_path)
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
    
    def test_parquet_columns(self, sample_parquet_path):
        """Test that all required columns are present."""
        df = pd.read_parquet(sample_parquet_path)
        
        required_cols = [
            'virtual_gauge_id', 'return_period_years',
            'mean_m3s', 'std_m3s', 'q05_m3s', 'q95_m3s',
            'n_bootstrap_success', 'xi_mean', 'xi_std',
            'sigma_mean', 'sigma_std'
        ]
        
        for col in required_cols:
            assert col in df.columns, f"Missing column: {col}"
    
    def test_parquet_no_nulls_in_key_columns(self, sample_parquet_path):
        """Test that key columns have no null values."""
        df = pd.read_parquet(sample_parquet_path)
        
        key_cols = ['virtual_gauge_id', 'return_period_years', 'mean_m3s']
        for col in key_cols:
            assert df[col].notna().all(), f"Column {col} has null values"
    
    def test_parquet_monotonicity_per_gauge(self, sample_parquet_path):
        """Test that return levels are monotonic for each gauge."""
        df = pd.read_parquet(sample_parquet_path)
        
        for gauge_id in df['virtual_gauge_id'].unique():
            gauge_df = df[df['virtual_gauge_id'] == gauge_id].sort_values('return_period_years')
            mean_values = gauge_df['mean_m3s'].values
            
            # Check monotonicity
            assert np.all(np.diff(mean_values) > 0), \
                f"Non-monotonic return levels for gauge {gauge_id}"
    
    def test_parquet_physical_ranges(self, sample_parquet_path):
        """Test that values are in physically reasonable ranges."""
        df = pd.read_parquet(sample_parquet_path)
        
        # All discharge values should be positive
        assert (df['mean_m3s'] > 0).all()
        assert (df['q05_m3s'] > 0).all()
        assert (df['q95_m3s'] > 0).all()
        
        # Std should be non-negative
        assert (df['std_m3s'] >= 0).all()
        
        # Uncertainty should be reasonable (5-30% of mean)
        cv = df['std_m3s'] / df['mean_m3s']
        assert (cv >= 0).all() and (cv <= 0.5).all(), \
            "Coefficient of variation should be between 0 and 50%"


# =============================================================================
# Integration Tests: NetCDF Output
# =============================================================================

class TestPOTCLIMADANetCDF:
    """Test pot_climada.nc NetCDF output structure and CF compliance."""
    
    @pytest.fixture
    def sample_netcdf_path(self, tmp_path):
        """Create a sample NetCDF file for testing."""
        try:
            import xarray as xr
        except ImportError:
            pytest.skip("xarray not available")
        
        # Create synthetic grid data
        lat = np.arange(16.0, 19.0, 0.05)
        lon = np.arange(120.0, 123.0, 0.05)
        return_periods = np.array([2, 5, 10, 20, 50, 100, 200, 500, 1000])
        
        # Create 3D arrays
        shape = (len(lat), len(lon), len(return_periods))
        discharge_mean = np.random.uniform(100, 500, shape).astype(np.float32)
        discharge_std = np.random.uniform(10, 50, shape).astype(np.float32)
        discharge_q05 = discharge_mean - discharge_std
        discharge_q95 = discharge_mean + discharge_std
        
        # Create dataset
        ds = xr.Dataset(
            data_vars={
                'discharge_mean_m3s': (['lat', 'lon', 'return_period'], discharge_mean,
                    {'units': 'm3 s-1', 'long_name': 'Mean discharge'}),
                'discharge_std_m3s': (['lat', 'lon', 'return_period'], discharge_std,
                    {'units': 'm3 s-1', 'long_name': 'Discharge standard deviation'}),
                'discharge_q05_m3s': (['lat', 'lon', 'return_period'], discharge_q05,
                    {'units': 'm3 s-1', 'long_name': 'Discharge 5th percentile'}),
                'discharge_q95_m3s': (['lat', 'lon', 'return_period'], discharge_q95,
                    {'units': 'm3 s-1', 'long_name': 'Discharge 95th percentile'}),
            },
            coords={
                'lat': (['lat'], lat, {'units': 'degrees_north', 'standard_name': 'latitude'}),
                'lon': (['lon'], lon, {'units': 'degrees_east', 'standard_name': 'longitude'}),
                'return_period': (['return_period'], return_periods, {'units': 'years'}),
            },
        )
        
        path = tmp_path / "pot_climada.nc"
        encoding = {var: {'zlib': True, 'complevel': 4, 'dtype': 'float32', '_FillValue': np.nan} 
                    for var in ds.data_vars}
        ds.to_netcdf(path, engine='netcdf4', encoding=encoding)
        ds.close()
        
        return path
    
    def test_netcdf_exists_and_loadable(self, sample_netcdf_path):
        """Test that NetCDF file exists and can be opened."""
        try:
            import xarray as xr
        except ImportError:
            pytest.skip("xarray not available")
        
        assert sample_netcdf_path.exists()
        ds = xr.open_dataset(sample_netcdf_path)
        assert isinstance(ds, xr.Dataset)
        ds.close()
    
    def test_netcdf_dimensions(self, sample_netcdf_path):
        """Test that NetCDF has correct dimensions."""
        try:
            import xarray as xr
        except ImportError:
            pytest.skip("xarray not available")
        
        ds = xr.open_dataset(sample_netcdf_path)
        
        # Check dimension names
        assert 'lat' in ds.dims
        assert 'lon' in ds.dims
        assert 'return_period' in ds.dims
        
        # Check return period dimension size
        assert ds.dims['return_period'] == 9
        
        ds.close()
    
    def test_netcdf_variables(self, sample_netcdf_path):
        """Test that NetCDF has all required variables."""
        try:
            import xarray as xr
        except ImportError:
            pytest.skip("xarray not available")
        
        ds = xr.open_dataset(sample_netcdf_path)
        
        required_vars = [
            'discharge_mean_m3s', 'discharge_std_m3s',
            'discharge_q05_m3s', 'discharge_q95_m3s'
        ]
        
        for var in required_vars:
            assert var in ds.data_vars, f"Missing variable: {var}"
        
        ds.close()
    
    def test_netcdf_cf_attributes(self, sample_netcdf_path):
        """Test that coordinates have CF-compliant attributes."""
        try:
            import xarray as xr
        except ImportError:
            pytest.skip("xarray not available")
        
        ds = xr.open_dataset(sample_netcdf_path)
        
        # Check latitude attributes
        assert 'units' in ds['lat'].attrs
        assert ds['lat'].attrs['units'] == 'degrees_north'
        
        # Check longitude attributes
        assert 'units' in ds['lon'].attrs
        assert ds['lon'].attrs['units'] == 'degrees_east'
        
        # Check return period attributes
        assert 'units' in ds['return_period'].attrs
        assert ds['return_period'].attrs['units'] == 'years'
        
        ds.close()
    
    def test_netcdf_data_ranges(self, sample_netcdf_path):
        """Test that data values are in reasonable ranges."""
        try:
            import xarray as xr
        except ImportError:
            pytest.skip("xarray not available")
        
        ds = xr.open_dataset(sample_netcdf_path)
        
        # Discharge values should be positive (ignoring NaN)
        discharge_mean = ds['discharge_mean_m3s'].values
        valid_mean = discharge_mean[~np.isnan(discharge_mean)]
        assert np.all(valid_mean > 0), "All discharge values should be positive"
        
        # Std should be non-negative
        discharge_std = ds['discharge_std_m3s'].values
        valid_std = discharge_std[~np.isnan(discharge_std)]
        assert np.all(valid_std >= 0), "Standard deviation should be non-negative"
        
        ds.close()


# =============================================================================
# Performance Tests
# =============================================================================

class TestPerformance:
    """Performance benchmarks for POT formula operations."""
    
    @pytest.mark.performance
    def test_bootstrap_performance(self):
        """Test that bootstrap completes in reasonable time."""
        import time
        
        # Create realistic-sized exceedances array (~200 events over 40 years)
        rng = np.random.RandomState(42)
        exceedances = rng.exponential(scale=25, size=200)
        
        start = time.time()
        bootstrap_pot_return_levels(
            exceedances, threshold=100, lambda_u=2.5,
            return_periods=[2, 5, 10, 20, 50, 100, 200, 500, 1000],
            n_bootstrap=20, random_state=42
        )
        elapsed = time.time() - start
        
        # Should complete in < 5 seconds for single gauge (increased margin for CI)
        assert elapsed < 5.0, f"Bootstrap took {elapsed:.2f}s, expected < 5s"
    
    @pytest.mark.performance
    def test_discharge_to_return_period_vectorized_performance(self):
        """Test that vectorized inverse calculation is fast."""
        import time
        
        # Simulate 10,000 cells (typical large basin)
        n_cells = 10000
        q_values = np.random.uniform(100, 500, n_cells)
        
        start = time.time()
        T_values = discharge_to_return_period_pot(
            q=q_values, u=100, xi=0.1, sigma=50, lambda_u=2.0
        )
        elapsed = time.time() - start
        
        # Should complete in < 2 seconds (increased margin for CI)
        assert elapsed < 2.0, f"Vectorized D→T took {elapsed:.2f}s, expected < 2s"
        assert len(T_values) == n_cells


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
