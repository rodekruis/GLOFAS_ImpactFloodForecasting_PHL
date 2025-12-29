# Philippines Flood Trigger Project

Welcome! This repository contains all of the code, data templates and documentation needed to develop an open‑source early action flood trigger for the Philippines.

## 🚀 Quick Start

**New to PhilFlood?** See the [QuickStart Guide](docs/quickstart.md) for step-by-step installation and setup instructions.

**Ready to deploy?** Check the [Deployment Guide](docs/deployment.md) for production deployment options.

---

## Structure

The project is divided into two clearly defined layers:

1. **Calibration (`calibration/`)** – notebooks and scripts used to explore, test and calibrate the models. This is the *playground* where most of the development is happening; it contains exploratory notebooks for fitting extreme value theory (EVT) models, tuning hazard/impact assumptions and assessing risk metrics. Outputs from calibration (e.g. fitted parameters, selected thresholds, vulnerability settings) are written into machine‑readable YAML files under `ops/configs/`, together with human‑readable calibration reports in `docs/`.

2. **Operations (`ops/`)** – a lean, reproducible pipeline that reads the pre‑calibrated configuration and uses it to monitor real‑time forecasts and issue trigger decisions. The operational code never re‑fits statistical models; it simply applies the calibrated parameters to new forecast data.

All reusable code lives in `src/philflood/`, which is organised by functional domain. Calibration notebooks and operational scripts import from this package. By keeping code in a package rather than in notebooks, we avoid duplication when scaling up to multiple basins or countries.

---

## Installation

### Quick Install

```powershell
git clone https://github.com/yourusername/GLOFAS_ImpactFloodForecasting_PHL.git
cd GLOFAS_ImpactFloodForecasting_PHL

mamba create -n PHLFlood -c conda-forge python=3.11 -y
mamba activate PHLFlood

mamba install -c conda-forge -y `
  numpy pandas xarray netcdf4 cftime `
  geopandas rasterio shapely pyproj pyogrio `
  scipy pyyaml python-dateutil

pip install -e . --no-deps
### Installation Options

- **Development** (includes Jupyter): `pip install -e ".[dev]"`
- **Operations only** (minimal): `pip install -e ".[ops]"`
- **Requirements only**: `pip install -r requirements.txt`

**Verify installation:**
```powershell
philflood --help
```

---

## Getting Started

### 1. Validate Your Setup

```powershell
# Check that example config loads
philflood validate --basins ops/configs/basins/example_basin.yaml

# Run smoke tests
python tests/test_smoke.py
```

### 2. Explore Calibration Notebooks

Open Jupyter and work through the calibration notebooks under `calibration/notebooks/`. Each notebook focuses on one step of the modelling pipeline and includes rich markdown explanations aimed at humanitarian practitioners:

   * `01_evt_threshold_basin_X.ipynb` – shows how to load a GloFAS time series, explore the extremes, and choose an appropriate POT threshold using diagnostic plots.
   * `02_evt_threshold_basin_X_gpd_fit.ipynb` – fits a Generalised Pareto Distribution to the peaks over threshold, evaluates the fit and summarises the results.
   * `10_synthetic_impacts_AEP_OEP.ipynb` – demonstrates how to generate synthetic events, convert them into flood impacts using CLIMADA and compute AEP/OEP/AAPA curves.

```powershell
# Launch Jupyter
jupyter notebook calibration/notebooks/
```

### 3. Generate Basin Configuration

After calibration, save your parameters to a basin config:

```powershell
python calibration/scripts/generate_basin_config_from_calibration.py \
    --input calibration/output/my_basin_calibration.yaml \
    --output ops/configs/basins/my_basin.yaml

# Validate before deployment
philflood validate --basins ops/configs/basins/my_basin.yaml
```

### 4. Run Operational Monitoring

#### Using the CLI (Recommended)

```powershell
# Monitor all basins for today
philflood monitor --basin-dir ops/configs/basins

# Monitor specific basin for a date
philflood monitor --date 2025-12-29 --basins ops/configs/basins/agusan.yaml

# Save results to JSON
philflood monitor --basin-dir ops/configs/basins --output results.json --format json
```

