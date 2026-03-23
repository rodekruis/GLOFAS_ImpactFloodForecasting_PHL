# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**PhilFlood** is a Python package for impact-based flood forecasting in the Philippines using GloFAS discharge data and Extreme Value Theory (EVT/POT-GPD). The package calibrates statistical models per river basin, generates hazard maps, and evaluates population impact.

Current version: **v0.3.0**. Key placeholder implementations (CLIMADA hazard integration, full population impact) are slated for v1.0.0 (Q2 2026).

## Environment Setup

```bash
# Create conda environment (required — cfgrib/eccodes for GRIB files don't install well via pip alone)
conda env create -f environment.yml
conda activate philflood  # or the name in environment.yml

# Install package in editable mode
pip install -e .

# Dev dependencies
pip install -r requirements-dev.txt

# Ops dependencies (only needed for scheduled monitoring)
pip install -r requirements-ops.txt
```

## Common Commands

```bash
# Run all tests
pytest

# Run tests verbosely
pytest tests/ -v

# Run a single test file
pytest tests/test_smoke.py -v
pytest tests/test_threshold_selection.py -v

# Lint (ruff + black)
ruff check src/ tests/
black --check src/ tests/

# Auto-fix lint issues
ruff check --fix src/
black src/ tests/

# CLI entry points
philflood monitor --basin ops/configs/basins/Cagayan_01.yaml
philflood validate --basin ops/configs/basins/Cagayan_01.yaml
philflood calibrate --basin ops/configs/basins/Cagayan_01.yaml
```

## Architecture

### Source Layout (`src/philflood/`)

The package follows a layered architecture with strict separation of concerns:

- **`adapters/`** — External data access. `glofas_grib_v4.py` for standard use; `glofas_grib_v4_optimized.py` for low-memory streaming (94% RAM reduction). Legacy adapters are in `_archive/` (glofas, glofas_grib_streaming, climada_river, hazard_maps, geo/aoi, geo/worldpop) — deprecated since v0.3.0, do not import from there.
- **`domain/`** — Core business entities. `basin.py` defines the canonical dataclasses: `BasinConfig`, `EVTConfig`, `VulnerabilityConfig`, `TriggerConfig`. `config.py` handles YAML serialization.
- **`calibration/`** — EVT/POT fitting. `evt_pot.py` is the main entry point; wraps `pyextremes` with memory cleanup and cross-version API compatibility.
- **`models/`** — Statistical models. `ev/` for extreme value (GPD/POT threshold selection), `impact/` for population exposure calculations (partial in v0.3).
- **`geo/`** — Spatial ops (HydroBASINS watershed extraction, worldpop raster joins, interpolation).
- **`pipelines/`** — Orchestration. `monitoring.py` runs operational forecasts; `validation.py` validates basin configs.
- **`ops/`** — Production support. `logging_config.py` provides structured JSON logging; `config.py` for runtime configuration.
- **`qc/`** — Time series quality control.
- **`utils/`** — Memory profiling, path helpers, event detection/declustering, notebook config.

### Configuration System

Basin configurations are YAML files in `ops/configs/basins/`. They are deserialized into `BasinConfig` dataclasses via `load_basin_config(path)`. See `ops/configs/basins/example_basin.yaml` for the schema, and `Cagayan_01.yaml` for a real example.

`calibration/scripts/config_schema.yaml` documents the schema shared by the calibration notebooks.

### Notebook Config Auto-Discovery

All notebooks NB02–NB06 auto-detect the latest NB01 run via:

```python
from philflood.ops.config import load_run_config
cfg = load_run_config(PROCESSED_ROOT, auto_select_latest=True)
# or explicit:
cfg = load_run_config(run_config_path="/path/to/run_config.json")
```

Config file location: `data/processed/calibration/evt_pot/{BASIN_ID}/{RUN_TAG}/run_config.json`

Auto-discovery glob: `data/processed/calibration/evt_pot/*/*/run_config.json` — picks the most recently modified when multiple exist. Returns empty dict `{}` (never raises) if not found; notebooks fall back to hardcoded paths. See `src/philflood/ops/config.py` for the full API.

### Notebook Workflow (Calibration Pipeline)

Notebooks are the primary interface for analysts; they run sequentially and pass state via `run_config.json`:

