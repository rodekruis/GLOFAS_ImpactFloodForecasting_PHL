# PhilFlood Architecture Overview

This document explains the module organization and data flow within the PhilFlood system.

## Module Organization

The `src/philflood/` package is organized into logical layers following separation of concerns:

### **Core Layers**

#### **`adapters/`** - External System Interfaces
Handles communication with external data sources:
- **GRIB extraction**: Memory-efficient streaming of GloFAS discharge data from ECMWF GRIB files

**Key files:**
- `glofas_grib_v4.py` - Standard GRIB extraction for operational use
- `glofas_grib_v4_optimized.py` - Streaming extraction with 94% memory reduction (use for historical/large datasets)

**Legacy (do not import):**
- `_archive/` — Deprecated adapters (glofas, glofas_grib_streaming, climada_river, hazard_maps, geo/aoi, geo/worldpop). Removed since v0.3.0.

#### **`domain/`** - Business Logic & Entities
Contains core domain models and business rules:
- **Basin configuration**: Structured representation of monitoring regions
- **Domain entities**: Core objects — discharge thresholds, trigger parameters, vulnerability config

**Key files:**
- `basin.py` - Dataclasses: `BasinConfig`, `EVTConfig`, `VulnerabilityConfig`, `TriggerConfig`
- `config.py` - YAML serialization via `load_basin_config(path)` and `dump_basin_config(cfg, path)`

#### **`calibration/`** - Statistical Model Fitting
Tools for offline model calibration:
- EVT threshold selection and parameter estimation
- Bootstrap uncertainty quantification

**Key files:**
- `evt_pot.py` - Main EVT Peaks-Over-Threshold (POT) calibration workflow; wraps `pyextremes` with version-shimming

#### **`models/`** - Statistical & Impact Models
Implements scientific models for risk quantification:
- **`ev/`** - Extreme Value Theory (EVT) models using Generalized Pareto Distribution (GPD): threshold selection, GoF tests, MRL analysis
- **`impact/`** - Population exposure and impact calculations (v0.3: partial)

**Key files:**
- `models/ev/threshold_selection.py` - `auto_select_threshold()`, `compute_mrl()`, `gpd_gof_test()`
- `models/impact/impact_evt.py` - `fit_gpd_pot()`, `impact_to_return_period()`
- `models/impact/population_exposure.py` - `aggregate_affected_population()` (v0.3: placeholder)

#### **`geo/`** - Spatial Operations
Geographic data processing and analysis:
- **HydroBASINS**: Watershed boundary extraction and spatial joins
- **WorldPop**: Population raster processing

**Key files:**
- `geo/hydrobasins.py` - Watershed delineation
- `geo/worldpop.py` - Population density extraction

#### **`pipelines/`** - Workflow Orchestration
High-level workflows combining multiple modules:

**Key files:**
- `monitoring.py` - Operational monitoring stub: defines `TriggerDecision` dataclass and `run_monitoring()` (currently raises `NotImplementedError`; full implementation target: v1.0)

> **Note**: There is no `validation.py` in `pipelines/`. Basin config validation is done via `BasinConfig.validate()` in `domain/basin.py`.

#### **`ops/`** - Operational Utilities
Production-specific functionality:

**Key files:**
- `logging_config.py` - Structured JSON logging via `get_logger(__name__)`
- `config.py` - NB01 run config auto-discovery: `load_run_config(PROCESSED_ROOT, auto_select_latest=True)` — used by NB02–NB07 to find `run_config.json`

> **Note**: There is no `trigger.py` or `alerts.py` in `ops/`. Trigger decision logic will live in `pipelines/monitoring.py` when implemented.

#### **`qc/`** - Quality Control
Data quality checks and validation:

**Key files:**
- `timeseries.py` - Time series quality check implementations

#### **`utils/`** - Cross-cutting Utilities
Shared infrastructure code:

**Key files:**
- `memory_utils.py` - Memory profiling and optimization helpers
- `paths.py` - Common filesystem and path utilities
- `event_detection.py` - `peak_pick()`, `auto_select_threshold()` — declustering and independent-event extraction

#### **`cli.py`** - Command-Line Interface
Main entry point for the `philflood` command. Only `monitor` is implemented:
```bash
philflood monitor --basin ops/configs/basins/Cagayan_01.yaml
philflood monitor --basin-dir ops/configs/basins --format json --output results/
```

---

## Data Flow

### **Calibration Workflow** (Offline, Research Phase — Notebooks NB01–NB07)

```
Raw GloFAS GRIB  →  NB01 (EVT1 calibration)  →  run_config.json + evt_pot_calibration.parquet
                                 ↓
                     NB02 (hazard maps)       →  flood depth TIFFs per return period
                                 ↓
                     NB03 (validation)        →  F1 / IoU / Precision / Recall per RP
                                 ↓
                     NB04 (impact catalogue)  →  event_registry.parquet + EVT2 fit JSONs
                                 ↓
                     NB05 (risk profiles)     →  watershed_oep_curve.json + Excel workbook
                                 ↓
                     NB06 (event viewer)      →  interactive HTML dashboard
                                 ↓
                     NB07 (trigger validation)→  trigger performance stats vs. reforecast
```

