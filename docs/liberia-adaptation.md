# Adapting Notebook 01 for Liberia

**Analyst:** Silvia  
**Date started:** 2026-05-20  
**Notebook:** `calibration/notebooks/01_evt_pot_calibration_workflow.ipynb`  
**Target basin:** Saint Paul River (`saint_paul_01`)  
**Target output:** Population exposure table — County × District × RP2/5/10 (Montserrado, Lofa, Grand Bassa, Nimba + national total)  
**Status:** 🔄 In progress

This file tracks every change needed to run the calibration notebook for Liberia (LBR) instead of the Philippines (PHL). Changes are grouped into: things already done, things to edit in the notebook, new files to create, and data still needed.

---

## ✅ What's already done


| Item                                    | Status    | Detail                                                                                                                         |
| --------------------------------------- | --------- | ------------------------------------------------------------------------------------------------------------------------------ |
| GloFAS historical GRIB data (1979–2025) | ❌ Wrong region — re-download needed | `data/raw/glofas/historical/version_4_0/consolidated/discharge/grib2/area_-4_4_-12_10/` — 47 years present **but covers central Africa (Congo/Gabon), not Liberia** |


> **🚨 GRIB data confirmed wrong region — re-download required.**
> Verification script output:
> ```
> Lat range: -11.975 → -4.025   (≈ 12°S to 4°S — central Africa)
> Lon range:   4.025 → 9.975   (≈ 4°E to 10°E — Congo/Gabon area)
> ```
> Liberia sits at approximately 4–9°N, 7–12°W — this data does not cover it at all.
>
> **Action required:** Re-download via NB00-02 with `AREA = [10, -12, 4, -7]` (N=10, W=−12, S=4, E=−7).  
> This will write data to: `data/raw/glofas/historical/version_4_0/consolidated/discharge/grib2/area_10_-12_4_-7/`  
> Then update Changes 4 and 5 below to use area tag `area_10_-12_4_-7`.
>
> **⚠️ Credentials gotcha:** Before running NB00-02, make sure your `.cdsapirc` uses the **EWDS** URL, not the regular CDS URL. GloFAS (`cems-glofas-historical`) is hosted on the Early Warning Data Store, not the standard Climate Data Store.
> - ✅ Correct: `url: https://ewds.climate.copernicus.eu/api`
> - ❌ Wrong:   `url: https://cds.climate.copernicus.eu/api` → gives 404 `process not found`
>
> The file lives at `~/.cdsapirc` and is mirrored at `calibration/notebooks/.cdsapirc` — update both.

---

## 📝 Changes to make in the notebook

All edits are in **Cell 4** (Section 2A – User Inputs) unless otherwise noted.

---

### Change 1 — Basin config file path

**Cell:** 4 · **Status:** ⬜ To do

```python
# FROM (Philippines, Windows-style path):
basin_config_file = r"ops\configs\basins\Cagayan_01.yaml"

# TO (Saint Paul River, Liberia):
basin_config_file = "ops/configs/basins/saint_paul_01.yaml"
```

> The new file `ops/configs/basins/saint_paul_01.yaml` has been created — see **New files** section below.

---

### Change 2 — Admin boundary file

**Cell:** 4 · **Status:** ⬜ Blocked — file not yet downloaded

```python
# FROM (Philippines ADM3):
adm3_geojson = REPO_ROOT / "data/raw/vectors/admin/phl_cod_ab/phl_adm3.geojson"

# TO (Liberia ADM3 — GADM clan level, 305 clans):
adm3_geojson = REPO_ROOT / "data/raw/vectors/admin/lbr_cod_ab/gadm41_LBR_3.json"
```

> File is already on disk at `data/raw/vectors/admin/lbr_cod_ab/gadm41_LBR_3.json` (GADM v4.1).  
> 305 features, `TYPE_3 = "Clan"`. Unique ID column: `GID_3` (e.g. `"LBR.1.1.1_1"`). Name column: `NAME_3`.

---

### Change 3 — HydroBASINS shapefile (wrong continent)

**Cell:** 4 · **Status:** ⬜ Blocked — file not yet downloaded

```python
# FROM (Australasia/Asia-Pacific region — wrong for Liberia):
hybas_l12_shp = REPO_ROOT / "data/raw/vectors/hydrobasins/australasia/hybas_au_lev01-12_v1c/hybas_au_lev12_v1c.shp"

# TO (Africa region):
hybas_l12_shp = REPO_ROOT / "data/raw/vectors/hydrobasins/africa/hybas_af_lev01-12_v1c/hybas_af_lev12_v1c.shp"
```

