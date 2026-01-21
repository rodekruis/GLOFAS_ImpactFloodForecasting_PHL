from __future__ import annotations

import json
from pathlib import Path

import nbformat as nbf


def md(text: str):
    return nbf.v4.new_markdown_cell(text)


def code(text: str):
    return nbf.v4.new_code_cell(text)


def build() -> nbf.NotebookNode:
    nb = nbf.v4.new_notebook()
    nb.metadata.update({
        "kernelspec": {"name": "python3", "display_name": "Python 3"},
        "language_info": {"name": "python"},
    })

    nb.cells.append(md(
        """# EVT/POT Calibration Workflow (GloFAS v4 → Virtual Gauges → Poisson λ)

This notebook provides an **end-to-end, operator-friendly calibration workflow** for riverine flood triggers:

1. **Select impact units (HydroBASINS L12)**
   - **Mode A** (municipality AOI): population-weighted centroid (WorldPop) + 5 km geodesic buffer, clipped to ADM3
   - **Mode B** (context basin): select all L12 inside a configured context basin polygon (e.g., L7)
2. **Assign virtual gauges**
   - One representative point per L12: **L12 pour point → nearest GloFAS grid cell**
   - **Collisions are expected** (multiple L12 → same GloFAS cell). We calibrate **per unique cell**.
3. **GRIB → daily discharge time series** (cached)
4. **POT/EVT extraction** using `pyextremes` + run-length declustering
5. **Poisson frequency λ** per unique virtual gauge

> Locked decisions: all geometry remains in **EPSG:4326 (WGS84)** and we use **GloFAS historical/reanalysis v4 consolidated discharge GRIBs**.
"""
    ))

    nb.cells.append(md("""## 0) Setup (robust imports, repo root, dependency checks)

This cell makes the notebook robust to:
- `ModuleNotFoundError` when running from different working directories
- Windows path handling (use raw strings)

If anything fails here, fix it before proceeding.
"""))

    nb.cells.append(code(
        """%load_ext autoreload
%autoreload 2

import sys
from pathlib import Path
import warnings

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Optional interactivity
try:
    import ipywidgets as widgets
    from IPython.display import display
    HAS_WIDGETS = True
except Exception:
    HAS_WIDGETS = False

# --- Find repo root and add src/ to sys.path ---
try:
    from philflood.utils.paths import find_repo_root, ensure_src_on_path
except Exception:
    # Fallback: assume this notebook lives under <repo>/notebooks/
    def find_repo_root(start=None):
        p = Path.cwd().resolve() if start is None else Path(start).resolve()
        for parent in (p, *p.parents):
            if (parent / 'src').exists():
                return parent
        raise RuntimeError('Could not find repo root; set REPO_ROOT manually')

    def ensure_src_on_path(repo_root):
        repo_root = Path(repo_root).resolve()
        src = repo_root / 'src'
        if str(src) not in sys.path:
            sys.path.insert(0, str(src))
        return src

REPO_ROOT = find_repo_root()
SRC_PATH = ensure_src_on_path(REPO_ROOT)
print('REPO_ROOT:', REPO_ROOT)
print('SRC_PATH :', SRC_PATH)

# Now imports from src/
from philflood.config.basin import load_basin_config
from philflood.geo.worldpop import population_weighted_centroid
from philflood.geo.aoi import build_municipality_aoi
from philflood.geo.hydrobasins import read_vector, select_context_polygon, select_l12_by_geometry, get_id_field
from philflood.adapters.glofas_grib_v4 import (
    discover_grib_year_files,
    open_grib_dataset,
    nearest_grid_cell,
    load_or_build_gauge_timeseries,
)
from philflood.qc.timeseries import qc_daily_series, qc_summary_dict
from philflood.calibration.evt_pot import pot_extract, fit_gpd_to_pot

print('Core imports OK')
"""
    ))

    nb.cells.append(md("""## 1) Operator inputs (edit here)

Set paths and mode switches below. The notebook will validate and **fail fast** if anything is missing.

**Locked data paths (examples):**
- WorldPop raster: `C:\\pipelines\\GLOFAS_ImpactFloodForecasting_PHL\\data\\raw\\worldpop\\PHL\\phl_pop_2025_CN_100m_R2025A_v1.tif`
- ADM3 municipalities: `C:\\pipelines\\GLOFAS_ImpactFloodForecasting_PHL\\data\\raw\\vectors\\admin\\phl_cod_ab\\phl_adm3.geojson`
- HydroBASINS L12 polygons: `C:\\pipelines\\GLOFAS_ImpactFloodForecasting_PHL\\data\\raw\\vectors\\hydrobasins\\australasia\\hybas_au_lev01-12_v1c\\hybas_au_lev12_v1c.shp`
- HydroBASINS L12 pour points: `C:\\pipelines\\GLOFAS_ImpactFloodForecasting_PHL\\data\\raw\\vectors\\hydrobasins\\australasia\\hybas_pour_lev01-12_v1_shp\\hybas_pour_lev12_v1.shp`
- GloFAS v4 GRIB root: `C:\\pipelines\\GLOFAS_ImpactFloodForecasting_PHL\\data\\raw\\glofas\\historical\\version_4_0\\consolidated\\discharge\\grib2\\area_35_63_4_131`

> Tip: use raw strings `r"..."` on Windows.
"""))

    nb.cells.append(code(
        """# --- Mode toggle (locked requirement) ---
USE_MUNI_AOI = True  # True = municipality AOI mode, False = context basin mode

# --- Municipality AOI mode inputs ---
adm3_ids = [
    # Example: "PHLxxxx". Must match adm3_id in the ADM3 GeoJSON.
    # Fill with one or more municipalities.
]
aoi_buffer_km = 5

# --- Context basin mode inputs (legacy YAML) ---
basin_cfg_relpath = r"ops\configs\basins\Cagayan_01.yaml"  # repo-relative (legacy)
context_select_mode = "within"  # within|intersects

# --- Locked data paths (set these to your local repo paths) ---
worldpop_raster = Path(r"C:\pipelines\GLOFAS_ImpactFloodForecasting_PHL\data\raw\worldpop\PHL\phl_pop_2025_CN_100m_R2025A_v1.tif")
adm3_geojson = Path(r"C:\pipelines\GLOFAS_ImpactFloodForecasting_PHL\data\raw\vectors\admin\phl_cod_ab\phl_adm3.geojson")
hybas_l12_shp = Path(r"C:\pipelines\GLOFAS_ImpactFloodForecasting_PHL\data\raw\vectors\hydrobasins\australasia\hybas_au_lev01-12_v1c\hybas_au_lev12_v1c.shp")
hybas_pour_l12_shp = Path(r"C:\pipelines\GLOFAS_ImpactFloodForecasting_PHL\data\raw\vectors\hydrobasins\australasia\hybas_pour_lev01-12_v1_shp\hybas_pour_lev12_v1.shp")

glofas_grib_root = Path(r"C:\pipelines\GLOFAS_ImpactFloodForecasting_PHL\data\raw\glofas\historical\version_4_0\consolidated\discharge\grib2\area_35_63_4_131")

# --- Calibration defaults ---
run_tag = "2026-01-19_calib"  # used in output folder names
analyst_name = "YOUR_NAME"

run_length_days = 5
candidate_quantiles = [0.95, 0.97, 0.98, 0.99]

# Optional: explicitly set discharge variable name in GRIB (leave None to auto-detect)
discharge_var = None

# --- Processed output root (repo-relative) ---
processed_root = REPO_ROOT / "data" / "processed"

# Print resolved paths for transparency
print("USE_MUNI_AOI:", USE_MUNI_AOI)
print("worldpop_raster:", worldpop_raster)
print("adm3_geojson  :", adm3_geojson)
print("hybas_l12_shp :", hybas_l12_shp)
print("pour points   :", hybas_pour_l12_shp)
print("glofas_grib_root:", glofas_grib_root)
print("processed_root:", processed_root)
"""
    ))

    nb.cells.append(md("""## 2) Validate inputs (fail fast)

We stop early if any required file is missing. This prevents silent downstream failures.
"""))

    nb.cells.append(code(
        """def _assert_exists(p: Path, label: str):
    if not p.exists():
        raise FileNotFoundError(f"{label} not found: {p}")

_assert_exists(worldpop_raster, "WorldPop raster")
_assert_exists(adm3_geojson, "ADM3 GeoJSON")
_assert_exists(hybas_l12_shp, "HydroBASINS L12 polygons")
_assert_exists(hybas_pour_l12_shp, "HydroBASINS L12 pour points")
_assert_exists(glofas_grib_root, "GloFAS GRIB root")

# Context basin YAML is only required in context mode
if not USE_MUNI_AOI:
    basin_cfg_path = (REPO_ROOT / Path(basin_cfg_relpath)).resolve()
    _assert_exists(basin_cfg_path, "Legacy basin config YAML")

print("All required inputs exist.")
"""
    ))

    nb.cells.append(md("""## 3) Load vectors and (optionally) context basin config
"""))

    nb.cells.append(code(
        """import geopandas as gpd

adm3_gdf = read_vector(adm3_geojson)
l12_gdf = read_vector(hybas_l12_shp)
pour_gdf = read_vector(hybas_pour_l12_shp)

print("ADM3 rows:", len(adm3_gdf))
print("L12 rows :", len(l12_gdf))
print("Pour rows:", len(pour_gdf))

# Identify IDs
adm3_id_field = "adm3_id" if "adm3_id" in adm3_gdf.columns else None
if adm3_id_field is None:
    raise KeyError(f"ADM3 GeoJSON must include 'adm3_id'. Found columns: {list(adm3_gdf.columns)}")

l12_id_field = get_id_field(l12_gdf)
pour_id_field = get_id_field(pour_gdf)

print("ADM3 id field:", adm3_id_field)
print("L12  id field:", l12_id_field)
print("Pour id field:", pour_id_field)

basin_cfg = None
context_gdf = None
context_geom = None
if not USE_MUNI_AOI:
    basin_cfg = load_basin_config(basin_cfg_path)
    print("Loaded basin config:", basin_cfg.basin_id)
    print("Context hydrobasins level/id:", basin_cfg.hydrobasins_level, basin_cfg.hydrobasins_id)
    # Load the context basin polygons for that level (user should set path if needed)
    # For now, we re-use the L12 shapefile only when level=12; otherwise you must point to the appropriate level file.
    if basin_cfg.hydrobasins_level == 12:
        context_gdf = l12_gdf
    else:
        # Operator: set this to the correct HydroBASINS level shapefile for your context
        raise RuntimeError(
            "Context basin mode requires the HydroBASINS polygon file for the configured level. "
            "Set a path to hybas_au_levXX_v1c.shp and load it here."
        )

"""
    ))

    nb.cells.append(md("""## 4) Select L12 impact units

Two modes:

### Mode A: Municipality AOI
- For each selected municipality:
  - population-weighted centroid (WorldPop)
  - AOI = geodesic buffer(5 km) clipped to municipality polygon
  - select all intersecting L12 polygons

### Mode B: Context basin
- Select all L12 polygons inside the context basin geometry
"""))

    nb.cells.append(code(
        """selected_l12 = None
muni_aoi_records = []
aoi_geoms = []

if USE_MUNI_AOI:
    if not adm3_ids:
        raise ValueError("USE_MUNI_AOI=True requires adm3_ids to be provided")

    for mid in adm3_ids:
        muni = adm3_gdf[adm3_gdf[adm3_id_field] == mid]
        if len(muni) != 1:
            raise ValueError(f"Expected exactly 1 municipality for adm3_id={mid}, found {len(muni)}")
        muni_geom = muni.geometry.values[0]

        # Population-weighted centroid (fails loudly if no population)
        wc = population_weighted_centroid(muni_geom, worldpop_raster)
        aoi = build_municipality_aoi(muni_geom, wc.point, buffer_km=aoi_buffer_km)

        aoi_geoms.append(aoi.aoi_polygon)

        sel = select_l12_by_geometry(l12_gdf, aoi.aoi_polygon, mode="intersects")
        muni_aoi_records.append({
            "adm3_id": mid,
            "centroid_lon": float(wc.point.x),
            "centroid_lat": float(wc.point.y),
            "total_population": float(wc.total_population),
            "valid_pixel_count": int(wc.valid_pixel_count),
            "n_l12_selected": int(len(sel)),
            "l12_ids": sel[l12_id_field].astype(int).tolist(),
        })

    # Union selection across municipalities
    all_ids = sorted({i for r in muni_aoi_records for i in r["l12_ids"]})
    selected_l12 = l12_gdf[l12_gdf[l12_id_field].astype(int).isin(all_ids)].copy()

else:
    # Placeholder: requires context basin geometry loaded above
    context_sel = select_context_polygon(context_gdf, basin_cfg.hydrobasins_id)
    context_geom = context_sel.geometry.values[0]
    selected_l12 = select_l12_by_geometry(l12_gdf, context_geom, mode=context_select_mode)

print("Selected L12 count:", len(selected_l12))
"""
    ))

    nb.cells.append(md("""## 5) Build virtual gauges (L12 pour point → nearest GloFAS grid cell)

Locked decisions:
- **One representative discharge point per selected L12** = its L12 pour point
- Map to **nearest GloFAS v4 grid cell**
- If multiple L12 map to the same cell: **expected**. We calibrate per **unique cell**.

We also guard against a common xarray pitfall: `.sel(method='nearest')` can snap points even if the input point is outside the dataset extent (so we check bounds first).
"""))

    nb.cells.append(code(
        """# Join selected L12 to pour points
pour_sel = pour_gdf[[pour_id_field, "geometry"]].copy()
pour_sel[pour_id_field] = pour_sel[pour_id_field].astype(int)

sel = selected_l12[[l12_id_field, "geometry"]].copy()
sel[l12_id_field] = sel[l12_id_field].astype(int)

# Merge by HYBAS_ID
sel = sel.merge(pour_sel, left_on=l12_id_field, right_on=pour_id_field, how="left", suffixes=("_l12", "_pour"))
if sel["geometry_pour"].isna().any():
    missing = sel[sel["geometry_pour"].isna()][l12_id_field].tolist()
    raise RuntimeError(f"Missing pour points for some L12 IDs: {missing[:10]} (showing up to 10)")

# Build a points dataframe
points_df = pd.DataFrame({
    "l12_id": sel[l12_id_field].astype(int).values,
    "pour_lon": sel["geometry_pour"].x.astype(float).values,
    "pour_lat": sel["geometry_pour"].y.astype(float).values,
})

# Open one GRIB (first available year) to get grid and assign nearest cells
inventory = discover_grib_year_files(glofas_grib_root)
print(f"Discovered {len(inventory)} yearly GRIBs. Years: {inventory[0].year}..{inventory[-1].year}")

sample_grib = inventory[0].grib_path
index_dir = processed_root / "glofas" / "v4" / "area_35_63_4_131" / "_cfgrib_index"

import xarray as xr

ds = open_grib_dataset(sample_grib, index_dir=index_dir)

cell_lats = []
cell_lons = []
for lon, lat in zip(points_df["pour_lon"], points_df["pour_lat"]):
    lat0, lon0 = nearest_grid_cell(ds, lat=float(lat), lon=float(lon))
    cell_lats.append(lat0)
    cell_lons.append(lon0)

try:
    ds.close()
except Exception:
    pass

points_df["cell_lat"] = cell_lats
points_df["cell_lon"] = cell_lons

# Define virtual gauge id by unique cell coordinates (stable string)
points_df["virtual_gauge_id"] = points_df.apply(lambda r: f"VG__lat_{r.cell_lat:.4f}__lon_{r.cell_lon:.4f}", axis=1)

# Collision grouping
collision_sizes = points_df.groupby("virtual_gauge_id")["l12_id"].nunique().rename("collision_group_size")
points_df = points_df.merge(collision_sizes, on="virtual_gauge_id", how="left")

print("Unique virtual gauges:", points_df["virtual_gauge_id"].nunique())
print("Max collision group size:", int(points_df["collision_group_size"].max()))

points_df.head()
"""
    ))

    nb.cells.append(md("""## 6) Map preview (context / AOI / L12 / pour points / virtual gauges)
"""))

    nb.cells.append(code(
        """import geopandas as gpd
from shapely.geometry import Point

fig, ax = plt.subplots(1, 1, figsize=(10, 10))

# Base: selected L12
selected_l12.boundary.plot(ax=ax, linewidth=0.5)

# AOI (if any)
if USE_MUNI_AOI:
    aoi_gdf = gpd.GeoDataFrame({"geometry": aoi_geoms}, crs="EPSG:4326")
    aoi_gdf.boundary.plot(ax=ax, linewidth=1.5)
    adm3_gdf[adm3_gdf[adm3_id_field].isin(adm3_ids)].boundary.plot(ax=ax, linewidth=1.5)

# Pour points
pp = gpd.GeoDataFrame(points_df, geometry=[Point(xy) for xy in zip(points_df.pour_lon, points_df.pour_lat)], crs="EPSG:4326")
pp.plot(ax=ax, markersize=8)

# Virtual gauges (unique cells)
vg_unique = points_df.drop_duplicates("virtual_gauge_id").copy()
vg = gpd.GeoDataFrame(vg_unique, geometry=[Point(xy) for xy in zip(vg_unique.cell_lon, vg_unique.cell_lat)], crs="EPSG:4326")
vg.plot(ax=ax, markersize=40, marker="x")

ax.set_title("Selected L12 impact units and virtual gauges")
ax.set_xlabel("Lon")
ax.set_ylabel("Lat")
plt.show()
"""
    ))

    nb.cells.append(md("""## 7) Write mapping tables (deterministic, machine-readable)

We write:
- municipality → AOI → selected L12 (if AOI mode)
- L12 → pour point
- L12 → virtual gauge (GloFAS cell) + collision sizes
"""))

    nb.cells.append(code(
        """out_root = processed_root / "calibration" / "evt_pot" / (basin_cfg.basin_id if basin_cfg else "MUNI_SELECTION") / run_tag
mapping_dir = out_root / "mapping"
aoi_dir = out_root / "aoi"
for d in [mapping_dir, aoi_dir]:
    d.mkdir(parents=True, exist_ok=True)

# A) muni → AOI → L12
if USE_MUNI_AOI:
    muni_aoi_df = pd.DataFrame(muni_aoi_records)
    muni_aoi_df.to_parquet(mapping_dir / "muni_aoi_l12.parquet", index=False)

    # Save AOI geometries
    import geopandas as gpd
    aoi_gdf = gpd.GeoDataFrame(muni_aoi_df[["adm3_id", "centroid_lon", "centroid_lat", "total_population", "valid_pixel_count"]].copy(),
                              geometry=aoi_geoms, crs="EPSG:4326")
    aoi_gdf.to_file(aoi_dir / "municipality_aoi.geojson", driver="GeoJSON")

# B) L12 → pour point
l12_pour = points_df[["l12_id", "pour_lon", "pour_lat"]].copy()
l12_pour.to_parquet(mapping_dir / "l12_pour_points.parquet", index=False)

# C) L12 → virtual gauge
l12_vg = points_df[["l12_id", "cell_lat", "cell_lon", "virtual_gauge_id", "collision_group_size"]].copy()
l12_vg.to_parquet(mapping_dir / "l12_to_virtual_gauge.parquet", index=False)

print("Wrote mapping tables to:", mapping_dir)
"""
    ))

    nb.cells.append(md("""## 8) GRIB → daily discharge time series (cached)

We extract only the **unique virtual gauges** needed for this run.

- Auto-detect available years
- Skip already-processed gauge parquet files (unless forced)
"""))

    nb.cells.append(code(
        """timeseries_dir = processed_root / "glofas" / "v4" / "area_35_63_4_131" / "timeseries" / "virtual_gauges"
timeseries_dir.mkdir(parents=True, exist_ok=True)

vg_points = points_df.drop_duplicates("virtual_gauge_id").rename(columns={"cell_lat": "lat", "cell_lon": "lon"})
vg_points = vg_points[["virtual_gauge_id", "lat", "lon"]].copy()

# Extract or load cached time series
series_by_gauge = load_or_build_gauge_timeseries(
    grib_inventory=inventory,
    points=vg_points,
    processed_timeseries_dir=timeseries_dir,
    cfgrib_index_dir=index_dir,
    force=False,
    discharge_var=discharge_var,
)

print("Loaded/extracted gauges:", len(series_by_gauge))
"""
    ))

    nb.cells.append(md("""## 9) QC summary (batch)
"""))

    nb.cells.append(code(
        """qc_rows = []
for gid, s in series_by_gauge.items():
    summ = qc_daily_series(s)
    row = {"virtual_gauge_id": gid}
    row.update(qc_summary_dict(summ))
    qc_rows.append(row)

qc_df = pd.DataFrame(qc_rows).sort_values(["missing_pct", "longest_missing_streak_days"], ascending=[True, False])
qc_df.to_parquet(out_root / "results" / "qc_summary.parquet", index=False) if (out_root / "results").mkdir(parents=True, exist_ok=True) is None else None
qc_df.head(20)
"""
    ))

    nb.cells.append(md("""## 10) Interactive gauge browser (time series + POT calibration)

Select a virtual gauge and:
- view the daily discharge series
- compute candidate thresholds from quantiles
- run POT extraction + λ

If `ipywidgets` is not installed, set `selected_gauge_id` manually.
"""))

    nb.cells.append(code(
        """# Select gauge
if HAS_WIDGETS:
    dropdown = widgets.Dropdown(options=sorted(series_by_gauge.keys()), description='Gauge:')
    display(dropdown)
    selected_gauge_id = dropdown.value
else:
    selected_gauge_id = sorted(series_by_gauge.keys())[0]

selected_gauge_id
"""
    ))

    nb.cells.append(code(
        """s = series_by_gauge[selected_gauge_id].dropna().sort_index()

fig, ax = plt.subplots(1, 1, figsize=(12, 4))
s.plot(ax=ax)
ax.set_title(f"Daily discharge (m³/s) — {selected_gauge_id}")
ax.set_xlabel("Date")
ax.set_ylabel("Discharge (m³/s)")
plt.show()

# Candidate thresholds from quantiles
cand = sorted({float(s.quantile(q)) for q in candidate_quantiles})
print("Candidate thresholds (m³/s):", [round(u, 2) for u in cand])
"""
    ))

    nb.cells.append(code(
        """# Choose threshold (default: highest candidate) and run POT extraction
threshold_m3s = cand[-1]

pot = pot_extract(s, threshold_m3s=threshold_m3s, run_length_days=run_length_days)
xi_sigma = fit_gpd_to_pot(s, threshold_m3s=threshold_m3s, run_length_days=run_length_days)

print(f"Selected threshold_m3s: {threshold_m3s:.2f}")
print(f"Run-length (days): {run_length_days}")
print(f"Events extracted: {len(pot.events)}")
print(f"Coverage years (approx): {pot.coverage_years:.2f}")
print(f"Lambda (events/year): {pot.lambda_events_per_year:.3f}")
print(f"GPD params (xi, sigma): {xi_sigma}")

pot.annual_counts.head()
"""
    ))

    nb.cells.append(md("""## 11) Save calibration outputs (per gauge)
"""))

    nb.cells.append(code(
        """events_dir = out_root / "events"
results_dir = out_root / "results"
logs_dir = out_root / "logs"
for d in [events_dir, results_dir, logs_dir]:
    d.mkdir(parents=True, exist_ok=True)

# Save events for selected gauge
pot_events_path = events_dir / f"{selected_gauge_id}__pot_events.parquet"
pot.events.to_parquet(pot_events_path, index=False)

# Append/update results table
res_row = {
    "virtual_gauge_id": selected_gauge_id,
    "threshold_m3s": pot.threshold_m3s,
    "run_length_days": pot.run_length_days,
    "lambda_events_per_year": pot.lambda_events_per_year,
    "coverage_years": pot.coverage_years,
    "gpd_xi": float(xi_sigma[0]) if xi_sigma else None,
    "gpd_sigma": float(xi_sigma[1]) if xi_sigma else None,
}

results_path = results_dir / "evt_pot_calibration.parquet"
if results_path.exists():
    df = pd.read_parquet(results_path)
    df = df[df.virtual_gauge_id != selected_gauge_id]
    df = pd.concat([df, pd.DataFrame([res_row])], ignore_index=True)
else:
    df = pd.DataFrame([res_row])

df.to_parquet(results_path, index=False)
print("Wrote:", pot_events_path)
print("Updated:", results_path)
"""
    ))

    nb.cells.append(md("""## 12) Decision log (operator-editable)

Fill the fields and write a JSON log into the run folder.
"""))

    nb.cells.append(code(
        """from datetime import datetime
import json

# Operator edits:
decision_notes = "WHY did you choose this threshold/run-length? Note any data issues."
threshold_method = "MANUAL"  # MANUAL|AUTO (AUTO can be added later)

decision = {
    "run_tag": run_tag,
    "timestamp_utc": datetime.utcnow().isoformat() + "Z",
    "analyst_name": analyst_name,
    "USE_MUNI_AOI": USE_MUNI_AOI,
    "selected_gauge_id": selected_gauge_id,
    "threshold_m3s": float(pot.threshold_m3s),
    "run_length_days": int(pot.run_length_days),
    "lambda_events_per_year": float(pot.lambda_events_per_year),
    "threshold_method": threshold_method,
    "decision_notes": decision_notes,
}

log_path = logs_dir / "decision_log.json"
log_path.write_text(json.dumps(decision, indent=2), encoding="utf-8")
print("Wrote decision log:", log_path)
"""
    ))

    return nb


if __name__ == "__main__":
    out = Path(__file__).resolve().parents[1] / "notebooks" / "01_evt_pot_calibration_workflow.ipynb"
    out.parent.mkdir(parents=True, exist_ok=True)
    nb = build()
    nbf.write(nb, str(out))
    print("Wrote", out)
