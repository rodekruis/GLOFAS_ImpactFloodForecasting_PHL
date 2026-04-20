# API Reference

Module-level API documentation for PhilFlood.

**Status**: v0.3.1 — this page lists the real public functions as they exist in `src/philflood/`. Full autodoc (pdoc3/Sphinx) is not yet set up.

---

## Correct Import Paths

```python
# Adapters — data extraction
from philflood.adapters.glofas_grib_v4 import extract_daily_discharge_for_points
from philflood.adapters.glofas_grib_v4_optimized import extract_timeseries_streaming

# Calibration — EVT/POT fitting
from philflood.calibration.evt_pot import (
    fit_gpd_to_pot,
    bootstrap_pot_return_levels,
    return_period_to_discharge_pot,
    discharge_to_return_period_pot,
    gpd_gof_test,
)

# Threshold selection (separate module from calibration)
from philflood.models.ev.threshold_selection import (
    auto_select_threshold_pot,
    compute_mrl,
)

# Domain — configuration
from philflood.domain.config import load_basin_config
from philflood.ops.config import load_run_config

# Impact models
from philflood.models.impact.population_exposure import aggregate_affected_population

# Operational pipeline
from philflood.pipelines.monitoring import TriggerDecision, run_monitoring
```

---

## Core Modules

### adapters/
**Data extraction from external sources.**

- `glofas_grib_v4.py` — Standard GRIB extraction
  - `extract_daily_discharge_for_points()` — Extract discharge for a list of GloFAS cell IDs

- `glofas_grib_v4_optimized.py` — Low-memory streaming variant (94% RAM reduction vs standard)
  - `extract_timeseries_streaming()` — Year-by-year streaming extraction

> Legacy adapters are in `adapters/_archive/` — deprecated since v0.3.0, do not import from there.

### calibration/
**Extreme Value Theory calibration.**

- `evt_pot.py` — Peaks Over Threshold calibration
  - `fit_gpd_to_pot()` — Fit GPD to POT exceedances; returns `POTResult`
  - `bootstrap_pot_return_levels()` — Bootstrap CIs for return levels
  - `return_period_to_discharge_pot()` — RP → discharge using GPD formula
  - `discharge_to_return_period_pot()` — Discharge → RP using GPD formula
  - `gpd_gof_test()` — KS goodness-of-fit test on PIT residuals
  - `pot_extract()` — Extract POT exceedances from a time series

### models/ev/
**Extreme value threshold selection.**

- `threshold_selection.py` — Threshold diagnostics and auto-selection
  - `auto_select_threshold_pot()` — 3-tier stability-based threshold selection
  - `compute_mrl()` — Mean residual life plot values
  - `plot_parameter_stability()` — Diagnostic plots

### models/impact/
**Population exposure calculations (partial in v0.3).**

- `population_exposure.py`
  - `aggregate_affected_population()` — Intersect flood depth raster + WorldPop to count people affected per admin unit

- `impact_evt.py`
  - `impact_to_return_period()` — Map impact (people affected) → RP using EVT2 fit

### domain/
**Configuration entities.**

- `basin.py` — Canonical dataclasses: `BasinConfig`, `EVTConfig`, `VulnerabilityConfig`, `TriggerConfig`
- `config.py` — YAML deserialization
  - `load_basin_config(path)` — Load and validate basin YAML → `BasinConfig`

### ops/
**Runtime configuration and logging.**

- `config.py`
  - `load_run_config()` — Auto-discover NB01 `run_config.json`; see [Ops Config Reference](../ops-config-reference.md) for full usage
- `logging_config.py`
  - `get_logger(__name__)` — Structured JSON logger for production; human-readable for dev

### pipelines/
**Orchestration.**

- `monitoring.py`
  - `TriggerDecision` (dataclass) — Output struct with fields: `basin_id`, `issue_date`, `probability_exceed`, `expected_people`, `triggered`
  - `run_monitoring()` — **Stub** — raises `NotImplementedError` until v1.0

### utils/
**Shared utilities.**

- `event_detection.py` — `peak_pick()` — declustering for independent-event extraction
- `memory_utils.py` — Memory profiling helpers
- `paths.py` — Filesystem path utilities

### geo/
**Spatial operations.**

- HydroBASINS watershed extraction, WorldPop raster joins, coordinate reprojection

---

## Basin Configuration YAML Schema

See `ops/configs/basins/example_basin.yaml` for the full annotated template. Key fields:

```yaml
basin_id: Cagayan_01
country_iso3: PHL
hydrobasins_level: 6
hydrobasins_id: 4060906180
glofas_point_ids:
  - PHL_12345

evt:
  method: POT-GPD
  threshold_m3s: 1500.0
  run_length_days: 5
  gpd_shape_xi: -0.15
  gpd_scale_sigma: 250.0
  event_rate_per_year: 2.5

vulnerability:
  depth_threshold_m: 0.3
  impact_fraction: 1.0

# trigger: section intentionally omitted — thresholds come from
# data/processed/Riskprofiles/oep_curves_all_units.json (NB05 output)
```

---

## TriggerDecision Output

`TriggerDecision` is the current v0.3 stub output struct. It will be extended in v1.0 to carry per-unit, per-tier results.

```python
@dataclass
class TriggerDecision:
    basin_id: str
    issue_date: date
    probability_exceed: float
    expected_people: float
    triggered: bool

    def to_dict(self) -> Dict[str, object]: ...
```

See [Trigger Pipeline Handover](../../operations/trigger-pipeline-handover.md) for the v1.0 output design (per ADM3/ADM2/watershed, per tier T1/T2/T3).

---

## Module Status

| Module | Status | Notes |
|---|---|---|
| `adapters/glofas_grib_v4_optimized` | ✅ Full | Primary for large datasets |
| `calibration/evt_pot` | ✅ Full | GoF tests + bootstrap CIs |
| `models/ev/threshold_selection` | ✅ Full | 3-tier stability + MRL + GoF |
| `domain/basin` + `domain/config` | ✅ Full | Canonical config dataclasses |
| `ops/config` | ✅ Full | `load_run_config()` auto-discovery |
| `models/impact/population_exposure` | 🟡 Partial | Raster intersection works; CLIMADA full integration v1.0 |
| `models/impact/impact_evt` | 🟡 Partial | EVT2 fit and RP conversion working |
| `geo/` | ✅ Full | HydroBASINS + WorldPop joins |
| `pipelines/monitoring` | 🔴 Stub | `run_monitoring()` raises `NotImplementedError` |

---

## Building Full API Docs

```bash
# Install pdoc3 if not present
pip install pdoc3

# Generate HTML API docs
pdoc3 --html --output-dir docs/technical/api-reference/ \
  src/philflood
```

---

**Related Documentation**:
- [ARCHITECTURE.md](../ARCHITECTURE.md) - Module organization and data flows
- [Methods Overview](../methods-overview.md) - Scientific basis and formulas
- [Ops Config Reference](../ops-config-reference.md) - `load_run_config()` full usage
- [Contributing Guide](../../contributing/CONTRIBUTING.md) - Code style and development workflow
