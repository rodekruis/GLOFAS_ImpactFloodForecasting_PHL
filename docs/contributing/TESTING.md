# Testing Guide

This document explains how to run tests, expectations for coverage, and integration test procedures.

## Running Tests

### Quick Test

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_smoke.py -v

# Run specific test function
pytest tests/test_pot_climada_integration.py::test_pot_to_climada_flow -v

# Run with coverage report
pytest tests/ --cov=philflood --cov-report=html
```

### Test Organization

```
tests/
├── test_smoke.py                          # Basic import and CLI tests
├── test_pot_climada_integration.py        # EVT-to-CLIMADA pipeline
├── test_direct_municipality_selection.py  # Municipality mode
└── fixtures/
    └── generate_test_data.py              # Test data generators
```

## Test Coverage Expectations

- **Minimum coverage**: 70% of core modules (`src/philflood/`)
- **High-priority coverage** (>80%):
  - `models/ev/` - Statistical calculations (critical for accuracy)
  - `config/` - Configuration loading (must detect errors)
  - `domain/` - Business logic (ensures consistency)
  - `qc/` - Quality checks (data validation)

- **Medium-priority coverage** (>60%):
  - `adapters/` - External system interfaces
  - `geo/` - Spatial operations
  - `pipelines/` - Workflow orchestration
  - `utils/` - Infrastructure code

- **Optional coverage** (<60%):
  - `calibration/` - Research notebooks (tested manually)
  - `ops/` - Operational utilities (tested in integration)

**Check coverage**:
```bash
pytest tests/ --cov=philflood --cov-report=term-missing
```

## Unit Tests

### Structure

```python
# tests/test_models_ev.py
import pytest
import pandas as pd
from philflood.models.ev.threshold_selection import auto_select_threshold_pot

class TestThresholdSelection:
    """Tests for POT threshold selection."""
    
    def setup_method(self):
        """Create test fixtures before each test."""
        self.sample_data = pd.Series([1, 2, 3, 5, 8, 13, 21, 34, 55, 89])
        
    def test_auto_select_threshold_basic(self):
        """Test that threshold selection returns a positive value."""
        threshold = auto_select_threshold_pot(self.sample_data)
        
        assert threshold is not None
        assert threshold > 0
        
    def test_auto_select_threshold_validation(self):
        """Test that threshold must be reasonable."""
        with pytest.raises(ValueError, match="Threshold"):
            fit_gpd(self.sample_data, threshold=100.0)  # > all data
            
    def test_fit_gpd_insufficient_data(self):
        """Test behavior with too few exceedances."""
        small_data = pd.Series([1, 2])
        with pytest.raises(ValueError, match="exceedances"):
            fit_gpd(small_data, threshold=0.5)
```

### Assertions

**Good assertions**:
```python
# Exact equality
assert result == expected_value

# Approximate equality (floats)
assert result == pytest.approx(expected_value, rel=0.01)  # 1% tolerance

# Type checking
assert isinstance(result, dict)

# Conditional
assert len(results) > 0
assert 0 <= probability <= 1

# Exceptions
with pytest.raises(ValueError):
    bad_function()
```

**Avoid**:
```python
# Too vague
assert result  # What is "truthy"?

# No message
assert x == y  # Failure message unclear

# Side effects
connection.setup()  # Use fixtures instead
```

## Integration Tests

### POT-to-CLIMADA Pipeline

**File**: `tests/test_pot_climada_integration.py`

**Test flow**:
```python
def test_pot_to_climada_flow(tmp_path):
    """Test complete calibration → CLIMADA hazard pipeline.
    
    Exercises:
    1. EVT threshold selection (POT)
    2. GPD parameter estimation
    3. Bootstrap return level calculation
    4. NetCDF hazard generation
    5. CLIMADA object creation
    """
    
    # 1. Create synthetic discharge data
    discharge_data = generate_synthetic_discharge()
    
    # 2. Perform POT calibration
    pot_model = POTCalibrator(data=discharge_data)
    pot_model.select_threshold_via_mrl()
    evt_params = pot_model.fit_gpd()
    
    # 3. Generate bootstrap return levels
    return_levels = pot_model.bootstrap_return_levels(n_resamples=20)
    
    # 4. Create CLIMADA hazard
    hazard = CLIMADAHazardBuilder(
        return_levels=return_levels,
        centroids=test_centroids
    ).build()
    
    # 5. Validate
    assert hazard.intensity.shape == (8, len(test_centroids))  # 8 return periods
    assert (hazard.frequency > 0).all()
    assert hazard.check()