#### Using Direct Script

```powershell
python ops/pipeline/run_monitoring_once.py --date 2025-12-29 \
    --basins ops/configs/basins/example_basin.yaml --output results.csv
```

---

## Command-Line Interface

PhilFlood provides a user-friendly CLI with three main commands:

### `philflood monitor`
Run trigger monitoring for one or more basins.

```powershell
philflood monitor --basin-dir ops/configs/basins --output results.json
philflood monitor --date 2025-12-29 --basins basin1.yaml basin2.yaml
```

### `philflood validate`
Validate basin configurations before deployment.

```powershell
philflood validate --basins ops/configs/basins/*.yaml
philflood validate --basin-dir ops/configs/basins
```

### `philflood calibrate`
Run EVT calibration diagnostics.

```powershell
philflood calibrate --basin ops/configs/basins/example.yaml \
    --start 1980-01-01 --end 2020-12-31
```

---

## Documentation

- **[QuickStart Guide](docs/quickstart.md)** - Installation and first run (15 minutes)
- **[Methods Overview](docs/methods_onepager.md)** - Scientific methodology
- **[Deployment Guide](docs/deployment.md)** - Production deployment (Docker, Cloud, Scheduling)
- **[Architecture Improvements](docs/architecture_improvements.md)** - Recent enhancements

---

## Project Structure
Also update this later. TODO
```
📁 GLOFAS_ImpactFloodForecasting_PHL/
├── 📄 setup.py                      # Package installation
├── 📄 requirements*.txt             # Dependencies (base, dev, ops)
├── 📁 calibration/                  # Research & model fitting
│   ├── 📁 notebooks/                # Interactive calibration notebooks
│   └── 📁 scripts/                  # Batch calibration tools
├── 📁 ops/                          # Operational deployment
│   ├── 📁 configs/                  # Basin configurations (YAML)
│   └── 📁 pipeline/                 # Production monitoring scripts
├── 📁 src/philflood/                # Core library
│   ├── 📄 cli.py                    # Command-line interface
│   ├── 📁 data/                     # Data extraction (GloFAS, hazard)
│   ├── 📁 ev/                       # Extreme value analysis (GPD, POT)
│   ├── 📁 hazard/                   # Flood depth mapping (CLIMADA)
│   ├── 📁 impact/                   # Population impact calculation
│   ├── 📁 ops/                      # Operational utilities (logging, validation)
│   └── 📁 risk/                     # Risk metrics (AEP/OEP, triggers)
├── 📁 tests/                        # Testing & validation
│   ├── 📄 test_smoke.py             # Installation verification
│   └── 📁 fixtures/                 # Test data generation
└── 📁 docs/                         # Documentation
    ├── 📄 quickstart.md
    ├── 📄 deployment.md
    └── 📄 methods_onepager.md
```

---

## Development & Testing

### Run Tests

```powershell
# Smoke tests (verify installation)
python tests/test_smoke.py

# Generate synthetic test data
python tests/fixtures/generate_test_data.py

# Full test suite (requires pytest)
pytest tests/ -v
```

### Code Quality

```powershell
# Format code
black src/ tests/

# Lint
flake8 src/

# Type checking
mypy src/
```

---

## Contributing

This repository follows common Python best practices. New functions should live in the appropriate module under `src/philflood/` and include docstrings describing inputs, outputs and context. 

### Contribution Guidelines

- **Code**: Add new features in appropriate modules under [src/philflood/](src/philflood/)
- **Documentation**: Update relevant docs when adding features
- **Testing**: Add tests for new functionality
- **Notebooks**: Include markdown explanations for humanitarian practitioners
- **Clarity**: Transparency and reproducibility are paramount

### Before Submitting

1. Validate changes: `python tests/test_smoke.py`
2. Format code: `black src/ tests/`
3. Update documentation if needed
4. Test on clean environment

---

## License

See [LICENSE](LICENSE) file for details.

---

## Contact & Support

- **Issues**: Report bugs via GitHub Issues
- **Questions**: Contact the IBF team
- **Documentation**: See [docs/](docs/) folder

---

**Built for humanitarian impact-based forecasting** 🌊🚨

