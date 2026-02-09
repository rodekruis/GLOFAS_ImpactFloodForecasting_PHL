# PhilFlood Documentation Hub

Welcome to the PhilFlood documentation! This hub guides you to the right resources based on your role.

## Quick Navigation

### 🚀 **New Users** → Getting Started Path
1. [Quick Start Guide](getting-started/quickstart.md) - 15-minute installation & first run
2. [FAQ](getting-started/FAQ.md) - Common questions answered
3. [Notebook 1 Calibration Guide](user-guides/notebook01-calibration-guide.md) - Learn how to calibrate your first basin

**Next**: Run Notebook 1 to calibrate a test basin, then check [Notebook 2 Quickstart](user-guides/notebook02-quickstart.md)

---

### 📊 **Practitioners & Data Teams** → User Guides
- [Notebook 1 Calibration Workflow](user-guides/notebook01-calibration-guide.md) - Deep dive into basin calibration
- [Notebook 2 Hazard Analysis](user-guides/notebook02-hazard-guide.md) - Flood depth mapping and CLIMADA integration  
- [Notebook 2 Quickstart](user-guides/notebook02-quickstart.md) - 5-minute quick reference  
- [Troubleshooting Guide](user-guides/troubleshooting.md) - Solutions to common issues
- [FAQ](getting-started/FAQ.md) - Q&A on calibration, data, CLIMADA

---

### 🔧 **Operators & System Admins** → Operations
- [Deployment Guide](operations/deployment.md) - Scheduled monitoring, Docker, cloud deployment
- [Configuration Management](../ops/configs/README.md) - Basin config formats and validation
- [Troubleshooting](user-guides/troubleshooting.md) - Operational issues and solutions

**Typical workflow**: `philflood monitor --basin-dir ops/configs/basins --format json`

---

### 👨‍💻 **Developers** → Contributing & Technical
- [Architecture Overview](technical/ARCHITECTURE.md) - Module organization & data flows
- [Contributing Guide](contributing/CONTRIBUTING.md) - Development setup, PR process, code standards
- [Testing Guide](contributing/TESTING.md) - How to run tests, coverage expectations, test patterns
- [API Reference](technical/api-reference/index.md) - Public module documentation
- [Methods & Theory](technical/methods-overview.md) - Statistical foundations (EVT, POT, GPD)
- [Glossary](technical/GLOSSARY.md) - Technical term definitions

