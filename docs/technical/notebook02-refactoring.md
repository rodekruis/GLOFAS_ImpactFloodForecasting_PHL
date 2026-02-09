# Notebook 2 (Hazard-Only Workflow) Refactoring Summary

## Overview
Notebook 2 (02_HazardOnly_Workflow_v2.ipynb) has been refactored to support **dual-mode operation**:
- **Basin mode**: Flood analysis for a single defined basin (e.g., "Cagayan_01")
- **Municipality mode**: Flood analysis for a user-selected cluster of municipalities

The notebook now automatically detects which mode was used in Notebook 1 and adapts all processing accordingly.

## Key Changes

### 1. Helper Functions (New Cell after Environment Setup)

Three new helper functions support mode detection and path flexibility:

#### `detect_calibration_mode(processed_root, basin_id=None, run_tag=None) → dict`
**Purpose**: Auto-detect which mode was used in Notebook 1

**Logic**:
- Checks for `MUNI_SELECTION` folder first (indicates municipality mode)
- If found, loads `selected_municipalities.geojson` and extracts municipality geometries
- Falls back to basin mode if `MUNI_SELECTION` doesn't exist
- If manual `basin_id` provided, uses that directly

**Returns**:
```python
{
    "mode": "basin" | "municipality",
    "basin_id": "<BASIN_ID>" | "MUNI_SELECTION",
    "muni_gdf": GeoDataFrame | None,
    "aoi_boundary": Shapely polygon | None,
    "run_tag": str
}
```

#### `get_flood_zone_boundary(processed_root, mode, basin_id, muni_gdf=None) → Polygon`
**Purpose**: Get the appropriate geographic boundary for flood analysis

**Basin mode**: 
- Loads boundary from basin YAML config (`ops/configs/basins/{basin_id}.yaml`)
- Extracts `aoi_bbox` coordinates
- Returns `box()` polygon

**Municipality mode**:
- Takes union of all selected municipality geometries
- Returns `muni_gdf.geometry.unary_union`
- (Optional: can use `.convex_hull` instead for simplified boundary)

#### `construct_hazard_paths(processed_root, mode, basin_id, run_tag) → dict`
**Purpose**: Create mode-aware output paths

**Returns**:
```python
{
    "hazard_output": Path,              # Main output directory
    "viz_output": Path,                 # Visualizations subdirectory
    "hazard_hdf5": Path,                # CLIMADA hazard HDF5 file
    "dashboard_path": Path,             # Dashboard HTML
    "jrc_cache": Path,                  # JRC tile cache directory
}
```

**Key feature**: All paths use the mode-aware folder naming:
- Basin mode: `climada_hazard/{BASIN_ID}/{RUN_TAG}/`
- Municipality mode: `climada_hazard/MUNI_SELECTION/{RUN_TAG}/`

---

### 2. Configuration Cell Refactoring (Cell 4)

**Before**: Hardcoded configuration
```python
BASIN_ID = "Cagayan_01"
RUN_TAG = "2026-01-19_calib-test"
CALIBRATION_OUTPUT = PROCESSED_ROOT / "calibration" / "evt_pot" / BASIN_ID / RUN_TAG
```

**After**: Mode-aware configuration with auto-detection
```python
# === Option A: AUTO-DETECT (Recommended)
AUTO_DETECT = True
basin_id_input = None      # None = auto-detect
run_tag_input = None       # None = auto-detect

# === Option B: MANUAL
# Uncomment below for specific run:
# AUTO_DETECT = False
# basin_id_input = "Cagayan_01"
# run_tag_input = "2026-01-19_calib-test"

# Call mode detection
mode_info = detect_calibration_mode(PROCESSED_ROOT, basin_id=basin_id_input, run_tag=run_tag_input)

# Extract results
mode = mode_info["mode"]                          # "basin" | "municipality"
BASIN_ID = mode_info["basin_id"]                 # Basin ID | "MUNI_SELECTION"
RUN_TAG = mode_info["run_tag"]                   # Auto-discovered run tag
MUNI_GDF = mode_info["muni_gdf"]                 # Municipality geometries (if mode="municipality")
AOI_BOUNDARY = mode_info["aoi_boundary"]         # Boundary geometry

# Construct paths using helper
output_paths = construct_hazard_paths(PROCESSED_ROOT, mode, BASIN_ID, RUN_TAG)
HAZARD_OUTPUT = output_paths["hazard_output"]
VIZ_OUTPUT = output_paths["viz_output"]

# Get flood zone boundary for JRC tile selection
flood_zone_boundary = get_flood_zone_boundary(PROCESSED_ROOT, mode, BASIN_ID, MUNI_GDF)
```

