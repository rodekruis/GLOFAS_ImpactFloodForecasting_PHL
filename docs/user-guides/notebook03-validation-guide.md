# Notebook 3: Validation & Impact Assessment Guide

Guide to validating flood calibration results using Notebook 3 (`calibration/notebooks/03_validation_notebook_FINAL.ipynb`).

## Overview

Notebook 3 compares your **modeled flood extent** (from Notebooks 1 & 2) against **observed flood extent** from GloFAS Flood Maps (GFM). Produces quantitative validation metrics, population exposure estimates, and an interactive HTML dashboard for stakeholder review.

**Duration**: ~30-60 minutes per flood episode  
**Prerequisites**: Notebooks 1 & 2 complete + GFM observed extent data  
**Output**: CSV validation metrics, affected population tables, interactive Leaflet dashboard

**Typical Users**: Data scientists (validation), Operations teams (pre-deployment QA), Stakeholders (interactive dashboard)

---

## Quick Start (5 min)

```python
# Auto-detect from Notebook 1 (recommended)
AUTO_DETECT = True
basin_id_input = None
run_tag_input = None

# Configure GFM directory (where observed extent files are stored)
GFM_VALIDATION_ROOT = Path("data/raw/glofas/GFM")  # Adjust path as needed

# Run all cells
# Notebook will auto-load calibration, detect AOI, validate against observations
```

---

## Key Sections

### Setup & Imports (Sections 1-2)
- **Section 1**: Title and overview
- **Section 2**: Import all dependencies (rasterio, geopandas, xarray, CLIMADA-Petals, pandas)

**Important**: Requires `CLIMADA-Petals` library (same as Notebook 2). If not installed, Section 3 will report error.

### Pre-Flight Checks (Section 3)
Validates environment before processing:

**Checks performed**:
- ✅ All required Python packages installed (numpy, pandas, geopandas, rasterio, xarray, CLIMADA-Petals)
- ✅ Data files exist: HYBAS HydroBASINS, ADM3 municipality boundaries, WorldPop, GFM validation directory
- ✅ Output directory is writable
- ✅ CLIMADA-Petals version compatible

**Action**: If any check fails, notebook stops with clear error message. Fix issue before proceeding.

### Calibration Auto-Detection (Section 4)
Automatically finds and loads your Notebook 1 calibration:

**Steps**:
1. Searches `data/processed/calibration/evt_pot/` for latest run
2. Loads `run_config.json` (basin ID, selection mode, municipality list)
3. Loads calibrated EVT parameters (parquet file)
4. Detects: **Basin mode** or **Municipality mode**?

**Output**: Confirms basin/municipalities selected, paths configured

### AOI Boundary Construction (Section 5)
Builds the Area of Interest (AOI) boundary:

**Basin Mode**:
- Uses HydroBASINS L7 boundary
- Intersects with GFM data bounds
- Single basin extent

**Municipality Mode**:
- Merges all ADM3 polygons for selected municipalities
- Union of all selected Admin3 boundaries
- Multiple AOI possible

**Validation**: Prints number of polygons, total area
**Careful**: If AOI too small, may miss relevant gauges. Check output!

### GFM Observed Extent Processing (Section 6)
Processes GloFAS Flood Maps (observed extent) into usable format:

**Steps**:
1. **Date parsing**: Reads GFM filenames, extracts dates
   - Accepts multiple formats: YYYYMMDD, YYYY-MM-DD, etc.
   
2. **Declustering**: Groups dates into flood episodes
   - 5-day gap rule: dates within 5 days = same episode
   - Example: Days 1, 2, 5, 10 → Episodes [1-5], [10]
   
3. **Mosaicking**: Merges daily GFM tiles by date
   - Each day has multiple GeoTIFFs
   - Combines into single daily extent raster
   
4. **Episode maximum**: Computes per-episode maximum
   - Stacks all days in episode
   - Takes pixel-wise maximum extent
   - "Where did water reach at ANY point in episode?"

**Output**: `obs_extent__EPXX_*.tif` files (one per episode)

**Check**: Verify episode groupings are realistic (avoid 5-day rule splitting long events)

### Discharge to Return Period (Section 7)
Converts calibrated discharge → return period maps:

**Steps**:
1. **Gauge filtering**: Selects gauges within AOI
   - Reads EVT parameters from Notebook 1
   - Keeps only CELL__* gauges (cell-level discharge)
   - Removes VG__* gauges (virtual pour points)
   
