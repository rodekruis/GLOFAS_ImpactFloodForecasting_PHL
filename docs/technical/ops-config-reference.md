# Configuration Management for Calibration Notebooks

## Overview

This document explains the new dynamic configuration system that allows calibration notebooks (NB01–NB04) to automatically discover and reuse run configurations across the pipeline.

## Key Components

### 1. `philflood/ops/config.py`

A new module providing utilities for configuration management:

- **`load_run_config()`** — Load NB01 run_config.json with auto-discovery
- **`resolve_evt_paths()`** — Resolve EVT1 data paths dynamically
- **`find_repo_root()`** — Locate repository root automatically
- **`print_config_summary()`** — Print formatted configuration to console
- **`get_standard_data_paths()`** — Get standard data directory paths

### 2. Configuration File Format

NB01 saves a `run_config.json` file at:
```
data/processed/calibration/evt_pot/{BASIN_ID}/{RUN_TAG}/run_config.json
```

**Expected keys:**
```python
{
    "basin_id": "Cagayan_01",                    # Basin identifier
    "run_tag": "2026-01-19_calib-test",          # Run timestamp/tag
    "selection_mode": "basin",                   # 'basin' or 'municipality'
    "evt_params_parquet": "/path/to/evt_params.parquet",
    "discharge_ts_parquet": "/path/to/discharge_ts.parquet",
    "timeseries_dir": "/path/to/timeseries/",
    "adm3_geojson": "/path/to/admin/boundaries.geojson",
    "worldpop_raster": "/path/to/worldpop.tif",
    "jrc_root": "/path/to/jrc/flood/maps/",
    "run_config_path": "/path/to/run_config.json"
}
```

## Usage in Notebooks

### NB02, NB03, NB04: Loading Configuration

```python
from philflood.ops.config import load_run_config, print_config_summary

# Auto-load latest NB01 config
config = load_run_config(
    search_processed_root=PROCESSED_ROOT,
    auto_select_latest=True,
)

if config:
    print_config_summary(config, title="NB01 Run Configuration")
    evt_params = Path(config['evt_params_parquet'])
else:
    print("No NB01 config found; using fallback paths")
```

### NB04 Specific: Dynamic EVT1 Paths

The updated NB04 notebook automatically discovers NB01 output paths:

```python
# Config is loaded in Section 0
nbs_run_config = load_run_config(
    search_processed_root=PROCESSED_ROOT,
    auto_select_latest=True,
)

# EVT1 paths are resolved dynamically
if nbs_run_config:
    EVT1_PARAMS_PARQUET = Path(nbs_run_config.get('evt_params_parquet'))
    DISCHARGE_TS_PARQUET = Path(nbs_run_config.get('discharge_ts_parquet'))
else:
    # Fallback to standard paths
    EVT1_PARAMS_PARQUET = PROCESSED_ROOT / "calibration" / "evt_pot" / "evt_params.parquet"
    DISCHARGE_TS_PARQUET = PROCESSED_ROOT / "calibration" / "evt_pot" / "discharge_ts.parquet"
```

## Workflow Scenarios

### Scenario A: Single Basin, Single Run

1. **NB01** runs calibration → saves `run_config.json`
2. **NB02** auto-discovers the config → resolves paths automatically
3. **NB03** auto-discovers the config → resolves paths automatically
4. **NB04** auto-discovers the config → resolves EVT1 paths automatically

**No manual path editing required!**

### Scenario B: Multiple Basins, Testing

If multiple `run_config.json` files exist in `data/processed/calibration/evt_pot/`:

- **With `auto_select_latest=True`**: Loads the most recently modified config
- **With `auto_select_latest=False`**: Returns empty dict; user must provide explicit path

### Scenario C: Manual Override

For explicit control, provide a specific config path:

```python
config = load_run_config(
    run_config_path="/path/to/specific/run_config.json"
)
```

## Fallback Behavior

All downstream notebooks include fallback logic:

1. **Try to load** NB01 config from `data/processed/calibration/evt_pot/*/`
2. **If found**: Use paths from config
3. **If not found**: Use standard hardcoded fallback paths