```

### Municipality Mode Integration

**File**: `tests/test_direct_municipality_selection.py`

Tests the municipality selection workflow:
1. Load multiple municipality boundaries
2. Generate unified AOI (area of interest)
3. Extract discharge from all cells in AOI
4. Verify mode detection in Notebook 2

```python
def test_municipality_mode_detection(tmp_path, muni_geometries):
    """Test auto-detection of municipality mode."""
    
    # Setup: Save municipality geojson
    muni_geojson = tmp_path / "aoi" / "selected_municipalities.geojson"
    muni_gdf.to_file(muni_geojson)
    
    # Test: detect_calibration_mode from Notebook 2
    mode_info = detect_calibration_mode(tmp_path)
    
    assert mode_info['mode'] == 'municipality'
    assert len(mode_info['muni_gdf']) == 3
    assert mode_info['basin_id'] == 'MUNI_SELECTION'
```

## Test Data Generation

### Creating Synthetic Data

```python
# tests/fixtures/generate_test_data.py
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def generate_synthetic_discharge(
    n_years=10,
    base_flow=100,
    flood_frequency=2.5,
    seed=42
) -> pd.DataFrame:
    """Generate synthetic GloFAS-like discharge timeseries.
    
    Args:
        n_years: Years of daily data
        base_flow: Mean baseflow (m³/s)
        flood_frequency: Mean annual exceedances
        seed: Random seed for reproducibility
        
    Returns:
        DataFrame with datetime index and discharge column
    """
    np.random.seed(seed)
    
    dates = pd.date_range(
        start='2015-01-01',
        periods=n_years * 365,
        freq='D'
    )
    
    # Autocorrelated baseflow
    baseflow = np.random.normal(base_flow, 20, len(dates))
    baseflow = pd.Series(baseflow).rolling(7, min_periods=1).mean().values
    
    # Occasional large events (floods)
    floods = np.random.poisson(flood_frequency / 365, len(dates))
    flood_magnitude = np.random.exponential(500, len(dates)) * floods
    
    discharge = np.maximum(baseflow + flood_magnitude, 10)
    
    return pd.DataFrame({
        'datetime': dates,
        'discharge_m3s': discharge
    }).set_index('datetime')
```

## Continuous Integration

### GitHub Actions Workflow

Tests automatically run on:
- **Push to main** - Full test suite
- **Pull requests** - Full test suite + coverage check
- **Scheduled** - Weekly full run

**Required to merge**:
- ✅ All tests pass
- ✅ Coverage ≥70% overall (≥80% for modified modules)
- ✅ No new linter warnings

**Check locally before pushing**:
```bash
# Format code
black src/ tests/
isort src/ tests/

# Run linter
pylint src/philflood --fail-under=8.0

# Run tests
pytest tests/ -v

# Check coverage
pytest tests/ --cov=philflood --cov-report=term-missing
```

## Debugging Failed Tests

### Verbose Output

```bash
# Show print statements
pytest tests/test_file.py -v -s

# Show local variables on failure
pytest tests/test_file.py -v -l

# Drop into debugger on failure
pytest tests/test_file.py -v --pdb
```

### Inspect Test Data

```python
def test_example(tmp_path):
    """Temporarily save and inspect test data."""
    
    # Do something
    data = create_test_data()
    
    # Save for inspection
    data.to_csv(tmp_path / "debug_data.csv")
    print(f"Test data saved: {tmp_path / 'debug_data.csv'}")
    
    # During test failure, the file persists in tmp_path
    # Check pytest output for temp directory location
