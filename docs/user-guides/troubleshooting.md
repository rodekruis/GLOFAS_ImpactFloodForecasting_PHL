# Troubleshooting Guide

Solutions to common PhilFlood issues organized by category.

---

## Installation Issues

### "ModuleNotFoundError: No module named 'rasterio'"
**Cause**: GIS libraries not installed  
**Fix**:
```bash
mamba install -c conda-forge rasterio geopandas
```

### "pip install fails with cryptic compilation errors"
**Cause**: Installing from source without prebuilt binaries  
**Fix** (Windows/Mac):
```bash
mamba install -c conda-forge python=3.11 \
  numpy pandas rasterio geopandas
pip install -e . --no-deps
```

### "Can't find GDAL/GEOS"
**Cause**: System libraries missing  
**Fix**: Use conda-forge (prebuilt binaries):
```bash
# Don't install gdal via pip!
mamba install -c conda-forge gdal geopandas
```

---

## CLIMADA-Specific Issues

### "ImportError: No module named 'climada'"
**Cause**: Optional dependency  
**Fix**:
```bash
pip install climada>=3.0.0
```

### "PyArrow memory error in Notebook 2"
**Cause**: Large JRC tile downloads  
**Fix**:
- Increase chunk size (LOW_RAM_MODE setting)
- Run with increased RAM available
- Check [Section 4 Optimization](../technical/notebook02-section4-optimization.md)

### "GEOS error: 'NoneType' object is not callable"
**Cause**: Shapely/GEOS compatibility  
**Fix**:
```bash
pip install --upgrade shapely
```

### "Regridding produces NaN grid"
**Cause**: Coordinate system mismatch  
**Fix**:
- Verify all data in EPSG:4326
- Check basin boundary is valid
- Inspect intermediate NetCDF: `xr.open_dataset(...)`

---

## Data Download & GloFAS Issues

