# Trigger Pipeline — Automation Handover Guide

This document is for the engineer implementing automated operational triggering. It explains what the trigger system decides, what has been built, what is still a stub, and exactly which components can be reused.

**Status note**: The trigger algorithm documented here is implemented in NB07 for reforecast validation but has **not yet been accepted by START Network** as operational. NB07 is the reference implementation — the operational pipeline still needs to be built.

---

## What the Trigger Decides

The system issues a **yes/no early-action trigger** per spatial unit (ADM3 municipality / ADM2 province / watershed) per forecast day:

> **Triggered = True** when more than 50% of the ensemble forecast members produce flood impacts exceeding the impact threshold calibrated for that spatial unit at a given return period.

The decision is impact-based (people affected), not just discharge-based. This means a large flood in a sparsely populated area will not trigger, but even a moderate event in a dense municipality will.

The impact thresholds come from **risk profiles** — OEP (Occurrence Exceedance Probability) curves computed per spatial unit in NB05. These are the source of truth for what "a 1-in-10-year flood impact" looks like for each municipality/province/watershed. The threshold is **not configured in any YAML file** — it is a statistical output of the calibration process.

---

## Two-Phase Architecture

| Phase | Where | Frequency | Goal |
|---|---|---|---|
| **Calibration** | Notebooks NB01–NB07 | Once per basin (and when re-calibrating) | Fit statistical models, produce risk profiles |
| **Operations** | `pipelines/monitoring.py` (stub) | Daily (automated — not yet built) | Apply calibrated risk profiles to new forecast |

The two phases share no runtime code — operations reads calibration outputs as static files.

---

## Calibration Artifacts Required at Runtime

All of these are produced once by running NB01–NB05:

| Artifact | Produced by | Path | Contents |
|---|---|---|---|
| EVT1 fits | NB01 | `data/processed/calibration/evt_pot/{BASIN_ID}/{RUN_TAG}/evt_pot_calibration.parquet` | Per-cell GPD parameters: `u`, `xi`, `sigma`, `lam` |
| Hazard maps | NB02 | `data/processed/climada_hazard/{BASIN_ID}/{RUN_TAG}/*.tif` | Flood depth TIFFs per return period (m) |
| **Per-unit OEP curves** | **NB05** | **`data/processed/Riskprofiles/oep_curves_all_units.json`** | **Impact thresholds per admin unit at each RP — this is the trigger source of truth** |
| Watershed OEP | NB05 | `data/processed/Riskprofiles/watershed_oep_curve.json` | Watershed-level OEP for severity classification |
| Population grid | External | `data/raw/worldpop/PHL/phl_pop_*.tif` | WorldPop 100m population raster |

**NB01 column rename on load** (consistent across NB04/NB07):
```python
df = pd.read_parquet("evt_pot_calibration.parquet").rename(columns={
    "virtual_gauge_id":       "cell_id",
    "threshold_m3s":          "u",
    "lambda_events_per_year": "lam",
    "gpd_xi":                 "xi",
    "gpd_sigma":              "sigma",
})
```

---

## How Trigger Thresholds Work (Risk Profiles)

The `oep_curves_all_units.json` file (from NB05) is the heart of the trigger logic. It contains a separate OEP curve for every spatial unit — each ADM3 municipality, ADM2 province, and the whole watershed.

**Structure of `oep_curves_all_units.json`:**

```json
{
  "rp_report": [1, 2, 5, 10, 20, 25, 50, 75, 100, 200, 500],
  "units": [
    {
      "unit": "ADM3::Amulung",
      "level": "ADM3",
      "oep_rl": [0, 9868, 13288, 15560, 17200, ...],
      "aep_rl": [0, 12164, 23862, 31200, ...]
    },
    {
      "unit": "ADM2::Cagayan",
      "level": "ADM2",
      "oep_rl": [0, 45000, 82000, 120000, ...],
      ...
    },
    ...
  ]
}
```