1. **NB00** — Download GloFAS GRIB data from ECMWF
2. **NB01** (`01_evt_pot_calibration_workflow.ipynb`) — **Primary entry point**: fit EVT/POT models per GloFAS cell; outputs `run_config.json`
   - **EVT1 robustness improvements** (completed): threshold selection now includes MRL linearity check (`compute_mrl()`), KS GoF test on PIT (`gpd_gof_test()`), dispersion hard-gated (`DISPERSION_HARD=True`), `TARGET_LAMBDA_RANGE` demoted to soft flag only (`lambda_flag` column, never blocks). `N_BOOTSTRAP` increased 20→500 for stable CIs.
   - New diagnostics columns in per-gauge parquets: `gof_pvalue`, `gof_pass`, `mrl_linear_ok`, `lambda_flag`. Output schema of `evt_pot_calibration.parquet` and `return_levels_bootstrap.parquet` is **unchanged** — downstream notebooks (NB02–NB07) unaffected.
   - Section 11B now renders: GoF p-value histogram, dispersion histogram, lambda histogram, per-gauge MRL curve, and a table of gauges requiring manual review.
   - **scipy sign convention**: `gpd_xi` in `evt_pot_calibration.parquet` uses EVT convention — positive ξ means heavy tail. The old negation bug in `threshold_selection.py` (line 280) has been fixed. `bootstrap_pot_return_levels()` also uses scipy `c = ξ` directly (no flip).
3. **NB02** — Generate hazard maps (flood depth TIFF/NetCDF) from EVT + JRC data.
   - Dual-mode: basin (default) or municipality cluster — auto-detected from NB01 output (`MUNI_SELECTION` folder presence).
   - Output paths: `climada_hazard/{BASIN_ID}/{RUN_TAG}/` or `climada_hazard/MUNI_SELECTION/{RUN_TAG}/`.
   - `LOW_RAM_MODE` auto-detected at runtime (< 8 GB available RAM → 256×256 tile chunks; ≥ 8 GB → 512×512). Override: `PHILFLOOD_LOW_RAM=1` or `PHILFLOOD_LOW_RAM=0`.
4. **NB03** — Validate NB02 hazard maps against observed flood events.
   - Inputs: NB02 flood depth TIFFs + observed flood extent shapefile.
   - Outputs: confusion matrix, F1 / IoU / Bias / Precision / Recall per return period.
   - Key decision parameter: binary flood classification threshold (default 0.2 m depth).
5. **NB04** (`04_ImpactCatalogue_ImpactEVT_CATMODEL_10000y_UPDATED.ipynb`) — Build impact event catalogue; fit EVT2 on people-affected; reforecast tail mining.
   - Detects historical flood events via connected-component analysis on active GloFAS cells exceeding EVT1 discharge thresholds.
   - Intersects flood depth TIFFs (from NB02) with WorldPop population grid to compute PopAffected at multiple depth thresholds per event.
   - **Multi-depth-threshold EVT2** (v0.5.0): Fits EVT2 (spliced empirical body + POT-GPD tail) independently for **11 depth thresholds** [0.01, 0.02, 0.03, 0.04, 0.05, 0.1, 0.15, 0.2, 0.3, 0.5, 1.0] m. Each threshold produces a `PopAffected_{N}mm` column (e.g., `PopAffected_20mm`). `DEPTH_PRIMARY = 0.02` is the main pipeline threshold. Legacy aliases `PopAffected_op` and `PopAffected_sat` preserved for backward compat.
   - Processes reforecast ensemble members (2005 onward) with same multi-threshold pipeline.
   - Exports: event registry parquet + per-threshold EVT2 fit JSONs → `data/processed/impact_catalogue_catmodel/`.
   - Auto-discovers NB01 `run_config.json` via `load_run_config(PROCESSED_ROOT, auto_select_latest=True)`.
   - **Reads from NB01**: `evt_pot_calibration.parquet` (columns: `virtual_gauge_id`, `threshold_m3s`, `lambda_events_per_year`, `gpd_xi`, `gpd_sigma`). Column rename on load: `virtual_gauge_id→cell_id`, `threshold_m3s→u`, `lambda_events_per_year→lam`, `gpd_xi→xi`, `gpd_sigma→sigma`.
   - **EVT2 threshold selection** (`select_evt2_threshold()`): 3-tier stability approach per depth threshold. Wider tolerances than EVT1 (xi: 0.15, sigma_rel: 0.25). Thresholds that fail (too few exceedances) are silently skipped with summary table.
   - **GOF diagnostics**: GOF computed for all fitted thresholds (KS test summary table). Full plots (QQ, PP, MRL, stability) for primary threshold only. `PLOT_ALL_THRESHOLDS=False` flag for optional full diagnostics.
   - **Distribution comparison**: GPD vs Log-normal vs GEV via AIC/BIC (diagnostic only).
   - **Key outputs**:
     - `evt2/evt2_fit_manifest.json`: lists all 11 thresholds with status (OK/FAILED) and filenames.
     - `evt2/evt2_fit_depth_{N}mm.json`: per-threshold fit parameters (keys: `depth_threshold_m, u, xi, sigma, lam_total, p_exc, lambda_u, threshold_tier, gof_ks_*, hist`). Version `0.5.0`.
     - `evt2/evt2_fit_popaffected_op.json`: **backward-compat copy** of primary threshold file. NB05/NB06/NB07 read this unchanged.
     - `evt2/evt2_return_levels_depth_{N}mm.parquet` + legacy `evt2_return_levels_popaffected_op.parquet`.
     - `event_registry_hist.parquet`: per-event columns include `PopAffected_{N}mm` for all thresholds + `PopAffected_op`, `PopAffected_sat` aliases + `RP_impact`, `RP_empirical` (primary only).
     - `reforecast_library/`: per-year event registries (with all threshold columns) + monthly `impacts_by_admin` parquets.
   - **Performance optimizations** (reforecast loop): bounding-box crop before connected-components labeling (~5-30x faster on sparse grids), `gc.collect()` moved from per-timestep to per-month level.
   - **Sign convention**: `xi = scipy genpareto shape c` directly (positive xi = heavy tail). No sign flip. Consistent with `evt_pot.py` and `threshold_selection.py` (fixed in v0.3.x).
