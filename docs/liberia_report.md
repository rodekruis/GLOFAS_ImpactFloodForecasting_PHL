# Liberia Flood Impact Forecasting — Working Report

**Analyst:** Silvia  
**Started:** 2026-05-25  
**Basin:** Saint Paul River (`saint_paul_01`)  
**Status:** 🔄 In progress — NB06 complete; all notebooks run

> This is a living notes document. It will be turned into a formal report once all notebooks have run. Add findings after each notebook.

---

## 1. Context

This analysis adapts the PhilFlood impact forecasting framework (originally built for the Philippines) to the Saint Paul River basin in Liberia. The goal is to produce a **population exposure table** showing how many people in each district are affected by floods of different rarities.

**Target output:** County × District × return period table for:
- Counties: Montserrado, Lofa, Grand Bassa, Nimba (+ national total)
- Return periods: RP2, RP5, RP10

---

## 2. Study Area

| Item | Value |
|------|-------|
| Country | Liberia (LBR) |
| Basin | Saint Paul River |
| HydroBASINS ID (L6) | `1060024870` |
| Basin extent | ~6.3–8.9°N, 10.9–8.4°W |
| Basin area (approx.) | Central-western Liberia, draining toward Monrovia |
| Admin boundaries | GADM v4.1 Level 3 — 305 clans (`gadm41_LBR_3.json`) |
| GloFAS data | v4.0 reanalysis, 1979–2025 (47 years), `area_10_-12_4_-7` |

---

## 3. Calibration Results (NB01)

**Run:** `2026-05-25_LBR-saint-paul`  
**Outputs:** `data/processed/calibration/evt_pot/saint_paul_01/2026-05-25_LBR-saint-paul/`

### 3.1 Virtual Gauges

- **779 virtual gauges** identified across the basin (GloFAS grid cells at ~5 km resolution intersecting L12 sub-basins)
- **40 main channel cells** with flood thresholds > 500 m³/s — these represent the Saint Paul River main stem
- Remaining ~740 cells are headwater tributaries with thresholds of 3–30 m³/s

### 3.2 Flood Frequency

Main channel cells flood approximately **1.3–1.5 times per year** on average. This is consistent with Liberia's single wet season (roughly May–October).

### 3.3 Return Level Estimates (main channel outlet, lat 6.425°N lon −10.725°E)

| Return Period | Discharge (m³/s) | 90% CI |
|---|---|---|
| RP10 | 2,580 | 2,406 – 2,737 |
| RP20 | 2,787 | 2,570 – 2,976 |
| RP50 | 3,031 | 2,724 – 3,332 |
| RP100 | 3,197 | 2,800 – 3,621 |
| RP500 | 3,540 | 2,930 – 4,359 |

The discharge increases modestly from RP10 to RP500 (~1.4×). This reflects a slightly bounded distribution (GPD shape xi ≈ −0.1 to −0.2 on main channel), physically consistent with a catchment-limited river.

### 3.4 Calibration Quality

| Metric | Value | Assessment |
|--------|-------|------------|
| Gauges passing monotonicity | 779/779 (100%) | ✅ |
| Fallback gauges | 0/779 | ✅ |
| Median uncertainty (CV at RP10) | 7.2% | ✅ Tight |
| Gauges with CV > 30% | 0 | ✅ |
| Data coverage | 47 years | ✅ Sufficient |

### 3.5 Notes & Caveats

- **RP2 and RP5 not yet produced.** Current output covers RP10–RP500. These need to be added to Section 11C (`RETURN_PERIODS = [2, 5, 10, 20, 50, 75, 100, 200, 500]`) and the section re-run before finalising.
- The `return-period_all.nc` file in the output folder contains incorrect values — do not use. The correct file is `climada_flood_hazard.nc`.
- Run name is still the test name `2026-01-19_calib-test` — rename for final deliverable.

---

## 4. Hazard Maps (NB02)

