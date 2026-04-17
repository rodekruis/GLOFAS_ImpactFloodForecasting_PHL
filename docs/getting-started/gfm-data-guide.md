# GloFAS Flood Maps (GFM) Data Guide

Guide to obtaining and preparing GloFAS Flood Maps (GFM) observed extent data for validation in Notebook 03.

---

## What is GFM?

**GloFAS Flood Maps (GFM)** are satellite-derived observations of actual flood extent. These maps show **where water was present** during historical flood events, used as ground truth to validate model predictions.

**Key characteristics**:
- **Source**: Satellite imagery (optical or radar)
- **Format**: Binary extent (flooded / not flooded)
- **Resolution**: Typically 30-100m
- **Coverage**: Global, but not all flood events captured
- **Temporal**: Daily snapshots during flood periods

**Purpose in PhilFlood**: Notebook 03 uses GFM as "observed truth" to compare against model-predicted flood extent.

---

## Data Requirements for Notebook 03

### File Format
- **Format**: GeoTIFF (`.tif`)
- **Values**: Binary or classified (water vs. non-water)
- **CRS**: EPSG:4326 (WGS 84 lat/lon) preferred
- **NoData**: 0 or 255 (configurable in Notebook 03)

### Naming Convention
GFM files must include dates in their filename for Notebook 03 to parse correctly.

**Accepted patterns**:
```
extent__YYYYMMDD.tif           # Example: extent__20241215.tif
obs_flood_YYYYMMDD.tif         # Example: obs_flood_20241215.tif
GFM_YYYY-MM-DD.tif             # Example: GFM_2024-12-15.tif
flood_extent_YYYYMMDD.tif
```

**Pattern**: Any filename with `YYYYMMDD` or `YYYY-MM-DD` format will be auto-detected.

### Directory Structure
Organize GFM files in a single directory (can have subdirectories):

```
data/raw/glofas/GFM/
├── extent__20241201.tif
├── extent__20241202.tif
├── extent__20241205.tif
├── extent__20241210.tif
└── ... (more dates)
```

Or with subdirectories:
```
data/raw/glofas/GFM/
├── Philippines/
│   ├── Cagayan/
│   │   ├── extent__20241201.tif
│   │   └── extent__20241205.tif
│   └── Mindanao/
│       └── extent__20250115.tif
```

**Notebook 03 will recursively search** for all `.tif` files with dates.

---

## Data Sources