### **Operational Workflow** (Online, Production Phase — Target v1.0)

```
Daily GloFAS Forecast  →  adapters/glofas_grib_v4  →  discharge per ensemble member
                                    ↓
                   models/ev (EVT1 GPD fits from NB01)  →  return period per cell
                                    ↓
                   models/impact (NB02 depth TIFFs + worldpop)  →  PopAffected
                                    ↓
                   models/impact (EVT2 fit from NB04)  →  P(impact > threshold)
                                    ↓
                   pipelines/monitoring.run_monitoring()  →  TriggerDecision (triggered: bool)
```

**Required calibration artifacts** (produced once by NB01–NB05, read daily):
- `evt_pot_calibration.parquet` — EVT1 per-cell GPD parameters
- Flood depth TIFFs — NB02 hazard maps per return period
- `evt2_fit_popaffected_op.json` — NB04 EVT2 fit for impact → RP
- `watershed_oep_curve.json` — NB05 severity thresholds (RP → people affected)

---

## Key Design Principles

### **Separation of Calibration & Operations**
- **Calibration** (`calibration/`, notebooks): Research-grade, interactive, parameter estimation
- **Operations** (`ops/`, `pipelines/`): Production-grade, automated, fixed parameters
- No model re-fitting in production — only apply pre-calibrated thresholds

### **Adapter Pattern for External Dependencies**
- All external systems accessed via `adapters/` to enable easy mocking for tests and data-source swapping

### **Domain-Driven Design**
- Core business logic in `domain/` independent of data sources
- `domain/basin.py` defines canonical dataclasses; `domain/config.py` handles YAML I/O
- All basin-specific parameters are YAML-serialized (version-controlled, schema-validated)

---

## Development Status by Module

### **✅ Fully Implemented (v0.3.0)**
- `adapters/glofas_grib_v4*` — Streaming extraction, optimized
- `calibration/evt_pot.py` — EVT fitting, bootstrap, diagnostics
- `models/ev/` — GPD parameter estimation, return level calculation, GoF tests
- `domain/` — Basin entities and business rules, YAML I/O
- `ops/config.py` — NB01 run_config auto-discovery
- `ops/logging_config.py` — Structured logging
- `cli.py` — `monitor` command
- `utils/` — Memory management, event detection/declustering

### **🟡 Partial / Stub (v0.3.0 → v1.0.0)**
- `models/impact/population_exposure.py` — Placeholder; full implementation in v1.0
- `pipelines/monitoring.py` — `TriggerDecision` struct is correct; `run_monitoring()` raises `NotImplementedError`

### **📋 Planned (v1.0 → v2.0)**
- Full `run_monitoring()` implementation with CLIMADA depth maps and worldpop
- REST API for programmatic trigger access
- Real-time GloFAS ingestion (currently manual download via NB00)
- Automated model retraining pipeline

See [CHANGELOG.md](../../CHANGELOG.md) for detailed roadmap.

---

## Navigation Tips

### **I want to...**
- **Understand the methodology** → [Methods Overview](methods-overview.md)
- **Run my first calibration** → [Getting Started Guide](../getting-started/quickstart.md)
- **Deploy to production** → [Deployment Guide](../operations/deployment.md)
- **Understand the trigger pipeline** → [Trigger Pipeline Handover](../operations/trigger-pipeline-handover.md)
- **Modify EVT calibration** → `src/philflood/calibration/` + `calibration/notebooks/`
- **Add a new data source** → Implement new adapter in `src/philflood/adapters/`
- **Implement trigger logic** → `src/philflood/pipelines/monitoring.py` (see trigger handover doc)
- **Debug configuration issues** → `src/philflood/domain/config.py` + `src/philflood/qc/`

### **Import Paths**
```python
# Correct module imports
from philflood.adapters.glofas_grib_v4 import extract_daily_discharge_for_points
from philflood.adapters.glofas_grib_v4_optimized import extract_timeseries_streaming
from philflood.calibration.evt_pot import calibrate_pot_model
from philflood.models.ev.threshold_selection import auto_select_threshold, compute_mrl
from philflood.models.impact.impact_evt import impact_to_return_period
from philflood.domain.config import load_basin_config
from philflood.ops.config import load_run_config
from philflood.pipelines.monitoring import TriggerDecision, run_monitoring
```

### **Configuration Files**
```
ops/configs/
├── country.yaml              # Philippines-level settings
└── basins/
    ├── Cagayan_01.yaml       # Basin-specific parameters
    └── example_basin.yaml    # Template for new basins
```

---

## Contributing to Architecture

When adding new modules:
1. **Identify the layer**: Does this belong in `adapters/`, `models/`, `domain/`, etc.?
2. **Check dependencies**: Can this module import from lower layers only? (`pipelines/` can import `models/`, but not vice versa)
3. **Add tests**: New modules require corresponding test files in `tests/`
4. **Update this document**: Add module description and data flow diagram

---

**Last Updated:** April 2026 (v0.3.1)  
**Maintainers:** IBF Philippines Team