**Benefits**:
- No manual path updating required
- Automatically detects Notebook 1 output mode
- Supports both basin and municipality workflows
- Clear separation between auto and manual configuration

---

### 3. JRC Tile Selection Update (Cell 6)

**Before**: 
```python
# Hard-coded basin extent
basin_bbox = box(float(lons_all.min()), float(lats_all.min()),
                 float(lons_all.max()), float(lats_all.max()))
tiles_sel = tiles_gdf[tiles_gdf.intersects(basin_bbox)].copy()
```

**After**:
```python
# Mode-aware vs. mode-independent boundary
print(f"\n• Selecting tiles for {mode.upper()} mode:")
print(f"  Boundary type: {'Union of municipalities' if mode == 'municipality' else 'Basin extent'}")
tiles_sel = tiles_gdf[tiles_gdf.intersects(flood_zone_boundary)].copy()
```

**Impact**:
- Basin mode: Uses basin YAML boundary for tile selection
- Municipality mode: Uses union of municipality boundaries for tile selection
- Ensures correct JRC tiles downloaded for both workflows

---

### 4. Visualization Titles Update

**Section 8.1 - Return Period Map**:
```python
# Old
ax.set_title(f'Return Period Grid - {BASIN_ID}\nCalibrated from POT/GPD Analysis')

# New
area_name = BASIN_ID if mode == "basin" else "Municipality Selection"
ax.set_title(f'Return Period Grid - {area_name}\nCalibrated from POT/GPD Analysis')
```

**Section 6 - Summary Report**:
```python
# Old
print(f"📂 Basin: {BASIN_ID}")

# New
area_name = BASIN_ID if mode == "basin" else "Municipality Selection"
print(f"\n✓ OUTPUTS CREATED:\n")
print(f"  Mode: {mode.upper()}")
print(f"  Area: {area_name}")
```

**Impact**: Users see clear mode-aware labels in all outputs

---

### 5. CLIMADA Hazard Naming

**Section 6 - Hazard object creation**:
```python
# Now uses mode-aware BASIN_ID variable
hazard_hdf5 = HAZARD_OUTPUT / f"climada_hazard_{BASIN_ID}.hdf5"

# Output examples:
# Basin mode: climada_hazard_Cagayan_01.hdf5
# Municipality mode: climada_hazard_MUNI_SELECTION.hdf5
```

---

## Data Flow Architecture

### Input (from Notebook 1)
```
Notebook 1 Output Structure:
├── data/processed/calibration/evt_pot/
│   ├── Cagayan_01/
│   │   └── {RUN_TAG}/
│   │       ├── return-period_all.nc          ◄── RETURN_PERIOD_NC
│   │       ├── climada_flood_hazard.nc       (optional CLIMADA intermediate)
│   │       └── aoi/
│   │           └── mapping tables, etc.
│   │
│   └── MUNI_SELECTION/
│       └── {RUN_TAG}/
│           ├── return-period_all.nc          ◄── RETURN_PERIOD_NC
│           ├── climada_flood_hazard.nc       (optional)
│           └── aoi/
│               └── selected_municipalities.geojson  ◄── MUNI_GDF source
```

### Output (from Notebook 2)
```
Notebook 2 Output Structure:
├── data/processed/climada_hazard/
│   ├── Cagayan_01/
│   │   └── {RUN_TAG}/
│   │       ├── climada_hazard_Cagayan_01.hdf5
│   │       ├── flood-depth_all.nc
│   │       ├── return-period_regrid_all.nc
│   │       ├── visualizations/
│   │       │   ├── 01_return_period_map.png
│   │       │   ├── 02_flood_depth_maps.png
│   │       │   └── ... (stakeholder maps)
│   │       └── _jrc_cache/
│   │
│   └── MUNI_SELECTION/
│       └── {RUN_TAG}/
│           ├── climada_hazard_MUNI_SELECTION.hdf5
│           ├── flood-depth_all.nc
│           ├── return-period_regrid_all.nc
│           ├── visualizations/
│           │   ├── 01_return_period_map.png
│           │   ├── 02_flood_depth_maps.png
│           │   └── ...
│           └── _jrc_cache/
```

