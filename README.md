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

## License

[License details here]

## Citation

If you use PhilFlood in research or operational settings, please cite:

```
PhilFlood: Open-source early action flood trigger for the Philippines
Repository: https://github.com/yourusername/GLOFAS_ImpactFloodForecasting_PHL
```