6. **NB05** (`05_Risk_Profiles_IMPROVED_UPDATED_EPMatrix (1).ipynb`) — Risk profiles: 10,000-year YLT simulation → AEP/OEP exceedance curves.
   - **Reads from NB04**: `evt2/evt2_fit_popaffected_op.json` (primary EVT2 fit, backward-compat alias for 20mm threshold) + `evt2/evt2_fit_manifest.json` (all fitted thresholds) + `event_registry_reforecast_library_*.parquet` (all years, auto-glob) + monthly `impacts_by_admin_*` parquets.
   - **Single threshold parameter**: `IMPACT_DEPTH_THR_M = 0.2` controls all three simultaneously: (1) which `PopAffected_{N}mm` column is used for the numerator, (2) which `evt2_fit_depth_{N}mm.json` is loaded, (3) the JRC flood depth used for the population denominator. All three must match so severity ratios stay in [0, 1]. Default 0.2m = humanitarian standard for meaningful flood damage.
   - **NB04 v0.5+ wide-format**: impacts_by_admin parquets have `PopAffected_{N}mm` columns (not long-format with `depth_thr_m`). `col_depth` detection is optional — if absent, depth filter is skipped and `col_aff = depth_thr_to_col(IMPACT_DEPTH_THR_M)` is used directly.
   - **EVT2 fit loading**: Cell 5 tries `evt2_fit_depth_{N}mm.json` first (NB04 v0.5+), falls back to `evt2_fit_popaffected_op.json` with a warning.
   - **Per-event RP**: Cell 6 now always recomputes `rp_evt` using `compute_rp_from_evt2_spliced(watershed_evt, evt2)` — uses the loaded EVT2 fit (matching `IMPACT_DEPTH_THR_M`), replaces hardcoded `RP_impact_op_full` from registry.
   - **Multi-threshold OEP comparison** (implemented, fully dynamic): when `MULTI_THR_ENABLED=True`, each threshold uses its own EVT2 fit, own impact column, and own per-event RP via `compute_rp_from_evt2_spliced`. Plots overlay chart, exports `Riskprofiles/watershed_oep_multithr.json`. The only shared input across thresholds is the event set (discharge-detected).
   - **Helpers in Cell 3**: `depth_thr_to_col()`, `depth_thr_to_file_tag()`, `build_elt_for_threshold()`, `compute_rp_from_evt2_spliced()`.
   - Outputs: stakeholder Excel workbook with 5×5 portfolio risk matrix + EP curves per municipality/province/watershed.
   - **Required export for NB06**: `data/processed/Riskprofiles/watershed_oep_curve.json` — array of `{return_period, pop_affected}`. Hard dependency. Unchanged.
7. **NB06** (`06_flood_event_viewer (1).ipynb`) — Interactive HTML dashboard for non-technical stakeholders showing named historical flood events.
   - **Reads from NB04**: `evt2/evt2_fit_popaffected_op.json` (metadata only) + `event_registry_hist.parquet`.
   - **Requires NB05** to have run first — hard-fails without `watershed_oep_curve.json`.
   - Classifies event severity using NB05 watershed OEP curve (log-RP interpolation), not the raw EVT2 formula.
   - Flood depth colormap: YlOrRd (yellow→orange→red) for visibility on light OSM basemap.
   - Optional: exports `events_for_risk_matrix.json` → NB05 can re-use to overlay named-event markers on the EP chart (re-run NB05 Cell 16 only after NB06).