### "Cannot download GloFAS data from CDS"
**Cause**: CDS access not configured  
**Fix**:
1. Create CDS account: [cds.climate.copernicus.eu](https://cds.climate.copernicus.eu)
2. Add `.cdsapirc` file to home directory:
   ```
   url: https://cds.climate.copernicus.eu/api/v2
   key: USERNAME:API_KEY
   ```
3. Test: `cdsapi.Client().retrieve(...)`

### "No data for specified date/region"
**Cause**: GloFAS doesn't cover region or date unavailable  
**Fix**:
- Check GloFAS coverage (Phlippines covered)
- Verify date in valid range (1979-2025 for history, 0-10 days for forecasts)
- Check GLOFAS_POINT_IDS are correct format

### "Forecast data not released yet"
**Cause**: GloFAS releases on schedule  
**Fix**:
- GloFAS releases typically 6-12 hours after valid time
- Check [GloFAS calendar](https://cds.climate.copernicus.eu) for release times
- Retry after release time

---

## Memory & Performance Issues

### "MemoryError: Unable to allocate X GB"
**Cause**: Data too large for available RAM  
**Fix** (Notebook 1):
- Settings in Section 3.5 should auto-detect
- If still exceeding: Set `LOW_RAM_MODE = True`
- Process smaller year ranges
- Reference: [Methods - Streaming Architecture](../technical/methods-overview.md#streaming-grib-extraction-architecture)

### "Notebook 1 taking >3 hours"
**Cause**: Processing all cells instead of pour point  
**Fix** (Section 1):
```python
USE_CELL_EXTRACTION = False  # Don't extract all cells
```

### "Notebook 2 slow (>1 hour for Section 6)"
**Cause**: Fast internet needed for JRC downloads  
**Fix**:
- Check internet connection
- JRC servers in Europe (higher latency from Asia)
- Try again during off-peak hours
- Can manually download specific tiles if needed

---

## Calibration & EVT Issues

### "ValueError: Not enough exceedances above threshold"
**Cause**: Threshold too high  
**Fix** (Notebook 1, Section 10):
- Lower threshold in MRL plot
- Should have ≥ 50 exceedances
- Re-run calibration

### "All return levels are NaN"
**Cause**: GPD fitting numerical issue  
**Fix**:
- Try different threshold
- Check raw discharge data quality
- Ensure > 5 years of continuous data

### "Parameter stability plot shows wild variation"
**Cause**: Threshold too low  
**Fix**:
- Increase threshold (move to right on plot)
- Should have "stable" region where parameters don't jump
- Verify with Section 11 "Parameter Stability Plot"

### "Bootstrap return levels unreasonable (negative discharge or huge values)"
**Cause**: Fitting issues or data quality  
**Fix**:
- Inspect raw discharge in Section 8
- Check for outliers or errors
- Verify gauge location correct
- Consider removing clearly bad years

---

## Configuration & Validation Issues

### ""ValidationError: 'threshold' must be numeric"
**Cause**: YAML config has wrong data type  
**Fix** (ops/configs/basins/your_basin.yaml):
```yaml
# WRONG
evt_parameters:
  threshold_m3s: "1500"  # String!

# CORRECT
evt_parameters:
  threshold_m3s: 1500.0  # Float
```

### "Cannot find basin config"
**Cause**: Missing YAML file  
**Fix**:
```bash
# Check file exists
ls ops/configs/basins/your_basin.yaml

# Validate it
philflood validate ops/configs/basins/your_basin.yaml
```

### "Basin polygon invalid"
**Cause**: Malformed geometry in YAML  
**Fix**:
- Check `aoi_bbox` format: `[min_lat, min_lon, max_lat, max_lon]`
- Verify coordinates in EPSG:4326 (lat/lon)
- Test with geopandas:
  ```python
  from shapely.geometry import box
  box(lons[0], lats[0], lons[1], lats[1])
  ```

---

## Notebook Issues

### "Cannot detect calibration mode"  (Notebook 2)
**Cause**: Notebook 1 outputs missing  
**Fix**:
- Check `data/processed/calibration/evt_pot/` exists
- Verify Notebook 1 completed successfully
- Check either `Cagayan_01/` or `MUNI_SELECTION/` subfolder exists
- Re-run Notebook 1 if needed

### "Return period file not found"
**Cause**: Notebook 1 didn't export NetCDF  
**Fix**:
- Run Notebook 1 through Section 13
- Check `return-period_all.nc` exists in output folder
- Verify file not 0 bytes

### "No tiles selected" (Notebook 2, Section 5)
**Cause**: Basin geometry outside JRC coverage  
**Fix**:
- Check basin coordinates valid
- Expand boundary: `flood_zone_boundary.buffer(0.1)`
- Verify basin in Philippines

### "Regridding fails with shape mismatch"
**Cause**: Coordinate system or dimension mismatch  
**Fix**:
- Check all data in EPSG:4326
- Verify return period NetCDF structure
- Inspect intermediate files: `xr.open_dataset(...)`
- Reference: [Notebook 2 Section 4 Optimization](../technical/notebook02-section4-optimization.md)

---

## Operational/Monitoring Issues

### "Monitoring command not found"
**Cause**: PhilFlood not installed or activated  
**Fix**:
```bash
# Verify in active environment
which philflood

# Reinstall if needed
pip install -e .
```

### "Monitoring fails: 'Basin config not valid'"
**Cause**: Configuration error  
**Fix**:
```bash
# Validate all basins
philflood validate --basin-dir ops/configs/basins

# Fix errors in YAML
vim ops/configs/basins/problematic.yaml
```

### "No GloFAS forecast data"
**Cause**: Forecast not released or data unavailable  
**Fix**:
- Check GloFAS release schedule
- Test with historical date: `--date 2024-12-15`
- Verify GLOFAS data connection

### "Output JSON malformed"
**Cause**: Processing interrupted  
**Fix**:
- Check logs for errors
- Re-run monitoring
- Verify all basins valid first

---

## Notebook 03 (Validation) Issues

### "CLIMADA-Petals not found" (Pre-flight check fails)
**Cause**: Optional library not installed  
**Fix**:
```bash
pip install climada[petals]>=3.0.0
```
**Note**: Same as Notebook 2 requirement. Check [CLIMADA-Specific Issues](#climada-specific-issues) above.

### "GFM validation directory not found"
**Cause**: `GFM_VALIDATION_ROOT` path incorrect or GFM files missing  
**Fix**:
1. Verify path exists and is readable:
   ```python
   from pathlib import Path
   gfm_path = Path("your/path/to/GFM")
   print(gfm_path.exists())
   print(list(gfm_path.glob("*.tif")))  # Check for GeoTIFF files
   ```
2. Update Notebook 03 Cell 6:
   ```python
   GFM_VALIDATION_ROOT = Path("data/raw/glofas/GFM")  # Adjust path
   ```
3. See [GFM Data Guide](../getting-started/gfm-data-guide.md) for format requirements

### "Output directory not writable"
**Cause**: Permissions issue on output destination  
**Fix**:
```bash
# Check permissions
ls -ld data/processed/validation/
# Make writable (Linux/Mac)
chmod 755 -R data/processed/validation/
# (Windows): Right-click folder → Properties → Security → Edit permissions
```

### "Calibration auto-detect failed: No recent calibration found"
**Cause**: Notebook 1 outputs missing or in unexpected location  
**Fix**:
1. Verify Notebook 1 completed successfully
2. Check output exists: `data/processed/calibration/evt_pot/{BASIN_ID}/{RUN_TAG}/`
3. Manually specify in Notebook 03 Cell 8:
   ```python
   AUTO_DETECT = False
   basin_id_input = "Cagayan_01"
   run_tag_input = "20260209_test"
   ```

### "ValueError: Could not parse GFM filenames"
**Cause**: GFM file naming doesn't match expected pattern  
**Fix**:
1. Check file names. Expected formats:
   - `extent__YYYYMMDD.tif` (e.g., `extent__20241215.tif`)
   - `extent__YYYY-MM-DD.tif`
   - Similar with date patterns
2. Rename files to match expected pattern
3. Or adjust date parsing in Notebook 03 Cell 10:
   ```python
   # See code for custom date format handling
   ```
4. See [GFM Data Guide](../getting-started/gfm-data-guide.md) for naming conventions

### "Only X% of gauges have timeseries data"
**Cause**: Some discharge files missing or incomplete  
**Fix**:
- If > 50%: Proceed, results will be sparse but valid
- If < 30%: Investigate why discharge files missing
  - Check Notebook 1 extraction completed
  - Verify GloFAS data coverage for your basin
  - Check historical vs. forecast data availability
- Missing data is noted in output; results still valid

### "Dimension mismatch during reprojection"
**Cause**: CRS or grid alignment issue  
**Fix**:
1. Run diagnostic cells (Notebook 03 Cells 13-14) to inspect coordinates
2. Verify all data in EPSG:4326 (WGS84 lat/lon):
   ```python
   import rasterio
   with rasterio.open("your_file.tif") as src:
       print(src.crs)  # Should be EPSG:4326
   ```
3. Check basin boundary is valid:
   ```python
   print(aoi_boundary.is_valid)
   print(aoi_boundary.bounds)  # Should be W, S, E, N in lat/lon
   ```

### "Memory error during raster reprojection"
**Cause**: Large basin or high-resolution data  
**Fix**:
1. Enable LOW_RAM_MODE in Notebook 03 Cell 3:
   ```python
   LOW_RAM_MODE = True
   ```
2. Reduce AOI (fewer municipalities selected)
3. Run on machine with more available RAM
4. Process smaller episode date ranges

### "JRC tile download taking >2 hours"
**Cause**: Slow internet or server load  
**Fix**:
- Check internet connection
- JRC servers in Europe (higher latency from Asia/Oceania)
- Run during off-peak hours (e.g., early morning UTC)
- Tiles are cached: subsequent runs much faster
- Can interrupt and resume (partial downloads re-used)

### "NaN values in return period or depth maps"
**Cause**: Missing gauge data or interpolation issues  
**Fix**:
- This is often expected (data gaps are normal)
- Check gauge availability (Notebook 03 Section 7 output)
- Verify AOI includes several gauges within it
- NaN regions noted in metrics CSV

### "Confusion matrix metrics are zero or NaN"
**Cause**: No overlap between predicted and observed extent, or data issue  
**Fix**:
1. Check raw extents are present:
   ```python
   print(observed_extent.sum())  # Should be > 0
   print(modeled_extent.sum())
   ```
2. Verify observed GFM files loaded correctly
3. Check depth threshold hasn't clipped all data
4. Inspect difference maps in output directory

### "Dashboard HTML not loading in browser"
**Cause**: File path issue or browser compatibility  
**Fix**:
1. Open file directly (avoid network issues):
   - Right-click HTML file → Open with → Browser
   - Or drag file into browser tab
  - Ensure no spaces in file path
2. Try different browser (Chrome, Firefox, Edge preferred)
3. Check browser console for errors (F12 → Console tab)
4. If Leaflet map loads but no tiles: check internet for basemap tile access

### "Dashboard shows all NaN values on map"
**Cause**: Extent data not loaded correctly  
**Fix**:
1. Verify extent GeoTIFFs exist in `maps_for_dashboard/` folder
2. Check GeoTIFFs have valid data (not all nodata):
   ```python
   import rasterio
   with rasterio.open("file.tif") as src:
       data = src.read(1)
       print(data.min(), data.max())  # Should have some valid values
   ```
3. Check Notebook 03 Section 11 completed without errors

---

## Debugging Tips

### Enable Verbose Output
```bash
# Notebook: Add to cell
import logging
logging.basicConfig(level=logging.DEBUG)

# CLI: Check logs
tail -f logs/monitoring.log
```

### Inspect Intermediate Files
```python
import xarray as xr
import geopandas as gpd

# NetCDF
ds = xr.open_dataset("file.nc")
print(ds)  # Structure
print(ds.dims, ds.data_vars)

# GeoJSON
gdf = gpd.read_file("file.geojson")
print(gdf.head())
print(gdf.crs, gdf.bounds)
```

### Test Individual Components
```python
# Test GRIB extraction
from philflood.adapters.glofas_grib_v4_optimized import extract_timeseries_streaming
ts = extract_timeseries_streaming("file.grib", vg_ids=["PHL_12345"])

# Test config loading
from philflood.config import load_basin_config
cfg = load_basin_config("ops/configs/basins/my_basin.yaml")

# Test EVT fitting
from philflood.calibration.evt_pot import fit_gpd_to_pot
result = fit_gpd_to_pot(your_data, threshold_m3s=1500)
```

---

## Getting More Help

| Issue Type | Resource |
|---|---|
| General questions | [FAQ](../getting-started/FAQ.md) |
| Technical concepts | [Glossary](../technical/GLOSSARY.md) |
| Scientific method | [Methods Overview](../technical/methods-overview.md) |
| Architecture details | [ARCHITECTURE.md](../technical/ARCHITECTURE.md) |
| Installation help | [Quick Start](../getting-started/quickstart.md) |
| Development issues | [Contributing Guide](../contributing/CONTRIBUTING.md) |
| Bug reports | [GitHub Issues](https://github.com/rodekruis/GLOFAS_ImpactFloodForecasting_PHL/issues) |

---

**Still stuck?** [Open an issue](https://github.com/rodekruis/GLOFAS_ImpactFloodForecasting_PHL/issues/new) with:
- Error message (full traceback)
- Steps to reproduce
- Your environment (Python version, OS, packages)
- What you were trying to do
