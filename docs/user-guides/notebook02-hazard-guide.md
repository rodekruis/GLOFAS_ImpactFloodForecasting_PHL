# Notebook 2: Flood Hazard Analysis Guide

Guide to creating flood hazard maps using Notebook 2 (`calibration/notebooks/02_HazardOnly_Workflow_v2.ipynb`).

## Overview

Notebook 2 transforms calibrated return periods (from Notebook 1) into flood depth maps and CLIMADA hazard objects. Integrates JRC global flood maps with your basin discharge calibration.

**Duration**: ~20-30 minutes (mostly download time)  
**Prerequisite**: Notebook 1 calibration complete  
**Output**: CLIMADA flood hazard HDF5 + visualizations

---

## Quick Start (5 min)

### Option 1: Automatic Mode Detection (Recommended)

1. Run Notebook 1 first (basin or municipality mode)
2. Open Notebook 2, leave configuration as default:
   ```python
   AUTO_DETECT = True
   basin_id_input = None
   run_tag_input = None
   ```
3. Run all cells — everything auto-configures

### Option 2: Manual Configuration

```python
AUTO_DETECT = False
basin_id_input = "Cagayan_01"             # Your basin ID
run_tag_input = "2026-01-19_calib-test"   # Your run tag
```

### What auto-detection changed vs. the previous version

| Aspect | Before | After |
|--------|--------|-------|
| **Configuration** | Hardcoded BASIN_ID | Auto-detects from Notebook 1 |
| **Output paths** | Always `climada_hazard/{BASIN_ID}/` | `climada_hazard/{BASIN_ID or MUNI_SELECTION}/` |
| **Tile selection** | Fixed basin extent | Uses flood_zone_boundary |
| **Mode support** | Basin only | Basin + Municipality |
| **User effort** | Manual path editing | Zero manual path editing |

### Expected console output when running successfully

**Basin mode:**
```
✓ Detected BASIN mode with basin_id: Cagayan_01
✓ Detected mode: BASIN
  Basin ID/Selection: Cagayan_01
  Run tag: 2026-01-20_calib-test
```

**Municipality mode:**
```
✓ Detected MUNICIPALITY mode with 3 municipalities
✓ Detected mode: MUNICIPALITY
  Basin ID/Selection: MUNI_SELECTION
  Run tag: 2026-01-20_calib-test
```

---

## Key Sections

### Configuration (Sections 1-4)
- **Section 1**: Environment setup, package imports
- **Section 2**: Load config paths, basins
- **Section 3**: Resource detection (RAM, memory mode)
- **Section 4**: Mode auto-detection
  - Reads Notebook 1 output
  - Determines: Basin or Municipality mode?
  - Sets output paths automatically

**Output**: Mode confirmed, paths ready

### JRC Tile Selection (Section 5)
- Downloads JRC global flood map tile index
- Intersects with your basin boundary
- Selects tiles covering your area
- Lists manifest URLs for download

**Check**: Correct number of tiles for basin size (~10-20 typically)

### Flood Map Processing (Section 6-7)
- **Section 6**: Download JRC tiles for all RP (return periods)
  - 8 return periods × N tiles = large download (30 min+)
- **Section 7**: Mosaic tiles into single grid per RP
  - Combines tiles into merged raster
  - All 8 RPs stacked

**Output**: Intermediate NetCDF with raw JRC depths

### Regridding & Interpolation (Section 8)
- **Section 8**: Regrid from JRC grid → regular lat/lon
  - Uses CLIMADA-Petals `petals_regrid()`
  - Preserves all 8 return periods
  - Generates interpolated depths

**Key fix** (v0.3.0): All 8 RPs flow through (previously only 1 survived)

### CLIMADA Hazard Creation (Section 9)
- Creates CLIMADA Hazard object
- Sets centroids (grid points)
- Assigns intensity (flood depth per centroid)
- Sets frequency (1/RP for each event)
- Validates with `hazard.check()`
- Exports as HDF5

**Output**: `climada_hazard_{BASIN_ID or MUNI_SELECTION}.hdf5`

### Visualization (Section 10)
- Return period map (all periods)
- Flood depth distribution maps
- Saves PNG files for stakeholder review
- Optional interactive maps

---

## Data Dimensions

### Input (from Notebook 1)
- Return levels: 8 periods (1, 10, 20, 50, 75, 100, 200, 500 years)
- Grid: ~4000 × 3000 cells (global, but clipped to basin)
- Structure: 3D (gauges × RPs × 1)

