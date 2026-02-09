# API Reference

Module-level API documentation for PhilFlood.

**Status**: v0.3.0 implementation. Full docstring extraction in progress.

---

## Using the API in Your Code

```python
# Example: Extract and calibrate discharge data
from philflood.adapters.glofas_grib_v4_optimized import extract_timeseries_streaming
from philflood.calibration.evt_pot import fit_gpd_from_exceedances
from philflood.config import load_basin_config

# Load basin configuration
config = load_basin_config("ops/configs/basins/Cagayan_01.yaml")

# Stream GRIB data
ts = extract_timeseries_streaming(
    grib_file="discharge_data.grib",
    point_coords=[(config['aoi_bbox'][1], config['aoi_bbox'][0])]
)

# Fit bootstrap return levels
return_levels = fit_gpd_from_exceedances(
    ts.values, 
    threshold=config['evt_parameters']['threshold_m3s']
)
```

---

## Core Modules

### adapters/
**Data extraction and transformation from external sources.**

- `glofas_grib_v4_optimized.py` - Streaming GRIB file extraction
  - `extract_timeseries_streaming()` - Memory-efficient year-by-year discharge extraction
  - Returns: pandas.Series or xarray.DataArray

- (Planned) `climada_river.py` - CLIMADA hazard integration

### calibration/
**Extreme Value Theory calibration workflows.**

- `evt_pot.py` - Peaks Over Threshold calibration
  - `fit_gpd_from_exceedances()` - Fit distribution to threshold exceedances
  - `calculate_return_levels_bootstrap()` - Generate return periods with uncertainty
  - `estimate_evt_threshold()` - Auto-detect optimal threshold from MRL plot

### models/
**Core domain models and calculations.**

#### models/ev/
- `gpd_estimator.py` - Generalized Pareto Distribution
  - `fit_gpd()` - MLE parameter estimation
  - `gdp_cdf()`, `gpd_pdf()` - Distribution functions
  - `return_period_to_discharge()`, `discharge_to_return_period()` - Conversion formulas

#### models/impact/
- (Planned) Impact calculation models for Notebook 2+
- CLIMADA Hazard → Exposure → Impact workflow

#### models/risk/
- (Planned) Risk aggregation for multi-basin operations

### config/
**Configuration loading and validation.**

- `load_basin_config()` - Load and validate YAML basin configuration
- `validate_config()` - Check YAML schema compliance
- `BasinConfig` (dataclass) - Schema definition

### domain/
**Domain entities (business logic independent of frameworks).**

- `Basin` (dataclass) - Watershed configuration and metadata
- `CalibrationMetadata` - EVT calibration results storage

### geo/
**Spatial operations for coordinates and boundaries.**

- `reproject_to_wgs84()` - Convert to EPSG:4326
- `get_basin_centroid()` - Calculate center point
- `buffer_bbox()` - Expand boundary box

### pipelines/
**Orchestration of multi-step workflows.**

- (Partial) `monitoring.py` - Operational alert generation
- (Planned) `validation.py` - QC checks for production outputs

### ops/
**Operational deployment and CLI.**

- `cli.py` - Command-line interface
  - `monitor` - Run monitoring for basin(s)
  - `validate` - QC configuration and data

### qc/
**Quality control and verification utilities.**

- `validate_output.py` - Check output file integrity
- `compare_versions.py` - Compare calibration outputs

### utils/
**General utilities (logging, file I/O, etc.).**

---

## Configuration YAML Schema

```yaml
# Example: ops/configs/basins/my_basin.yaml
basin_id: "Cagayan_01"
basin_name: "Cagayan Basin"
country: "PHL"

aoi_bbox: [16.0, 121.0, 19.0, 123.0]  # [min_lat, min_lon, max_lat, max_lon]
calibration_mode: "basin"  # or "municipality" for gridded impacts

glofas_point_id: "PHL_12345"  # From GloFAS documentation

evt_parameters:
  threshold_m3s: 1500.0              # POT threshold
  shape_xi: -0.15                    # GPD shape parameter
  scale_sigma: 250.0                 # GPD scale parameter
  annual_exceedances: 2.5            # Expected events per year

return_periods: [2, 5, 10, 20, 50, 100, 200, 500]  # Years

hazard_output_dir: "data/processed/climada_hazard/Cagayan_01/"
```

---

## Data Structures

### Basin Configuration
```python
{
  'basin_id': str,
  'aoi_bbox': tuple[4],  # (lat_min, lon_min, lat_max, lon_max)
  'glofas_point_id': str,
  'evt_parameters': {
    'threshold_m3s': float,
    'shape_xi': float,
    'scale_sigma': float,
    'annual_exceedances': float
  },
  'return_periods': list[int]
}
```

### Calibration Output
```python
{
  'return_levels': xarray.DataArray,  # (return_period, bootstrap)
  'parameters': {
    'shape': float,
    'scale': float,
    'loc': float  # Threshold
  },
  'goodness_of_fit': {
    'ks_statistic': float,
    'anderson_darling': float
  }
}
```

### Operational Output (JSON)
```json
{
  "basin_id": "Cagayan_01",
  "forecast_date": "2024-12-15T12:00:00Z",
  "alarms": [
    {
      "return_period": 20,
      "probability": 0.15,
      "status": "alert"
    }
  ],
  "output_path": "data/ops/outputs/2024-12-15/"
}
```

---

## Development Status

| Module | Status | v0.3.0 | v1.0.0 |
|---|---|---|---|
| adapters/glofas_grib_v4_optimized | ✅ Full | ✓ | ✓ |
| calibration/evt_pot | ✅ Full | ✓ | ✓ |
| models/ev | ✅ Full | ✓ | ✓ |
| config | ✅ Full | ✓ | ✓ |
| domain | ✅ Full | ✓ | ✓ |
| geo | ✅ Full | ✓ | ✓ |
| ops/cli | ✅ Full | ✓ | ✓ |
| qc/validate_output | 🟡 Partial | ✓ | ✓ |
| adapters/climada_river | 📋 Planned | - | ✓ |
| models/impact | 📋 Planned | - | ✓ |
| models/risk | 📋 Planned | - | ✓ |
| pipelines/monitoring | 🟡 Skeleton | ✓ | ✓ |
| ops/rest_api | 📋 Planned | - | ✓ |

---

## Building from Source

### Extract Full Docstrings
```bash
cd src/philflood

# Generate API documentation
pdoc3 --html --output-dir ../../docs/technical/api-reference/ \
  adapters calibration models config domain geo pipelines ops qc utils
```

### Generate from Notebook Examples
See [Notebook 1 Calibration Guide](../../user-guides/notebook01-calibration-guide.md) and [Notebook 2 Hazard Guide](../../user-guides/notebook02-hazard-guide.md) for practical API usage examples.

---

## Testing the API

See [TESTING.md](../../contributing/TESTING.md) for:
- Unit test patterns for API methods
- Integration test examples
- Mock fixtures for external dependencies (GRIB data, CLIMADA)

---

**Related Documentation**:
- [ARCHITECTURE.md](../ARCHITECTURE.md) - Module organization and data flows
- [Methods Overview](../methods-overview.md) - Scientific basis and formulas
- [Contributing Guide](../../contributing/CONTRIBUTING.md) - Code style and development workflow