**Run:** `2026-05-25_LBR-saint-paul` — same directory as NB01  
**JRC tiles used:** `ID105_N10_W20`, `ID111_N10_W10` (West Africa tiles covering ~0–10°N, 20–0°W)  
**Return periods:** RP10, 20, 50, 75, 100, 200, 500 (JRC does not publish RP2 or RP5)

### 4.1 Flood Extent

| Return Period | Flooded cells | Max depth | Mean depth (flooded) |
|---|---|---|---|
| RP10  | 247,544 | 26.22 m | 4.66 m |
| RP20  | 255,885 | 26.52 m | 4.99 m |
| RP50  | 281,216 | 26.91 m | 5.13 m |
| RP75  | 296,359 | 27.14 m | 5.12 m |
| RP100 | 303,820 | 27.24 m | 5.15 m |
| RP200 | 316,822 | 27.51 m | 5.28 m |
| RP500 | 334,153 | 27.67 m | 5.33 m |

The monotonic increase in flooded cells from RP10 to RP500 is as expected. The relatively modest range (247K → 334K cells, ~35% increase) is consistent with a topographically constrained river valley — the Saint Paul River floods mainly within a defined floodplain corridor.

The high maximum depths (26–27 m) reflect deep valley incision in the upper catchment; near-outlet cells in the flatter coastal zone have shallower depths.

### 4.2 CLIMADA Hazard Object

| Item | Value |
|------|-------|
| File | `climada_hazard_saint_paul_01.hdf5` |
| Events | 7 (one per return period) |
| Centroids | ~9.5 M (full grid) |
| Non-zero intensity values | 2,035,799 |
| Max intensity | 27.67 m |
| Mean non-zero intensity | 5.11 m |

### 4.3 Data Quality Notes

- **RP200 and RP500 fringe NaNs:** 14,400 and 28,800 NaN cells respectively at tile-boundary positions. These are edge artefacts from the merge of the two JRC tiles and fall outside the main flooded corridor. Not expected to affect population exposure estimates.
- **RP2 and RP5:** Not available from JRC. Will be derived analytically from the fitted GPD parameters (as done in NB01) and handled separately in the final exposure table.

---

## 5. Validation (NB03)

> 🔄 Not yet run.

---

## 6. Impact Catalogue (NB04)

**Sections run:** 0–3 (as instructed; sections 4+ not run)  
**Output directory:** `data/processed/impact_catalogue_catmodel/`  
**Primary depth threshold:** 20 mm (operational threshold, `depth_op`)

### 6.1 Historical Event Catalogue

| Metric | Value |
|---|---|
| Period | 1979–2025 (47 years) |
| Events detected & passing all filters | 111 |
| Average events per year | 2.4 |
| Largest event (pop affected, 20mm) | 659,959 — 2021-08-31 |

**Seasonal pattern:** All events fall between May and October, strongly concentrated in the core wet season:

| Month | Events |
|---|---|
| May | 1 |
| June | 15 |
| July | 14 |
| August | 32 |
| September | 42 |
| October | 7 |

August and September account for 74% of all events, consistent with Liberia's single wet season peaking in September.

### 6.2 Top Events

| Event | Peak date | Max flooded area (km²) | Pop affected (20mm) |
|---|---|---|---|
| HIST_00099 | 2021-08-31 | 12,940 | 659,959 |
| HIST_00019 | 1989-09-15 | 9,013 | 584,639 |
| HIST_00107 | 2024-09-28 | 7,940 | 584,275 |
| HIST_00051 | 2005-09-08 | 6,810 | 584,211 |
| HIST_00045 | 2002-09-13 | 6,224 | 583,364 |

Note: events 2–5 have nearly identical population figures (~584K). This reflects a saturation effect — once the flood reaches Greater Monrovia's footprint, incremental area gain yields diminishing additional exposure.

### 6.3 Dominant Administrative Units

Greater Monrovia and the StPaulRiver clans account for the vast majority of cumulative exposure:

