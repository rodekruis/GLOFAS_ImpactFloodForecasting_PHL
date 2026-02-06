# Changelog

All notable changes to the PhilFlood project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

---

## [0.3.1] - February 6, 2026 (In Progress)

### Critical Bug Fix: Discharge-to-Return-Period Function Consolidation

**Issue Identified & Fixed:** Two different implementations of `discharge_to_return_period()` existed in the codebase with a critical mathematical discrepancy in the exponential case (|ξ| < 1e-6), causing a **63.2% error** in return period calculations.

**Root Cause:**
- **Notebook function** (`01_evt_pot_calibration_workflow.ipynb`, Section 13.5): Incorrectly implemented exponential case as `T = σ / (λ * (q - u))` (wrong)
- **Module function** (`src/philflood/calibration/evt_pot.py`): Correctly implemented as `T = (1/λ) * exp[(q-u)/σ]` (correct per EVT theory)

**Error Magnitude (Example):**
- Input: u=100 m³/s, σ=50 m³/s, λ=2 events/year, q=150 m³/s
- Notebook result: 0.5 years (WRONG)
- Correct result: 1.359 years (63.2% error)

**Solution Implemented:**
1. **Removed** the buggy local function from notebook 01, Section 13.5
2. **Added import** statement: `from philflood.calibration.evt_pot import discharge_to_return_period_pot`
3. **Updated** all call sites to use `discharge_to_return_period_pot()` instead of local `discharge_to_return_period()`
4. **Verified** that Notebook 02 does not use these functions directly (no changes needed there)

**Files Modified:**
- `calibration/notebooks/01_evt_pot_calibration_workflow.ipynb` (Section 13.5: replaced function definition with import + updated function call)
- `calibration/notebooks/02_HazardOnly_Workflow_v2.ipynb` (Section 8: fixed index vs. label selection ambiguity)

**Additional Fix: Index vs. Label Selection in Visualizations**

**Issue:** Section 8 visualizations used positional index selection (`.isel(event=idx)`) instead of label-based selection (`.sel(event=rp)`), creating fragility when return period order changes.

**Impact:** If `rps_display = [10, 20, 50, 100, 200, 500]` doesn't match the actual data order `[10, 20, 50, 75, 100, 200, 500]`, visualizations would show wrong return periods (e.g., idx=3 would select RP=75 instead of RP=100).

**Solution:** Replaced all 4 vulnerable `.isel(event=event_idx)` calls in Section 8 (8.3, 8.5, 8.6, 8.7) with `.sel(event=rp)` for robust label-based selection.

**Benefits:**
- ✅ Explicit: Code references `RP=100` directly, not "position 3"
- ✅ Robust: Works even if return period order changes
- ✅ Fail-safe: Clear warnings if RP doesn't exist
- ✅ Maintainable: Adding/removing RPs doesn't break visualizations

**Theory Verification:**
- Confirmed correct formula per Peaks-Over-Threshold (POT) / Extreme Value Theory (EVT) literature (Coles 2001, Pickands 1975, WMO 2016)
- Both exponential (ξ → 0) and GPD cases (ξ ≠ 0) validated against theoretical formulas
- Test suite `tests/test_pot_climada_integration.py` already validates `discharge_to_return_period_pot()` with 11 test cases ✓

**Impact on Results:**
- Return period grid calculations now use mathematically correct formula
- Flood depth interpolation in Notebook 02 will reflect corrected return periods
- Estimated impact: **Up to 63% adjustment in return period values** for cells with small ξ (exponential-like tails)

**Verification Checklist:**
- ✅ Function comparison documented and analyzed
- ✅ Bug quantified with test case (63.2% error)
- ✅ Correct function identified from EVT theory
- ✅ Codebase audited for usage patterns
- ✅ Consolidation implemented (single source of truth)
- ✅ Existing test suite covers correct function

---

## [0.3.0] - February 2, 2026

### CLIMADA Integration Phase - Formula-Based POT Implementation

**Issue Fixed:** Notebook 02 discarded 7 of 8 return periods (87.5% data loss)

**Solution:** 
- Section 5: Stack all return periods into event dimension before regrid/flood_depth
- Section 6: Extract per-event depths and create 8 unique hazard events
- Section 13: Generate CF-1.8 NetCDF with proper 3D structure + stakeholder visualizations

**Files Modified:**

**Testing:** See [VERIFICATION_CHECKLIST_v0.3.0.md](docs/archive/VERIFICATION_CHECKLIST_v0.3.0.md)

**Impact:**
- ✅ 0% data loss (previously 87.5%)
- ✅ 8 unique flood depths (previously 8 duplicates)
- ✅ 5-10x faster return level calculation (formula-based)
- ✅ All 8 return periods processed through CLIMADA-Petals
- ✅ 38% reduction in documentation files (removed redundant files)

