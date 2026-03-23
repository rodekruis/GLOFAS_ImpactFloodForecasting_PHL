# Calibration Scripts & Configuration Reference

This directory contains scripts and configuration files for the calibration workflow.

## Files

### `config_schema.yaml`

Complete schema and reference documentation for all user-configurable parameters across all four calibration notebooks (01–04).

**Usage:**
- Reference guide for what each configuration variable does
- Schema definition for validation
- Default values and valid options
- Data types and examples

**Key Sections:**
- `notebook_01`, `notebook_02`, `notebook_03`, `notebook_04`: Configuration per notebook
- `shared_utilities`: Description of functions in `philflood.utils.notebook_config`

### Other Scripts

- `generate_basin_config_from_calibration.py`: Generate YAML basin configs from calibration runs
- `run_evt_calibration.py`: Command-line tool for running NB01 programmatically

## Configuration Pattern

All notebooks now follow a **standardized three-section pattern**:

```
Section 0.1: Imports & Logging Setup
Section 0.2: User Configuration (EDIT THIS)
Section 0.3: Auto-detection & Path Resolution
Section 0.4: Validation & Summary
```

### Key Principles

1. **Explicit User Configuration** — Section 0.2 clearly marks what users should edit
2. **Auto-Detection** — Section 0.3 automatically discovers paths from prior notebook outputs
3. **Graceful Fallbacks** — Manual overrides available if auto-detection fails
4. **Consistent Logging** — Standardized logging wrapper (`_log()` or ProgressLogger)
5. **Path Validation** — All paths checked before processing; helpful error messages

## Quick Start

### For Notebook 01 (Calibration)
1. Edit Section 0.2: Set `run_name`, `basin_config_file` or `municipality_ids`
2. Run notebook
3. Output: `data/processed/calibration/{basin_id}/{run_name}/run_config.json`

### For Notebook 02, 03, or 04
1. Set `AUTO_DETECT=True` in Section 0.2 (default)
2. Notebook automatically loads latest NB01 output
3. Override any paths manually if needed (set to non-None value)
4. Run notebook

## Shared Configuration Functions

Located in `src/philflood/utils/notebook_config.py`:

- `load_run_config()` — Load NB01 config.json with auto-discovery
- `get_nb_output_paths()` — Derive standard output paths
- `validate_data_paths()` — Check path existence
- `print_config_summary()` — Print formatted config status
- `load_adm3_gdf()` — Load admin boundaries with standard columns
- `resolve_aoi_boundary()` — Build AOI from admin IDs or basin

## Directory Structure

```
calibration/
├── notebooks/
│   ├── 00_download_ECMWF.ipynb
│   ├── 01_evt_pot_calibration_workflow.ipynb
│   ├── 02_HazardOnly_Workflow_v2.ipynb
│   ├── 03_validation_notebook_FINAL.ipynb
│   └── 04_ImpactCatalogue_ImpactEVT.ipynb ← STANDARDIZED
│
└── scripts/
    ├── config_schema.yaml ← THIS FILE (reference)
    ├── generate_basin_config_from_calibration.py
    ├── run_evt_calibration.py
    └── README.md (this file)
```

## Configuration File Locations

### Inputs (Read by Notebooks)

- `ops/configs/basins/*.yaml` — Basin configuration files
- `data/processed/calibration/*/*/run_config.json` — NB01 output (auto-discovered)
- Various `data/raw/*` paths — Input data

### Outputs (Written by Notebooks)

- `data/processed/calibration/{basin_id}/{run_name}/run_config.json` — NB01 export (central artifact)
- `data/processed/calibration/{basin_id}/{run_name}/evt_params.parquet` — NB01 output
- `data/processed/calibration/{basin_id}/{run_name}/timeseries/` — NB01 output
- `data/processed/hazard/{basin_id}/{run_name}/` — NB02 output
- `data/processed/validation/{basin_id}/{run_name}/` — NB03 output
- `./outputs_nb4_5/` — NB04 output (configurable)

## Common Configuration Tasks

### Run latest calibration straight into validation
```python
# NB03 / NB04 (Set in Section 0.2):
AUTO_DETECT = True  # Auto-loads most recent NB01 run
basin_id_input = None  # If auto-detection works, leave as None
```

### Process multiple basins sequentially
```python
# Run NB01 for each basin with different run_names
# NB02/03/04 will auto-detect each new basin's outputs
```

### Manual override for specific paths
```python
# In any notebook Section 0.2:
EVT_PARAMS_PARQUET = Path("data/processed/calibration/CUSTOM/path/evt_params.parquet")
# Auto-detection will be skipped for this variable
```

### Use self-test mode for development
```python
# NB04 (Section 0.2):
RUN_SELF_TEST = True  # Mock data generation

# NB02/03 also support read-only mode with mock layouts
```

## Troubleshooting

### "Could not find repository root"
→ Ensure you're running from within the repo and `src/` folder exists

### "No run_config.json found"
→ Run NB01 first; check that it exported the config file

### "Missing input paths"
→ Check that `data/raw/` has all required input files
→ Or set paths explicitly in Section 0.2 (don't leave as `None`)

### "Auto-detection failed but I have the paths"
→ Set explicit paths in Section 0.2; notebooks fall back to using them

## For Developers

- Add new parameters to `config_schema.yaml` when modifying notebooks
- Use `print_config_summary()` for formatted config output
- Use `validate_data_paths()` to check all required files exist
- Export new metadata to `run_config.json` if it's needed downstream

## References

- **Full Guide:** [docs/user-guides/notebook-config-guide.md](../../docs/user-guides/notebook-config-guide.md)
- **API Reference:** [src/philflood/utils/notebook_config.py](../../src/philflood/utils/notebook_config.py)
- **Architecture:** [docs/technical/ARCHITECTURE.md](../../docs/technical/ARCHITECTURE.md)