> Download source: [HydroSHEDS — HydroBASINS](https://www.hydrosheds.org/products/hydrobasins)  
> Select: **Africa**, Level 1–12 package (file name: `hybas_af_lev01-12_v1c.zip`)  
> Free registration required on the HydroSHEDS website.  
> Unzip to: `data/raw/vectors/hydrobasins/africa/hybas_af_lev01-12_v1c/`

---

### Change 4 — GloFAS GRIB root path

**Cell:** 4 · **Status:** ⬜ Blocked — correct Liberia data not yet downloaded

```python
# FROM (Windows Google Drive path, Philippines area tag):
glofas_grib_root = Path(r"G:\My Drive\GLOFAS_ImpactFloodForecasting_PHL\data\raw\glofas\historical\version_4_0\consolidated\discharge\grib2\area_35_63_4_131")

# TO (local repo path, correct Liberia area tag — after re-download):
glofas_grib_root = REPO_ROOT / "data/raw/glofas/historical/version_4_0/consolidated/discharge/grib2/area_10_-12_4_-7"
```

> ⚠️ The data currently on disk (`area_-4_4_-12_10`) covers central Africa — **do not use it**.  
> Re-download via NB00-02 with `AREA = [10, -12, 4, -7]` first, then apply this change.  
> `REPO_ROOT` is automatically set in Cell 2 of the notebook.

---

### Change 5 — Timeseries cache directory

**Cell:** 22 (Section 8 – Extract Historical Discharge) · **Status:** ⬜ Blocked — correct Liberia data not yet downloaded

```python
# FROM (Philippines area tag in path):
timeseries_dir = processed_root / "glofas" / "v4" / "area_35_63_4_131" / "timeseries" / "virtual_gauges"

# TO (correct Liberia area tag — after re-download):
timeseries_dir = processed_root / "glofas" / "v4" / "area_10_-12_4_-7" / "timeseries" / "virtual_gauges"
```

> This is the cache folder where extracted per-gauge discharge `.parquet` files are stored.  
> ⚠️ Use the `area_10_-12_4_-7` tag (matching the re-downloaded GRIB folder), not `area_-4_4_-12_10`.

---

### Change 6 — Run name

**Cell:** 4 · **Status:** ⬜ To do (cosmetic but useful for output organisation)

```python
# FROM:
run_name = "2026-05-18_calib-test"

# TO (example — update to today's date and your basin name):
run_name = "2026-05-20_LBR-calib"
```

---

### Change 7 — Add `adm3_id` column (Liberia has ADM2 only)
**Cell:** 7 (Section 3 – Load Geographic Boundaries) · **Status:** ⬜ To do

The notebook hard-requires a column named `adm3_id`. Liberia's OCHA COD only goes to ADM2 level — both `lbr_adm2.geojson` and `lbr_adm3.geojson` are identical ADM2 files (136 districts) with column `adm2_pcode` as the unique ID.

Add these two lines immediately after `adm3_gdf = read_vector(adm3_geojson)` in Cell 7:

```python
adm3_gdf = read_vector(adm3_geojson)

# Liberia has ADM2 only — create adm3_id from adm2_pcode so the notebook's
# column checks pass. adm2_pcode contains the unique district code e.g. "LR0601".
if "adm3_id" not in adm3_gdf.columns:
    adm3_gdf["adm3_id"] = adm3_gdf["GID_3"]
```

---

### Change 8 — Fix hardcoded Australasia HydroBASINS prefix in basin mode
**Cell:** 7 (Section 3 – Load Geographic Boundaries) · **Status:** ⬜ To do

When running in basin mode (i.e. `ANALYZE_BY_MUNICIPALITY = False`), Cell 7 builds the path to the context-level HydroBASINS shapefile with `hybas_au` (Australasia) hardcoded — it will look for `hybas_au_lev06_v1c.shp` instead of `hybas_af_lev06_v1c.shp` and crash with `FileNotFoundError`.

Replace:
```python
hybas_context = hybas_parent / f"hybas_au_lev{level_str}_v1c.shp"
```

With:
```python
# Derive continent code from the L12 filename (e.g. "hybas_af_lev12_v1c" → "af")
continent_code = hybas_l12_shp.stem.split("_")[1]
hybas_context = hybas_parent / f"hybas_{continent_code}_lev{level_str}_v1c.shp"
```

---

## 🗂️ New files to create

### `ops/configs/basins/saint_paul_01.yaml`

**Status:** ✅ Created (placeholder — `hydrobasins_id` and EVT values to be filled)

File is at `ops/configs/basins/saint_paul_01.yaml`.

- **`hydrobasins_id`**: Must be confirmed in QGIS. Best candidates from bounding box analysis:
  - `1060024880` — lon[−11.6,−9.2] lat[6.4,8.7] — most likely Saint Paul River outlet basin
  - `1060024870` — lon[−10.8,−8.6] lat[6.3,8.8] — alternative
  - Open `data/raw/vectors/hydrobasins/africa/hybas_af_lev01-12_v1c/hybas_af_lev06_v1c.shp` in QGIS → Identify Features (`Cmd+Shift+I` on macOS) → click the Saint Paul River basin polygon → note `HYBAS_ID`
- **`glofas_point_ids`**: Leave as placeholder — NB01 Sections 4–7 fill these automatically
- **EVT parameters**: All filled after completing NB01

---

## 📥 Data files still needed


| File                                    | Expected path                                                                      | Source                                                        | Status           |
| --------------------------------------- | ---------------------------------------------------------------------------------- | ------------------------------------------------------------- | ---------------- |
| Liberia ADM3 clan boundaries (GADM) | `data/raw/vectors/admin/lbr_cod_ab/gadm41_LBR_3.json` | [GADM v4.1](https://gadm.org/download_country.html) | ✅ Present (305 clans) |
| HydroBASINS Africa Level 12 shapefile   | `data/raw/vectors/hydrobasins/africa/hybas_af_lev01-12_v1c/hybas_af_lev12_v1c.shp` | [HydroSHEDS](https://www.hydrosheds.org/products/hydrobasins) | ⬜ Not downloaded |


> Both files are free but require registration/account on their respective portals.

---

## 🔢 Summary checklist

Before running the notebook end-to-end, confirm:

- **Change 1** — `basin_config_file` updated to `"ops/configs/basins/saint_paul_01.yaml"`
- **Change 2** — `adm3_geojson` updated to Liberia path + file downloaded
- **Change 3** — `hybas_l12_shp` updated to Africa region + file downloaded
- **Change 4** — `glofas_grib_root` updated to `area_10_-12_4_-7` (after re-download)
- **Change 5** — `timeseries_dir` updated to `area_10_-12_4_-7` (after re-download)
- **Change 6** — `run_name` updated (cosmetic)
- **Change 7** — `adm3_id` column added after loading admin boundaries in Cell 7
- **Change 8** — Hardcoded `hybas_au` prefix fixed to derive continent from filename in Cell 7
- **🚨 Re-download GRIB data** — run NB00-02 with `AREA = [10, -12, 4, -7]`; existing `area_-4_4_-12_10` data confirmed to be central Africa (Congo/Gabon), not Liberia
- **Find HYBAS_ID** — open `hybas_af_lev06_v1c.shp` in QGIS, click Saint Paul basin, update `hydrobasins_id` in `saint_paul_01.yaml` (candidates: `1060024880`, `1060024870`)
- **Post-calibration** — `ops/configs/basins/saint_paul_01.yaml` updated with fitted EVT parameters (`threshold_m3s`, `gpd_shape_xi`, `gpd_scale_sigma`, `event_rate_per_year`) and actual `glofas_point_ids`
- **⚠️ RP2 and RP5 missing** — project target requires RP2/5/10 but NB01 only produces RP10/20/50/75/100/200/500. To add RP2 and RP5: edit `RETURN_PERIODS` list in Section 11C cell and re-run from Section 11C onwards (fast — extraction already done)

---

## 🗒️ Notes & decisions log


| Date       | Note                                                                                                             |
| ---------- | ---------------------------------------------------------------------------------------------------------------- |
| 2026-05-20 | File created. GRIB data 1979–2025 confirmed present. Admin boundaries and HydroBASINS Africa not yet downloaded. |
| 2026-05-20 | Admin boundaries and HydroBASINS downloaded by user. `lbr_adm3.geojson` is a copy of ADM2 (136 districts, column `adm2_pcode`). Added Change 7 (`adm3_id` alias) and Change 8 (hardcoded `hybas_au` prefix fix). |
| 2026-05-20 | Found GADM v4.1 ADM3 clan boundaries at `gadm41_LBR_3.json` (305 clans, `GID_3` as ID, `NAME_3` as name). Updated Change 2 and Change 7 to use this file instead of the ADM2 copy. |
| 2026-05-20 | Project slides confirm target basin is Saint Paul River (`saint_paul_01`). Correct Liberia GRIB bbox is `[10, -12, 4, -7]` → expected folder `area_10_-12_4_-7`. Data on disk is `area_-4_4_-12_10` — **needs verification**. Created `saint_paul_01.yaml`. HYBAS_ID candidates: `1060024880` or `1060024870` (confirm in QGIS). Target deliverable: County × District × RP2/5/10 table for Montserrado, Lofa, Grand Bassa, Nimba + national total. |
| 2026-05-20 | **GRIB region verified — confirmed wrong.** Verification script output: lat −11.975→−4.025, lon 4.025→9.975. This is central Africa (Congo/Gabon), not Liberia. Data must be re-downloaded via NB00-02 with `AREA = [10, -12, 4, -7]`. Changes 4 and 5 updated to use `area_10_-12_4_-7` as the target area tag. |
| 2026-05-20 | **EWDS URL fix.** NB00-02 was failing with `404 process not found` for `cems-glofas-historical`. Cause: `.cdsapirc` had `url: https://cds.climate.copernicus.eu/api` (regular CDS) instead of `url: https://ewds.climate.copernicus.eu/api` (EWDS, where GloFAS lives). Fixed in both `~/.cdsapirc` and `calibration/notebooks/.cdsapirc`. Added explanatory comments to both files. |
| 2026-05-24 | **HYBAS_ID confirmed in QGIS.** Saint Paul River catchment is `1060024870` (covers central-western Liberia draining toward Monrovia). Updated `saint_paul_01.yaml`. Note: Identify Features shortcut on macOS is `Cmd+Shift+I`, not `I`. |
| 2026-05-24 | **GloFAS longitude convention fix.** NB01 Section 5 crashed with `RuntimeError: No grid cells found in any L12 polygons`. Root cause: GloFAS GRIB files for western-hemisphere regions store longitudes in 0–360° convention (Liberia's −12 to −7°E stored as 348–353°), but HydroBASINS L12 polygons use −180–180°. The spatial join found zero matches. Fixed in `src/philflood/adapters/glofas_grib_v4.py` → `open_grib_dataset()`: after opening, if `longitude.max() > 180`, subtract 360 from all longitude values. Also added `warnings.filterwarnings("ignore")` around the `xr.open_dataset` call to suppress harmless ECCODES zero-date padding warnings. |
| 2026-05-25 | **NB01 completed successfully.** 779 virtual gauges across the Saint Paul basin. 47 years coverage. All gauges passed monotonicity and zero fallbacks. Outputs in `data/processed/calibration/evt_pot/saint_paul_01/2026-01-19_calib-test/`. Key outputs: `evt_pot_calibration.parquet`, `return_levels/return_levels_bootstrap.parquet`, `climada_flood_hazard.nc`. Note: `return-period_all.nc` (also present) is from a different section and stores values incorrectly — use `climada_flood_hazard.nc` for downstream work. Return periods produced: RP10/20/50/75/100/200/500 — RP2 and RP5 still needed for final deliverable. |
| 2026-05-25 | **NB02 AOI fallback bug — wrong JRC tiles downloaded.** `detect_calibration_mode()` in NB02 Cell 5 falls through to a hardcoded Philippines bounding box (`box(116, 4, 127, 22)`) for basin mode, because it tries to load `hydrobasins_philippines.shp` which doesn't exist for Liberia. Result: 42 Philippines tiles (N10_E110, N20_E120, etc.) were downloaded instead of the two Liberia tiles. The wrong tiles caused a kernel crash (GDAL segfault). **Fix applied to NB02 Cell 5:** replaced the Philippines-hardcoded fallback with logic that reads `hydrobasins_id` and `hydrobasins_level` from `saint_paul_01.yaml`, derives the continent code from `country_iso3`, and loads the correct polygon from `data/raw/vectors/hydrobasins/africa/hybas_af_lev01-12_v1c/hybas_af_lev06_v1c.shp`. The patched code correctly resolves the Liberia AOI to bounds `(−10.8°, 6.3°N, −8.6°, 8.8°N)` and selects exactly two tiles: `ID105_N10_W20` and `ID111_N10_W10`. Wrong Philippines tiles deleted from `data/raw/jrc_flood_maps/`. |
| 2026-05-25 | **NB02 completed successfully.** JRC tiles downloaded (`ID105_N10_W20`, `ID111_N10_W10`) for RP10/20/50/75/100/200/500. Flood depth computed for 7 return periods. CLIMADA hazard HDF5 saved as `climada_hazard_saint_paul_01.hdf5` (7 events, ~9.5M centroids, 2.04M non-zero intensity values). Minor NaN fringe: RP200 has 14,400 NaN cells and RP500 has 28,800 NaN cells at tile-edge positions — outside the main flooded area, no impact on exposure estimates. Flood depth max (nanmax): 27.51m (RP200), 27.67m (RP500). |
| 2026-05-25 | **Run tag mismatch fixed.** NB01 Cell 4 had two separate variables: `run_name` (display label, already updated) and `run_tag = "2026-01-19_calib-test"` (directory name, never updated from the original Philippines test value). Output directory renamed to `2026-05-25_LBR-saint-paul`, `run_config.json` paths updated, and `run_tag` corrected in NB01 Cell 4. |
| 2026-05-25 | **NB03 skipped (optional).** NB03 (validation against GFM satellite observations) is marked optional in the project slides and was skipped. Notes for future use: (1) `rasterstats` must be installed (`pip install rasterstats`); (2) Cell 6 hardcoded Windows/Philippines paths replaced with `REPO_ROOT`-relative paths (`HYBAS_L7_SHP`, `ADM3_GEOJSON`, `WORLDPOP_RASTER`, `GFM_VALIDATION_ROOT`, `JRC_RAW_ROOT`); (3) GFM satellite flood data for the Saint Paul basin would need to be placed in `data/interim/validation/GFM/saint_paul_01/` before validation can run. |
| 2026-05-25 | **NB04 Section 0 — hardcoded Windows paths and Philippines-only discovery fixed.** Four issues patched: (1) `REPO_ROOT = Path(r"C:\pipelines\...")` replaced with auto-detection using repo markers; (2) WorldPop search replaced `phl_pop*.tif` glob with `worldpop/**/*.tif` so it finds `lbr_pop_2025_CN_100m_R2025A_v1.tif`; (3) JRC fallback added — if no raw tiles found, uses NB02's `flood-maps_intermediate.nc` from the processed calibration directory; (4) `ANCILLARY_DIR` and `REFORECAST_GRIB_ROOT` switched to `RAW_ROOT`-relative paths, `REFORECAST_GRIB_AREA_SUBPATH` updated to `area_10_-12_4_-7` (Liberia). |
| 2026-05-25 | **NB04 Section 2 — admin ID/name field detection missing GADM columns.** `ADMIN3_ID_FIELD` lookup only checked for `pcode`, `adm3_id`, `ADM3_PCODE` (Philippines OCHA COD names); `ADMIN3_NAME_FIELD` only checked for `ADM3_EN`, `ADM3_NAME`, `adm3_name`. GADM v4.1 uses `GID_3` (ID) and `NAME_3` (name) — both raised `ValueError`. Fixed by adding `GID_3`, `GID_2`, `adm3_pcode`, `adm2_pcode` to the ID candidates and `NAME_3`, `NAME_2` to the name candidates. |
| 2026-05-25 | **NB04 completed (Sections 0–3).** Impact catalogue built from 111 historical events (1979–2025, 2.4 events/year). Largest event: 2021-08-31 (659,959 people affected at 20 mm threshold). EVT2 GPD fit: xi=−0.42 (bounded), sigma=204,384, threshold=241,464, KS p=0.036. Return levels at RP2/5/10: 366K/479K/542K people. Dominant exposure unit: Greater Monrovia (67% of cumulative exposure). Sections 4+ (10,000-year synthetic catalogue, reforecast library) not run per project slides — NB05 uses humanitarian simplified path instead. |
| 2026-05-25 | **NB05 — 8 fixes applied before first run.** Issues diagnosed and patched: (1–2) `REPO_ROOT = Path(r"C:\pipelines\...")` in Cells 1 and 2 replaced with auto-detection using repo markers; (3) `N_SIM_YEARS = 10_000` → `1_000` in Cell 2 (per project slides — sufficient for RP2/5/10, 10× faster); (4) `discover_reforecast_registries()` hard-fail replaced with fallback to `reforecast_library/checkpoints/year=2005/event_registry_hist.parquet` (111 historical events from NB04 Section 2); (5) `discover_impacts_by_admin()` hard-fail replaced with fallback to `reforecast_library/checkpoints/year=2005/impacts_by_admin_historical.parquet` (157,509 rows, long-format with `depth_thr_m` and `affected_pop`); (6) `HYBAS_DIR` hardcoded to `australasia/hybas_au_lev01-12_v1c` replaced with dynamic continent derivation from `cfg["country_iso3"]` → `africa/hybas_af_lev01-12_v1c` for LBR; (7) `ADMIN3_ID_FIELD` lookup extended to include `GID_3`, `GID_2`; `ADMIN3_NAME_FIELD` extended to include `NAME_3`, `NAME_2`; (8) `ADM2_NAME_COL = "adm2_name"` (hardcoded Philippines OCHA name) replaced with dynamic detection checking `NAME_2`, `adm2_name`, `ADM2_NAME`, `ADM2_EN`. |
| 2026-05-25 | **NB05 — 3 further fixes during first run.** (A) `ValueError: Duplicate column names ['NAME_2', 'NAME_2']` — both `ADMIN3_NAME_FIELD` and `ADM2_NAME_COL` resolved to `"NAME_2"` because the lookup iterated over dataframe columns (where `NAME_2` col 8 appears before `NAME_3` col 10). Fixed by iterating candidate list in priority order instead: `ADMIN3_NAME_FIELD` now tries `NAME_3` first, falling back to `NAME_2`; `ADMIN3_ID_FIELD` tries `GID_3` first. (B) `DataSourceError: '.prj' not recognised` — glob `*lev06*.*` matched all shapefile sidecar files (`.dbf`, `.prj`, `.shp`, `.shx`); first alphabetically is `.dbf`. Fixed by changing glob to `*lev06*.shp`. (C) `KeyError: 'adm3_name'` in Cell 9 diagnostic — `nb5_xwalk` renamed only `ADM3_ID_COL → "adm3_id_num"` but left `ADM3_NAME_COL` as `"NAME_3"`; downstream code expected the canonical name `"adm3_name"`. Fixed by adding `ADM3_NAME_COL: "adm3_name"` and `ADM2_NAME_COL: "adm2_name"` to the rename mapping. |
| 2026-05-25 | **NB05 completed successfully.** Outputs: `data/processed/Riskprofiles/RiskProfile_saint_paul_01_2026-05-25_LBR-saint-paul.xlsx`, `oep_curves_all_units.json`, `watershed_oep_curve.json`. 238 units computed (ADM3 clan, ADM2 district, watershed total). RP2/5/10 watershed totals: 258K / 457K / 543K people. See report Section 7 for full district table. |
| 2026-05-25 | **NB06 — 6 fixes applied before first run (RP-scenario path).** Per the project slides, NB06 is run in RP-scenario mode (cells 1→2→3→4→5→9→10→11); event-specific cells (6, 7, 8, 12–15) are skipped by leaving `NAMED_EVENTS = {}`. Fixes: (1) `HYBAS_L7_SHP` hardcoded Windows absolute path to `australasia/hybas_au_lev07_v1c.shp` → `RAW_ROOT`-relative `africa/hybas_af_lev01-12_v1c/hybas_af_lev06_v1c.shp`; (2) `ADM3_GEOJSON` Philippines path → `lbr_cod_ab/gadm41_LBR_3.json`; (3) `WORLDPOP_RASTER` Philippines path → auto-discovery `worldpop/**/*.tif`; (4) `JRC_RAW_ROOT` Windows path → `RAW_ROOT / 'jrc_flood_maps'`; (5) `HYBAS_L7_SHP` override in Cell 4 used `hybas_au_lev...` → `hybas_af_lev...`; (6) `BASIN_DISPLAY_NAME = 'Cagayan River Basin'` → `'Saint Paul River Basin'`. Cell 5 `load_adm3()` assertion `adm3_name`/`adm3_id` replaced with GADM-aware aliasing (`NAME_3→adm3_name`, `GID_3→adm3_id`); `_GFM_ROOT` hardcoded to `validation/GFM/Cagayan` → `validation/GFM/{BASIN_ID}`. Cell 10 event-depth loop guarded with `if NAMED_EVENTS:` so it skips gracefully and sets `depth_df = pd.DataFrame([])` instead of crashing on `NameError: events_df`. New Cell 11 added: RP-scenario population exposure — for each JRC return period, reprojects WorldPop to depth grid, applies `DEPTH_THRESHOLD_M` mask, runs `rasterstats.zonal_stats` per GADM polygon, outputs `rp_district_table`, `rp_county_table`, and `rp_scenario_admin_exposure.csv` to `OUT_DIR`. |