---

## [0.2.0] - January 28-29, 2026

### Streaming Extraction and Memory Optimization

#### Added - Streaming GRIB Extraction

- **`src/philflood/adapters/glofas_grib_streaming.py`**
  - Streaming-based extraction of single-year GRIB data to temporary parquet outputs
  - Memory-efficient merging of yearly data into long historical time series
  - Orchestrated processing with checkpoint/resume to recover from interruptions
  - Reduces peak memory usage from 1.8 GB to ~31 MB (94% reduction)
  - Enables processing of full 47-year historical dataset (1979-2025) without crashes

#### Added - Memory Optimization Infrastructure

- **`src/philflood/utils/memory_utils.py`**
  - Utilities for real-time RAM tracking, warnings, and graceful shutdown under pressure
  - Helpers for clipping GRIB grids to relevant geographic areas (up to ~70% size reduction)
  - Support for streaming parquet writes without full in-memory concatenation

- **`src/philflood/adapters/glofas_grib_v4_optimized.py`**
  - Drop-in replacement for `load_or_build_gauge_timeseries()`
  - Automatic geographic chunking + gauge batching
  - Integrated memory monitoring with configurable thresholds
  - Backward compatible with existing notebooks

#### Fixed - NetCDF Return Period Dimension

- **`src/philflood/adapters/glofas_grib_v4.py`**: `write_return_period_netcdf()`
  - Root cause: Return period was stored as scalar attribute instead of dimension
  - Solution: Restructured to create 2D array (gauge × return_period) indexed by both coordinates
  - Impact: NetCDF now properly supports discharge variation across 9 return periods
  - File locking: Added explicit `.close()` in try/except blocks to prevent handle leaks
  - Backward compatible: Falls back gracefully when return-level parquet files unavailable

#### Enhanced - Data Loss Logging

- Loud console warnings (⚠️) when invalid dates detected in GRIB files
- Per-gauge extraction statistics: `records_processed`, `records_dropped`, `reason`
- Final accounting: Total records written vs. dropped across all years

#### Changed - Environment and Dependencies

- **`environment.yml`**: Updated to include all critical packages
  - `cfgrib 0.9.15.1`: GRIB file decoding (was missing, caused crashes)
  - `pyextremes 2.4.0`: EVT/POT calibration library
  - `psutil 7.0.0`: Memory monitoring
- **`requirements.txt`**: Added missing EVT dependencies
- **Python version**: Verified compatibility with Python 3.11

#### Performance Improvements

| Metric | Before | After | Reduction |
|---|---|---|---|
| Peak Memory (47 years) | 1.8 GB | 31 MB | 94% ↓ |
| Memory at Year 30 | 850 MB | 26 MB | 97% ↓ |

---

## [0.1.0] - December 29, 2025

### Initial Release: Operational Infrastructure

#### Added - Operational Infrastructure

##### Package & Installation
- Proper Python package setup with pip installability
- Requirements files for base, development, and operations

##### Command-Line Interface
- **src/philflood/cli.py**: User-friendly CLI with main commands:
  - `philflood monitor`: Run trigger monitoring
  - `philflood validate`: Validate basin configurations
  - `philflood calibrate`: Run EVT calibration diagnostics
- JSON and CSV output formats
- Batch processing of multiple basins

##### Configuration Validation
- **src/philflood/ops/validation.py**: Pre-deployment configuration validation
  - Checks required fields and data paths
  - Validates EVT parameters are physically reasonable
  - Detects placeholder values

##### Testing & Documentation
- **tests/test_smoke.py**: Installation verification
- **docs/quickstart.md**: 15-minute setup guide
- **docs/deployment.md**: Production deployment guide

---

## Version Roadmap

- **0.x series** (Current): CLIMADA integration development phase
- **1.x series** (Future): Production deployment and operationalization
- **2.x series** (Future): Full system integration with automated triggers

---

## Future Roadmap

### Version 1.0.0 (Target: Q2 2026)
**Production-Ready Release**
- Complete operational monitoring with automated triggers
- Full CLIMADA integration for impact-based forecasting
- Multi-country support
- Full test coverage (>80%)
- Production deployment examples
- Performance benchmarks

### Version 2.0.0 (Target: Q4 2026)
**Full System Integration**
- CLIMADA-petals integration for population exposure modeling
- Impact-based forecasting with automatic early action triggers
- Real-time forecast ingestion from GloFAS API
- Web dashboard for monitoring and visualization
- REST API for external integration
- Historical performance tracking and evaluation

---

For detailed technical documentation, see the `docs/` directory.
