# PhilFlood Architecture Overview

This document explains the module organization and data flow within the PhilFlood system.

## Module Organization

The `src/philflood/` package is organized into logical layers following separation of concerns:

### **Core Layers**

#### **`adapters/`** - External System Interfaces
Handles communication with external data sources and libraries:
- **GRIB extraction**: Memory-efficient streaming of GloFAS discharge data from ECMWF GRIB files
- **CLIMADA interfaces**: Integration with CLIMADA hazard and impact models (v1.0: full integration)
- **Data loaders**: Parsing and validation of raw data files

**Key files:**
- `glofas_grib_v4_optimized.py` - Streaming extraction with 94% memory reduction
- `climada_river.py` - Flood hazard mapping adapter (v0.3: placeholder)

#### **`domain/`** - Business Logic & Entities
Contains core domain models and business rules:
- **Basin configuration**: Structured representation of monitoring regions
- **Domain entities**: Core objects (discharge thresholds, trigger parameters)
- **Validation rules**: Business logic for configuration consistency

**Key files:**
- `basin.py` - Basin entity with gauge points, thresholds, spatial bounds
- `config.py` - Configuration schema and validation

#### **`models/`** - Statistical & Impact Models
Implements scientific models for risk quantification:
- **`ev/`** - Extreme Value Theory (EVT) models using Generalized Pareto Distribution (GPD)
- **`impact/`** - Population exposure and impact calculations (v1.0: full implementation)
- **`risk/`** - Risk metrics including Annual Exceedance Probability (AEP) and Occurrence Exceedance Probability (OEP)

**Key files:**
- `models/ev/pot_calibration.py` - Peaks Over Threshold (POT) calibration
- `models/impact/population_exposure.py` - Population-at-risk calculations (v0.3: placeholder)

#### **`calibration/`** - Statistical Model Fitting
Tools for offline model calibration:
- EVT threshold selection and parameter estimation
- Bootstrap uncertainty quantification
- Diagnostic plotting and model validation

**Key files:**
- `evt_pot.py` - Main EVT Peaks-Over-Threshold (POT) calibration workflow
- Diagnostics and threshold-analysis helpers under `models/ev/` - Mean residual life plots, parameter stability

#### **`config/`** - Configuration Management
YAML configuration schema and loading:
- Basin-specific parameter files (`ops/configs/basins/*.yaml`)
- Country-level configuration (`ops/configs/country.yaml`)
- Schema validation and defaults

**Key files:**
- `loader.py` - YAML parsing with validation
- `schema.py` - Configuration schema definitions

#### **`geo/`** - Spatial Operations
Geographic data processing and analysis:
- **HydroBASINS**: Watershed boundary extraction and spatial joins
- **WorldPop**: Population raster processing and exposure calculations
- **Spatial utilities**: Coordinate transformations, rasterization

**Key files:**
- `hydrobasins.py` - Watershed delineation
- `worldpop.py` - Population density extraction

#### **`pipelines/`** - Workflow Orchestration
High-level workflows combining multiple modules:
- **Monitoring pipeline**: Automated forecast processing and trigger generation
- **Validation pipeline**: Quality control and performance checks
- **Calibration pipeline**: End-to-end parameter estimation

**Key files:**
- `monitoring.py` - Operational forecast monitoring
- `validation.py` - Configuration and data validation

#### **`ops/`** - Operational Utilities
Production-specific functionality:
- Trigger decision logic
- Alert formatting and delivery
- Health checks and monitoring

**Key files:**
- `trigger.py` - Threshold exceedance detection
- `alerts.py` - Email and webhook notifications

#### **`qc/`** - Quality Control
Data quality checks and validation:
- Discharge data completeness checks
- Temporal consistency validation
- Spatial extent verification

**Key files:**
- `data_quality.py` - Quality check implementations

#### **`utils/`** - Cross-cutting Utilities
Shared infrastructure code:
- Memory management and optimization
- Logging configuration
- Date/time utilities

**Key files:**
- `memory.py` - Memory profiling and optimization
- `logging.py` - Structured logging setup

#### **`cli.py`** - Command-Line Interface
Main entry point for the `philflood` command:
```bash
philflood monitor --basin Cagayan_01
philflood validate --config ops/configs/basins/Cagayan_01.yaml
```

---

## Data Flow

### **Calibration Workflow** (Offline, Research Phase)
```
Raw GloFAS → adapters/glofas_grib → calibration/evt_calibrator → config/basin.yaml
    GRIB       (streaming extract)     (GPD fitting, bootstrap)    (thresholds)
```

