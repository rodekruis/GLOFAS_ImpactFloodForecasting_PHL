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
- Reference: [Notebook 2 Refactoring](../technical/notebook02-refactoring.md)

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
from philflood.calibration.evt_pot import fit_gpd_from_exceedances
params = fit_gpd_from_exceedances(your_data, threshold=1500)
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