Reading: for Amulung municipality, the OEP curve says a 1-in-10-year impact event affects ~15,560 people. So the trigger threshold for RP10 in Amulung is 15,560 people. These numbers come from the YLT simulation in NB05, not from manual configuration.

**Detection return periods** evaluated in NB07: `FLOOD_DETECT_RPS = [2, 5, 10, 20]`  
**Ensemble activation threshold** (hardcoded in NB07): `TRIGGER_PROB_LINE = 0.50` (50% of ensemble members)

---

## Detection Algorithm (NB07 Reference Implementation)

This is the algorithm in NB07 cells 3–10. It needs to be extracted and automated.

**Hardcoded parameters in NB07 (should move to config when implementing automation):**
```
T0_YEARS          = 2.0    # RP threshold for marking a GloFAS cell "active"
A_MIN_KM2         = 100.0  # minimum contiguous active patch area (km²)
DEPTH_THRESHOLD_M = 0.02   # flood depth (20mm) for counting affected population
TRIGGER_PROB_LINE = 0.50   # 50% of ensemble must exceed threshold to trigger
FLOOD_DETECT_RPS  = [2, 5, 10, 20]  # return periods to evaluate trigger at
```

**Algorithm per forecast initialization date:**

```
INPUT:
  - evt_pot_calibration.parquet (NB01): EVT1 GPD fits per cell
  - GloFAS forecast GRIB: discharge for all ensemble members and lead times
  - Hazard maps (NB02): flood depth TIFFs per return period
  - WorldPop raster: population grid
  - oep_curves_all_units.json (NB05): impact thresholds per unit per RP

For each ensemble member m in [1..N]:
  For each lead time t in [24h, 48h, ... up to max forecast horizon]:

    1. LOAD discharge Q[cell_id] at basin GloFAS points for (m, t)
       → adapters/glofas_grib_v4.extract_daily_discharge_for_points()

    2. COMPUTE return period per cell using EVT1 GPD:
       RP[cell_id] = 1 / (lam * (1 - F_GPD((Q - u) / sigma, xi)))
       where F_GPD is scipy.stats.genpareto.cdf(shape=xi)

    3. MARK active cells: active[cell_id] = (RP[cell_id] >= T0_YEARS)

    4. CONNECTED-COMPONENT LABELING on active cells (rasterized on GloFAS grid)
       → scipy.ndimage.label() on binary active grid
       Discard components with area < A_MIN_KM2

    5. FOR EACH detected event patch:
       a. Load flood depth raster for the event RP (from NB02 hazard maps)
       b. For each admin unit (ADM3/ADM2/watershed):
          Count people where depth >= DEPTH_THRESHOLD_M using WorldPop
          → models/impact/population_exposure.aggregate_affected_population()
       c. Record PopAffected[unit, m, t]

TRIGGER EVALUATION:
  For each unit and each RP in FLOOD_DETECT_RPS:
    threshold = oep_curves_all_units.json → oep_rl at that RP for that unit
    prob_exceed[unit, RP] = fraction of ensemble members where PopAffected[unit] >= threshold

  triggered[unit, RP] = (prob_exceed[unit, RP] >= TRIGGER_PROB_LINE)  # 50%
```

**Output per unit**: a triggered/not-triggered flag per RP, plus the probability of exceedance. The primary reporting level is ADM3 (municipality), but ADM2 and watershed levels are also computed.

---

## Reusable Source Modules

These modules are already in `src/philflood/` and can be imported directly:

| Module | Key functions | Use in trigger pipeline |
|---|---|---|
| `adapters/glofas_grib_v4.py` | `extract_daily_discharge_for_points()` | Step 1: extract discharge per ensemble × lead time |
| `adapters/glofas_grib_v4_optimized.py` | streaming variant | Better for large batch reforecast loops |
| `utils/event_detection.py` | `peak_pick()`, `auto_select_threshold()` | Declustering when needed |
| `models/impact/population_exposure.py` | `aggregate_affected_population()` | Step 5b: intersect flood depth + WorldPop per admin unit |
| `domain/config.py` | `load_basin_config()` | Load `BasinConfig` (basin metadata, EVT1 params for new basins) |
| `ops/config.py` | `load_run_config(root, auto_select_latest=True)` | Auto-discover NB01 `run_config.json` for paths to calibration artifacts |
| `pipelines/monitoring.py` | `TriggerDecision` dataclass | Output struct — already defined; fill in `run_monitoring()` |