2. **Timeseries loading**: Loads discharge for each episode date range
   - Queries GloFAS historical discharge
   - Handles missing files gracefully
   
3. **Return period computation**: Applies EVT/POT formula per gauge per day
   - Formula: T = (1/λ) × exp[(q-u)/σ]  (for exponential case)
   - Discards RP < 1.0 (invalid exponentials)
   
4. **Spatial maps**: Creates two RP maps per episode:
   - **Envelope**: Maximum RP over entire episode (max over all days)
   - **Peakday**: RP on day with maximum median discharge
   - Both used for validation comparison

**Diagnostic**: Prints % of gauges with available data. >70% good, <50% risky.

### Diagnostics (Sections 8-9)
Quality checks on coordinate systems and gauge locations:

**Checked**:
- Gauge ID parsing (extract lat/lon from virtual_gauge_id strings)
- Philippines geographic bounds (all gauges within 4°N-21.5°N, 116°E-127°E)
- CRS validation (all data in EPSG:4326 / WGS84)
- Spatial filter accuracy (gauges intersecting AOI)
- Filename consistency (timeseries files match gauge IDs)

**Output**: 
- Map 1: Philippines context with all gauges
- Map 2: AOI detail with filtered gauges
- Summary statistics

**Action**: If warnings appear, check gauge coordinates and AOI definition.

### JRC Flood Maps Download (Section 10)
Downloads and processes JRC global flood depth maps:

**Steps**:
1. **Tile selection**: Downloads JRC tile index GeoJSON
   - Identifies tiles covering your AOI
   
2. **Tile download**: Downloads flood depth maps for all RP
   - 8 return periods × N tiles = large volume (30-60+ min)
   - Cached: if tiles exist, skips download
   
3. **Mosaicking**: Merges tiles into single grid
   - All 8 RPs stacked in single NetCDF
   
4. **Interpolation**: Regrid to regular lat/lon grid
   - Uses CLIMADA-Petals `petals_regrid()`
   - Output: flood_depth for each RP at each grid point

**Output**: Intermediate file `flood-maps_intermediate.nc` (depth ≥ 0.05 m)

**Memory note**: Large rasters. If memory errors, try LOW_RAM_MODE toggle.

### Hazard Extent Validation (Section 11)
**Core validation step**: Compares modeled vs. observed flood extent quantitatively.

**Steps**:
1. **Reprojection**: Transforms observed GFM extent to model grid
   - Bilinear interpolation
   - Ensures same grid for pixel-by-pixel comparison
   
2. **Confusion matrix** at 5 depth thresholds:
   - 0.05 m (minimal flooding)
   - 0.10 m (threshold water)
   - 0.20 m (problematic flooding)
   - 0.50 m (significant flooding)
   - 1.00 m (major flooding)

**For each threshold**, computes:
- **TP (True Positive)**: Model predicted flood, GFM observed flood → **Correct prediction**
- **FP (False Positive)**: Model predicted flood, GFM did NOT observe → **Over-prediction** (false alarm)
- **FN (False Negative)**: Model did NOT predict flood, GFM observed → **Miss** (under-prediction)
- **TN (True Negative)**: Model did NOT predict, GFM did NOT observe → **Correct non-prediction**

**Derived metrics** (explained below):
- **Precision**: TP/(TP+FP) — Of predicted floods, what fraction correct?
- **Recall**: TP/(TP+FN) — Of actual floods, what fraction did model catch?
- **F1 Score**: Harmonic mean of precision & recall (single performance number)
- **IoU** (Intersection over Union): TP/(TP+FP+FN) — Spatial overlap of extent
- **Bias**: (TP+FP)/(TP+FN) — Over (+) or under (-) prediction?

**Output**: `hazard_extent_metrics.csv` (one row per episode/scenario/threshold combination)

**Interpretation guide**:
- **F1 > 0.7**: Excellent match
- **F1 0.5-0.7**: Good match, some discrepancies
- **F1 < 0.5**: Poor match, needs investigation
- **Bias > 1.0**: Overpredicting (more area than observed)
- **Bias < 1.0**: Underpredicting (less area than observed)

### Population Exposure (Section 12)
Estimates affected population as impact proxy:

