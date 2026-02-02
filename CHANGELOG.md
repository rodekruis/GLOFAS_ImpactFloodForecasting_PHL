# Changelog

All notable changes to the PhilFlood project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

---

## [0.3.0] - February 2, 2026

### CLIMADA Integration Phase - Formula-Based POT Implementation

#### Replaced - Synthetic Event Catalog with Direct Formula Approach

- **Archived Section 12** from calibration notebook
  - Reason: Synthetic events were intermediate step, now bypassed
  - New approach: Direct formula-based return level calculation in Section 11C
  - Migration: Formula uses POT/GPD parameters directly: `Q(T) = u + (σ/ξ) * ((T*λ)^ξ - 1)`
  - Performance: 5-10x faster, no large intermediate datasets needed

#### Added - Section 11C: Bootstrap Return Levels (Formula-Based)

- **calibration/notebooks/01_evt_pot_calibration_workflow.ipynb**
  - Bootstrap uncertainty quantification (N=20 samples by default)
  - Generates return levels for 9 return periods (1-500 years)
  - Outputs: `return_levels_bootstrap.parquet` with mean, std, q05, q95
  - Runtime: <2 seconds per gauge (typically <1s)
  - QA metrics: Monotonicity check, CV statistics, fallback detection

#### Enhanced - Section 13: CLIMADA-Compatible NetCDF Generation

- **Replaced** raster-based approach with event-based structure
  - Event format: Each return period = one event (not a dimension)
  - Required variables: `intensity`, `frequency`, `intensity_std`, `event_id`, `event_name`
  - Frequency calculation: `np.diff(1/return_periods, prepend=0)`
  - CF-1.8 compliant with proper coordinate systems
  - File size: Typically <1 MB for regional basins

#### Added - Section 13B: NetCDF Verification & QA Maps

- **Visualization**: 4-panel verification map
  - Key return periods (1yr, 10yr, 100yr, 500yr)
  - Spatial patterns validation
  - Uncertainty (CV) assessment
- **Quality checks**: Monotonicity, NaN detection, frequency structure

#### Added - Section 13C: Stakeholder Spatial Maps

- **Publication-ready visualizations**:
  - Multi-panel return period intensity maps
  - Coefficient of variation (uncertainty) spatial map
  - Colorblind-friendly palettes (Viridis, RdYlBu_r)
  - 300 DPI PNG outputs for reports/papers

#### Fixed - Documentation Redundancy

- **Removed** redundant documentation files:
  - Superseded files merged into comprehensive docs/quickstart.md
  - Outdated implementation tracking files archived
  - Result: 38% reduction in documentation files, eliminated ~60% of redundant content

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