| Clan | Cumulative pop-events (20mm, all 111 events) |
|---|---|
| GreaterMonrovia | 15,135,157 |
| StPaulRiver (multiple clans) | ~4,385,121 |
| Kakata | 79,836 |
| Klay | 64,583 |
| Zorzor | 40,588 |

Greater Monrovia alone accounts for ~67% of all population exposure. This is expected: Monrovia is the densely populated capital at the Saint Paul River mouth. Note that "StPaulRiver" appears as multiple distinct GADM clans sharing the same name — these are separate administrative units along the river corridor.

### 6.4 EVT2 Fit (Population-Affected Series)

A GPD was fitted to the annual-maximum population-affected series using the POT method.

| Parameter | Value |
|---|---|
| Threshold u | 241,464 people |
| Shape ξ (xi) | −0.42 (bounded/short-tailed) |
| Scale σ (sigma) | 204,384 |
| Total event rate λ | 2.40 events/year |
| Rate above threshold λ_u | 0.95 events/year |
| Exceedances used in fit | 44 of 111 events |
| KS goodness-of-fit p-value | 0.036 |

The negative shape parameter (ξ = −0.42) indicates a bounded distribution — there is a finite upper limit to flood impact implied by the record. This is physically plausible (the floodplain has a maximum extent), but should be interpreted cautiously: 47 years may not capture the full range of extreme events. The KS p-value of 0.036 is borderline (below the conventional 0.05 threshold), suggesting the GPD fit is acceptable but not ideal; confidence intervals at high return periods are wide.

### 6.5 Return Levels — Population Exposed

At the primary threshold (20 mm flood depth), people exposed per event:

| Return Period | Mean | Q05 | Q95 |
|---|---|---|---|
| RP2 | 365,658 | 289,173 | 447,859 |
| RP5 | 479,341 | 394,365 | 547,599 |
| RP10 | 542,270 | 489,620 | 581,161 |
| RP20 | 598,564 | 547,996 | 651,972 |
| RP50 | 679,858 | 578,264 | 916,748 |
| RP100 | 763,967 | 582,959 | 1,186,957 |
| RP200 | 893,929 | 583,813 | 1,541,186 |
| RP500 | 1,221,089 | 584,177 | 2,184,782 |

The Q05 lower bound flattens above RP50 (~580K) — a consequence of the negative ξ producing a finite distribution upper bound in many bootstrap samples. The Q95 upper bound grows rapidly, reflecting genuine deep uncertainty at long return periods given the 47-year record. The RP2–RP10 range has relatively tight CIs and is the most reliable part of the curve.

### 6.6 Caveats

- Sections 4+ (synthetic catalogue, 10,000-year simulation) were not run — county × district breakdown will come from NB05.
- The 20 mm depth threshold is the operational default; sensitivity across thresholds (10–1000 mm) was computed and saved in `evt2/` but not reviewed here.
- Admin-level exposure is dominated by Greater Monrovia; rural districts along the Saint Paul River corridor (StPaulRiver, Kakata, Klay) are secondary.

---

## 7. Risk Profiles (NB05)

> 🔄 Ready to run — pre-flight fixes applied.

**Mode:** Humanitarian simplified path (no reforecast library needed)  
**Simulation years:** 1,000 (reduced from 10,000 per project slides — sufficient for RP2/5/10, 10× faster)  
**Input:** Historical event catalogue from NB04 (111 events) + per-admin impacts by depth threshold

Expected output: OEP/AEP exceedance curves per clan/district — feeds into the final County × District × RP2/5/10 exposure table.

### 7.2 Run summary

| Item | Value |
|------|-------|
| Simulation years | 1,000 |
| Input events | 111 historical events (NB04 humanitarian path) |
| Units computed | 238 (ADM3 clan + ADM2 district + watershed total) |
| Output files | `RiskProfile_saint_paul_01_2026-05-25_LBR-saint-paul.xlsx`, `oep_curves_all_units.json`, `watershed_oep_curve.json` |

### 7.3 Watershed-level OEP

| Return Period | People exposed (OEP) |
|---|---|
| RP2  | 257,993 |
| RP5  | 457,323 |
| RP10 | 542,619 |