**Steps**:
1. **Reprojection**: Regrid WorldPop to model grid
   - Bilinear interpolation
   - Preserves total population (mass balance check)
   
2. **Exposure calculation**: For each depth threshold:
   - Identify flooded areas (depth ≥ threshold)
   - Sum WorldPop within flood extent
   - Mask to AOI municipalities (ADM3)
   
3. **GFM comparison**: Same calculation for observed extent
   - Modeled population vs. Observed population
   - Identifies over/under-prediction of exposure

**Output**: `affected_population_by_adm3.csv`
- Columns: episode_id, scenario, depth_threshold, adm3_name, affected_pop, observed_pop
- Grouped by municipality for easy stakeholder consumption

**Note**: Population is a **proxy for impact**, not true impact modeling. Use to identify areas of concern, not absolute damage estimates.

### Interactive HTML Dashboard (Section 13)
Generates standalone HTML file for non-technical stakeholders:

**Features**:
- **Map**: Leaflet map with observed (blue) vs. modeled (red) flood extent
- **Event selector**: Dropdown to choose flood episode
- **Scenario toggle**: Compare FLOPROS on/off (flood protection scenario)
- **Municipality selector**: Filter to specific ADM3 boundary
- **Depth threshold slider**: 0.0-3.0 m range, 0.1 m increments
- **Base map options**: OpenStreetMap, topographic, satellite imagery
- **Bar charts**: Modeled vs. observed population by municipality
- **Choropleth**: Affected population intensity by municipality
- **KPI indicators**: Total AOI population, selected municipality metrics
- **Metrics display**: Current F1, IoU, Precision, Recall values

**Usage**: Open `validation_dashboard.html` in any web browser. Fully self-contained, no server needed.

**Sharing**: Email HTML file to stakeholders. Works offline.

---

## Typical Workflow

### 1. Calibration Complete (From Notebooks 1 & 2)
- EVT parameters fitted (Notebook 1)
- Hazard HDF5 created (Notebook 2)
- Files available in `data/processed/calibration/evt_pot/{BASIN_ID}/`

### 2. Prepare GFM Data
- Download or provide observed flood extent GeoTIFFs
- Place in directory specified by `GFM_VALIDATION_ROOT`
- Name with dates: `extent__YYYYMMDD.tif` or similar

### 3. Run Notebook 3
```python
AUTO_DETECT = True  # Load Notebook 1 output automatically
GFM_VALIDATION_ROOT = Path("data/raw/glofas/GFM")

# Run all cells
# Time: 30-60 minutes (mostly JRC download + raster operations)
```

### 4. Review CSV Outputs
- Open `hazard_extent_metrics.csv` in Excel or pandas
- Check F1, IoU, Bias for each episode and depth threshold
- Look for patterns: which thresholds match best?

### 5. Share Dashboard
- Upload `validation_dashboard.html` to stakeholders
- Or email directly (fully self-contained file)
- Non-technical users can interact without assistance

### 6. Post-Validation Decisions
- **F1 > 0.7 for key thresholds**: Proceed with operational deployment
- **F1 0.5-0.7**: Acceptable, but document limitations
- **F1 < 0.5**: Investigate: is calibration accurate? GFM data quality? AOI definition?

---

## Metrics Explained

### Confusion Matrix Components

| Condition | Flooded (Model) | Not Flooded (Model) |
|-----------|-----------------|-------------------|
| **Flooded (Observed)** | TP ✓ | FN ✗ (missed) |
| **Not Flooded (Observed)** | FP ✗ (false alarm) | TN ✓ |

### Key Metrics

**Precision** = TP / (TP + FP)
- "Of all areas model predicted as flooded, what fraction actually flooded?"
- Range: 0-1 (1 = no false alarms)
- Use: To evaluate false positives (nuisance alerts)

**Recall** (Sensitivity) = TP / (TP + FN)
- "Of all actually flooded areas, what fraction did model catch?"
- Range: 0-1 (1 = no misses)
- Use: To evaluate missed floods (dangerous under-prediction)

**F1 Score** = 2 × (Precision × Recall) / (Precision + Recall)
- Harmonic mean balancing precision & recall
- Range: 0-1 (1 = perfect)
- **Single metric for overall performance**
- Interpretation:
  - **0.8-1.0**: Excellent
  - **0.6-0.8**: Good
  - **0.4-0.6**: Fair
  - **< 0.4**: Poor