### Output (Notebook 2)
- Centroids: ~N grid points (thousands, depending on basin)
- Intensity: 8 events × N centroids (sparse matrix)
- Frequency: [1.0, 0.1, 0.05, 0.02, ...] (reciprocals of RPs)
- Stored: HDF5 format (efficient for large matrices)

---

## Mode Detection

### Basin Mode
```
Input: data/processed/calibration/evt_pot/Cagayan_01/{RUN_TAG}/
Output: data/processed/climada_hazard/Cagayan_01/{RUN_TAG}/
Files: climada_hazard_Cagayan_01.hdf5
```

### Municipality Mode
```
Input: data/processed/calibration/evt_pot/MUNI_SELECTION/{RUN_TAG}/
Output: data/processed/climada_hazard/MUNI_SELECTION/{RUN_TAG}/
Files: climada_hazard_MUNI_SELECTION.hdf5
```

**Auto-detection**: Notebook 2 checks input path structure and adapts output automatically!

---

## Performance Tuning

### Memory Issues

**Symptom**: "Memory exceeded" or slow regridding

**Solutions**:
1. Check Section 3.5: LOW_RAM_MODE should be auto-detected
2. Manual override:
   ```python
   LOW_RAM_MODE = True  # Force smaller chunks
   ```
3. Reduce chunk size further if needed

### Slow Tile Download

**Symptom**: Section 6 taking > 1 hour

**Solutions** (try in order):
1. Check internet speed (JRC server is in Europe)
2. Run at night (less server load)
3. Manually download specific return periods if needed
4. Use cached tiles from previous run

---

## Validation

After Notebook 2, verify outputs:

```python
import xarray as xr
from climada.hazard import Hazard

# Check intermediate files
ds = xr.open_dataset("data/processed/climada_hazard/.../return-period_regrid_all.nc")
assert 'return_period' in ds.dims
assert ds.dims['return_period'] == 8

# Check hazard object
haz = Hazard.from_hdf5("data/processed/climada_hazard/.../climada_hazard_*.hdf5")
assert haz.intensity.shape[0] == 8  # 8 events
assert (haz.frequency > 0).all()
assert haz.check()  # Validation passed
```

---

## Troubleshooting

**"No tiles selected"**
- Basin geometry outside JRC coverage
- Check boundary: `print(flood_zone_boundary.bounds)`
- Solution: Expand boundary with `.buffer(0.1)`

**"Cannot detect calibration mode"**
- Notebook 1 output missing
- Check: `data/processed/calibration/evt_pot/` exists?
- Re-run Notebook 1

**"Only 1 return period in output" (v0.2 issue)**
- Fixed in v0.3.0
- Ensure latest version: `pip install -e . --upgrade`
- All 8 RPs should flow through

**"Regridding very slow"**
- Normal for large basins
- Check chunk settings in Section 3.5
- Consider running overnight

---

## Using the Hazard Object

After Notebook 2, you have a CLIMADA flood hazard object. Use it:

```python
from climada.hazard import Hazard

# Load
haz = Hazard.from_hdf5("climada_hazard_Cagayan_01.hdf5")

# Access properties
print(f"Events: {haz.intensity.shape[0]}")  # Should be 8
print(f"Centroids: {haz.intensity.shape[1]}")
print(f"Frequency: {haz.frequency}")

# For impact modeling (Notebook 3, future)
# exposure = ... (population)
# impact = exposure.impact(haz)
```

---

## Output Files

| File | Purpose |
|---|---|
| `climada_hazard_{ID}.hdf5` | Main CLIMADA hazard object |
| `flood-depth_all.nc` | Interpolated flood depths (NetCDF) |
| `return-period_regrid_all.nc` | Regridded return periods |
| `flood-maps_intermediate.nc` | Raw JRC tiles (temporary) |
| `visualizations/01_return_period_map.png` | Return period map |
| `visualizations/02_flood_depth_maps.png` | Depth maps for all RPs |
| `_jrc_cache/` | Downloaded tiles (for reuse) |

---

## References

- [Section 4 Optimization](../technical/notebook02-section4-optimization.md) - Performance tuning (rasterio fast path, chunk sizing)
- [Methods Overview - CLIMADA](../technical/methods-overview.md#return-period-to-hazard-integration-climada)
- [FAQ - CLIMADA](../getting-started/FAQ.md#climada--hazard-integration)

---

**Questions?** Check [Troubleshooting](troubleshooting.md) or [FAQ](../getting-started/FAQ.md).
