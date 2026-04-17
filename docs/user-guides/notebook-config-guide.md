# Standardized Notebook Configuration Pattern

This document describes the standardized configuration pattern used across all calibration notebooks (01–04) to ensure consistency, reduce code duplication, and eliminate path-related errors.

## Quick Reference

All notebooks follow this structure:

### Section 0: Configuration
1. **Section 0.1: Imports & Setup** — Load dependencies and standardized utilities
2. **Section 0.2: User Configuration** — Edit this section to change behavior
3. **Section 0.3: Auto-detection & Path Resolution** — Automatically discover paths from prior notebook outputs
4. **Section 0.4: Validation & Summary** — Check that all inputs are available

### Shared Utilities Module

All notebooks use functions from `philflood.utils` for consistent path handling:

```python
from philflood.utils import (
    find_repo_root,              # Locate repo root reliably
    load_run_config,             # Load NB01 config.json with auto-discovery
    get_nb_output_paths,          # Derive standard output paths
    validate_data_paths,         # Check file existence
    print_config_summary,        # Print formatted config status
)
```

### Configuration Sections by Notebook

#### **Notebook 01 (evt_pot_calibration_workflow.ipynb)**

| Section | Purpose | Edit | Example |
|---------|---------|------|---------|
| 0.1 | Imports, repo root detection | No | Auto-detects `src/` folder |
| 0.2 | User Configuration | **YES** | `ANALYZE_BY_MUNICIPALITY`, `run_name`, `years_to_analyze` |
| 0.3 | Advanced Settings | Rarely | Basin paths, processing parameters |
| 0.4 | Validation | No | Checks required input paths |
| **Output** | Exports `run_config.json` | — | Central artifact for downstream notebooks |

**Key Configuration Variables:**
- `ANALYZE_BY_MUNICIPALITY` (bool): Choose analysis mode
- `run_name` (str): Run identifier (e.g., `"2026-01-19_calib-test"`)
- `basin_config_file` (str): Path to YAML basin config (if basin mode)

**Output:** Creates `data/processed/calibration/{basin_id}/{run_name}/run_config.json`

---

#### **Notebook 02 (HazardOnly_Workflow_v2.ipynb)**

| Section | Purpose | Edit | Example |
|---------|---------|------|---------|
| 0.1 | Imports, PyArrow compat | No | Environment workaround |
| 0.2 | User Configuration | **YES** | `AUTO_DETECT`, `APPLY_FLOPROS`, `REGRID_METHOD` |
| 0.3 | System Resource Detection | Rarely | Auto-detects RAM, storage type |
| 0.4 | Auto-detection & Path Resolution | No | Loads NB01 `run_config.json` |
| 0.5 | Derived Paths | No | JRC URLs, processing paths |
| 0.6 | Validation | No | Checks system resources, paths |

**Key Configuration Variables:**
- `AUTO_DETECT` (bool): Auto-load from most recent NB01 run
- `basin_id_input` (str, optional): Override auto-detected basin ID
- `run_tag_input` (str, optional): Override auto-detected run tag
- `APPLY_FLOPROS` (bool): Apply flood protection masking

**Input:** Loads `data/processed/calibration/{basin_id}/{run_tag}/run_config.json` (from NB01)

**Processing Strategy:**
1. Try to load `run_config.json` from NB01 output
2. If successful, extract `basin_id`, `run_tag`, and other metadata
3. Automatically resolve paths to EVT parameters and timeseries
4. Fall back to manual configuration if auto-detect fails

---

#### **Notebook 03 (validation_notebook_FINAL.ipynb)**

| Section | Purpose | Edit | Example |
|---------|---------|------|---------|
| 0.1 | Imports, repo root detection | No | Auto-detects repo structure |
| 0.2 | Repo Root & Default Paths | **YES** (if needed) | Standard data paths |
| 0.3 | Auto-detection & Mode Selection | No | Loads NB01 `run_config.json` |
| 0.4 | User Controls | **YES** | Validation parameters (thresholds, metrics) |
| 0.5 | AOI Boundary Building | No | Constructs AOI from admin units |
| 0.6 | Summary & Validation | No | Logs config + checks path existence |

**Key Configuration Variables:**
- `AUTO_DETECT` (bool): Auto-load from NB01 output
- `basin_id_input` (str, optional): Override auto-detected basin ID
- `DECLUSTER_GAP_DAYS` (int): Event clustering parameter
- `DEPTH_THRESHOLDS_FOR_METRICS` (list): Thresholds for confusion matrix

**Input:** Loads `data/processed/calibration/{basin_id}/{run_tag}/run_config.json` (from NB01)

**Processing Strategy:**
1. Load `run_config.json` to get basin_id, run_tag, selected municipalities
2. Derive paths to EVT parameters, timeseries, and validation output directories
3. Build AOI boundary from selected municipalities
4. Validate that all required input files exist

---