**IoU** (Intersection over Union) = TP / (TP + FP + FN)
- "What fraction of the union of predicted & actual extent is correct?"
- Range: 0-1 (1 = perfect spatial match)
- Stricter than F1 (penalizes both types of error equally)

**Bias** = (TP + FP) / (TP + FN)
- Ratio of predicted flooded area to observed flooded area
- **> 1.0**: Model overpredicts (thinks more area flooded than observed)
- **< 1.0**: Model underpredicts (thinks less area flooded than observed)
- **= 1.0**: Perfect area match
- Use: To diagnose systematic over/under-estimation

---

## Understanding Output Files

### Directory Structure
```
data/processed/validation/
├── {BASIN_ID}/
│   └── {RUN_TAG}/
│       ├── observed/
│       │   ├── daily/          (daily GFM extents)
│       │   └── episodes/       (episode maxima)
│       ├── model/
│       │   ├── return_period/  (RP maps)
│       │   └── depth/          (modeled flood depths)
│       ├── jrc/                (downloaded JRC tiles)
│       ├── metrics/
│       │   └── hazard_extent_metrics.csv
│       ├── maps_for_dashboard/ (difference maps)
│       ├── population/
│       │   └── affected_population_by_adm3.csv
│       └── validation_dashboard.html
```

### hazard_extent_metrics.csv Schema

| Field | Type | Description |
|-------|------|-------------|
| episode_id | str | E.g., "EP01" |
| rp_label | str | E.g., "envelope" or "peakday" |
| scenario | str | "NoProt" or "FLOPROS" (if run both) |
| depth_threshold_m | float | 0.05, 0.10, 0.20, 0.50, 1.00 |
| tp | int | True positives (pixels) |
| fp | int | False positives |
| fn | int | False negatives |
| tn | int | True negatives |
| precision | float | TP/(TP+FP) |
| recall | float | TP/(TP+FN) |
| f1 | float | Harmonic mean |
| iou | float | TP/(TP+FP+FN) |
| bias | float | (TP+FP)/(TP+FN) |

### affected_population_by_adm3.csv Schema

| Field | Type | Description |
|-------|------|-------------|
| episode_id | str | E.g., "EP01" |
| rp_label | str | "envelope" or "peakday" |
| scenario | str | "NoProt" or "FLOPROS" |
| depth_threshold_m | float | Threshold for flood definition |
| adm3_id | int | Municipality ID |
| adm3_name | str | Municipality name |
| affected_pop | float | Population in model flood extent |
| observed_pop | float | Population in observed flood extent |

**Use**: Compare affected_pop vs. observed_pop to identify over/under-prediction by municipality.

---

## Troubleshooting

### Pre-Flight Check Failures

**Error: "CLIMADA-Petals not found"**
- Solution: Install with `pip install climada[petals]`

**Error: "GFM validation directory not found"**
- Solution: Check `GFM_VALIDATION_ROOT` path exists and contains GFM files
- Format: `extent__YYYYMMDD.tif` or similar naming

**Error: "Output directory not writable"**
- Solution: Check write permissions on `data/processed/validation/`

### Calibration Auto-Detection Failures

**Error: "No recent calibration found"**
- Solution: Run Notebook 1 first, check output in `data/processed/calibration/evt_pot/{BASIN_ID}/`

**Error: "Selection mode mismatch"**
- Solution: Ensure Notebook 1 `run_config.json` has valid `selection_mode` field

### Discharge & RP Computation

**Error: "Gauge timeseries files not found"**
- Solution: Check GloFAS discharge files in `data/interim/glofas/timeseries/` or `data/processed/glofas/`
- Notebook 1 should have generated these

**Warning: "Only X% of gauges have timeseries data"**
- If > 50%: Proceed, but results may be sparse
- If < 30%: Investigate data availability, may have wrong basin

### Dimension Mismatches

**Error: "Shapes don't match during reprojection"**
- Cause: CRS mismatch (check all data in EPSG:4326)
- Solution: Run diagnostics cells (Sections 8-9) to identify CRS issues

**Error: "Return period map has NaN values"**
- Cause: Gauge outside AOI or missing discharge data
- Solution: Check Section 5 AOI extent, verify gauge coverage
- This is often expected (data gaps are normal)

### Memory & Performance Issues

