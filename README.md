# GLOFAS Philippines Flood Forecasting

An open-source early action flood trigger system for the Philippines using Global Flood Awareness System (GloFAS) forecasts and Extreme Value Theory (EVT) statistical modeling.

## What This Project Does

PhilFlood combines real-time GloFAS ensemble discharge forecasts with calibrated extreme value statistics to provide automated, evidence-based flood trigger decisions. The system:

- **Processes historical GloFAS discharge data** (1979-2025, 47 years) using streaming GRIB extraction to identify extreme flood events
- **Fits statistical models** using Generalized Pareto Distribution (GPD) to quantify flood frequency and magnitude
- **Converts discharge forecasts to flood impacts** using depth-to-population models, generating probability distributions of affected people
- **Issues triggers** when forecast impacts exceed pre-defined thresholds, enabling early action

## Key Features

### 🏗️ Streaming Extraction Architecture
- **Memory-efficient processing** of large multi-decade GRIB datasets (94% memory reduction vs. legacy approach)
- **Year-by-year streaming** with checkpoint/resume capability
- Processes 47 years of global GloFAS data without exceeding 100 MB RAM peak

### 📊 Calibration Pipeline
- Interactive Jupyter notebooks guide practitioners through EVT model fitting
- Diagnostic plots (mean residual life, parameter stability) for threshold selection
- Synthetic event generation for impact modeling and risk profiling
- All parameters stored in machine-readable YAML configuration

### ⚡ Production Operations
- Lean, reproducible monitoring pipeline using pre-calibrated parameters
- CLI interface (`philflood` command) for single-basin or batch processing
- JSON/CSV output formats for integration with existing early warning systems
- No re-fitting in operations—applies fixed calibrated thresholds

### 🔍 Data Transparency
- Comprehensive logging of all data processing steps
- Per-gauge extraction statistics showing exactly what data was used
- ⚠️ Loud warnings when invalid dates or data loss detected
- Full accounting of records: what was processed, what was dropped, why

## Directory Structure

```
GLOFAS_ImpactFloodForecasting_PHL/
├── calibration/               # Model development and tuning
│   ├── notebooks/            # Interactive EVT calibration workflow
│   └── scripts/              # Batch calibration and config generation
├── src/philflood/            # Reusable package code
│   ├── adapters/            # GRIB extraction, data loading
│   ├── calibration/         # EVT model fitting
│   ├── ops/                 # Operational monitoring and validation
│   └── utils/               # Memory management, logging
├── ops/                      # Production configuration and monitoring
│   ├── configs/            # Basin-specific YAML parameters
│   └── pipeline/           # Scheduled monitoring scripts
├── data/                     # Data storage (raw/interim/processed)
├── tests/                    # Smoke tests and test data generation
└── docs/                     # Comprehensive guides
```

## Quick Links

- **Getting Started**: [Quickstart Guide](docs/quickstart.md) – Installation and first run (15 minutes)
- **Production Deployment**: [Deployment Guide](docs/deployment.md) – Scheduled monitoring, Docker, cloud options
- **Methods & Theory**: [Methods Overview](docs/methods_onepager.md) – EVT approach, data flow, references

## How to Contribute

1. **Calibration improvements**: Add new basins or refine EVT threshold selection in `calibration/notebooks/`
2. **New data sources**: Extend adapters in `src/philflood/adapters/` for alternative forecast systems
3. **Operational enhancements**: Improve monitoring logic in `src/philflood/ops/`
4. **Documentation**: Clarify methodology or add deployment examples in `docs/`

Please ensure all contributions:
- Include unit tests in `tests/`
- Follow the existing code structure (separate calibration and operations layers)
- Update relevant YAML configs and documentation
- Are validated with `philflood validate` before submission

## Installation

```bash
git clone https://github.com/yourusername/GLOFAS_ImpactFloodForecasting_PHL.git
cd GLOFAS_ImpactFloodForecasting_PHL

# Create conda environment with all dependencies
mamba env create -f environment.yml
mamba activate PHLFlood

# Install as editable package
pip install -e .

# Verify installation
philflood --help
```

### Core Dependencies (Minimal)

PhilFlood requires only **4 core packages** (all others are automatically included):

| Package | Version | Purpose |
|---------|---------|---------|
| `climada` | ≥3.0.0 | Flood hazard modeling, centroids, impact calculation |
| `climada-petals` | ≥1.0.0 | Regridding and flood depth interpolation |
| `ipywidgets` | ≥7.6.0 | Interactive Jupyter notebook diagnostics |
| `pyextremes` | ≥2.3.0 | Extreme Value Theory: POT/GPD calibration |

**Important**: Do NOT manually install numpy, pandas, xarray, scipy, geopandas, or rasterio - these are automatically included by the 4 core packages and version conflicts can occur if installed separately.

Install these versions via `requirements.txt`:
```bash
pip install -r requirements.txt
```

## Troubleshooting

### Memory Issues with Large Datasets

**Problem:** "Memory exceeded" or "Killed" when processing 47+ years of GloFAS GRIB  
**Root Cause:** Attempting to load entire historical dataset into RAM at once  
**Solution:** Use the streaming adapter designed for large datasets
- The system automatically uses memory-efficient streaming extraction
- If manual processing, use `src/philflood/adapters/glofas_grib_v4_optimized.py`
- See [Methods Overview](docs/methods_onepager.md#streaming-grib-extraction-architecture) for details

### Return Period Mismatches (Only 1 of 8 in Output)

**Problem:** Output contains only 1 return period instead of 8  
**Root Cause:** Fixed in v0.3.0 - see [CHANGELOG.md](CHANGELOG.md#030---february-2-2026)  
**Solution:** Using current notebook version automatically applies the fix
- Notebooks handle all 8 return periods simultaneously through event dimension stacking
- No manual action needed if running updated code

### CLIMADA-Petals Data Shape Errors

**Problem:** `petals_regrid()` expecting 3D but got 2D array  
**Root Cause:** Return periods not properly stacked into event dimension before regridding  
**Solution:** Ensure Section 5 of Notebook 02 properly executes event dimension stacking
- Reference implementation: `calibration/notebooks/02_HazardOnly_Workflow_v2.ipynb` Section 5
- See Section 5 markdown: "Stack all return periods before passing to regrid"

### Dataset Incompatibility ("No return_period_* variables")

**Problem:** Script cannot find return period variables  
**Cause:** Potential mismatch between Notebook 01 output naming and Notebook 02 expectations  
**Fix:** Both notebooks now follow consistent naming convention: `return_period_RP{N}yr`
- Verify `return_levels_bootstrap.parquet` exists in `data/processed/calibration/`
- Check output files match naming pattern in notebook comments

### Installation Issues with Requirements

**Important:** Only install the 4 core packages from `requirements.txt`:
- `climada>=3.0.0` - All flood modeling dependencies included
- `climada-petals>=1.0.0` - Regridding and flood depth utilities
- `ipywidgets>=7.6.0` - Interactive notebook features
- `pyextremes>=2.3.0` - EVT and POT calibration

Do NOT manually install numpy, pandas, xarray, etc. - these are automatically included by the above packages and version conflicts can occur.

## License

[License details here]

## Citation

If you use PhilFlood in research or operational settings, please cite:

```
PhilFlood: Open-source early action flood trigger for the Philippines
Repository: https://github.com/yourusername/GLOFAS_ImpactFloodForecasting_PHL
```