1. **Extract** historical discharge via `adapters/glofas_grib_v4_optimized.py`
2. **Calibrate** EVT models using `calibration/evt_calibrator.py`
3. **Generate** basin configuration with thresholds in `ops/configs/basins/*.yaml`

### **Operational Workflow** (Online, Production Phase)
```
GloFAS Forecast → adapters → models/ev → models/impact → ops/trigger → Alert
   (Real-time)     (extract)  (Q→RP)    (RP→People)    (threshold)   (email)
```

1. **Ingest** forecast via `adapters/glofas_grib.py`
2. **Convert** discharge to return period using calibrated `models/ev/` parameters
3. **Calculate** population impact via `models/impact/` (v1.0: full integration)
4. **Evaluate** triggers using `ops/trigger.py` logic
5. **Issue** alerts via `ops/alerts.py`

### **Validation Workflow** (Continuous)
```
Configuration → config/loader → qc/data_quality → pipelines/validation → Report
  (Basin YAML)   (parse+validate)  (quality checks)   (orchestrate)      (JSON)
```

---

## Key Design Principles

### **Separation of Calibration & Operations**
- **Calibration** (`calibration/`, notebooks): Research-grade, interactive, parameter estimation
- **Operations** (`ops/`, `pipelines/`): Production-grade, automated, fixed parameters
- No model re-fitting in production—only apply pre-calibrated thresholds

### **Adapter Pattern for External Dependencies**
- All external systems accessed via `adapters/` to enable:
  - Easy mocking for tests
  - Swapping data sources (e.g., GloFAS v3 → v4)
  - Fallback when CLIMADA unavailable

### **Domain-Driven Design**
- Core business logic in `domain/` independent of data sources
- Clear separation between models (statistics) and domain (business rules)

### **Configuration as Code**
- All basin-specific parameters in YAML (version-controlled)
- Schema validation prevents configuration errors
- Enables reproducibility and auditability

---

## Development Status by Module

### **✅ Fully Implemented (v0.3.0)**
- `adapters/glofas_grib_*` - Streaming extraction, optimized
- `calibration/` - EVT fitting, bootstrap, diagnostics
- `models/ev/` - GPD parameter estimation, return level calculation
- `config/` - YAML schema and validation
- `domain/` - Basin entities and business rules
- `cli.py` - Command-line interface
- `utils/` - Memory management, logging

### **🟡 Partial Implementation (v0.3.0 → v1.0.0)**
- `adapters/climada_river.py` - Returns placeholder zeros, full integration in v1.0
- `models/impact/` - Placeholder population exposure, full implementation in v1.0
- `pipelines/monitoring.py` - Skeleton present, requires CLIMADA completion
- `ops/trigger.py` - Basic threshold logic, impact-based triggers in v1.0

### **📋 Planned (v1.0 → v2.0)**
- REST API for programmatic access
- Web dashboard for visualization
- Real-time GloFAS ingestion (currently manual download)
- Automated model retraining pipeline

See [CHANGELOG.md](../CHANGELOG.md) for detailed roadmap.

---

## Navigation Tips

### **I want to...**
- **Understand the methodology** → [docs/methods_onepager.md](methods_onepager.md)
- **Run my first calibration** → [docs/quickstart.md](quickstart.md)
- **Deploy to production** → [docs/deployment.md](deployment.md)
- **Modify EVT calibration** → `src/philflood/calibration/` + `calibration/notebooks/`
- **Add a new data source** → Implement new adapter in `src/philflood/adapters/`
- **Change trigger logic** → `src/philflood/ops/trigger.py`
- **Debug configuration issues** → `src/philflood/config/` + `src/philflood/qc/`

### **Import Paths**
```python
# Correct module imports
from philflood.adapters.glofas_grib_v4_optimized import extract_timeseries_streaming
from philflood.calibration.evt_pot import calibrate_pot_model
from philflood.models.ev.peaks_over_threshold import calculate_return_levels
from philflood.config.basin import load_basin_config
from philflood.pipelines.monitoring import run_monitoring_pipeline
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
2. **Check dependencies**: Can this module import from lower layers only? (e.g., `pipelines/` can import `models/`, but not vice versa)
3. **Add tests**: New modules require corresponding test files in `tests/`
4. **Update this document**: Add module description and data flow diagram

---

**Last Updated:** February 6, 2026 (v0.3.0)  
**Maintainers:** IBF Philippines Team