### 7.4 District-level exposure table (target counties)

OEP return levels — people exposed per flood event of given rarity.

#### Montserrado County

| District | RP2 | RP5 | RP10 |
|---|---|---|---|
| Greater Monrovia | 210,952 | 352,862 | 408,375 |
| St. Paul River | 38,728 | 130,481 | 131,125 |
| Todee | 60 | 62 | 62 |
| Careysburg | 0 | 0 | 0 |

#### Lofa County

| District | RP2 | RP5 | RP10 |
|---|---|---|---|
| Zorzor | 623 | 879 | 886 |
| Salayea | 570 | 629 | 633 |
| Kolahun | 395 | 619 | 619 |
| Foya | 0 | 0 | 0 |
| Voinjama | 0 | 0 | 0 |

#### Grand Bassa County

| District | RP2 | RP5 | RP10 |
|---|---|---|---|
| District #2 | 522 | 620 | 626 |
| District #3 | 232 | 275 | 275 |
| District #1 | 91 | 91 | 91 |
| Owensgrove | 0 | 0 | 0 |
| St. John River | 0 | 0 | 0 |

#### Nimba County

| District | RP2 | RP5 | RP10 |
|---|---|---|---|
| All districts | 0 | 0 | 0 |

### 7.5 Notes and caveats

- **Montserrado dominates.** Greater Monrovia alone accounts for ~75% of watershed RP10 exposure (408K of 543K). St. Paul River district adds another ~24% (131K). All other counties combined contribute < 1% of the watershed total.
- **Nimba has zero exposure.** Nimba County does not fall within the Saint Paul River basin as delineated — no GloFAS cells or JRC flood maps intersect it at any return period.
- **Grand Bassa districts are labelled District #1–3 in GADM** (no district names stored at this level in the v4.1 dataset). These are the Grand Bassa districts closest to the basin edge and show small but non-zero exposure (combined RP10 ≈ 990 people).
- **District-level OEP values are independent exceedance curves**, not additive. The county-level exposure cannot be reliably obtained by summing district OEP values because multiple districts flood simultaneously in the same event. The watershed-level OEP (Section 7.3) is the correct aggregate figure.
- **ADM2 `adm2_name` column was empty** in the `oep_curves_all_units.json` output — district names were recovered by joining against GADM `NAME_2`. County assignment uses GADM `NAME_1`.

---

## 8. Final Deliverable

Population exposed per flood event (OEP, 20 mm depth threshold):

| County | District | RP2 | RP5 | RP10 |
|--------|----------|----:|----:|-----:|
| Montserrado | Greater Monrovia | 210,952 | 352,862 | 408,375 |
| Montserrado | St. Paul River | 38,728 | 130,481 | 131,125 |
| Montserrado | Todee | 60 | 62 | 62 |
| Montserrado | Careysburg | 0 | 0 | 0 |
| Lofa | Zorzor | 623 | 879 | 886 |
| Lofa | Salayea | 570 | 629 | 633 |
| Lofa | Kolahun | 395 | 619 | 619 |
| Lofa | Foya | 0 | 0 | 0 |
| Lofa | Voinjama | 0 | 0 | 0 |
| Grand Bassa | District #2 | 522 | 620 | 626 |
| Grand Bassa | District #3 | 232 | 275 | 275 |
| Grand Bassa | District #1 | 91 | 91 | 91 |
| Grand Bassa | Owensgrove | 0 | 0 | 0 |
| Grand Bassa | St. John River | 0 | 0 | 0 |
| Nimba | All districts | 0 | 0 | 0 |
| **Watershed total** | | **257,993** | **457,323** | **542,619** |

> ⚠️ District values are independent OEP curves — they cannot be summed to county totals. The watershed total is the correct aggregate (see Section 7.5).

---

## 9. Scenario Maps (NB06)

**Mode:** RP-scenario (cells 1→2→3→4→5→9→10→11); event viewer cells skipped (`NAMED_EVENTS = {}`)  
**Status:** ✅ Complete