8. **NB07** (`07_Trigger_Validation_Reforecast.ipynb`) — Evaluates trigger performance against reforecast ensemble.
   - **Reads from NB01**: `evt_pot_calibration.parquet` with same column rename as NB04 (`virtual_gauge_id→cell_id`, `threshold_m3s→u`, `lambda_events_per_year→lam`, `gpd_xi→xi`, `gpd_sigma→sigma`).
   - **Reads from NB05**: `watershed_oep_curve.json` for impact-space severity thresholds (RP2/5/10 in people affected).
   - Detection thresholds: `T0_YEARS=2.0` (discharge RP), `A_MIN_KM2=100.0` (spatial extent), `DEPTH_THRESHOLD_M=0.02`.
   - **Pending**: Cell 3 copies NB04 helper functions verbatim with old names — must sync after NB04 v0.4.0 rename (see Pending Work below).

**Execution order**: NB05 → NB06 required. NB06 → NB05 optional (named-event markers on EP chart).

`run_config.json` generated by NB01 is auto-detected by NB02–NB06 as the linking artifact.

### Logging

Use `get_logger` from `philflood.ops.logging_config`:
```python
from philflood.ops.logging_config import get_logger
logger = get_logger(__name__)
```
Supports JSON structured logging for production and human-readable console output for development.

## Key Design Decisions

- **CRS**: All spatial data assumes EPSG:4326 throughout the package.
- **Memory**: Large GloFAS datasets (47 years global) must use the streaming adapter (`glofas_grib_v4_optimized`), not the standard one.
- **pyextremes compatibility**: `calibration/evt_pot.py` wraps pyextremes with version-shimming helpers (`_build_eva`, `_get_pot_extremes`) because the API changed between versions.
- **CLIMADA dependency**: CLIMADA and climada-petals are core dependencies for hazard/impact modeling, but full integration is still in progress (v1.0 target).

## Pending Work

### NB05 — Multi-Threshold Risk Profiles (Completed)

Multi-threshold OEP comparison is now implemented. The new cell (after Cell 11 — AEP/OEP Curves) loops over all OK thresholds in `evt2_fit_manifest.json`, builds an ELT per threshold, runs YLT simulation, computes watershed OEP, and exports `watershed_oep_multithr.json`.

**Possible future extension**: Per-ADM3/ADM2 multi-threshold OEP curves (currently only watershed level is compared). The primary path (single threshold, all admin units) is unchanged and still drives the Excel workbook and `watershed_oep_curve.json` for NB06.

### NB07 — Function Rename Sync (Required)

`calibration/notebooks/07_Trigger_Validation_Reforecast.ipynb` Cell 3 copies NB04 helper functions verbatim. After the NB04 v0.4.0 rename, NB07 must be updated:
- `w_to_rp_spliced` → `impact_to_rp_spliced`
- `fit_evt2_spliced_wpeak` → `fit_evt2_spliced_impact` (if copied)
- Remove any copies of deleted functions (`sample_w_from_evt2`, `compute_w_series_from_discharge`)
- Update any `w_peak_series` / `RP_W_peak` variable names to match NB04
- Add `depth_thr_to_col()` and `depth_thr_to_file_tag()` helpers if NB07 needs multi-threshold support

### Physical Plausibility Check

After NB04 EVT2 fitting, verify that high-RP impact estimates (e.g., RP500 ~300k people affected) are plausible against total exposed population in the AOI. This is a manual sanity check, not automated. Now available per depth threshold — compare across thresholds for consistency.

### NB04 EVT2 Threshold Selection — MRL + GoF Not Yet Applied

NB04's `select_evt2_threshold()` uses only parameter stability (3-tier). It does not yet include:
- MRL linearity check (now in `compute_mrl()`)
- KS GoF test on PIT (now in `gpd_gof_test()`)

These were added to EVT1 (NB01) as part of the robustness improvements. Consider applying the same pattern to EVT2, keeping in mind that impact data is noisier and sample sizes are smaller (GoF tests have lower power; be cautious about hard-gating).

### Cell 28 — Further Performance Optimizations (Deferred)

The reforecast loop has additional optimization potential beyond what was implemented:
- Vectorize `iterrows()` loop in impact computation (est. 2-5x)
- GRIB subset reading via eccodes/cfgrib (est. 5-20x, high difficulty)
- Month-level parallelism with multiprocessing (est. Nx, moderate difficulty)