**Getting started**: See [CONTRIBUTING.md](contributing/CONTRIBUTING.md#development-setup)

---

## Documentation Structure

```
docs/
├── README.md (you are here)           # Documentation hub
│
├── getting-started/                   # For new users
│   ├── quickstart.md                  # 15-min setup guide
│   └── FAQ.md                         # Frequently asked questions
│
├── user-guides/                       # For practitioners
│   ├── notebook01-calibration-guide.md
│   ├── notebook02-hazard-guide.md
│   ├── notebook02-quickstart.md
│   └── troubleshooting.md
│
├── operations/                        # For operators
│   ├── deployment.md                  # Scheduling, Docker, cloud
│   └── README.md                      # Operations overview
│
├── technical/                         # For developers
│   ├── ARCHITECTURE.md                # Module design
│   ├── methods-overview.md            # Statistical approach
│   ├── notebook02-refactoring.md      # Notebook 2 design
│   ├── notebook02-section4-optimization.md  # Performance tuning
│   ├── GLOSSARY.md                    # Technical terms
│   └── api-reference/                 # Code API docs
│       └── index.md
│
├── contributing/                      # For contributors
│   ├── CONTRIBUTING.md                # Code standards, PR process
│   └── TESTING.md                     # Testing procedures
│
└── archive/                           # Historical docs
```

---

## Key Concepts at a Glance

### What PhilFlood Does
- **Calibrates** Extreme Value statistics from 47 years of GloFAS discharge data
- **Converts** discharge forecasts to flood impacts (people affected)
- **Issues** automated trigger alerts when probability exceeds threshold

### Data Flow
```
Historical Discharge (GRIB) 
    ↓ [Notebook 1: EVT Calibration]
Fitted Parameters (YAML)
    ↓ [Monitoring: Daily]
Forecast Discharge Ensemble
    ↓ [Inference: Apply GPD]
Impact Probability Distribution
    ↓ [Decision Logic]
Trigger Alert (JSON)
```

### Three Main Workflows

#### 1. **Calibration** (Offline, Research)
**Where**: Notebook 1 (`calibration/notebooks/01_evt_pot_calibration_workflow.ipynb`)

**What you do**:
- Select a basin or municipalities
- Configure GloFAS stations
- Run Notebook 1 to calibrate EVT parameters
- Review diagnostic plots (mean residual life, parameter stability)

**Output**: Calibrated YAML config with threshold, GPD shape/scale, etc.

**Time**: ~2-3 hours per basin

#### 2. **Hazard Analysis** (Optional, Research)
**Where**: Notebook 2 (`calibration/notebooks/02_HazardOnly_Workflow_v2.ipynb`)

**What you do**:
- Download JRC global flood depth maps  
- Regrid to your basin
- Interpolate depth at forecast return periods
- Create CLIMADA flood hazard object

**Output**: HDF5 hazard file + visualizations

**Time**: ~20-30 mins (mostly tile download)

#### 3. **Operational Monitoring** (Online, Production)
**Where**: CLI command (`philflood monitor`)

**What happens**:
- Daily GloFAS forecast ingested
- GPD converts discharge → return period
- Probability assessment (will impacts exceed threshold?)
- Automatic trigger decision
- Results saved as JSON/CSV

**Output**: Trigger alerts

**Frequency**: Daily (configurable)

---

## Common Tasks

### "I want to set up flood monitoring for a new basin"
1. Have historical GloFAS data ready (download from CDS)
2. Know the basin geometry (HydroBASINS ID or shapefiles)
3. Follow [Quick Start Guide](getting-started/quickstart.md)
4. Run Notebook 1 with your basin using [Calibration Guide](user-guides/notebook01-calibration-guide.md)
5. Deploy using [Deployment Guide](operations/deployment.md)

**Est. time**: 4-6 hours (including notebook running)

### "I want to understand how PhilFlood works scientifically"
1. Read [Methods Overview](technical/methods-overview.md) for EVT approach
2. Review [ARCHITECTURE.md](technical/ARCHITECTURE.md) for system design
3. Check [GLOSSARY.md](technical/GLOSSARY.md) for technical terms
4. Study Notebook 1 markdown cells for hands-on examples

### "I want to modify the EVT calibration or add a new data source"
1. Fork the GitHub repo
2. Follow [CONTRIBUTING.md](contributing/CONTRIBUTING.md) setup
3. Read [ARCHITECTURE.md](technical/ARCHITECTURE.md) for where to add code
4. Add tests (see [TESTING.md](contributing/TESTING.md))
5. Submit Pull Request

### "Monitoring failed with an error"
1. Check [Troubleshooting Guide](user-guides/troubleshooting.md) for common issues
2. Verify basin configs: `philflood validate --basin-dir ops/configs/basins`
3. Check logs for detailed error messages
4. Search [FAQ](getting-started/FAQ.md) for your specific issue

---

## By Topic

### Installation & Getting Started
- [Quick Start Guide](getting-started/quickstart.md) - Installation steps
- [FAQ Installation Section](getting-started/FAQ.md#installation--setup) - Common setup issues
- [Troubleshooting](user-guides/troubleshooting.md#installation-issues) - Detailed fixes

### EVT & Calibration
- [Methods Overview](technical/methods-overview.md) - POT, GPD, return periods
- [Notebook 1 Guide](user-guides/notebook01-calibration-guide.md) - Walkthrough
- [GLOSSARY](technical/GLOSSARY.md) - EVT, POT, GPD, Bootstrap definitions

### CLIMADA & Hazard
- [Notebook 2 Guide](user-guides/notebook02-hazard-guide.md) - Detailed explanation
- [Notebook 2 Refactoring](technical/notebook02-refactoring.md) - Mode detection
- [Section 4 Optimization](technical/notebook02-section4-optimization.md) - Performance tuning
- [Methods Overview - CLIMADA section](technical/methods-overview.md#return-period-to-hazard-integration-climada)

### Operational Deployment
- [Deployment Guide](operations/deployment.md) - All scheduling options
- [FAQ Operational Section](getting-started/FAQ.md#operational-monitoring) - Monitoring questions
- [Troubleshooting - Operations](user-guides/troubleshooting.md#operational-monitoring-issues) - Running issues

### Development & Contributing
- [Contributing Guide](contributing/CONTRIBUTING.md) - Full development workflow
- [Testing Guide](contributing/TESTING.md) - Test standards and patterns
- [Architecture](technical/ARCHITECTURE.md) - Module organization

---

## Recommended Reading Order

### For New Users
1. [Quick Start](getting-started/quickstart.md) (15 min)
2. [Methods Overview](technical/methods-overview.md) (20 min)
3. [Notebook 1 Guide](user-guides/notebook01-calibration-guide.md) (30 min)
4. Run Notebook 1 (2-3 hours)
5. [Notebook 2 Quickstart](user-guides/notebook02-quickstart.md) (5 min)

### For Operators
1. [Deployment Guide](operations/deployment.md) (20 min)
2. [Troubleshooting](user-guides/troubleshooting.md) (15 min)
3. Review [ops/configs/](../../ops/configs/README.md) examples (10 min)
4. Set up scheduling (30 min)

### For Developers
1. [Architecture](technical/ARCHITECTURE.md) (30 min)
2. [Contributing Guide](contributing/CONTRIBUTING.md) (15 min)
3. [Testing Guide](contributing/TESTING.md) (15 min)
4. Review `src/philflood/` code structure (30 min)
5. Run test suite locally: `pytest tests/ -v`

---

## Documentation Conventions

**✅ Links that work**:
- Relative paths: `[FAQ](getting-started/FAQ.md)`
- Links in docs dir to technical: `[ARCHITECTURE](technical/ARCHITECTURE.md)`
- Links in user guides to docs: `[Methods](../technical/methods-overview.md)`

**📌 Code blocks**: Use `bash` for shell commands, `python` for code

**🔗 Cross-references**: Link from one doc to related content

**📋 Lists**: Use bullet lists for options, numbered for procedures

---

## Version & Status

**Current Version**: v0.3.0 (February 2026)

**Status**:
- ✅ EVT calibration (Notebook 1) - Fully functional
- ✅ GloFAS  GRIB streaming - Fully optimized
- ✅ CLIMADA hazard integration (Notebook 2) - Working
- 🟡 Population impact modeling - Planned for v1.0
- 🟡 REST API - Planned for v1.0
- 🟡 Web dashboard - Planned for v2.0

See [CHANGELOG](../../CHANGELOG.md) for detailed roadmap.

---

## Getting Help

| Question Type | Where to Ask |
|---|---|
| Installation issues | [FAQ](getting-started/FAQ.md#installation--setup) → [Troubleshooting](user-guides/troubleshooting.md) |
| How do I...? | [FAQ](getting-started/FAQ.md)  |
| Common error message | [Troubleshooting Guide](user-guides/troubleshooting.md#troubleshooting-common-errors) |
| Scientific method question | [Methods Overview](technical/methods-overview.md) + [Glossary](technical/GLOSSARY.md) |
| Code structure question | [Architecture](technical/ARCHITECTURE.md) |
| Bug or feature request | [GitHub Issues](https://github.com/rodekruis/GLOFAS_ImpactFloodForecasting_PHL/issues) |
| Want to contribute | [Contributing Guide](contributing/CONTRIBUTING.md) |

---

## About PhilFlood

**Project**: Open-source early action flood trigger for the Philippines  
**Organization**: Red Cross Red Crescent Climate Centre (RCCC) - IBF Philippines  
**License**: GPL-3.0  
**Repository**: [github.com/rodekruis/GLOFAS_ImpactFloodForecasting_PHL](https://github.com/rodekruis/GLOFAS_ImpactFloodForecasting_PHL)

**Citation**:
```
PhilFlood: Open-source early action flood trigger for the Philippines
Repository: https://github.com/rodekruis/GLOFAS_ImpactFloodForecasting_PHL
```

---

**Last Updated**: February 2026 (v0.3.0)  
**Maintained By**: IBF Philippines Team

---

## Summary of Changes in This Documentation Restructure

**Deleted** (completed milestones, now archived):
- `IMPLEMENTATION_COMPLETE.md`
- `IMPLEMENTATION_STATUS.md`

**Moved & Reorganized**:
- `quickstart.md` → `getting-started/quickstart.md`
- `NOTEBOOK2_QUICKSTART.md` → `user-guides/notebook02-quickstart.md`
- `deployment.md` → `operations/deployment.md`
- `ARCHITECTURE.md` → `technical/ARCHITECTURE.md`
- `NOTEBOOK2_REFACTORING_SUMMARY.md` → `technical/notebook02-refactoring.md`
- `IMPLEMENTATION_NOTES.md` → `technical/notebook02-section4-optimization.md`
- `methods_onepager.md` + `quick_reference_pot_climada.txt` → `technical/methods-overview.md`

**Created New**:
- `docs/README.md` (this file) - Documentation hub
- `docs/getting-started/FAQ.md` - Frequently asked questions
- `docs/technical/GLOSSARY.md` - Technical term definitions
- `docs/user-guides/troubleshooting.md` - Issue solutions
- `docs/user-guides/notebook01-calibration-guide.md` - Calibration walkthrough
- `docs/user-guides/notebook02-hazard-guide.md` - Hazard modeling guide
- `docs/technical/api-reference/index.md` - API documentation
- `docs/contributing/CONTRIBUTING.md` - Development guidelines
- `docs/contributing/TESTING.md` - Testing procedures

**Benefit**: ~10 organized docs in clear paths, replacing 12 scattered files. Clear navigation for new users, operators, and developers.