### 1. **Copernicus Emergency Management Service (EMS)**
- **URL**: [https://emergency.copernicus.eu/mapping/](https://emergency.copernicus.eu/mapping/)
- **Coverage**: Major flood events globally
- **Format**: GeoTIFF, Shapefile
- **Cost**: Free

**How to use**:
1. Visit EMS Activations page
2. Search for Philippines flood events by date
3. Download "flood extent" or "observed water extent" layers
4. Rename files to include date (e.g., `extent__YYYYMMDD.tif`)
5. Place in GFM_VALIDATION_ROOT directory

### 2. **GloFAS Rapid Flood Mapping**
- **URL**: [https://www.globalfloods.eu/](https://www.globalfloods.eu/)
- **Coverage**: Near-real-time flood observations
- **Format**: NetCDF, GeoTIFF
- **Cost**: Free (requires CDS account)

**How to use**:
1. Register on Copernicus CDS
2. Search for GloFAS rapid flood mapping products
3. Download for Philippines region and dates of interest
4. Convert to GeoTIFF if needed
5. Rename with date pattern

### 3. **Sentinel-1 Flood Service (Google Earth Engine)**
- **URL**: Cloud-based processing (requires GEE account)
- **Coverage**: Global, Sentinel-1 radar
- **Format**: GeoTIFF export
- **Cost**: Free (GEE account)

**How to use** (requires GEE scripting):
```javascript
// Example GEE code (simplified)
var s1 = ee.ImageCollection('COPERNICUS/S1_GRD')
  .filterBounds(philippines)
  .filterDate('2024-12-01', '2024-12-31');
// ... flood detection logic ...
Export.image.toDrive({image: floodExtent, description: 'extent_20241215'});
```

### 4. **Manual Digitization from News/Reports**
- **Source**: News imagery, social media, humanitarian reports
- **Format**: Manually create polygons in QGIS
- **Cost**: Free (labor intensive)

**Process**:
1. Collect flood photos/reports with known locations and dates
2. Open base imagery in QGIS (OSM, Google Satellite)
3. Manually digitize flood extent polygons
4. Rasterize to GeoTIFF: Vector → Raster → Rasterize
5. Export as `extent__YYYYMMDD.tif`

---

## Data Preparation Checklist

Before running Notebook 03, verify:

### ✅ Format Check
```python
import rasterio
with rasterio.open("extent__20241215.tif") as src:
    print(f"CRS: {src.crs}")              # Should be EPSG:4326 (or will be reprojected)
    print(f"Resolution: {src.res}")       # Typically ~0.0001-0.001 degrees
    print(f"Bands: {src.count}")          # Should be 1
    print(f"Data type: {src.dtypes[0]}")  # uint8 or int16
    data = src.read(1)
    print(f"Unique values: {set(data.flatten()[:1000])}")  # Should have 0, 1, or 0, 1, 255
```

### ✅ Naming Check
```python
from pathlib import Path
import re

gfm_root = Path("data/raw/glofas/GFM")
files = list(gfm_root.rglob("*.tif"))
print(f"Found {len(files)} GeoTIFF files")

# Check date parsing
date_pattern = r"(\d{4}[-_]?\d{2}[-_]?\d{2})"
for file in files[:5]:
    match = re.search(date_pattern, file.name)
    if match:
        print(f"✓ {file.name} → Date: {match.group(1)}")
    else:
        print(f"✗ {file.name} → NO DATE DETECTED")
```

### ✅ Spatial Coverage Check
Verify GFM covers your basin of interest:

```python
import geopandas as gpd
import rasterio

# Load your basin boundary (from Notebook 1 output)
basin = gpd.read_file("your_basin.geojson")

# Check GFM extent
with rasterio.open("extent__20241215.tif") as src:
    gfm_bounds = src.bounds  # (left, bottom, right, top)
    print(f"Basin bounds: {basin.total_bounds}")
    print(f"GFM bounds: {gfm_bounds}")
    # Should overlap!
```

### ✅ Value Range Check
Ensure pixel values are interpretable:

```python
import rasterio
import numpy as np

with rasterio.open("extent__20241215.tif") as src:
    data = src.read(1)
    unique_vals = np.unique(data)
    print(f"Unique values: {unique_vals}")
    
# Expected patterns:
# - Binary: [0, 1] or [0, 255] (0=no water, 1 or 255=water)
# - Classified: [0, 1, 2, ...] (0=no water, 1+=water classes)
# - NoData: Often -9999, 255, or 0 (check metadata)
```

---

## Common Data Issues & Fixes

### Issue: "CRS not EPSG:4326"
**Fix**: Reproject using `gdalwarp`:
```bash
gdalwarp -t_srs EPSG:4326 input.tif output_4326.tif
```

Or in Python:
```python
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling

with rasterio.open("input.tif") as src:
    transform, width, height = calculate_default_transform(
        src.crs, 'EPSG:4326', src.width, src.height, *src.bounds)
    kwargs = src.meta.copy()
    kwargs.update({'crs': 'EPSG:4326', 'transform': transform, 'width': width, 'height': height})
    
    with rasterio.open("output_4326.tif", 'w', **kwargs) as dst:
        reproject(source=rasterio.band(src, 1), destination=rasterio.band(dst, 1),
                  src_transform=src.transform, src_crs=src.crs,
                  dst_transform=transform, dst_crs='EPSG:4326',
                  resampling=Resampling.nearest)
```

### Issue: "Multi-band file (RGB image)"
**Fix**: Extract single band:
```bash
gdal_translate -b 1 rgb_input.tif single_band_output.tif
```

### Issue: "Continuous values (0-255 intensity)"
**Fix**: Threshold to binary:
```python
import rasterio
import numpy as np

with rasterio.open("input.tif") as src:
    data = src.read(1)
    binary = (data > 128).astype(np.uint8)  # Threshold at 128
    
    with rasterio.open("output_binary.tif", 'w', **src.meta) as dst:
        dst.write(binary, 1)
```

### Issue: "File names don't include dates"
**Fix**: Rename files with dates:
```bash
# If you know the dates, rename manually
mv flood_map_event1.tif extent__20241215.tif
mv flood_map_event2.tif extent__20241220.tif
```

Or with Python:
```python
from pathlib import Path
import shutil

# Manual date mapping
date_mapping = {
    "flood_map_event1.tif": "20241215",
    "flood_map_event2.tif": "20241220"
}

for old_name, date in date_mapping.items():
    old_path = Path("data/raw/glofas/GFM") / old_name
    new_path = Path("data/raw/glofas/GFM") / f"extent__{date}.tif"
    shutil.move(old_path, new_path)
```

---

## Notebook 03 Configuration

Once GFM data is prepared, configure Notebook 03:

**Cell 6** - Set path:
```python
GFM_VALIDATION_ROOT = Path("data/raw/glofas/GFM")  # Your GFM directory
```

**Cell 11** - Declustering settings:
```python
DECLUSTER_GAP_DAYS = 5  # Group dates within 5 days as same episode
```

**Expected behavior**:
- Notebook 03 will automatically discover all GFM files
- Parse dates from filenames
- Group into episodes based on gap threshold
- Report number of episodes and days found

**Example output** (Cell 15):
```
Found 23 GFM files
Parsed 23 dates
Identified 4 flood episodes:
  Episode 1: 2024-12-01 to 2024-12-05 (5 days)
  Episode 2: 2024-12-15 to 2024-12-18 (4 days)
  Episode 3: 2025-01-10 to 2025-01-11 (2 days)
  Episode 4: 2025-02-03 to 2025-02-03 (1 day)
```

---

## Quality Guidelines

For reliable validation results:

| Criterion | Recommendation | Impact if not met |
|-----------|----------------|-------------------|
| **Temporal coverage** | ≥3 flood events (episodes) | Statistical significance low |
| **Spatial coverage** | GFM covers entire basin | Partial validation only |
| **Resolution** | ≤100m pixel size | Coarse validation, less accurate metrics |
| **Accuracy** | Official products (EMS, GloFAS) preferred | Manual digitization has uncertainty |
| **Date precision** | Daily (YYYYMMDD) | Weekly/monthly reduces temporal matching |
| **Completeness** | All major events in calibration period | Biased validation (only evaluates subset) |

**Minimum requirement**: At least **1 flood event** with **≥1 day** of observed extent to run Notebook 03.

---

## Example: Full Workflow

### Step 1: Download GFM
```bash
# Copernicus EMS download (manual via web interface)
# Save files to: data/raw/glofas/GFM/downloaded/
```

### Step 2: Rename & Organize
```bash
cd data/raw/glofas/GFM/downloaded
mv EMSR999_AOI01_DEL_v1_observed_event_a.tif ../extent__20241215.tif
mv EMSR999_AOI01_DEL_v2_observed_event_b.tif ../extent__20241220.tif
```

### Step 3: Verify Format
```python
import rasterio
files = ["extent__20241215.tif", "extent__20241220.tif"]
for f in files:
    with rasterio.open(f"data/raw/glofas/GFM/{f}") as src:
        print(f"{f}: CRS={src.crs}, Shape={src.shape}, Dtype={src.dtypes[0]}")
```

Output should show EPSG:4326, reasonable dimensions (e.g., 3000×2000), and uint8 or int16.

### Step 4: Configure Notebook 03
```python
# Cell 6
GFM_VALIDATION_ROOT = Path("data/raw/glofas/GFM")

# Cell 8 (optional: force specific calibration)
AUTO_DETECT = True  # Or False to manually specify basin_id_input
```

### Step 5: Run Notebook 03
Execute all cells. Check:
- Cell 15: Confirms episodes detected
- Cell 24: Confusion matrix metrics populated (not all NaN)
- Cell 28: Dashboard generated with map & charts

---

## Troubleshooting GFM Data

### "No GFM files found"
- Check `GFM_VALIDATION_ROOT` path is correct
- Verify `.tif` files exist (not `.tiff` or other extensions)
- Use recursive search if files in subdirectories

### "Could not parse dates from filenames"
- Check filename includes `YYYYMMDD` or `YYYY-MM-DD`
- Rename files to match pattern
- See [Troubleshooting](../user-guides/troubleshooting.md#notebook-03-validation-issues)

### "GFM extent doesn't overlap basin"
- Download GFM for correct geographic region
- Check basin boundary is correct in Notebook 1
- Verify CRS matches (both EPSG:4326)

### "All validation metrics are zero"
- Check GFM values are binary (0/1 or 0/255)
- Verify model predicted flood extent (not all zero)
- Ensure dates match between GFM and modeled episodes

---

## References

- **Copernicus EMS**: [https://emergency.copernicus.eu/](https://emergency.copernicus.eu/)
- **GloFAS**: [https://www.globalfloods.eu/](https://www.globalfloods.eu/)
- **GDAL tools**: [https://gdal.org/](https://gdal.org/)
- **Rasterio docs**: [https://rasterio.readthedocs.io/](https://rasterio.readthedocs.io/)

---

## Next Steps

Once GFM data is prepared:
1. Follow [Notebook 3 Validation Guide](../user-guides/notebook03-validation-guide.md)
2. Run validation
3. Review metrics CSV and interactive dashboard
4. Decide whether to deploy model to operations

**Questions?** See [FAQ](FAQ.md) or [Troubleshooting](../user-guides/troubleshooting.md#notebook-03-validation-issues).
