# PhilFlood Documentation Hub

Welcome to the PhilFlood documentation! This hub guides you to the right resources based on your role.

## Quick Navigation

### 🚀 **New Users** → Getting Started Path
1. [Quick Start Guide](getting-started/quickstart.md) - 15-minute installation & first run
2. [FAQ](getting-started/FAQ.md) - Common questions answered
3. [Notebook 1 Calibration Guide](user-guides/notebook01-calibration-guide.md) - Learn how to calibrate your first basin

**Next**: Run Notebook 1 to calibrate a test basin, then work through NB02–NB05 for the full pipeline.

---

### 📊 **Practitioners & Data Teams** → User Guides

**Calibration pipeline (run in order):**
- [Notebook 1 — EVT Calibration](user-guides/notebook01-calibration-guide.md) - Deep dive into basin calibration
- [Notebook 2 — Hazard Maps](user-guides/notebook02-hazard-guide.md) - Flood depth mapping and CLIMADA integration (includes quick-start and mode detection)
- [Notebook 3 — Validation & QA](user-guides/notebook03-validation-guide.md) - Validate calibration against observations, interactive dashboard

**Impact & risk pipeline (run in order, after NB03):**
- [Notebook 4 — Impact Catalogue](#notebook-4-impact-catalogue) - see inline notes below
- [Notebook 5 — Risk Profiles](#notebook-5-risk-profiles) - see inline notes below
- [Notebook 6 — Event Viewer](#notebook-6-event-viewer) - see inline notes below
- [Notebook 7 — Trigger Validation](#notebook-7-trigger-validation) - see inline notes below

**Reference:**
- [Troubleshooting Guide](user-guides/troubleshooting.md) - Solutions to common issues
- [FAQ](getting-started/FAQ.md) - Q&A on calibration, data, CLIMADA

---

### 🔧 **Operators & System Admins** → Operations
- [Deployment Guide](operations/deployment.md) - **Not yet implemented** — placeholder for when `run_monitoring()` is built
- [Trigger Pipeline Handover](operations/trigger-pipeline-handover.md) - Architecture, reusable modules, and implementation checklist for automating the trigger
- [Troubleshooting](user-guides/troubleshooting.md) - Operational issues and solutions

**Typical workflow**: `philflood monitor --basin-dir ops/configs/basins --format json`

---

### 👨‍💻 **Developers** → Contributing & Technical
- [Architecture Overview](technical/ARCHITECTURE.md) - Module organization & data flows (up-to-date)
- [Contributing Guide](contributing/CONTRIBUTING.md) - Development setup, PR process, code standards
- [Testing Guide](contributing/TESTING.md) - How to run tests, coverage expectations, test patterns
- [API Reference](technical/api-reference/index.md) - Public module documentation
- [Ops Config Reference](technical/ops-config-reference.md) - `load_run_config()` usage and auto-discovery
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
│   ├── notebook02-hazard-guide.md     # Includes quick-start and mode detection
│   ├── notebook03-validation-guide.md
│   └── troubleshooting.md
│
├── operations/                        # For operators
│   ├── deployment.md                  # Placeholder — not yet implemented
│   └── trigger-pipeline-handover.md  # Trigger automation guide
│
├── technical/                         # For developers
│   ├── ARCHITECTURE.md                # Module design (current)
│   ├── methods-overview.md            # Statistical approach
│   ├── notebook02-section4-optimization.md  # NB02 performance tuning
│   ├── ops-config-reference.md        # load_run_config() usage and auto-discovery
│   ├── GLOSSARY.md                    # Technical terms
│   └── api-reference/                 # Code API docs
│       └── index.md
│
└── contributing/                      # For contributors
    ├── CONTRIBUTING.md                # Code standards, PR process
    └── TESTING.md                     # Testing procedures
```

---

## Key Concepts at a Glance

### What PhilFlood Does
- **Calibrates** Extreme Value statistics from 47 years of GloFAS discharge data
- **Converts** discharge forecasts to flood impacts (people affected)
- **Issues** automated trigger alerts when probability exceeds threshold

### Full Notebook Pipeline

| Notebook | Purpose | Key output |
|---|---|---|
| NB00 | Download GloFAS GRIB from ECMWF | Raw GRIB files |
| NB01 | EVT/POT calibration per GloFAS cell | `evt_pot_calibration.parquet` + `run_config.json` |
| NB02 | Generate flood depth hazard maps | Flood depth TIFFs per return period |
| NB03 | Validate NB02 maps vs. observed floods | F1 / IoU / Precision / Recall |
| NB04 | Build impact event catalogue; fit EVT2 | `event_registry_hist.parquet` + EVT2 fit JSONs |
| NB05 | 10,000-year YLT → AEP/OEP curves | `watershed_oep_curve.json` + Excel workbook |
| NB06 | Interactive event viewer for stakeholders | HTML dashboard |
| NB07 | Evaluate trigger performance vs. reforecast | Trigger ROC stats |

**Execution order**: NB01 → NB02 → NB03 → NB04 → NB05 → NB06. NB07 can run after NB05.

All notebooks auto-detect the latest NB01 output via `philflood.ops.config.load_run_config()`.

### Notebook 4 — Impact Catalogue
`calibration/notebooks/04_ImpactCatalogue_ImpactEVT_CATMODEL_10000y_UPDATED.ipynb`

- Detects historical flood events from discharge (connected-component analysis)
- Intersects flood depth TIFFs with WorldPop to compute PopAffected at 11 depth thresholds (0.01–1.0 m)
- Fits EVT2 (spliced empirical + POT-GPD) on impact series; primary threshold: `DEPTH_PRIMARY = 0.02 m`
- Processes reforecast ensemble (2005–present) with same multi-threshold pipeline

**Key outputs** (in `data/processed/impact_catalogue_catmodel/{BASIN_ID}/{RUN_TAG}/`):
- `evt2/evt2_fit_manifest.json` — status for all 11 thresholds
- `evt2/evt2_fit_depth_{N}mm.json` — per-threshold EVT2 parameters
- `evt2/evt2_fit_popaffected_op.json` — backward-compat alias (primary threshold)
- `event_registry_hist.parquet` — historical events with PopAffected columns

### Notebook 5 — Risk Profiles
`calibration/notebooks/05_Risk_Profiles_IMPROVED_UPDATED_EPMatrix copy.ipynb`

- 10,000-year YLT simulation → AEP/OEP exceedance curves per municipality/province/watershed
- `IMPACT_DEPTH_THR_M = 0.2` controls which EVT2 fit and PopAffected column to use (humanitarian standard)
- Multi-threshold OEP comparison available (`MULTI_THR_ENABLED=True`)

**Required export for NB06**: `data/processed/Riskprofiles/watershed_oep_curve.json`

### Notebook 6 — Event Viewer
`calibration/notebooks/06_flood_event_viewer.ipynb`

- Interactive HTML dashboard for non-technical stakeholders
- Classifies event severity using NB05 OEP curve (not raw EVT2 formula)
- Requires NB05 to have run first (`watershed_oep_curve.json` hard dependency)

### Notebook 7 — Trigger Validation
`calibration/notebooks/07_Trigger_Validation_Reforecast.ipynb`

- Evaluates trigger performance against reforecast ensemble (skill / ROC analysis)
- Reads NB01 EVT1 fits + NB05 OEP curve
- Detection parameters: `T0_YEARS=2.0`, `A_MIN_KM2=100.0`, `DEPTH_THRESHOLD_M=0.02`

**For automation**: This notebook is the reference implementation for `run_monitoring()`. See [Trigger Pipeline Handover](operations/trigger-pipeline-handover.md) for the handover doc.

---

## Common Tasks

### "I want to set up flood monitoring for a new basin"
1. Have historical GloFAS data ready (download from CDS using NB00)
2. Know the basin geometry (HydroBASINS ID or shapefiles)
3. Follow [Quick Start Guide](getting-started/quickstart.md)
4. Run NB01–NB05 using the notebook guides above
5. Implement `run_monitoring()` (see [Trigger Pipeline Handover](operations/trigger-pipeline-handover.md)), then deploy

### "I want to automate the trigger"
1. Read [Trigger Pipeline Handover](operations/trigger-pipeline-handover.md) — full guide
2. Review NB07 for the reference implementation
3. Implement `run_monitoring()` in `src/philflood/pipelines/monitoring.py`
4. Use the reusable modules listed in the handover doc

### "I want to understand how PhilFlood works scientifically"
1. Read [Methods Overview](technical/methods-overview.md) for EVT approach
2. Review [ARCHITECTURE.md](technical/ARCHITECTURE.md) for system design
3. Check [GLOSSARY.md](technical/GLOSSARY.md) for technical terms
4. Study Notebook 1 markdown cells for hands-on examples

### "Monitoring failed with an error"
1. Check [Troubleshooting Guide](user-guides/troubleshooting.md) for common issues
2. Check logs for detailed error messages
3. Search [FAQ](getting-started/FAQ.md) for your specific issue

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
- [Section 4 Optimization](technical/notebook02-section4-optimization.md) - Performance tuning
- [Methods Overview - CLIMADA section](technical/methods-overview.md#return-period-to-hazard-integration-climada)

### Validation & Quality Assurance
- [Notebook 3 Validation Guide](user-guides/notebook03-validation-guide.md) - Extent validation and metrics
- [GLOSSARY - Validation Metrics](technical/GLOSSARY.md#validation--metrics-notebook-03) - F1, IoU, Precision, Recall definitions

### Trigger & Operations
- [Trigger Pipeline Handover](operations/trigger-pipeline-handover.md) - Automation guide
- [Deployment Guide](operations/deployment.md) - Placeholder (not yet implemented)
- [FAQ Operational Section](getting-started/FAQ.md#operational-monitoring) - Monitoring questions

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
4. Run NB01 (2-3 hours)
5. [Notebook 2 Guide](user-guides/notebook02-hazard-guide.md) (10 min)
6. Run NB02 (20-30 min)
7. [Notebook 3 Validation Guide](user-guides/notebook03-validation-guide.md) (20 min)
8. Run NB03–NB07

### For Operators (Phuoc)
1. [Trigger Pipeline Handover](operations/trigger-pipeline-handover.md) (30 min) — start here
2. [Deployment Guide](operations/deployment.md) (5 min) — stub; fill in once `run_monitoring()` is built
3. [Troubleshooting](user-guides/troubleshooting.md) (15 min)
4. Review `ops/configs/basins/` example configs (10 min)

### For Developers
1. [Architecture](technical/ARCHITECTURE.md) (30 min)
2. [Contributing Guide](contributing/CONTRIBUTING.md) (15 min)
3. [Testing Guide](contributing/TESTING.md) (15 min)
4. Review `src/philflood/` code structure (30 min)
5. Run test suite locally: `pytest tests/ -v`

---

## Documentation Conventions

**📌 Code blocks**: Use `bash` for shell commands, `python` for code

**🔗 Cross-references**: Link from one doc to related content

**📋 Lists**: Use bullet lists for options, numbered for procedures

---

## Version & Status

**Current Version**: v0.3.1 (April 2026)

**Status**:
- ✅ EVT calibration (NB01) - Fully functional with GoF tests and MRL checks
- ✅ GloFAS GRIB streaming - Fully optimized
- ✅ Hazard mapping (NB02) - Working
- ✅ Impact catalogue + EVT2 (NB04) - Multi-threshold (v0.5)
- ✅ Risk profiles (NB05) - AEP/OEP + multi-threshold OEP
- 🟡 Operational monitoring (`pipelines/monitoring.py`) - Stub, v1.0 target
- 🟡 Population impact source module - Partial, v1.0 target

See [CHANGELOG](../../CHANGELOG.md) for detailed roadmap.

---

## Getting Help

| Question Type | Where to Ask |
|---|---|
| Installation issues | [FAQ](getting-started/FAQ.md#installation--setup) → [Troubleshooting](user-guides/troubleshooting.md) |
| How do I...? | [FAQ](getting-started/FAQ.md) |
| Common error message | [Troubleshooting Guide](user-guides/troubleshooting.md#troubleshooting-common-errors) |
| Trigger automation | [Trigger Pipeline Handover](operations/trigger-pipeline-handover.md) |
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

---

**Last Updated**: April 2026 (v0.3.1)  
**Maintained By**: IBF Philippines Team
