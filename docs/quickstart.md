# Quick Start Guide

Get PhilFlood running in 15 minutes. This guide covers installation, verification, and your first calibration run.

---

## Prerequisites

- Python **3.10+** (recommended **3.11**)
- Basic command-line knowledge
- Access to GloFAS data (for operational use)

> **Windows note (recommended):** install compiled geo/netCDF dependencies via **conda-forge**, then install PhilFlood with `pip install -e . --no-deps` to avoid source builds.

---

## Step 1: Installation

### Option A: Install from source (recommended)

```powershell
# Clone the repository
git clone https://github.com/yourusername/GLOFAS_ImpactFloodForecasting_PHL.git
cd GLOFAS_ImpactFloodForecasting_PHL

# Create and activate environment
mamba create -n PHLFlood -c conda-forge python=3.11 -y
mamba activate PHLFlood

# Install compiled dependencies via conda-forge (prebuilt binaries)
mamba install -c conda-forge -y `
  numpy pandas xarray netcdf4 cftime `
  geopandas rasterio shapely pyproj pyogrio `
  scipy pyyaml python-dateutil

# Install PhilFlood in editable mode WITHOUT re-installing deps via pip
pip install -e . --no-deps

# Optional: development extras (Jupyter, testing, linting)
pip install -e ".[dev]" --no-deps

# Optional: operations extras (scheduler/logging/CLI niceties)
pip install -e ".[ops]" --no-deps
---

## Step 2: Verify Installation

Check that the CLI is available:

```powershell
philflood --help
```

You should see the main help menu with available commands.

---

## Step 3: Validate Example Configuration

Before running anything, validate the example basin configuration:

```powershell
philflood validate ops/configs/basins/example_basin.yaml
```
**Expected output:** You'll see warnings about placeholder values. This is normal! The example config is a template that needs calibration data.

---

## Step 4: Set Up Your First Basin

### 4.1 Copy the Example Template

```powershell
# Create a new basin config from the template
cp ops/configs/basins/example_basin.yaml ops/configs/basins/my_basin.yaml
```

### 4.2 Edit Basic Information

Open [ops/configs/basins/my_basin.yaml](../ops/configs/basins/my_basin.yaml) and update:

```yaml
basin_id: my_basin_name
hydrobasins_id: 123456  # Your actual HydroBasins ID
glofas_point_ids:
  - PHL_12345  # Your GloFAS station ID(s)
data_root: "C:/data/my_basin"  # Path to your data folder
```
Re-validate:
philflood validate ops/configs/basins/my_basin.yaml
---

## Step 5: Run Calibration (Research Phase)

### 5.1 Launch Jupyter for Interactive Calibration

The main calibration notebook is **01_evt_pot_calibration_workflow.ipynb**:

```powershell
jupyter notebook calibration/notebooks/01_evt_pot_calibration_workflow.ipynb
```

### 5.2 Calibration Features

#### Cell-Level Extraction (Optional Advanced Feature)
Instead of using just the pour point (outlet), you can extract discharge from **all GloFAS grid cells within the basin polygon**:

```python
# Add this in Section 1 (after USE_MUNI_AOI):
USE_CELL_EXTRACTION = True   # False = pour point (default), True = all cells
```

**When to use:**
- ✅ Maximum spatial detail needed
- ✅ Multiple discharge estimates per basin  
- ✅ Analyze local vs. outlet variations
- ❌ For quick testing, use default (False)

#### NetCDF Output (Automatic)
The notebook automatically generates `return-period.nc` containing:
- Return periods for each gauge (1, 2, 5, 10, 20, 50, 100, 200, 500 years)
- Discharge (m³/s) at each return period
- Latitude, longitude, and metadata
- CF-compliant format (readable by QGIS, xarray, GIS tools)

### 5.3 Run Through Calibration Sections

The workflow has 49 sections:
- **Sections 1–4**: Configuration and setup
- **Sections 5–8**: Virtual gauge extraction (automated for cell-level)
- **Sections 9–12**: POT threshold selection, GPD fitting, synthetic catalog
- **Section 13**: NetCDF generation (automatic)

### 5.4 Generate Operational Config

After calibration, save parameters to your basin config:

```powershell
# Update your basin YAML with calibrated parameters
python calibration/scripts/generate_basin_config_from_calibration.py \
    --input calibration/output/my_basin_results.yaml \
    --output ops/configs/basins/my_basin.yaml
```

---

## Step 6: Run Operational Monitoring

Once your basin is calibrated, run monitoring:

### Test with Historical Date

```powershell
philflood monitor --date 2024-08-15 --basins ops/configs/basins/my_basin.yaml
```

### Run for Today

```powershell
philflood monitor --basins ops/configs/basins/my_basin.yaml
```

### Monitor Multiple Basins

```powershell
philflood monitor ops/configs/basins/basin1.yaml ops/configs/basins/basin2.yaml
```

### Monitor All Basins in a Folder

```powershell
philflood monitor --basin-dir ops/configs/basins --output results.json
```

---

## Step 7: Understand the Output

Monitoring output shows:

```
🔍 Running monitoring for 1 basin(s) on 2025-12-29

✓ No trigger - my_basin_name
  Probability: 12.5%
  Expected people affected: 45,000

💾 Results saved to results.json
```

**Trigger activated** when:
- Probability of exceeding impact threshold > configured threshold (e.g., 30%)
- Expected people affected > impact threshold (e.g., 100,000)

---

## Common Issues & Solutions

### ❌ "Module not found: philflood"

**Solution:** Make sure you're in the virtual environment and installed with `pip install -e .`

### ❌ "No module named 'climada'"

**Solution:** CLIMADA is optional during development. For full operational use, install it separately:
```powershell
pip install climada
```

### ❌ "Data path does not exist"

**Solution:** Update `data_root` in your basin config to point to an existing directory where your GloFAS data is stored.

### ❌ Validation shows many warnings

**Solution:** This is expected for the example config! Update the parameters after running calibration notebooks.

---

## Next Steps

1. **Add More Basins**: Copy your working config and calibrate additional basins
2. **Schedule Monitoring**: See [Deployment Guide](deployment.md) for automation
3. **Integrate Notifications**: Extend [run_monitoring_once.py](../ops/pipeline/run_monitoring_once.py) to send alerts
4. **Connect to Real Data**: Configure access to GloFAS forecast API

---

## Getting Help

- **Documentation**: See [docs/methods_onepager.md](methods_onepager.md) for methodology
- **Issues**: Report problems via GitHub Issues
- **Questions**: Contact the IBF team

---

## Directory Structure Reminder
Update this with the latest structure. Do it later.
```
📁 GLOFAS_ImpactFloodForecasting_PHL/
├── 📁 calibration/          # Research & calibration (notebooks, scripts)
│   ├── notebooks/           # Interactive EVT fitting, diagnostics
│   └── scripts/             # Batch calibration tools
├── 📁 ops/                  # Operational deployment
│   ├── configs/             # Basin configurations (YAML)
│   └── pipeline/            # Production monitoring scripts
├── 📁 src/philflood/        # Core library (import from here)
│   ├── data/                # Data extraction
│   ├── ev/                  # Extreme value analysis
│   ├── hazard/              # Flood depth mapping
│   ├── impact/              # Population impact calculation
│   ├── ops/                 # Operational utilities
│   └── risk/                # Risk metrics (AEP/OEP)
└── 📁 docs/                 # Documentation
```

---

**You're ready to go!** 🚀