---

## Testing Strategy

### Test Case 1: Basin Mode (Cagayan_01)

**Setup**:
1. Run Notebook 1 with `USE_MUNI_AOI = False`
2. Verify outputs in `calibration/evt_pot/Cagayan_01/{RUN_TAG}/`

**Test Notebook 2**:
```python
# Configuration cell should output:
# ✓ Detected mode: BASIN
# ✓ Detected BASIN mode with basin_id: Cagayan_01
# Basin ID/Selection: Cagayan_01
# Run tag: 2026-01-19_calib-test  (or your actual run tag)
```

**Validation**:
- ✅ `RETURN_PERIOD_NC` file found and loaded
- ✅ `flood_zone_boundary` extracted from basin YAML
- ✅ JRC tiles selected using basin extent
- ✅ Output path: `climada_hazard/Cagayan_01/{RUN_TAG}/`
- ✅ Hazard HDF5: `climada_hazard_Cagayan_01.hdf5`
- ✅ Visualization titles show "Cagayan_01"

---

### Test Case 2: Municipality Mode

**Setup**:
1. Run Notebook 1 with `USE_MUNI_AOI = True`
2. Select municipalities (e.g., Rizal, Tayabas, Lucena)
3. Verify outputs:
   - `calibration/evt_pot/MUNI_SELECTION/{RUN_TAG}/`
   - `calibration/evt_pot/MUNI_SELECTION/{RUN_TAG}/aoi/selected_municipalities.geojson`

**Test Notebook 2**:
```python
# Configuration cell should output:
# ✓ Detected mode: MUNICIPALITY
# ✓ Detected MUNICIPALITY mode with 3 municipalities
# Basin ID/Selection: MUNI_SELECTION
# Run tag: 2026-01-19_calib-test  (auto-detected)
```

**Validation**:
- ✅ `MUNI_GDF` loaded with correct municipalities
- ✅ `flood_zone_boundary` = union of municipality geometries
- ✅ JRC tiles selected using municipality union boundary
- ✅ Output path: `climada_hazard/MUNI_SELECTION/{RUN_TAG}/`
- ✅ Hazard HDF5: `climada_hazard_MUNI_SELECTION.hdf5`
- ✅ Visualization titles show "Municipality Selection"

---

### Test Case 3: Auto-Detection with Different Run Tags

**Setup**:
1. Run Notebook 1 multiple times with `USE_MUNI_AOI=True` and different RUN_TAGs
2. Example run tags:
   - `2026-01-19_calib-test`
   - `2026-01-20_calib-test`
   - `2026-01-21_calib-test`

**Test Notebook 2**:
```python
# Configuration cell:
AUTO_DETECT = True
basin_id_input = None       # Will auto-detect MUNI_SELECTION
run_tag_input = None        # Will auto-detect FIRST run tag (sorted)

# Should correctly identify first municipaltymode run
```

**Validation**:
- ✅ Auto-detection picks correct run tag (first when sorted)
- ✅ All three RUN_TAG variations work without manual intervention

---

## Verification Checklist

### Configuration Section
- [ ] Helper functions load without errors
- [ ] `detect_calibration_mode()` identifies correct mode
- [ ] `get_flood_zone_boundary()` returns valid geometry
- [ ] `construct_hazard_paths()` creates all required directories
- [ ] `RETURN_PERIOD_NC` file validation passes
- [ ] Mode printed: "BASIN" or "MUNICIPALITY"
- [ ] Basin/Selection name displayed correctly
- [ ] Run tag auto-detected or manual value used

### Data Loading
- [ ] Return period dataset loads with correct dimensions
- [ ] Grid extent coordinates printed correctly
- [ ] Lats/lons arrays extracted without errors

### JRC Tile Selection
- [ ] Tile index downloads (if needed)
- [ ] Tiles loaded and intersected with `flood_zone_boundary`
- [ ] Correct number of tiles selected for mode/region
- [ ] JRC manifests created for all return periods
- [ ] Download counts reasonable (no 0 tiles)

