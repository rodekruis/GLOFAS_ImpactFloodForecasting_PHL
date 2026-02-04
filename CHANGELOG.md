# Changelog

All notable changes to the PhilFlood project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

---

## [0.3.0] - February 2, 2026

### CLIMADA Integration Phase - Formula-Based POT Implementation

**Issue Fixed:** Notebook 02 discarded 7 of 8 return periods (87.5% data loss)

**Solution:** 
- Section 5: Stack all return periods into event dimension before regrid/flood_depth
- Section 6: Extract per-event depths and create 8 unique hazard events
- Section 13: Generate CF-1.8 NetCDF with proper 3D structure + stakeholder visualizations

**Files Modified:**
- `calibration/notebooks/02_HazardOnly_Workflow_v2.ipynb` (Sections 5, 6, 13)
- `calibration/notebooks/01_evt_pot_calibration_workflow.ipynb` (Section 11C: formula-based bootstrap)

**Testing:** See [VERIFICATION_CHECKLIST_v0.3.0.md](VERIFICATION_CHECKLIST_v0.3.0.md)

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
