# Quick Start Guide

Get PhilFlood running in 15 minutes. This guide covers installation, verification, and your first calibration run.

---

## Prerequisites

- Python **3.9+** (recommended **3.11**)
- [Mamba](https://mamba.readthedocs.io/) or Conda package manager
- Basic command-line knowledge
- Access to GloFAS data (for operational use)

> **Windows note:** install compiled geo/netCDF dependencies via **conda-forge** (step 1 already does this), then install PhilFlood with `pip install -e . --no-deps` to avoid source builds.

---

## Step 1: Installation

```bash
# Clone the repository
git clone https://github.com/rodekruis/GLOFAS_ImpactFloodForecasting_PHL.git
cd GLOFAS_ImpactFloodForecasting_PHL

# Create conda environment (includes cfgrib, eccodes, geopandas, xarray, etc.)
mamba env create -f environment.yml
mamba activate PHLFlood

# Install PhilFlood and its pip dependencies (climada, climada-petals, pyextremes, ipywidgets)
pip install -e .

# Optional: development extras (Jupyter, testing, linting)
pip install -e ".[dev]"

# Optional: operations extras (scheduler/logging/CLI niceties)
pip install -e ".[ops]"
```

> **macOS note:** all commands above work as-is in macOS Terminal or iTerm2. No additional steps are needed.

---

## Step 2: Verify Installation

Check that the CLI is available:

```bash
philflood --help
```

You should see the main help menu with available commands (`monitor`, `validate`, `calibrate`).

---

## Step 3: Validate Example Configuration

Before running anything, validate the example basin configuration:

```bash
philflood validate ops/configs/basins/example_basin.yaml
```

**Expected output:** You'll see warnings about placeholder values. This is normal — the example config is a template that needs calibration data.

---

## Step 4: Set Up Your First Basin

### 4.1 Copy the Example Template

```bash
cp ops/configs/basins/example_basin.yaml ops/configs/basins/my_basin.yaml
```

### 4.2 Edit Basic Information

Open `ops/configs/basins/my_basin.yaml` and update:

```yaml
basin_id: my_basin_name
hydrobasins_id: 123456  # Your actual HydroBasins ID
glofas_point_ids:
  - PHL_12345  # Your GloFAS station ID(s)
data_root: "/data/my_basin"  # Path to your data folder
```

Re-validate:

```bash
philflood validate ops/configs/basins/my_basin.yaml
```

---

## Step 5: Run Calibration (Research Phase)

### 5.1 Launch Jupyter for Interactive Calibration

The main calibration notebook is **01_evt_pot_calibration_workflow.ipynb**:

```bash
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
- Return periods for each gauge: **1, 10, 20, 50, 75, 100, 200, 500 years** (8 return periods)
- Discharge (m³/s) at each return period
- Latitude, longitude, and metadata
- CF-compliant format (readable by QGIS, xarray, GIS tools)

### 5.3 Run Through Calibration Sections

The workflow is organised into 13 sections:

- **Sections 1–4**: Configuration and setup
- **Sections 5–8**: Virtual gauge extraction (automated for cell-level)
- **Sections 9–11**: POT threshold selection, GPD fitting, bootstrap return levels
- **Section 13**: NetCDF generation (automatic)

> **Note:** Section 12 (Synthetic Catalog) is archived. The current approach uses the formula-based bootstrap in Section 11C, which is faster and more accurate.

### 5.4 Generate Operational Config

After calibration, save parameters to your basin config:

```bash
python calibration/scripts/generate_basin_config_from_calibration.py \
    --input data/processed/calibration/evt_pot_calibration.parquet \
    --output ops/configs/basins/my_basin.yaml
```

---

## Step 6: Run Operational Monitoring

> **⚠️ Development status:** The automated monitoring pipeline (`philflood monitor`) is a planned feature targeting v1.0. Running it currently raises `NotImplementedError`. For now, use the calibration notebooks and `calibration/scripts/run_reforecast_month.py` for operational processing.

Once the monitoring pipeline is implemented, the CLI will work as follows:

### Test with Historical Date

```bash
philflood monitor ops/configs/basins/my_basin.yaml --date 2024-08-15
```

### Run for Today

```bash
philflood monitor ops/configs/basins/my_basin.yaml
```

### Monitor Multiple Basins

```bash
philflood monitor ops/configs/basins/basin1.yaml ops/configs/basins/basin2.yaml
```

### Monitor All Basins in a Folder

```bash
philflood monitor --basin-dir ops/configs/basins --output results.json
```

---

## Step 7: Understand the Output

When monitoring is operational, output will show:

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

```bash
mamba activate PHLFlood
pip install -e .
```

### ❌ "No module named 'cfgrib'" or "No module named 'eccodes'"

**Solution:** These GRIB-reading dependencies should be installed via `environment.yml`. If missing:

```bash
mamba install -c conda-forge cfgrib eccodes
```

### ❌ "No module named 'climada'"

**Solution:** Install via pip (not conda):

```bash
pip install climada climada-petals
```

### ❌ "Data path does not exist"

**Solution:** Update `data_root` in your basin config to point to an existing directory where your GloFAS data is stored.

### ❌ Validation shows many warnings

**Solution:** Expected for the example config — update the parameters after running calibration notebooks.

---

## Step 8: Validate Your Calibration

### Quick Validation Checks

After running the calibration notebook, verify the outputs:

#### Check Section 11C Output (Bootstrap Return Levels)

```python
import pandas as pd

# Load results
df = pd.read_parquet("data/processed/calibration/return_levels_bootstrap.parquet")

# Check one gauge
gauge_data = df[df["virtual_gauge_id"] == df["virtual_gauge_id"].iloc[0]]
for _, row in gauge_data.iterrows():
    T = row["return_period_years"]
    mean = row["mean_m3s"]
    std = row["std_m3s"]
    q05 = row["q05_m3s"]
    q95 = row["q95_m3s"]
    cv = std / mean
    print(
        f"T={T:3.0f}yr: mean={mean:6.1f} m³/s, CV={cv:.3f}, "
        f"q05={q05:6.1f} m³/s, q95={q95:6.1f} m³/s"
    )
```

**Expected:**
- CV (coefficient of variation) between 0.02–0.30 (2–30%)
- Discharge increases with return period
- No NaN values

#### Check Hazard NetCDF Output (from Notebook 02)

```python
import xarray as xr

# Load NetCDF (output of Notebook 02)
ds = xr.open_dataset("data/processed/flood_maps_ev.nc")

# Verify structure
print(f"Return periods: {ds.dims}")
print(f"Variables: {list(ds.data_vars)}")

# Check all 8 return periods are present
assert ds.dims.get("return_period", ds.dims.get("event", 0)) == 8, \
    "Expected 8 return periods: [1, 10, 20, 50, 75, 100, 200, 500 yr]"
print("Hazard NetCDF structure confirmed")
```

**Expected:**
- All 8 return period layers present
- No errors loading with xarray

### Common Validation Issues

**Issue:** Section 11C slow (>5s per gauge)
- Reduce `n_bootstrap` in the notebook call (default 500; 20 is enough for exploratory work)

**Issue:** NetCDF has NaN values
- Verify gauge ID format: `CELL__lat_XX.XX__lon_YY.YY`

**Issue:** Monotonicity failures (<90% passing)
- Check exceedances distribution, inspect failing gauges

---

## Next Steps

1. **Add More Basins**: Copy your working config and calibrate additional basins
2. **Schedule Monitoring**: See [Deployment Guide](../operations/deployment.md) for automation
3. **Integrate Notifications**: Extend [run_monitoring_once.py](../../ops/pipeline/run_monitoring_once.py) to send alerts
4. **Connect to Real Data**: Configure access to GloFAS forecast API

---

## Getting Help

- **Documentation**: See [Methods Overview](../technical/methods-overview.md) for methodology
- **Issues**: Report problems via [GitHub Issues](https://github.com/rodekruis/GLOFAS_ImpactFloodForecasting_PHL/issues)
- **Questions**: Contact the IBF team

---

## Directory Structure Reference

For a complete view of the codebase organisation, see the [main README](../../README.md#directory-structure). Key directories for this quickstart:

- **`calibration/notebooks/`** — Interactive EVT calibration workflows
- **`src/philflood/calibration/`** — Statistical model fitting code
- **`src/philflood/models/ev/`** — Extreme value theory models
- **`ops/configs/basins/`** — Basin-specific configuration files
- **`data/processed/calibration/`** — Calibration outputs

For architecture details, see [ARCHITECTURE.md](../technical/ARCHITECTURE.md).

---

**You're ready to go!**