```

## Test Fixtures

### Reusable Test Data

```python
# tests/conftest.py
import pytest
import geopandas as gpd
from shapely.geometry import box

@pytest.fixture
def sample_basin_geometry():
    """Basin boundary for all tests."""
    return box(16.0, 121.0, 17.0, 122.0)  # Cagayan-like bbox

@pytest.fixture
def sample_discharge_data():
    """10 years of synthetic discharge."""
    return generate_synthetic_discharge(n_years=10)

@pytest.fixture
def sample_municipalities():
    """Three test municipalities."""
    geoms = [
        box(16.0, 121.0, 16.3, 121.3),
        box(16.2, 121.2, 16.5, 121.5),
        box(16.4, 121.4, 16.7, 121.7),
    ]
    return gpd.GeoDataFrame(
        {'name': ['Rizal', 'Tayabas', 'Lucena'], 'geometry': geoms},
        crs='EPSG:4326'
    )
```

Use fixtures:
```python
def test_with_fixture(sample_discharge_data, sample_basin_geometry):
    """Fixtures automatically injected."""
    assert len(sample_discharge_data) > 0
    assert sample_basin_geometry.bounds is not None
```

## Mocking External Dependencies

### Mock GRIB Extraction

```python
from unittest import mock
from philflood.adapters.glofas_grib_v4_optimized import extract_timeseries_streaming

@mock.patch('rasterio.open')
def test_grib_extraction(mock_rasterio):
    """Test without actual GRIB files."""
    
    # Mock the file
    mock_rasterio.return_value.__enter__.return_value = MagicMock()
    
    # Call function
    result = extract_timeseries_streaming(
        grib_path="dummy.grib",
        vg_ids=[...]
    )
    
    # Verify call was made
    mock_rasterio.assert_called_once()
```

### Mock CLIMADA Hazard

```python
@pytest.fixture
def mock_climada_hazard():
    """Minimal CLIMADA hazard for testing."""
    from climada.hazard import Hazard
    from unittest import mock
    
    hazard = Hazard('RF')  # Riverine flood
    hazard.centroids.lat = [16.0, 16.1, 16.2]
    hazard.centroids.lon = [121.0, 121.1, 121.2]
    hazard.intensity = mock.MagicMock()
    hazard.frequency = np.array([0.1, 0.05, 0.02])
    
    return hazard
```

## Performance Testing

### Benchmarking

```python
import pytest
import time

@pytest.mark.benchmark
def test_grib_extraction_speed(benchmark):
    """Ensure streaming extraction stays < 60s for 10 years."""
    
    result = benchmark(
        extract_timeseries_streaming,
        grib_dir="data/raw/glofas/",
        vg_ids=['PHL_12345'],
        years=[2015, 2016, 2017]
    )
    
    assert result is not None
    # benchmark.max_time = 60  # seconds
```

Run benchmark:
```bash
pytest tests/ -m benchmark -v
```

## Common Test Patterns

### Configuration Validation

```python
def test_invalid_basin_config():
    """Ensure bad configs are rejected."""
    bad_config = {
        'basin_name': 'test',
        # Missing required 'glofas_points'
    }
    
    with pytest.raises(ValueError, match="glofas_points"):
        load_basin_config_dict(bad_config)
```

### Return Type Validation

```python
def test_fit_gpd_returns_correct_type():
    """EVT fitting returns expected structure."""
    params = fit_gpd(test_data, threshold=100)
    
    assert isinstance(params, dict)
    assert set(params.keys()) >= {'shape', 'scale', 'threshold'}
    for val in params.values():
        assert isinstance(val, (int, float))
```

### Edge Case Handling

```python
def test_pot_with_no_exceedances():
    """Gracefully handle data with no exceedances."""
    flat_data = np.ones(100) * 10
    
    with pytest.raises(ValueError, match="No exceedances"):
        fit_gpd(flat_data, threshold=100)
```

---

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [unittest.mock](https://docs.python.org/3/library/unittest.mock.html)
- [Coverage.py](https://coverage.readthedocs.io/)
- [Effective Python Testing](https://effective-python-testing.readthedocs.io/)

---

**Questions?** See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup.