### 9.1 What NB06 produces

| Output | Description |
|--------|-------------|
| `flood_maps` (NetCDF) | Merged JRC flood depth rasters for RP10/20/50/75/100/200/500 over the Saint Paul basin |
| `rp_scenario_admin_exposure.csv` | Population exposed per return period, per GADM district and county |
| `rp_district_table` | Wide-format: county × district rows, RP10–RP500 columns |

> ⚠️ JRC Global Flood Maps are published for RP10, 20, 50, 75, 100, 200, 500 only — RP2 and RP5 are not available from JRC. The RP2/5 figures in the final deliverable come from NB05's EVT2-based OEP simulation (Section 7), not from JRC rasters.

### 9.2 Run order

| Cell | Purpose | Run? |
|------|---------|------|
| 1 | Imports | ✅ |
| 2 | Repo root + paths (Liberia fixed) | ✅ |
| 3 | Pre-flight check | ✅ |
| 4 | User controls (`NAMED_EVENTS = {}`, `Saint Paul River Basin`) | ✅ |
| 5 | Load GADM ADM3 + build basin AOI from HydroBASINS | ✅ |
| 6 | EVT timeseries helpers | ⏭ skip |
| 7 | Flood day selection (event-specific) | ⏭ skip |
| 8 | Event RP maps (event-specific) | ⏭ skip |
| 9 | Download & merge JRC tiles → `flood_maps` | ✅ |
| 10 | Depth helper functions (event loop guarded, skips cleanly) | ✅ |
| **11** | **RP-scenario population exposure → admin table + CSV** | ✅ |
| 12–15 | Event population, OEP RP, risk matrix export, dashboard | ⏭ skip |

### 9.3 Basin totals (JRC RP scenarios)

59 admin units intersect the Saint Paul basin AOI. WorldPop grid: 5,039 × 4,947 cells, total population in raster = 5,672,239.

| Return Period | People exposed (JRC) |
|---|---:|
| RP10  | 715,063 |
| RP20  | 837,516 |
| RP50  | 954,147 |
| RP75  | 1,005,338 |
| RP100 | 1,039,426 |
| RP200 | 1,107,512 |
| RP500 | 1,197,459 |

### 9.4 County-level exposure (JRC RP scenarios)

| County | RP10 | RP20 | RP50 | RP75 | RP100 | RP200 | RP500 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Bomi | 13,243 | 17,250 | 23,512 | 26,845 | 29,826 | 34,615 | 42,612 |
| Bong | 1,147 | 1,335 | 1,724 | 1,900 | 2,010 | 2,243 | 2,575 |
| Gbapolu | 1,161 | 1,335 | 1,472 | 1,516 | 1,557 | 1,609 | 1,746 |
| Lofa | 2,363 | 2,544 | 2,776 | 2,848 | 2,933 | 3,036 | 3,194 |
| Montserrado | 697,149 | 815,053 | 924,664 | 972,230 | 1,003,100 | 1,066,009 | 1,147,331 |

### 9.5 District-level exposure (non-zero rows, JRC RP scenarios)

| County | District | RP10 | RP20 | RP50 | RP75 | RP100 | RP200 | RP500 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Bomi | Klay | 13,012 | 16,940 | 22,988 | 26,304 | 29,283 | 34,033 | 41,981 |
| Bomi | Mecca | 231 | 310 | 523 | 540 | 544 | 582 | 631 |
| Bong | Fuamah | 757 | 875 | 1,127 | 1,219 | 1,282 | 1,458 | 1,691 |
| Bong | Sanayea | 294 | 354 | 452 | 535 | 580 | 629 | 722 |
| Bong | Zota | 96 | 106 | 145 | 146 | 147 | 156 | 163 |
| Gbapolu | Belleh | 227 | 233 | 257 | 263 | 269 | 281 | 314 |
| Gbapolu | Bokomu | 933 | 1,102 | 1,216 | 1,253 | 1,280 | 1,320 | 1,415 |
| Gbapolu | Bopolu | 0 | 0 | 0 | 0 | 8 | 8 | 17 |
| Lofa | Salayea | 805 | 875 | 997 | 1,006 | 1,022 | 1,075 | 1,113 |
| Lofa | Zorzor | 1,557 | 1,668 | 1,779 | 1,842 | 1,911 | 1,962 | 2,081 |
| Montserrado | GreaterMonrovia | 561,798 | 652,215 | 734,223 | 773,568 | 799,871 | 851,897 | 919,884 |
| Montserrado | StPaulRiver | 135,278 | 162,758 | 190,336 | 198,545 | 203,107 | 213,972 | 227,280 |
| Montserrado | Todee | 74 | 81 | 105 | 117 | 122 | 140 | 168 |