#### **Notebook 04 (ImpactCatalogue_ImpactEVT.ipynb)** ← **NOW STANDARDIZED**

| Section | Purpose | Edit | Example |
|---------|---------|------|---------|
| 0.1 | Imports, standardized utilities | No | Auto-loads `philflood.utils` |
| 0.2 | User Configuration | **YES** | `RUN_SELF_TEST`, `AOI_MODE`, manual path overrides |
| 0.3 | Auto-detection & Path Resolution | No | Loads NB01 `run_config.json` |
| 0.4 | Validation & Summary | No | Checks all input paths |
| Processing (Sections 1–8) | Unchanged | — | — |

**Key Configuration Variables:**
- `RUN_SELF_TEST` (bool): Use mock data for testing
- `AOI_MODE` (str): Either `"adm3"` or `"custom"`
- `AOI_ADM3_IDS` (list): Admin unit IDs (if mode=`"adm3"`)
- `AOI_CUSTOM_GEOJSON_PATH` (str): Custom boundary polygon (if mode=`"custom"`)
- **Path overrides (LEAVE AS None FOR AUTO-DETECT):**
  - `NB1_RUN_CONFIG_JSON` (str, optional): Explicit path to NB01 config
  - `ADMIN3_GEOJSON` (str, optional): Admin boundaries
  - `WORLDPOP_TIF` (str, optional): Population raster
  - `JRC_ROOT` (str, optional): JRC flood maps directory

**Input:** Auto-loads `data/processed/calibration/*/*/run_config.json` (latest by modification time)

**Processing Strategy:**
1. Try to auto-load NB01 `run_config.json` from standard location
2. If successful, extract paths to EVT parameters, timeseries, admin boundaries, etc.
3. Allow manual override of any paths (set to non-None values)
4. Fall back to standard data directory structure if auto-detection incomplete
5. Validate all paths exist before processing
6. Support self-test mode (RUN_SELF_TEST=True) with generated mock data

---

## Common Pattern: Auto-Detection Pipeline

Each notebook (02–04) follows this cascade:

```
1. Try to load NB01.run_config.json
   ├─ If NB1_RUN_CONFIG_JSON is set explicitly
   ├─ OR search recursively in data/processed/
   └─ (auto-select latest by modification time if multiple found)

2. Extract configuration from JSON
   ├─ basin_id, run_tag, selection_mode
   ├─ Paths: evt_params_parquet, timeseries_dir
   └─ Metadata: adm3_ids, selected_municipalities

3. Resolve downstream paths using standard conventions
   ├─ data/processed/calibration/{basin_id}/{run_tag}/
   └─ data/raw/{required_data}/

4. Validate all paths exist
   ├─ Warn on missing optional paths
   ├─ Error on missing required paths

5. Proceed with processing
```

## Path Resolution Strategy

### Standard Directory Structure

```
REPO_ROOT/
├── data/
│   ├── raw/
│   │   ├── vectors/
│   │   │   └── admin/phl_cod_ab/phl_adm3.geojson
│   │   ├── worldpop/
│   │   ├── jrc_flood_maps/RP{10,20,50,...,500}/
│   │   └── glofas/
│   │
│   └── processed/
│       ├── calibration/
│       │   ├── {BASIN_ID}/
│       │   │   └── {RUN_TAG}/
│       │   │       ├── run_config.json (NB01 export)
│       │   │       ├── evt_params.parquet
│       │   │       ├── timeseries/ (discharge timeseries per cell)
│       │   │       ├── hazard_outputs/
│       │   │       └── validation_outputs/
│       │   │
│       │   └── municipality/
│       │       └── {RUN_TAG}/ (if municipality mode)
│       │
│       ├── ev/
│       ├── hazard/
│       └── validation/
│
├── calibration/
│   ├── notebooks/
│   │   ├── 00_download_ECMWF.ipynb
│   │   ├── 01_evt_pot_calibration_workflow.ipynb
│   │   ├── 02_HazardOnly_Workflow_v2.ipynb
│   │   ├── 03_validation_notebook_FINAL.ipynb
│   │   └── 04_ImpactCatalogue_ImpactEVT.ipynb ← standardized
│   │
│   └── scripts/
│       └── config_schema.yaml (configuration schema)
│
└── src/
    └── philflood/
        └── utils/
            ├── __init__.py
            ├── notebook_config.py (NEW: shared config functions)
            └── paths.py
```

### Path Resolution by Notebook