---

## What Still Needs to Be Implemented

`src/philflood/pipelines/monitoring.py::run_monitoring()` currently raises `NotImplementedError`. 

**Implementation checklist:**
- [ ] Load EVT1 fits from `evt_pot_calibration.parquet` with column rename
- [ ] Ingest forecast GRIB for the issue date
- [ ] Implement detection loop (steps 1–5 from algorithm above)
- [ ] Load `oep_curves_all_units.json` — extract per-unit thresholds for each RP in `FLOOD_DETECT_RPS`
- [ ] Compute `prob_exceed` per unit × RP across ensemble members
- [ ] Apply `TRIGGER_PROB_LINE` threshold → produce triggered/not-triggered per unit × RP
- [ ] Return `TriggerDecision` (or extend the dataclass to include per-unit results)
- [ ] Decide on config representation for `T0_YEARS`, `A_MIN_KM2`, `DEPTH_THRESHOLD_M`, `TRIGGER_PROB_LINE`

> **Note on YAML `TriggerConfig`**: The `trigger:` section in basin YAML files (`impact_threshold_people`, `probability_threshold`, `max_lead_time_days`) is a leftover v1.0 stub that does not reflect how the trigger actually works. It has been removed from the YAML files. The real thresholds live in `oep_curves_all_units.json`.

---

## Operational Monitoring — Conceptual Overview

The person implementing automation will need to make their own architecture decisions, but here is the conceptual flow of what a daily operational run should do:

**Daily trigger run (per basin, per forecast initialization):**

1. **Ingest**: Download today's GloFAS ensemble forecast GRIB (or pick it up from a shared drive/storage location if already downloaded)

2. **Detect**: For each ensemble member and lead time, run the spatial detection algorithm to identify active flood events (using EVT1 GPD fits from NB01)

3. **Impact**: For each detected event and admin unit, compute population affected using the flood depth TIFFs (NB02) and WorldPop grid

4. **Evaluate**: Compare per-unit impacts against the OEP-calibrated thresholds from `oep_curves_all_units.json` (NB05), count what fraction of the ensemble exceeds the threshold

5. **Decide**: Apply the 50% ensemble threshold — if ≥50% of members exceed the calibrated impact for any unit at any of the detection RPs [2, 5, 10, 20], record a trigger

6. **Output**: Save trigger decisions (per unit, per RP) in a format compatible with the downstream early warning system (e.g., 510 Global IBF system)

**Already available and reusable:** Steps 1 (download patterns in NB00-01), 2 and 4 (detection logic in NB07), 5 (thresholds in NB05 JSON), the source modules listed above. The main work is connecting these pieces into a scheduled, automated pipeline.

**Architecture choice left to the new engineer**: Whether to implement this as a Python script called by a cron job, an Azure Function, a Prefect/Airflow DAG, or some other orchestration. The existing `ops/pipeline/` scripts show one (non-production) pattern, but the choice depends on the target deployment environment.

---

## NB07 Function Rename — Pending Sync

NB07 Cell 3 copies NB04 helper functions verbatim with old v0.4 names. Before using NB07 as a definitive reference, sync these:

| Old name (NB07 Cell 3) | New name (NB04) |
|---|---|
| `w_to_rp_spliced` | `impact_to_rp_spliced` |
| `fit_evt2_spliced_wpeak` | `fit_evt2_spliced_impact` (if copied) |
| `w_peak_series` / `RP_W_peak` | updated variable names in NB04 |
| `sample_w_from_evt2`, `compute_w_series_from_discharge` | deleted — remove from NB07 |

---

**Last Updated:** April 2026  
**Questions?** Contact David Uruena — duruenaramirez@redcross.nl