**Error: "Memory exceeded during raster operation"**
- Solution 1: Enable LOW_RAM_MODE (lower chunk sizes)
- Solution 2: Reduce AOI size (fewer municipalities selected)
- Solution 3: Run on machine with more RAM (this is raster-heavy)

**Issue: Section 10 (JRC download) taking > 2 hours**
- Check internet speed and JRC server load
- Cached tiles are reused (first time slow, repeat runs fast)
- Can manually interrupt and resume (tiles partially downloaded are valid)

### Dashboard HTML Issues

**Issue: "Dashboard file not opening in browser"**
- Solution: Ensure file path has no spaces (or use quotes in browser Open dialog)
- Try different browser (Chrome, Firefox, Edge)

**Issue: "Map not loading, showing only background"**
- Cause: Possible issue with Leaflet basemap tiles
- Solution: Try different base map option in dropdown

---

## Key Assumptions & Limitations

| Aspect | Assumption | Impact |
|--------|-----------|--------|
| **Extent validation only** | Validates binary flood/no-flood, NOT depth accuracy | Cannot assess if model depth over/under-estimated |
| **Population proxy** | Affected population as "impact proxy," not true impact | Numbers are exposure estimates, not actual damage/mortality |
| **5-day declustering** | Hard gap rule for episode grouping | May split genuine multi-week events or join separate events |
| **Bilinear resampling** | All reprojections use bilinear interpolation | ±10% population mass balance drift acceptable |
| **GFM as ground truth** | Assumes GFM observations 100% accurate | GFM itself has uncertainty (sensor, processing) |
| **L12 gauge selection** | Assumes L12 cells used for gauge filtering are representative | May include gauges far from basin if L12 spans large area |
| **FLOPROS optional** | Flood protection scenario only applied if specified | "NoProt" scenario may overestimate exposure in protected areas |

---

## Workflow Integration

Notebook 3 fits into the complete calibration pipeline:

```
Notebook 1: EVT/POT Calibration
           ↓
        (EVT parameters, RP estimates)
           ↓
Notebook 2: CLIMADA Hazard Integration
           ↓
        (Flood depth maps, Hazard HDF5)
           ↓
Notebook 3: Validation & QA ← YOU ARE HERE
           ↓
        (Validation metrics, dashboard)
           ↓
DECISION: Deploy to ops or iterate calibration?
           ↓
Notebook 10: Synthetic Impacts (planned v1.0)
           ↓
        (Risk curves, trigger design)
```

**When to use Notebook 3**:
- ✅ **After Notebooks 1 & 2** complete
- ✅ **Before operational deployment** (QA gate)
- ✅ **After updating calibration** (if sensitive to changes)
- ❌ Not needed for operational monitoring runs (those use fixed parameters)

---

## Validation Success Criteria

**Recommended thresholds for deployment**:

| Metric | Threshold | Interpretation |
|--------|-----------|-----------------|
| **F1 @ 0.20 m** | > 0.65 | Acceptable extent match for moderate floods |
| **Bias @ 0.20 m** | 0.8 - 1.2 | Neither systematic over/under-prediction |
| **IoU @ 0.20 m** | > 0.50 | Good spatial overlap |
| **Population match** | ±20% of observed | Acceptable exposure estimates |

**Interpretation**:
- **All criteria met**: ✅ Validated, ready for deployment
- **2-3 criteria met**: ⚠️ Acceptable with documented limitations
- **< 2 criteria met**: ❌ Investigate calibration, data quality, or model assumptions

---

## Next Steps

1. **Review validation metrics** in CSV files
2. **Share dashboard** with stakeholders for feedback
3. **Document findings**: F1 scores, population estimates, known limitations
4. **Decision point**:
   - Deploy to operations (if F1 > 0.65)
   - Iterate calibration (if F1 < 0.5)
   - Document limitations (if 0.5 < F1 < 0.65)
5. **Archive outputs**: Save validation directory with run metadata for reference

---

## For More Information

- **Validation metrics theory**: See `docs/technical/GLOSSARY.md` (Confusion Matrix section)
- **GFM data requirements**: See `docs/getting-started/gfm-data-guide.md`
- **Notebook 1 (calibration)**: See `docs/user-guides/notebook01-calibration-guide.md`
- **Notebook 2 (hazard)**: See `docs/user-guides/notebook02-hazard-guide.md`
- **Troubleshooting**: See `docs/user-guides/troubleshooting.md` or Notebook cells for detailed error messages