| Component | NB01 (Output) | NB02 (Input) | NB03 (Input) | NB04 (Input) |
|-----------|---|---|---|---|
| **run_config.json** | ✍️ Exports | 📖 Loads (auto) | 📖 Loads (auto) | 📖 Loads (auto) |
| **evt_params.parquet** | ✍️ Creates | 📖 Reads | 📖 Reads | 📖 Reads |
| **timeseries/** | ✍️ Creates | 📖 Reads | 📖 Reads | 📖 Reads |
| **hazard_outputs/** | — | ✍️ Creates | 📖 Reads | — |
| **validation_outputs/** | — | — | ✍️ Creates | — |

**Key Rule:** Each notebook creates outputs in a subfolder named after itself and the run_tag:
- NB01: `data/processed/calibration/{basin_id}/{run_tag}/`
- NB02: `data/processed/hazard/{basin_id}/{run_tag}/` (if applicable)
- NB03: `data/processed/validation/{basin_id}/{run_tag}/`
- NB04: `./outputs_nb4_5/` (configurable via `OUTPUT_DIR`)

---

## Error Messages & Solutions

### "Could not find repository root"

**Cause:** Notebook can't auto-detect `src/` folder or other markers  
**Solution:**  
```python
# In Section 0.1, set manually:
REPO_ROOT = Path("/path/to/GLOFAS_ImpactFloodForecasting_PHL")
```

### "No run_config.json found"

**Cause:** NB01 has not been run yet, or output is in non-standard location  
**Solution:**  
```python
# In Section 0.2, set explicitly:
NB1_RUN_CONFIG_JSON = Path("data/processed/calibration/Cagayan_01/2026-01-19_test/run_config.json")
# OR
RUN_SELF_TEST = True  # Use mock data for development
```

### "Missing input paths: ADMIN3_GEOJSON_exists"

**Cause:** Auto-detected path doesn't exist  
**Solution:**  
```python
# In Section 0.2, override explicitly:
ADMIN3_GEOJSON = Path("data/raw/vectors/admin/phl_cod_ab/phl_adm3.geojson")
# OR check that file actually exists at that location
```

### "EVT params or timeseries missing"

**Cause:** NB01 output incomplete or in wrong location  
**Solution:**  
```python
# Verify NB01 completed successfully:
# Run NB01 with AUTO_DETECT=True to see summary
# Check that data/processed/calibration/{basin_id}/{run_tag}/ exists

# If NB01 output is in custom location:
EVT_PARAMS_PARQUET = Path("custom/path/to/evt_params.parquet")
TIMESERIES_DIR = Path("custom/path/to/timeseries")
```

---

## Configuration Validation Checklist

Before running production analysis, verify:

- [ ] **NB01:** Completed successfully; `run_config.json` exported
- [ ] **NB02:** Auto-detected NB01 output; paths are valid
- [ ] **NB03:** Auto-detected NB01 output; AOI boundary builds successfully
- [ ] **NB04:** 
  - [ ] `RUN_SELF_TEST=False` OR `True` (intentional choice)
  - [ ] `AOI_MODE` is either `"adm3"` or `"custom"`
  - [ ] All path overrides are either `None` (auto-detect) or valid absolute paths
  - [ ] Configuration summary shows all required paths exist ✅

---

## For Developers: Adding New Configuration

When adding a new configuration variable to a notebook:

1. **Add to Section 0.2 (User Configuration)** with clear comment
2. **Add to Section 0.4 (Validation)** if it's a path that needs checking
3. **Update the Configuration Summary** in this document
4. **Add docstring to any shared function** in `philflood.utils.notebook_config`

Example:
```python
# Section 0.2
MY_NEW_PARAM = None  # Optional: set to override auto-detection

# Section 0.3
if MY_NEW_PARAM is None:
    MY_NEW_PARAM = load_from_config_or_default()

# Section 0.4
config_summary['MY_NEW_PARAM_exists'] = Path(MY_NEW_PARAM).exists()
```

---

## Implementation Notes

### Backward Compatibility

Notebooks can still accept explicit paths as before:
```python
ADMIN3_GEOJSON = "/full/path/to/admin.geojson"  # Overrides auto-detection
```

### Auto-Detection Failures

If auto-detection fails but you have paths available manually, the notebooks gracefully fall back to using the values you set. No code changes needed.

### Run Config JSON Schema

The `run_config.json` file exported by NB01 contains:

```json
{
  "selection_mode": "basin or municipality",
  "basin_id": "Cagayan_01",
  "run_tag": "2026-01-19_test",
  "selected_municipalities": ["adm3_001", "adm3_002"],
  "adm3_geojson": "data/raw/vectors/.../phl_adm3.geojson",
  "worldpop_raster": "data/raw/worldpop/phl_pop_....tif",
  "jrc_root": "data/raw/jrc_flood_maps",
  "evt_params_parquet": "data/processed/calibration/Cagayan_01/2026-01-19_test/evt_params.parquet",
  "timeseries_dir": "data/processed/calibration/Cagayan_01/2026-01-19_test/timeseries",
  "run_config_path": "data/processed/calibration/Cagayan_01/2026-01-19_test/run_config.json"
}
```

---

## Links

- [Notebook 01 Calibration Guide](notebook01-calibration-guide.md)
- [Notebook 02 Hazard Guide](notebook02-hazard-guide.md)
- [Notebook 03 Validation Guide](notebook03-validation-guide.md)
- [Architecture Documentation](technical/ARCHITECTURE.md)
