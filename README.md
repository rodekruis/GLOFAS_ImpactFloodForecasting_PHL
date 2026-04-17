# GLOFAS Philippines Flood Forecasting

> **🎯 v0.3.0 Now Humanized (Feb 2026)**: Calibration Notebook 1 has been redesigned for non-technical operations personnel. Quick Start guide, simplified inputs (4 fields), input validation, and progress checkpoints all built in. See [Phase B Improvements](docs/user-guides/notebook01-calibration-guide.md#whats-new-in-v030) for details.

> **⚠️ Development Status**: This project is in active development (v0.3.0 → v1.0.0). The calibration pipeline and statistical modeling are fully functional. CLIMADA hazard integration and population impact calculations are implemented. See [CHANGELOG.md](CHANGELOG.md) for the full roadmap.

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
│   ├── adapters/            # GRIB extraction (glofas_grib_v4.py + optimized streaming)
│   ├── calibration/         # EVT model fitting and statistical calibration
│   ├── cli.py               # Command-line interface entry point
│   ├── domain/              # Core business logic, dataclasses, YAML config I/O
│   ├── geo/                 # Spatial operations (HydroBASINS, WorldPop)
│   ├── models/              # Statistical and impact models
│   │   ├── ev/             # Extreme value (EVT/POT) models
│   │   └── impact/         # Population impact calculations (partial v0.3)
│   ├── ops/                 # Operational utilities (logging, run_config auto-discovery)
│   ├── pipelines/           # Orchestration (monitoring.py stub — v1.0 target)
│   ├── qc/                  # Quality control checks
│   └── utils/               # Memory management, event detection, path helpers
├── ops/                      # Production configuration and monitoring
│   ├── configs/            # Basin-specific YAML parameters
│   └── pipeline/           # Scheduled monitoring scripts
├── data/                     # Data storage (raw/interim/processed)
├── tests/                    # Smoke tests and test data generation
└── docs/                     # Comprehensive guides
```

For detailed explanation of the module architecture, see [docs/technical/ARCHITECTURE.md](docs/technical/ARCHITECTURE.md).

## Quick Navigation

**For Humanitarian Officers & Operations Teams:**
- 🚀 [Calibrating a new basin?](docs/user-guides/notebook01-calibration-guide.md) – Start here for step-by-step instructions
- 🔍 [Operations dashboard guide](docs/user-guides/notebook02-hazard-guide.md) – How to generate hazard maps
- ✅ [Validation & QC guide](docs/user-guides/notebook03-validation-guide.md) – Quality control checklist
- ❓ [FAQ & Troubleshooting](docs/getting-started/FAQ.md) – Common issues and solutions

**For Technical Teams & Developers:**
- 📖 [Full Documentation Hub](docs/README.md) – Navigation by role, reading order, all guides
- 🚀 [Setup & Installation](docs/getting-started/quickstart.md) – Dev environment setup (15 minutes)
- 🔨 [Contributing Guide](docs/contributing/CONTRIBUTING.md) – Development workflow and code standards
- 🔧 [Architecture & Design](docs/technical/ARCHITECTURE.md) – System design and module structure
- 📊 [Methods & Theory](docs/technical/methods-overview.md) – EVT approach, data flow, references
- ⚙️ [Deployment Guide](docs/operations/deployment.md) – Production setup and scheduling

## How to Contribute

Contributions are welcome! See [Contributing Guide](docs/contributing/CONTRIBUTING.md) for development workflow, code standards, and testing requirements.

**Ways to contribute:**
1. **Add new basins**: Follow calibration notebook workflow to add basin configurations
2. **Improve statistical methods**: Refine EVT threshold selection and diagnostic tools
3. **Extend data sources**: Add new adapters for alternative forecast systems
4. **Documentation**: Clarify methodology, add examples, or improve guides
5. **Bug reports & ideas**: Open GitHub issues for bugs or feature requests

## Installation

```bash
git clone https://github.com/rodekruis/GLOFAS_ImpactFloodForecasting_PHL.git
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
| `climada` | ≥3.0.0 | Flood hazard modeling, centroids, impact calculation (v1.0: full integration) |
| `climada-petals` | ≥1.0.0 | Regridding and flood depth interpolation (v1.0: full integration) |
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
- See [Methods Overview](docs/technical/methods-overview.md#streaming-grib-extraction-architecture) for details

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

Licensed under GPL-3.0. See [LICENSE](LICENSE) for details.

## Citation

If you use PhilFlood in research or operational settings, please cite:

```
PhilFlood: Open-source early action flood trigger for the Philippines
Repository: https://github.com/rodekruis/GLOFAS_ImpactFloodForecasting_PHL
```