This ensures notebooks work even if:
- NB01 run_config.json is missing
- `philflood` package is not installed
- Directory structure differs slightly

## Benefits

### For Users

- ✅ **No manual path editing** between notebooks
- ✅ **Automatic basin/run detection** from NB01 output
- ✅ **Robust fallbacks** if configuration is missing
- ✅ **Auditable** — config path logged to console

### For Developers

- ✅ **Reusable code** — centralized in `philflood/ops/config.py`
- ✅ **Consistent pattern** — all notebooks use same logic
- ✅ **Testable** — standalone utility functions
- ✅ **Extensible** — easy to add new path types

## Testing the Configuration System

### Quick Test

```python
from pathlib import Path
from philflood.ops.config import load_run_config, print_config_summary

processed_root = Path("data/processed")
config = load_run_config(processed_root, auto_select_latest=True)

if config:
    print_config_summary(config)
    print(f"Basin: {config.get('basin_id')}")
    print(f"EVT params: {config.get('evt_params_parquet')}")
else:
    print("No config found!")
```

### Verify NB04 Integration

1. Open [04_ImpactCatalogue_ImpactEVT_CATMODEL_10000y.ipynb](../../calibration/notebooks/04_ImpactCatalogue_ImpactEVT_CATMODEL_10000y.ipynb)
2. Run Section 0 (CONFIG)
3. Check console output:
   - If NB01 config found: ✓ Loaded from [path]
   - If not found: ⚠ No NB01 run_config.json found

## Troubleshooting

### Issue: "No NB01 run_config.json found"

**Possible causes:**
1. NB01 hasn't been run yet
2. NB01 run_config.json is in a different location
3. `data/processed/` doesn't exist

**Solution:**
- Run NB01 first to generate run_config.json
- Or provide explicit path: `load_run_config(run_config_path="/full/path/run_config.json")`

### Issue: "Import from philflood.ops.config failed"

**Possible causes:**
1. `src/` not on Python path
2. Package not installed

**Solution:**
- Notebooks include fallback implementations with same behavior
- Or: `pip install -e .` from repo root to install package

### Issue: "EVT_PARAMS_PARQUET path does not exist"

**Possible causes:**
1. Paths in run_config.json are stale (from old NB01 run)
2. Files were moved or deleted

**Solution:**
- Rerun NB01 to regenerate run_config.json
- Or manually verify path in run_config.json file

## Migration Guide

### For Users Upgrading NB04

**Before:** Manually edit hardcoded paths in Section 0
```python
EVT1_PARAMS_PARQUET = PROCESSED_ROOT / "calibration" / "evt_pot" / "evt_params.parquet"
DISCHARGE_TS_PARQUET = PROCESSED_ROOT / "calibration" / "evt_pot" / "discharge_ts.parquet"
```

**After:** Automatic discovery (no editing needed)
```python
# Paths are resolved from NB01 config automatically
# Fallback to standard paths if config not found
```

### For Developers

To use configuration in other notebooks:

```python
from philflood.ops.config import load_run_config, print_config_summary

config = load_run_config(PROCESSED_ROOT, auto_select_latest=True)
print_config_summary(config)
```

## Related Documentation

- [NB01 Calibration Workflow](../../calibration/notebooks/01_evt_pot_calibration_workflow.ipynb)
- [NB04 Impact Catalogue](../../calibration/notebooks/04_ImpactCatalogue_ImpactEVT_CATMODEL_10000y.ipynb)
- [Configuration Schema](../../calibration/scripts/config_schema.yaml)

## Future Enhancements

Planned improvements:

1. **Validation function** — `validate_config()` to check required keys
2. **Merging configs** — Handle multiple basin runs in one workflow
3. **Config versioning** — Track schema changes over time
4. **Environment-specific paths** — Support dev/staging/production environments
5. **Encrypted credentials** — Secure handling of API keys/tokens

---

**Last Updated:** 2026-02-25
**Maintained By:** IFRC Climate Centre Philippines