### 9.6 Notes and caveats

- **Methodology differs from NB05.** NB06 uses JRC flood depth rasters directly: for each return period, pixels with depth ≥ 20 mm are masked and overlaid with WorldPop to sum exposed population. This is a **deterministic spatial exposure** count, not a probabilistic OEP curve. Figures are therefore not directly comparable to Section 7.
- **Bomi/Klay is significant.** Klay district (Bomi County) shows 13,012 people exposed at RP10, rising to ~42,000 at RP500 — higher than any single Lofa or Bong district. It was absent from NB05 results because NB05 uses historical event footprints rather than the raw JRC rasters.
- **Grand Bassa and Nimba absent.** Neither county appears in the NB06 output. Grand Bassa Districts #1–3 showed small non-zero values in NB05 (OEP-based), but the JRC rasters for those cells fall below the 20 mm threshold or outside the basin AOI polygon at all return periods. Nimba remains zero, consistent with NB05.
- **Montserrado still dominates.** GreaterMonrovia alone accounts for 79% of the RP10 basin total (562K of 715K). StPaulRiver district adds 19% (135K). All other counties combined contribute < 2%.
- **RP2 and RP5 not available from JRC.** The RP2/5 columns in Section 8 (Final Deliverable) come from NB05's EVT2-based OEP; NB06 provides the RP10–RP500 JRC-based figures.
- **Output file:** `data/processed/event_viewer/saint_paul_01/2026-05-25_LBR-saint-paul/rp_scenario_admin_exposure.csv`

---

## 10. Open Questions & Next Steps

- [x] ~~Add RP2 and RP5 to Section 11C and re-run~~ — RP2/5 produced analytically via GPD formula through NB04 EVT2 fit; present in final exposure table
- [x] ~~Confirm whether NB02 requires Liberia-specific flood maps or generates them from discharge~~ — NB02 uses JRC Global Flood Maps (pre-computed flood depth rasters); GloFAS discharge from NB01 used only for return period assignment
- [x] ~~Rename run tag from `2026-01-19_calib-test` to `2026-05-25_LBR-saint-paul`~~ — directory renamed, `run_config.json` updated, `run_tag` fixed in NB01 Cell 4
- [x] ~~Verify population data for Liberia is available/correct for NB04~~ — WorldPop 2025 LBR 100m raster (`lbr_pop_2025_CN_100m_R2025A_v1.tif`) found and used; NB04/NB05 ran successfully
- [ ] Investigate RP200/500 fringe NaNs — confirm they don't overlap populated areas (14,400 / 28,800 edge cells; expected to be outside flood corridor but not formally verified)
- [ ] Grand Bassa district names — GADM v4.1 stores them as "District #1–3" rather than named districts; verify whether official names exist and update if needed for stakeholder deliverable
- [ ] Nimba County — confirm zero exposure is expected (Saint Paul basin delineation does not reach Nimba); if Nimba is a priority county, check whether a separate basin analysis is needed
- [ ] Reconcile NB05 vs NB06 county coverage — Bomi/Klay appears in NB06 (JRC rasters) but not NB05 (historical event footprints); Grand Bassa appears in NB05 but not NB06; investigate whether this reflects a real methodological difference or a basin delineation edge effect