### Processing
- [ ] Flood maps intermediate netcdf created
- [ ] Return periods regridded correctly
- [ ] Flood depth interpolation completes
- [ ] No NaN/invalid data in result (or expected coverage documented)

### CLIMADA Hazard Creation
- [ ] Centroids created with correct count
- [ ] Sparse intensity matrices built
- [ ] Frequency array meaningful (1/RP values)
- [ ] `hazard.check()` validation passes
- [ ] HDF5 file saved with correct name (mode-aware)

### Visualization & Reporting
- [ ] Return period map title shows correct area name
- [ ] Flood depth maps generated without errors
- [ ] Visualization directory populated
- [ ] Summary section prints Mode and Area information
- [ ] File paths in summary output are correct

### Output Validation
- [ ] Output directory exists at correct location
- [ ] All expected files present:
  - [ ] `climada_hazard_{BASIN_ID or MUNI_SELECTION}.hdf5`
  - [ ] `flood-depth_all.nc`
  - [ ] `return-period_regrid_all.nc`
  - [ ] `flood-maps_intermediate.nc`
  - [ ] Visualization PNGs
- [ ] File sizes are reasonable (not 0 bytes)
- [ ] Data loads without corruption (can re-open HDF5)

---

## Migration Guide for Existing Users

### If you were running with hardcoded BASIN_ID:

**Before**:
```python
# Had to manually edit this line each time
BASIN_ID = "Cagayan_01"
RUN_TAG = "2026-01-19_calib-test"
```

**After** (Option 1 - Keep existing workflow):
```python
# Still works! But now it's:
AUTO_DETECT = False
basin_id_input = "Cagayan_01"
run_tag_input = "2026-01-19_calib-test"
```

**After** (Option 2 - Use new auto-detection):
```python
# Just run Notebook 1 normally
# Then run Notebook 2 without any manual config
AUTO_DETECT = True
basin_id_input = None
run_tag_input = None
# Everything auto-detected!
```

---

## Troubleshooting

### Error: "Cannot detect calibration mode"
**Cause**: Notebook 1 outputs not found in expected location
**Fix**: 
1. Verify Notebook 1 completed successfully
2. Check that outputs exist in `data/processed/calibration/evt_pot/`
3. For municipality mode: Verify `selected_municipalities.geojson` exists

### Error: "Basin config not found"
**Cause**: Basin YAML file missing for basin mode
**Fix**:
1. Check that basin YAML exists at `ops/configs/basins/{BASIN_ID}.yaml`
2. Verify basin ID spelling matches YAML filename
3. Ensure `aoi_bbox` key exists in YAML

### Error: "No tiles selected"
**Cause**: `flood_zone_boundary` doesn't intersect JRC tile grid
**Fix**:
1. Print boundary extent: `print(flood_zone_boundary.bounds)`
2. Verify coordinates are in EPSG:4326 (lat/lon)
3. Check JRC tile index loads correctly
4. Consider expanding boundary using `.buffer()` if legitimate flood risk exists outside exact boundaries

### Warning: "RP=X not available in data"
**Cause**: JRC tile download failed for specific return period
**Fix**:
1. Check internet connection
2. Verify JRC server is accessible
3. Example URL pattern: `https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/CEMS-GLOFAS/flood_hazard/RP100/...`
4. Manually download missing tiles if server temporarily down

---

## Future Enhancements

Potential improvements for future iterations:

1. **Caching**: Remember last used `basin_id` and `run_tag` in a config file
2. **Interactive mode**: GUI selector for basin/municipality and run tag
3. **Batch processing**: Process multiple basins in one Notebook 2 run
4. **Dashboard generation**: Auto-create interactive Folium/Plotly dashboards
5. **Report templating**: Generate PDF reports with mode-aware templates
6. **Parallel JRC downloads**: Speed up tile downloads with multithreading

---

## Questions & Support

If issues arise:

1. Check [VERIFICATION CHECKLIST](#verification-checklist) above
2. Review error messages for specific file/path requirements
3. Examine Notebook 1 outputs to confirm correct structure
4. Check console logs for helper function output
5. Inspect intermediate netcdf files with `xarray` if needed

For structural issues, check:
- `ops/configs/basins/{basin_id}.yaml` for basin mode
- Notebook 1 `aoi/selected_municipalities.geojson` for municipality mode
- `data/processed/calibration/evt_pot/` directory structure
