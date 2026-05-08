# PhilFlood — Humanitarian Operations Manual

**Simplified workflow for impact-based flood risk profiles**
Version: v0.3.0 | Last updated: 2026-05-07

---

## Contents

- [Part 0 — Introduction & Limitations](#part-0--introduction--limitations)
- [Part 1 — Environment Setup](#part-1--environment-setup)
- [Part 2 — Data Preparation](#part-2--data-preparation)
- [Part 3 — Basin / AOI Configuration](#part-3--basin--aoi-configuration)
- [Part 4 — EVT1 Calibration (NB01)](#part-4--evt1-calibration-nb01)
- [Part 5 — Flood Hazard Maps (NB02)](#part-5--flood-hazard-maps-nb02)
- [Part 6 — Validation (NB03, optional)](#part-6--validation-nb03-optional)
- [Part 7 — Event Catalog & EVT2 Curve (Simplified NB04)](#part-7--event-catalog--evt2-curve-simplified-nb04)
- [Part 8 — Risk Profiles (Simplified NB05)](#part-8--risk-profiles-simplified-nb05)
- [Part 9 — Scenario Flood Maps (Simplified NB06)](#part-9--scenario-flood-maps-simplified-nb06)
- [Part 10 — Contributor Roadmap](#part-10--contributor-roadmap)

---

## Part 0 — Introduction & Limitations

### Purpose

This manual describes how to produce **impact-based flood risk profiles** for humanitarian early-action planning using the PhilFlood pipeline. The output is a set of population exposure estimates at return periods RP2, RP5, and RP10 — the statistical thresholds used for Moderate Watch, High Alert, and Very High Activation decisions respectively.

This manual targets two audiences:
- **Operators** — analysts and GIS specialists running the workflow for a new country or basin
- **Contributors** — developers extending or simplifying the pipeline (see [Part 10](#part-10--contributor-roadmap))

### What this workflow produces

By the end of the pipeline you will have:
1. A calibrated statistical flood model per river basin (EVT1: Generalized Pareto Distribution on discharge)
2. Spatial flood depth maps at 8 return periods (from JRC Global Flood Maps)
3. A historical event impact catalog (people affected per flood event)
4. A statistical impact model (EVT2: GPD on population impact)
5. **Risk profiles**: OEP/AEP exceedance probability curves and point estimates of people affected at RP2, RP5, RP10
6. Scenario flood maps at RP2/5/10 (static HTML, no event-specific data needed)

### Relationship to the full pipeline

The full PhilFlood pipeline also includes a **reforecast library** (NB04 Section 7+) that processes 20+ years of GloFAS ensemble GRIB data (~200 GB) to generate thousands of synthetic flood events. This enriches the event catalog and is valuable for insurance-grade applications.

**For humanitarian operations, the reforecast library is not required.** The EVT2 statistical model fitted to historical events alone is sufficient for RP2/5/10 thresholds and OEP curves. The reforecast path is documented as an optional step in [Part 7](#part-7--event-catalog--evt2-curve-simplified-nb04).

---

### ⚠️ Methodology Limitations

These limitations are not caveats — they are structural constraints of the methodology. Read them before deploying thresholds operationally.

**Fluvial flooding only.** The model uses GloFAS river discharge as its input signal. It detects and characterizes riverine (fluvial) flooding. It does **not** capture:
- Pluvial flooding (surface water runoff from intense rainfall, often urban)
- Coastal flooding (storm surge, sea-level rise)
- Flash floods in small, fast-response catchments not represented in GloFAS

GloFAS has a native grid resolution of ~5 km. Small rivers and headwater basins may not be well-represented. In operational use, the model will miss flash flood events and give no signal for purely pluvial events.

**Historical record length.** The statistical model (GPD) requires sufficient extreme events to estimate the tail reliably. Rules of thumb:
- Fewer than 20 years of data → return period estimates above RP10 are highly uncertain
- Fewer than 20 flood events above the calibration threshold → EVT2 fitting is unreliable and may fail to tier 3 (fallback)
- Wide bootstrap confidence intervals (CV > 0.30) in NB01 output are a warning sign

**Static population exposure.** WorldPop rasters represent a snapshot population (typically 2020 or 2025). The model does not account for seasonal population movement, displacement, or urban growth since the raster vintage.

**JRC flood maps.** The JRC Global Flood Maps are a global 100m product based on hydrological modelling. Local accuracy varies: they tend to underestimate in complex terrain, may miss small rivers, and do not reflect recent floodplain land-use change. Validation against observed flood extents (NB03) is strongly recommended for any new deployment.

**JRC geographic coverage.** JRC tiles may not exist for very arid regions, some small island nations, and basins with minimal historical flood activity. NB02 will fail to find tiles for these areas.

**Uncertainty communication.** Risk profile outputs are point estimates. Bootstrap confidence intervals are computed (NB01) but not always propagated through the full pipeline. Stakeholder communications should always pair impact estimates with uncertainty ranges.

**Infrastructure changes.** The model does not account for changes in flood protection infrastructure (levees, dams, drainage) over the historical record or since calibration.

---

## Part 1 — Environment Setup

### Requirements

- **OS**: Linux, macOS, or Windows (WSL strongly recommended on Windows for GRIB handling)
- **RAM**: 2 GB minimum; 16 GB recommended for large basins
- **Disk**: ~5 GB free (GloFAS GRIB files alone are ~12 GB for a country-level bounding box)
- **Python**: 3.10–3.12

### Conda environment (required)

`cfgrib` and `eccodes` (needed to read GRIB files) do not install reliably with pip alone. Use conda:

```bash
conda env create -f environment.yml
conda activate philflood
```

### Install package in editable mode

```bash
pip install -e .
```

### Dev dependencies (for contributors)

```bash
pip install -r requirements-dev.txt
```

### External accounts (all free)

| Service | Purpose | Registration |
|---------|---------|--------------|
| ECMWF CEMS EWDS | GloFAS historical download + JRC tiles | https://ewds.climate.copernicus.eu/ |
| WorldPop | Population raster download | https://hub.worldpop.org/ |
| HydroSHEDS | Watershed boundary shapefiles | https://www.hydrosheds.org/ |
| OCHA HDX | Administrative boundaries | https://data.humdata.org/ |

### CDS API credentials

After registering with ECMWF CEMS EWDS, create `~/.cdsapirc`:

```ini
url: https://ewds.climate.copernicus.eu/api
key: <your-api-key>
```

The same credentials are used for both the GloFAS historical download (NB00-02) and the JRC tile download (NB02).

---

## Part 2 — Data Preparation

The pipeline requires four external datasets. This section explains where each comes from, what version to use, and where to place it.

> **[Missing Task #1]** A unified data-preparation notebook (`00B_data_preparation.ipynb`) does not yet exist. Once implemented, it will accept `COUNTRY_ISO3` and a bounding box and automate steps 2.2–2.4. Until then, follow the manual steps below.

### 2.1 GloFAS Historical Discharge

**Notebook**: `calibration/notebooks/00-02_GloFAS_Historical_download.ipynb`

**What is downloaded**: 43 years (1980–2022) of daily GloFAS v4.0 reanalysis river discharge. This is the primary hydrological record used to calibrate the EVT1 model.

**Dataset details**:
- Dataset ID: `cems-glofas-historical`
- System version: `version_4_0`
- Product type: `consolidated` (quality-controlled daily means; use this, not `intermediate`)
- Variable: `river_discharge_in_the_last_24_hours`
- Hydrological model: `lisflood`
- Time range: 1980–2025
- GloFAS v4.0 ends is up to date.

**How to set the bounding box for your country**:

Open the notebook and find the `AREA` parameter. It is defined as `[North, West, South, East]` in decimal degrees:

```python
# Philippines (default — replace with your country's extents)
AREA = [35, 63, 4, 131]

# Example: Mozambique
AREA = [-10, 30, -27, 41]

# Example: Bangladesh + surrounding drainage basin
AREA = [28, 86, 20, 93]
```

Use a bounding box slightly larger than your area of interest to capture upstream drainage. For river basins that cross borders, include all contributing upstream countries.

**Runtime**: 1-2 hours. The download is resume-safe — if interrupted, re-run the notebook and it will pick up where it stopped. Do not delete `_state/jobs_state.json`.

**Output**: `data/raw/glofas/historical/version_4_0/consolidated/discharge/grib2/area_{N}_{W}_{S}_{E}/` — one `data.grib` file per year.

**Hardcoded values to change before running**:
- `AREA` — replace bounding box with your region
- Output path — currently assumes shared G: Drive; change `OUTPUT_ROOT` to your local data directory

### 2.2 WorldPop Population Grid

**Purpose**: Used in NB04 to count people exposed to flood inundation, and in NB05 to compute the denominator for OEP curves.

**Recommended source**: https://hub.worldpop.org/geodata/listing?id=135 — Constrained individual countries, UN adjusted, 100m resolution

**How to download**:
1. Go to the WorldPop listing above
2. Select your country from the dropdown
3. Select the most recent available year (2020 or 2025 depending on country availability)
4. Download the GeoTIFF file (format: `{iso3}_pop_{year}_CN_100m_R{release}A_v1.tif`)
5. Place in `data/raw/worldpop/{ISO3}/`

**Naming convention** (the pipeline discovers files by glob):
```
data/raw/worldpop/PHL/phl_pop_2025_CN_100m_R2025A_v1.tif   # Philippines
data/raw/worldpop/MOZ/moz_pop_2020_CN_100m_R2020A_v1.tif   # Mozambique
data/raw/worldpop/BGD/bgd_pop_2020_CN_100m_R2020A_v1.tif   # Bangladesh
```

**Alternatives** (if WorldPop not available for your country):
- GHSL-POP (Global Human Settlement Layer): https://ghsl.jrc.ec.europa.eu/ghs_pop2023.php — EU-JRC product, 100m, global coverage
- GPW v4.11 (Gridded Population of the World): https://sedac.ciesin.columbia.edu/data/set/gpw-v4-population-count-rev11

Use the constrained model (UN-adjusted) when available — it is more accurate in low-density rural and periurban areas, which are typically the most flood-exposed populations.

### 2.3 HydroSHEDS Watershed Boundaries

**Purpose**: Defines basin boundaries for spatial analysis. Used in NB01 to delineate the watershed, and in NB04–NB05 for spatial joins.

**Source**: https://www.hydrosheds.org/products/hydrobasins

**What to download**:
- **Level 6** (`hybas_as_lev06_v1c.shp` for Asia, etc.) — Large river basins (~10,000–100,000 km²). Use this for basin-level configuration.
- **Level 8** — Medium sub-basins. Useful for larger watersheds you want to split.
- **Level 12** — Finest resolution. Required for spatial joins between GloFAS cells and admin units in NB04.

HydroSHEDS is divided by continent. Download the files for the relevant continent(s):
- `af` — Africa
- `as` — Asia
- `au` — Australasia
- `eu` — Europe
- `na` — North America
- `sa` — South America

**Placement**:
```
data/raw/hydrobasins/level_6/hybas_as_lev06_v1c.gpkg
data/raw/hydrobasins/level_8/hybas_as_lev08_v1c.gpkg
data/raw/hydrobasins/level_12/hybas_as_lev12_v1c.gpkg
```

**Finding the HYBAS_ID for your basin**:
The `hydrobasins_id` field in your basin config YAML (see [Part 3](#part-3--basin--aoi-configuration)) must match the `HYBAS_ID` attribute of the correct polygon in the shapefile.

1. Open the HydroSHEDS Level 6 shapefile in QGIS (or any GIS tool)
2. Use the "Identify Features" tool to click on your basin of interest
3. Note the `HYBAS_ID` value (e.g., `5060030230` for the upper Cagayan, Philippines)

Alternatively, use the HydroSHEDS online viewer at https://www.hydrosheds.org/hydrosheds-core-data to browse and identify basin IDs without downloading.

### 2.4 JRC Global Flood Maps

**Source**: Copernicus Emergency Management Service — automatically downloaded by NB02.

No manual download is needed. NB02 uses your CEMS EWDS credentials to fetch the relevant tiles for your basin bounding box. Tiles are cached in `_jrc_cache/` and reused on subsequent runs.

**Coverage note**: The JRC dataset covers most of the world's river systems at 100m resolution. However, tiles are absent or sparse in:
- Very arid regions (Sahara, Arabian Peninsula interior)
- Basins with minimal historical flood activity
- Some small island nations

If NB02 reports "No tiles selected" for your basin, the JRC product does not cover your area. Consider using an alternative flood depth dataset.

### 2.5 Administrative Boundaries

**Purpose**: Required for municipality-level analysis in NB01 (`USE_MUNI_AOI=True`) and admin-unit risk profiles in NB05.

**Source**: OCHA Humanitarian Data Exchange (HDX) — https://data.humdata.org/

HDX provides Common Operational Datasets (CODs) for administrative boundaries in humanitarian operation countries. These are standardized and regularly updated.

**How to download**:
1. Go to https://data.humdata.org/
2. Search for your country name + "administrative boundaries"
3. Download the COD-AB shapefile or GeoJSON (usually named `{country}_adm{N}.{ext}`)

**Required admin levels**:
- **ADM3** (municipality / commune / sub-district) — for granular trigger decisions
- **ADM2** (district / province) — for aggregated reporting

**Placement**:
```
data/raw/admin/{ISO3}_adm2.geojson
data/raw/admin/{ISO3}_adm3.geojson
```

CRS must be EPSG:4326. If downloaded files use a different CRS, reproject before use:
```bash
ogr2ogr -t_srs EPSG:4326 output.geojson input.shp
```

---

## Part 3 — Basin / AOI Configuration

### Basin YAML schema

Each basin is described by a YAML file in `ops/configs/basins/`. Create one file per basin before running the pipeline.

Full schema (from `ops/configs/basins/example_basin.yaml`):

```yaml
basin_id: my_basin_001          # String. Used for all output directory naming.
                                 # No spaces; use underscores.

country_iso3: PHL               # ISO 3166-1 alpha-3 country code. Used for
                                 # WorldPop file discovery and logging.

hydrobasins_level: 6            # HydroSHEDS level that defines the basin boundary.
                                 # Use level 6 for most large-river basins.
                                 # Use level 8 for sub-basin analysis.

hydrobasins_id: 5060030230      # HYBAS_ID attribute from the HydroSHEDS shapefile.
                                 # How to find: open the shapefile in QGIS and click
                                 # on your basin polygon; note the HYBAS_ID field.

glofas_point_ids:               # List of GloFAS grid cell identifiers.
  - PHL_00000                   # Discovered during NB01 calibration (see below).
                                 # Replace placeholder after first NB01 run.

data_root: data                 # Root directory for all data. Relative to the
                                 # project root, or absolute path.

evt:
  method: POT-GPD               # Do not change. Peaks-over-threshold GPD method.
  threshold_m3s: 0.0            # Filled after NB01 calibration. Discharge threshold
                                 # (m³/s) above which events are "extreme".
  run_length_days: 5            # Minimum separation between independent events (days).
  gpd_shape_xi: 0.0             # GPD shape parameter ξ. Filled after NB01.
                                 # Positive value = heavy tail (typical for floods).
  gpd_scale_sigma: 1.0          # GPD scale parameter σ. Filled after NB01.
  event_rate_per_year: 0.0      # Poisson event rate λ (events/year). Filled after NB01.

vulnerability:
  depth_threshold_m: 0.3        # Flood depth (m) above which people are counted
                                 # as "affected". 0.3m is a common operational
                                 # threshold for structural damage.
  impact_fraction: 1.0          # Fraction of exposed population considered affected.
                                 # 1.0 = all people in the inundated area.

# IMPORTANT: trigger: section is intentionally absent.
# Trigger thresholds (population affected at RP2/RP5/RP10) are NOT set here.
# They are statistical outputs of the risk profile calibration (NB05) stored in:
# data/processed/Riskprofiles/oep_curves_all_units.json
# See docs/operations/trigger-pipeline-handover.md for the trigger algorithm.
```

### Workflow mode: watershed vs. administrative units

NB01 supports two spatial aggregation modes, controlled by `USE_MUNI_AOI`:

| Mode | Parameter | Use when |
|------|-----------|---------|
| **Watershed** | `USE_MUNI_AOI = False` | Single basin, no admin boundary data, first-pass calibration |
| **Admin units** | `USE_MUNI_AOI = True` | Municipal/district-level triggers, detailed risk profiles |

This mode selection carries through all downstream notebooks (NB02–NB06). Auto-detection reads it from `run_config.json` produced by NB01.

### Finding `glofas_point_ids`

Before running NB01, you do not know your GloFAS point IDs. Use this procedure:

1. Run NB01 with `USE_CELL_EXTRACTION = False` (fast mode, single pour point)
2. Examine the output — the notebook prints discovered cell IDs and writes them to `run_config.json`
3. Copy the IDs into your basin YAML
4. (Optional) Re-run with `USE_CELL_EXTRACTION = True` if you need all cells within the watershed boundary (takes ~3 hours)

---

## Part 4 — EVT1 Calibration (NB01)

**Notebook**: `calibration/notebooks/01_evt_pot_calibration_workflow.ipynb`

**Purpose**: Fits a Generalized Pareto Distribution (GPD) to the extremes of the historical discharge time series. This produces the EVT1 statistical model: a threshold `u` and parameters `ξ` (shape) and `σ` (scale) that describe the behaviour of extreme discharge events at each GloFAS cell.

### Key input parameters (Section 0.2)

```python
USE_MUNI_AOI  = False       # False = watershed mode; True = municipality cluster
BASIN_ID      = "my_basin"  # Must match basin_id in your YAML
run_name      = "2026-05-07_initial"  # Label for this calibration run
```

### How threshold selection works

**Threshold selection is fully automatic.** You do not need to manually inspect a plot and type a threshold value. The notebook calls `auto_select_threshold_pot()` from `src/philflood/models/ev/threshold_selection.py`, which uses a 3-tier stability algorithm:

| Tier | Condition | Meaning |
|------|-----------|---------|
| **1 — Stable** ✅ | GPD ξ and σ stabilize across adjacent quantile candidates | Good data; model is well-behaved |
| **2 — Conservative** ⚠️ | Stability not reached; use lowest quantile with sufficient events | Marginal data quality; proceed with caution |
| **3 — Fallback** ❌ | No stable or conservative threshold found; uses 95th percentile | Poor data quality; review discharge record |

The tier is shown in the output diagnostics table. A `fallback` result is a warning that the historical record may be too short or that the basin has unusual hydrology. Interpret high-RP estimates with particular caution in this case.

**Manual override** (use only with domain reason):
```python
threshold_override = None    # set e.g. to 1500.0 to force a specific threshold
```

### Diagnostic plots (validate after auto-selection)

NB01 produces several validation plots. These do **not** require user action but should be reviewed:

**MRL (Mean Residual Life) plot**: Plots mean excess above each candidate threshold. The selected threshold (green dashed line) should fall in a region where the curve is approximately linear. Non-linearity above the threshold suggests the GPD assumption may not hold.

**Parameter stability plot**: Shows ξ and σ across candidate thresholds. Values should flatten out above the selected threshold. Wild variation suggests an unstable fit.

**Bootstrap return levels**: Shows RP estimates with 95% confidence intervals. Must increase monotonically. Wide intervals (CV > 0.30) indicate high uncertainty at high return periods.

**GoF diagnostics**: The output parquet includes `gof_pass` (boolean) and `gof_pvalue` (float) per gauge, derived from a KS test on the probability integral transform. Gauges where `gof_pass = False` should be examined — consider whether to exclude them or to manually override the threshold.

### Outputs

| File | Location | Contents |
|------|----------|---------|
| `run_config.json` | `data/processed/calibration/{basin_id}/{run_tag}/` | Master config for downstream notebooks |
| `evt_pot_calibration.parquet` | same | Per-gauge GPD parameters + diagnostics |
| `return-period_all.nc` | same | Return period estimates as CF-compliant NetCDF |

The `evt_pot_calibration.parquet` columns used downstream:

| Column | Renamed to (NB04/NB07) | Meaning |
|--------|----------------------|---------|
| `virtual_gauge_id` | `cell_id` | GloFAS grid cell identifier |
| `threshold_m3s` | `u` | POT discharge threshold (m³/s) |
| `gpd_xi` | `xi` | GPD shape parameter (EVT convention: positive = heavy tail) |
| `gpd_sigma` | `sigma` | GPD scale parameter |
| `lambda_events_per_year` | `lam` | Poisson event rate |

### Auto-detection by downstream notebooks

All notebooks NB02–NB06 find the NB01 output automatically:
```python
from philflood.ops.config import load_run_config
cfg = load_run_config(PROCESSED_ROOT, auto_select_latest=True)
```
This picks the most recently modified `run_config.json` under `data/processed/calibration/`. To use a specific run, pass `run_config_path` explicitly.

---

## Part 5 — Flood Hazard Maps (NB02)

**Notebook**: `calibration/notebooks/02_HazardOnly_Workflow.ipynb`

**Purpose**: Downloads JRC Global Flood Map tiles for the basin bounding box, merges them into a single mosaic, and regrids to a CLIMADA Hazard object (HDF5). The output contains flood depth maps at 8 return periods (1, 10, 20, 50, 75, 100, 200, 500 years).

### Key parameters

```python
AUTO_DETECT   = True    # Recommended: auto-load from latest NB01 run_config.json
APPLY_FLOPROS = False   # True applies flood protection masking (experimental)
LOW_RAM_MODE  = None    # None = auto-detect; set True/False to force
```

Memory auto-detection: if the machine has <8 GB of available RAM, the notebook enables `LOW_RAM_MODE` automatically (256×256 tile chunks). Override with the `PHILFLOOD_LOW_RAM=1` environment variable.

### What is downloaded and where

JRC tiles are fetched from CEMS using your EWDS credentials. Tiles are cached in `_jrc_cache/` — on re-runs only missing tiles are downloaded.

### Output

```
data/processed/climada_hazard/{basin_id}/{run_tag}/climada_hazard_{basin_id}.hdf5
```

The HDF5 file contains a CLIMADA Hazard object: 8 events (return periods) × N centroids (100m grid cells within the basin). Each event stores flood depth in metres.

Validate the output with:
```python
from climada.hazard import Hazard
haz = Hazard.from_hdf5("climada_hazard_*.hdf5")
assert haz.intensity.shape[0] == 8    # 8 return periods
assert haz.check()                    # Internal CLIMADA validation
```

### Known issues

- Basins larger than ~50,000 km² take 30–60 minutes for JRC tile download.
- If "No tiles selected" is reported, JRC does not cover your basin (see Section 2.4).
- All 8 return periods are preserved (fixed in v0.3.0; earlier versions only kept 1 RP).

---

## Part 6 — Validation (NB03, optional)

**Notebook**: `calibration/notebooks/03_validation_notebook.ipynb`

**Purpose**: Validates NB02 hazard maps against observed flood extents. Produces confusion matrices and scores (F1, IoU, Bias, Precision, Recall) per return period.

### When to run

Run this step only if you have **historical flood extent data** — satellite-derived inundation maps (e.g., from Copernicus EMS Rapid Mapping, UNOSAT, or Sentinel-1 SAR processing) or field-mapped flood extents for known events.

This step is **not required** to produce risk profiles. However, for any first deployment in a new country, running validation gives confidence that the JRC hazard maps reflect real flood behaviour in that specific region.

### What you need

- NB02 flood depth TIFFs
- One or more observed flood extent shapefiles (polygon, EPSG:4326) with a known event date
- A binary flood depth classification threshold (default: 0.2 m)

### What to do if validation fails

Low F1 / high Bias suggests the JRC maps are not well-calibrated for your basin. Options:
1. Adjust the depth threshold (try 0.1 m or 0.3 m)
2. Investigate whether the event return period is correctly estimated
3. Note the validation metrics in your documentation and apply appropriate uncertainty to risk profile outputs

---

## Part 7 — Event Catalog & EVT2 Curve (Simplified NB04)

**Notebook**: `calibration/notebooks/04_ImpactCatalogue_ImpactEVT_CATMODEL_10000y_UPDATED.ipynb`

**Purpose**: Detects historical flood events from the GloFAS discharge record, computes how many people were affected in each event (using NB02 hazard maps × WorldPop), and fits a second statistical model (EVT2) to the distribution of population impacts.

### ⚠️ Stop before Section 7

For humanitarian operations, **run only Sections 0–6**. Do not run Section 7 or later.

Section 7 processes the GloFAS reforecast GRIB archive (~200 GB, 10–40 hours compute). It generates additional synthetic events from ensemble diversity — useful for insurance-grade applications where the historical record is sparse. For humanitarian RP2/5/10 thresholds, the EVT2 model fitted to historical events is sufficient.

**Optional robustness step**: If your historical event catalog contains fewer than 25 events, consider running Section 7 to supplement the catalog. The reforecast data adds ensemble diversity but does not change the underlying hydrological model — it provides more realizations of the same physics. This trade-off should be documented when reporting results.

### Sections to run

| Section | What it does |
|---------|-------------|
| 0–1 | Config, dependencies, load `run_config.json` |
| 2 | Load EVT1 params from `evt_pot_calibration.parquet` |
| 3 | Support mask: JRC RP500 wet cells (defines spatial extent) |
| 4–4C | Detect historical flood events via connected-component labelling on active GloFAS cells |
| 5 | Compute population impact per event: flood depth TIFFs × WorldPop raster at 11 depth thresholds (0.01–1.0 m) |
| 6–6C | Fit EVT2 (spliced empirical body + POT-GPD tail) to historical impact peaks |

### EVT2 output parameters

The key output is `evt2_fit_popaffected_op.json` (primary depth threshold at 0.02 m):

| Field | Meaning |
|-------|---------|
| `u` | Threshold: minimum population impact to qualify as an "extreme event" |
| `xi` | GPD shape (positive = heavy tail; typical range 0.1–0.4 for flood impacts) |
| `sigma` | GPD scale (spread of impacts above threshold) |
| `lam_total` | Total Poisson event rate per year (all events, not just extremes) |
| `p_exc` | Proportion of events exceeding the threshold u |
| `tier` | Threshold selection tier: `stable` / `conservative` / `fallback` |

**Minimum data requirement**: At least 20 historical flood events above the EVT2 threshold are needed for reliable fitting. If the catalog has fewer, the `tier` output will be `fallback` and high-RP estimates will carry very wide uncertainty. This should be reported explicitly in any operational documentation.

### Outputs

| File | Path | Used by |
|------|------|---------|
| `evt2_fit_popaffected_op.json` | `{output_dir}/evt2/` | NB05, NB06 (primary EVT2 fit) |
| `evt2_fit_manifest.json` | `{output_dir}/evt2/` | NB05 multi-threshold comparison |
| `evt2_return_levels_popaffected_op.parquet` | `{output_dir}/evt2/` | NB05 RP curve validation |
| `event_registry_hist.parquet` | `{output_dir}/` | NB05, NB06 historical event list |

---

## Part 8 — Risk Profiles (Simplified NB05)

**Notebook**: `calibration/notebooks/05_Risk_Profiles_IMPROVED_UPDATED_EPMatrix.ipynb`

**Purpose**: Produces Occurrence Exceedance Probability (OEP) and Annual Exceedance Probability (AEP) curves showing the probability of exceeding a given population impact level. Also produces point estimates of people affected at RP2, RP5, RP10 for trigger threshold setting.

### Simplified path for humanitarian operations

The full NB05 runs a **10,000-year Year Loss Table (YLT) Monte Carlo simulation**. For humanitarian operations, a **1,000-year simulation** is sufficient there is no reforecast enrichment here, so the simulation will only use the footprints on the hisotrical catalogue.

**`N_SIM_YEARS` parameter**: Change this from 10,000 to 1,000 for the humanitarian workflow. This reduces simulation time by 10× with negligible impact on RP2/5/10 estimates.

### Direct GPD formula for quick estimates

For rapid estimates without running the simulation, the return period–impact relationship can be computed directly from the EVT2 parameters:

```python
import json, numpy as np

# Load EVT2 parameters
with open("data/processed/impact_catalogue_catmodel/.../evt2/evt2_fit_popaffected_op.json") as f:
    evt2 = json.load(f)

u, xi, sigma, lam = evt2["u"], evt2["xi"], evt2["sigma"], evt2["lam_total"]

# Impact (people affected) at a given return period T (years)
def impact_at_rp(T, u, xi, sigma, lam):
    return u + (sigma / xi) * ((lam * T) ** xi - 1)

for rp in [2, 5, 10]:
    n = impact_at_rp(rp, u, xi, sigma, lam)
    print(f"RP{rp}: ~{n:,.0f} people affected")
```

These point estimates are useful for stakeholder briefings and prioritizing. The full YLT simulation is needed for the probabilistic framing stakeholders need for insurance purposes and robustness. (Heavy to compute and download, could take weeks)

### Spatial aggregation mode

Set `USE_MUNI` to match the mode used in NB01:
- `USE_MUNI = False` → single watershed aggregate
- `USE_MUNI = True` → per-municipality / admin unit profiles

### Default return periods for humanitarian triggers

The following RP thresholds correspond to the three humanitarian activation tiers:

| Tier | Return Period | Label | Meaning |
|------|-------------|-------|---------|
| T1 | RP2 | Moderate Watch | 1-in-2-year event; elevated readiness |
| T2 | RP5 | High Alert | 1-in-5-year event; pre-position resources |
| T3 | RP10 | Very High Activation | 1-in-10-year event; deploy response |

These tiers are defined per default in the trigger pipeline; see `docs/operations/trigger-pipeline-handover.md`.

### Key outputs

| File | Contents | Used by |
|------|----------|---------|
| `watershed_oep_curve.json` | Watershed-level OEP: array of `{return_period, pop_affected}` | NB06 (required) |
| `oep_curves_all_units.json` | Per-admin-unit OEP at each RP | Trigger pipeline |
| Excel workbook | Stakeholder-facing risk profiles + EP curves | Reporting |

---

## Part 9 — Scenario Flood Maps (Simplified NB06)

**Notebook**: `calibration/notebooks/06_flood_event_viewer.ipynb`

**Purpose**: Interactive HTML flood maps and event classification for stakeholder communication.

### Current state and humanitarian adaptation

The current NB06 is an **event viewer** — it loads named historical flood events and classifies their severity using the NB05 OEP curve. This requires the full event registry from NB04 and the `watershed_oep_curve.json` from NB05.

For humanitarian operations, you generally want **general scenario maps** at fixed return periods (RP2, RP5, RP10) rather than event-specific maps. The existing NB06 can produce these maps if you:
1. Have completed NB02 (JRC hazard maps available)
2. Have completed NB05 (`watershed_oep_curve.json` available)
3. Focus on the RP-scenario rendering cells rather than the event-specific cells

> **[Missing Task #4]** A dedicated `06H_ScenarioMaps_Humanitarian.ipynb` does not yet exist. See [Part 10](#part-10--contributor-roadmap). Until it is built, use the RP-scenario rendering portion of NB06 and skip the event-catalog sections.

### What the maps show

- **Flood depth layer**: JRC RP maps at RP2, RP5, RP10 — flood depth in metres, coloured YlOrRd (yellow → orange → red) overlaid on OpenStreetMap basemap
- **Population exposure layer**: WorldPop pixels where depth > 0.02 m
- **Admin summary table**: ADM3/ADM2 × RP2/5/10 exposed population counts

### Hard dependency on NB05

NB06 requires `watershed_oep_curve.json` from NB05 to classify event severity. Run NB05 first. NB06 will fail without this file.

---

## Part 10 — Contributor Roadmap

The following tasks are suggested to fully simplify and make this workflow country-agnostic. Each is described with enough context to start working independently.

---

### Task 1 — `00B_data_preparation.ipynb` (High Priority)

**What**: A single notebook that accepts `COUNTRY_ISO3`, `COUNTRY_NAME`, and bounding box `[N, W, S, E]`, then downloads WorldPop, HydroSHEDS, and admin boundaries automatically.

**Why**: Currently users must manually download three datasets from three different websites and place files in the correct directories. This is the biggest friction point for deploying in a new country.

**How to build**:
- WorldPop REST API: `https://hub.worldpop.org/rest/data/pop/cic2020_100m?iso3={ISO3}` — returns download URL for the constrained 100m product
- HydroSHEDS: No public API; use `requests` to download from the direct file links on the HydroSHEDS product page; detect continent from bounding box centroid
- Admin boundaries: OCHA HDX API (`https://data.humdata.org/api/3/action/package_search?q={country}+admin+boundaries&fq=tags:cod-ab`) — returns GeoJSON download links

**Files to create**: `calibration/notebooks/00B_data_preparation.ipynb`

---

### Task 2 — `04H_EventCatalog_EVT2_Humanitarian.ipynb` (High Priority)

**What**: A stripped-down version of NB04 containing only Sections 0–6 (historical event detection and EVT2 fitting). Adds a `HUMANITARIAN_MODE = True` flag that explicitly disables reforecast processing with a clear explanation.

**Why**: The current NB04 includes Section 7+ (reforecast library), which takes 10–40 hours. Analysts running the humanitarian workflow will be confused by the long Section 7 or may run it by accident.

**How to build**:
- Copy NB04; delete or gate-out all cells from Section 7 onwards
- Add `HUMANITARIAN_MODE` config cell at the top with a comment explaining the trade-off
- Reduce `N_BOOTSTRAP_EVT2` default from 200 to 50 (sufficient for RP2/5/10 decisions)
- Add a warning cell: if `len(event_registry_hist) < 20`, print a clear warning that EVT2 results may be unreliable

**Files to create**: `calibration/notebooks/04H_EventCatalog_EVT2_Humanitarian.ipynb`

---

### Task 3 — `05H_RiskProfiles_Humanitarian.ipynb` (High Priority)

**What**: A simplified NB05 that defaults to `N_SIM_YEARS = 1000` and adds a `QUICK_ESTIMATES = True` flag to also print direct GPD inversion results alongside the simulation.

**Why**: The 10K-year simulation takes ~20 minutes on a standard laptop and provides minimal benefit over 1K years when the EVT2 model is trained on historical data only (no reforecast enrichment). For operators who need a quick result, the direct GPD formula gives RP2/5/10 in seconds.

**How to build**:
- Copy NB05; change `N_SIM_YEARS` default to 1000
- Add `QUICK_ESTIMATES` cell that computes `impact_at_rp(T, u, xi, sigma, lam)` for T in [2, 5, 10] and prints a formatted summary
- Keep all OEP/AEP curve output unchanged (needed for NB06 and trigger pipeline)
- Keep `watershed_oep_curve.json` output unchanged (hard dependency)
- Make the per-municipality Excel workbook optional via `EXPORT_EXCEL = False`

**Key function** in `src/philflood/models/impact/impact_evt.py`:
```python
from philflood.models.impact.impact_evt import impact_to_return_period
```

**Files to create**: `calibration/notebooks/05H_RiskProfiles_Humanitarian.ipynb`

---

### Task 4 — `06H_ScenarioMaps_Humanitarian.ipynb` (Medium Priority)

**What**: A scenario-map notebook that renders RP2, RP5, RP10 flood maps from JRC hazard rasters without any event-specific processing.

**Why**: The current NB06 is an event viewer that requires the historical event registry and named event classification. For humanitarian scenario planning, you want fixed-RP maps regardless of what events happened historically.

**How to build**:
- Load JRC RP maps (from NB02 CLIMADA hazard HDF5 or intermediate TIFFs) hazard space.
- Dependency on `watershed_oep_curve.json` since this is the impact space.
- Create shapefiles and rasters for post-analysis. Viewer is nice to keep for those who only care about results.
- Export admin-unit table: `{adm_id, adm_name, rp2_exposed, rp5_exposed, rp10_exposed}`

**Files to create**: `calibration/notebooks/06H_ScenarioMaps_Humanitarian.ipynb`

---

### Task 5 — Country-agnostic parameterization (High Priority)

**What**: Audit all existing notebooks (NB00-02 through NB06) and replace every hardcoded Philippines-specific value with a configurable parameter.

**Key hardcoded values to find and replace**:

| Notebook | Hardcoded value | Replace with |
|----------|----------------|-------------|
| NB00-02 | `AREA = [35, 63, 4, 131]` (Philippines bbox) | `COUNTRY_ISO3`, `AREA` config cell |
| NB00-02 | G: Drive output path | `OUTPUT_ROOT` environment variable |
| NB01 | `"PHL"` in file discovery | `COUNTRY_ISO3` from basin config |
| NB04 | `phl_pop_*` worldpop glob | derive from `country_iso3` field |
| All | Absolute paths to shared drives | relative `data_root` from basin YAML |

---

### Task 6 — Plain-language diagnostics in NB01 (Medium Priority)

**What**: Add an automated verdict cell after the EVT1 calibration diagnostics that interprets the results in plain language for non-statisticians.

**Why**: The MRL and parameter stability plots are not interpretable without statistics training. An operator running the workflow for the first time will not know what "ξ > 0" means or whether a slightly non-linear MRL is a problem.

**How to build**:
- After the diagnostics table, add a cell that reads `gof_pass`, `mrl_linear_ok`, and threshold `tier` per gauge
- Print a formatted summary: ✅ for good, ⚠️ for warning, ❌ for failure
- Add a legend explaining the meaning of ξ in plain terms: *"positive ξ (heavy tail) means large floods are relatively more common than a normal distribution would predict — this is typical for river systems"*

---

### Task 7 — MRL + GoF for EVT2 threshold selection (Low Priority)

**What**: Wire `compute_mrl()` and `gpd_gof_test()` (already implemented in `src/philflood/models/ev/threshold_selection.py`) into NB04's `select_evt2_threshold()` function.

**Why**: NB01 EVT1 threshold selection already uses MRL linearity and KS GoF tests as additional criteria. NB04 EVT2 uses only parameter stability, which is less robust.

**Caution**: Impact data is noisier than discharge data, and sample sizes are much smaller. GoF tests have low power with <50 exceedances. Apply with looser tolerances than EVT1 and use as an informational flag rather than a hard gate.

**Files to modify**:
- `calibration/notebooks/04_ImpactCatalogue_ImpactEVT_CATMODEL_10000y_UPDATED.ipynb` (Section 6)
- `calibration/notebooks/04H_EventCatalog_EVT2_Humanitarian.ipynb` (Task 2, once created)

---

### Task 8 — NB07 function rename sync (Medium Priority)

NB07 (`07_Trigger_Validation_Reforecast.ipynb`) Cell 3 contains copied versions of NB04 helper functions with old names. After the NB04 v0.4.0 rename, these must be updated:

| Old name (in NB07) | New name (in NB04) |
|--------------------|-------------------|
| `w_to_rp_spliced` | `impact_to_rp_spliced` |
| `fit_evt2_spliced_wpeak` | `fit_evt2_spliced_impact` |
| `w_peak_series` | `impact_peak_series` |
| `RP_W_peak` | `RP_impact` |

Remove any copies of deleted functions: `sample_w_from_evt2`, `compute_w_series_from_discharge`.

**Files to modify**: `calibration/notebooks/07_Trigger_Validation_Reforecast.ipynb`

---


## Appendix A — Workflow Summary

```
NB00-02   Download GloFAS historical (8–12 h, resume-safe)
           ↓
[00B]     [TODO] Download WorldPop, HydroSHEDS, admin bounds
           ↓
NB01      EVT1 calibration — auto-threshold → evt_pot_calibration.parquet
           ↓
NB02      Hazard maps — JRC tiles → CLIMADA Hazard HDF5
           ↓
[NB03]    [Optional] Validate against observed flood extents
           ↓
NB04*     Event catalog (Sections 0–6 only) → evt2_fit_popaffected_op.json
           ↓
NB05*     Risk profiles (N_SIM_YEARS=1000) → OEP curves + RP2/5/10 table
           ↓
NB06*     Scenario maps (RP2, RP5, RP10 flood depth + pop exposure)

* = simplified humanitarian version (Tasks 2–4 not yet implemented as separate notebooks)
```

---

## Appendix B — Data Directory Structure

```
data/
├── raw/
│   ├── glofas/
│   │   └── historical/version_4_0/consolidated/discharge/grib2/
│   │       └── area_{N}_{W}_{S}_{E}/
│   │           └── {year}/data.grib
│   ├── worldpop/
│   │   └── {ISO3}/
│   │       └── {iso3}_pop_{year}_CN_100m_R{release}A_v1.tif
│   ├── hydrobasins/
│   │   ├── level_6/hybas_{continent}_lev06_v1c.gpkg
│   │   ├── level_8/hybas_{continent}_lev08_v1c.gpkg
│   │   └── level_12/hybas_{continent}_lev12_v1c.gpkg
│   └── admin/
│       ├── {ISO3}_adm2.geojson
│       └── {ISO3}_adm3.geojson
└── processed/
    ├── calibration/
    │   └── {basin_id}/{run_tag}/
    │       ├── run_config.json
    │       ├── evt_pot_calibration.parquet
    │       └── return-period_all.nc
    ├── climada_hazard/
    │   └── {basin_id}/{run_tag}/
    │       └── climada_hazard_{basin_id}.hdf5
    ├── impact_catalogue_catmodel/
    │   └── {basin_id}/{run_tag}/
    │       ├── event_registry_hist.parquet
    │       └── evt2/
    │           ├── evt2_fit_popaffected_op.json
    │           ├── evt2_fit_manifest.json
    │           └── evt2_return_levels_popaffected_op.parquet
    └── Riskprofiles/
        ├── watershed_oep_curve.json
        └── oep_curves_all_units.json
```

---

## Appendix C — Cross-references

| Topic | Document |
|-------|---------|
| Trigger algorithm specification | `docs/operations/trigger-pipeline-handover.md` |
| Statistical methodology (EVT, GPD theory) | `docs/technical/methods-overview.md` |
| Glossary of terms (POT, GPD, EVT, OEP, AEP) | `docs/technical/GLOSSARY.md` |
| Architecture and module layout | `docs/technical/ARCHITECTURE.md` |
| NB01 calibration deep dive | `docs/user-guides/notebook01-calibration-guide.md` |
| NB02 hazard maps deep dive | `docs/user-guides/notebook02-hazard-guide.md` |
| Notebook config pattern (`load_run_config`) | `docs/user-guides/notebook-config-guide.md` |
| Troubleshooting common errors | `docs/user-guides/troubleshooting.md` |
