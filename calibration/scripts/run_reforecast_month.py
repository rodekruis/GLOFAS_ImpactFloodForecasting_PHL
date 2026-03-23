"""
run_reforecast_month.py — Azure ML / local CLI worker for one month of GloFAS reforecast.

Processes one month of GloFAS GRIB:
  7A  Detect flood events (Amax connected-component metric)
  7B  Deduplicate candidates by verifying date
  7C  Compute flood depth + population impact (CLIMADA-Petals)
  7D  QA checks + write outputs

Requires checkpoint artifacts produced by notebook Cell 19 (CHECKPOINT SAVE):
  - flood_maps_ev.nc
  - pop_ev.npy
  - admin_id_raster_ev.npy
  - admin_id_to_name.json
  - support_cells_present.json
  - evt_params.parquet   (or override with --evt-params)

Usage:
  python run_reforecast_month.py \\
    --year 2008 --month 3 \\
    --grib-root /mnt/grib \\
    --checkpoint-dir /mnt/checkpoints \\
    --output-dir /mnt/outputs/year=2008/month=03

  # Debug run (2 members, 3 steps):
  python run_reforecast_month.py ... --max-members 2 --max-steps 3

Azure ML: set PHILFLOOD_RFC_GRIB_ROOT env var or pass --grib-root as a uri_folder mount path.
"""

from __future__ import annotations

import argparse
import gc
import json
import logging
import sys
import warnings
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import xarray as xr
from scipy import stats
from scipy.ndimage import label, generate_binary_structure

# ============================================================
# CONSTANTS — match notebook defaults exactly
# ============================================================
DEPTH_THRESHOLDS = [0.01, 0.02, 0.03, 0.04, 0.05, 0.1, 0.15, 0.2, 0.3, 0.5, 1.0]
DEPTH_PRIMARY    = 0.02   # primary threshold (backward-compat)
DEPTH_SAT        = 0.2    # satellite alias
T0_YEARS         = 2.0    # RP threshold for "active" cells
A_MIN_KM2        = 100.0  # minimum event area
DECLUSTER_DAYS   = 5      # temporal declustering window
RP_CAP           = 500.0  # cap on per-cell RP fields
CC_CONNECTIVITY  = 2      # 8-neighbour connectivity
DEDUP_TOPK       = 999    # max events kept per verifying date
RFC_SHORTNAME    = "dis24"  # GRIB variable name (mean discharge last 24 h)
USE_FLOPROS      = False  # flood-protection layer (off by default)

# Column rename: NB01 evt_pot_calibration.parquet → script names
EVT_COLUMN_RENAME = {
    "virtual_gauge_id":       "cell_id",
    "threshold_m3s":          "u",
    "lambda_events_per_year": "lam",
    "gpd_xi":                 "xi",
    "gpd_sigma":              "sigma",
}

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


def _log(msg: str) -> None:
    log.info(msg)


# ============================================================
# CLIMADA-Petals imports (optional — needed only for 7C)
# ============================================================
try:
    from climada_petals.hazard.rf_glofas.transform_ops import (
        regrid as _petals_regrid,
        flood_depth as _petals_flood_depth,
    )
    _CLIMADA_OK = True
except ImportError:
    _CLIMADA_OK = False
    _petals_regrid = None   # type: ignore[assignment]
    _petals_flood_depth = None  # type: ignore[assignment]


# ============================================================
# HELPERS: discharge → return period  (NB1 sign convention)
# ============================================================

def _gpd_exceedance_rate(
    q: np.ndarray, u: np.ndarray, sigma: np.ndarray,
    xi: np.ndarray, lam: np.ndarray,
) -> np.ndarray:
    """Exceedance rate λ·P(Q>q) using POT-GPD. xi follows scipy convention (positive = heavy tail)."""
    q, u, sigma, xi, lam = np.broadcast_arrays(
        np.asarray(q, float), np.asarray(u, float),
        np.asarray(sigma, float), np.asarray(xi, float), np.asarray(lam, float),
    )
    y = np.maximum((q - u) / sigma, 0.0)
    near0 = np.isclose(xi, 0.0)
    surv = np.empty_like(y)
    surv[near0]  = np.exp(-y[near0])
    surv[~near0] = np.power(1.0 + xi[~near0] * y[~near0], -1.0 / xi[~near0])
    return np.clip(lam * surv, 1e-12, None)


def discharge_to_return_period(
    q: np.ndarray, u: np.ndarray, sigma: np.ndarray,
    xi: np.ndarray, lam: np.ndarray, rp_cap: float = 500.0,
) -> np.ndarray:
    return np.clip(1.0 / _gpd_exceedance_rate(q, u, sigma, xi, lam), 1.0, rp_cap)


# ============================================================
# HELPERS: peak picking (plateau-safe)
# ============================================================

def peak_pick(
    series: pd.Series, threshold: float, decluster_days: int,
) -> pd.DatetimeIndex:
    s = series.dropna().sort_index()
    if s.empty:
        return pd.DatetimeIndex([])
    roll_max = s.rolling(window=3, center=True, min_periods=1).max()
    cands = s[(s >= threshold) & (s == roll_max)].sort_values(ascending=False)
    if cands.empty:
        return pd.DatetimeIndex([])
    selected: list = []
    taken = pd.Series(False, index=s.index)
    for t, _ in cands.items():
        if taken.loc[t]:
            continue
        selected.append(t)
        win = ((s.index >= t - pd.Timedelta(days=decluster_days)) &
               (s.index <= t + pd.Timedelta(days=decluster_days)))
        taken.loc[win] = True
    return pd.DatetimeIndex(sorted(selected))


# ============================================================
# HELPERS: grid utilities
# ============================================================

def _earth_cell_area_km2(lat_deg: np.ndarray, dlat_deg: float, dlon_deg: float) -> np.ndarray:
    R = 6371.0
    return (R ** 2) * np.deg2rad(dlat_deg) * np.deg2rad(dlon_deg) * np.cos(np.deg2rad(lat_deg))


def _nearest_index_1d(arr_1d: np.ndarray, targets: np.ndarray) -> np.ndarray:
    arr = np.asarray(arr_1d, float)
    t   = np.asarray(targets, float)
    dif = np.diff(arr)
    if not (np.all(dif >= 0) or np.all(dif <= 0)):
        return np.array([int(np.argmin(np.abs(arr - x))) for x in t])
    rev = bool(np.all(dif <= 0))
    a   = arr[::-1] if rev else arr
    idx = np.clip(np.searchsorted(a, t, side="left"), 1, len(a) - 1)
    left, right = a[idx - 1], a[idx]
    idx_f = np.where(np.abs(right - t) < np.abs(t - left), idx, idx - 1).astype(int)
    return ((len(arr) - 1) - idx_f) if rev else idx_f


def _ensure_360(lons_deg: np.ndarray, grid_lon_1d: np.ndarray) -> np.ndarray:
    lons_deg = np.asarray(lons_deg, float)
    if float(np.nanmax(grid_lon_1d)) > 180.0:
        return np.where(lons_deg < 0, lons_deg + 360.0, lons_deg)
    return lons_deg


def _dt_from_grib(dataDate: int, dataTime: int) -> pd.Timestamp:
    return pd.to_datetime(f"{int(dataDate):08d}{int(dataTime):04d}", format="%Y%m%d%H%M")


# ============================================================
# HELPERS: GRIB indexing
# ============================================================

def _build_msg_index(
    grbs, shortName: str, scan_limit: Optional[int] = None,
) -> Tuple[dict, list, list, list, int]:
    """Index GRIB messages without loading values. Returns (msg_index, inits, steps, members, template_msgnum)."""
    msg_index: dict = {}
    inits: set = set(); steps: set = set(); members: set = set()
    template_msgnum: Optional[int] = None
    grbs.rewind()
    for i, g in enumerate(grbs, start=1):
        if scan_limit is not None and i > scan_limit:
            break
        try:
            if g.shortName != shortName:
                continue
            dd = int(g.dataDate); tt = int(g.dataTime)
            es = int(g.endStep);  pn = int(g.perturbationNumber)
        except Exception:
            continue
        msg_index[(dd, tt, es, pn)] = i
        inits.add((dd, tt)); steps.add(es); members.add(pn)
        if template_msgnum is None:
            template_msgnum = i
    if not msg_index:
        raise RuntimeError(f"No GRIB messages found for shortName='{shortName}'")
    return msg_index, sorted(inits), sorted(steps), sorted(members), template_msgnum  # type: ignore[return-value]


# ============================================================
# HELPERS: population impact aggregation
# ============================================================

def build_rp_grid_from_values(
    df: pd.DataFrame,
    value_col: str = "rp",
    lat_col:   str = "lat",
    lon_col:   str = "lon",
    fill:      float = np.nan,
    round_coords: int = 4,
) -> xr.DataArray:
    d = df.copy()
    d[lat_col] = d[lat_col].astype(float).round(round_coords)
    d[lon_col] = d[lon_col].astype(float).round(round_coords)
    lat_vals = np.sort(d[lat_col].unique())
    lon_vals = np.sort(d[lon_col].unique())
    grid = np.full((len(lat_vals), len(lon_vals)), fill, dtype="float32")
    lat_idx = {v: i for i, v in enumerate(lat_vals)}
    lon_idx = {v: j for j, v in enumerate(lon_vals)}
    for la, lo, val in zip(d[lat_col].values, d[lon_col].values, d[value_col].values):
        i, j = lat_idx.get(la), lon_idx.get(lo)
        if i is not None and j is not None:
            grid[i, j] = float(val)
    return xr.DataArray(
        grid,
        coords={"latitude": lat_vals.astype(float), "longitude": lon_vals.astype(float)},
        dims=("latitude", "longitude"),
        name=value_col,
    )


def aggregate_affected_population_nb3_fast(
    pop_grid: np.ndarray,
    depth_grid: np.ndarray,
    admin_id_raster: np.ndarray,
    admin_ids_present: np.ndarray,
    thresholds_m: List[float],
    id_to_name: Dict[int, str],
) -> pd.DataFrame:
    pop   = np.nan_to_num(np.clip(np.asarray(pop_grid, "float32"), 0, None), nan=0.0)
    depth = np.asarray(depth_grid, "float32")
    admin = np.asarray(admin_id_raster, "int32")
    ids_flat  = admin.ravel()
    valid     = ids_flat > 0
    ids_valid = ids_flat[valid]
    rows: list = []
    for thr in thresholds_m:
        flooded_pop = np.where(np.isfinite(depth) & (depth >= float(thr)), pop, 0.0).ravel()
        sums = np.bincount(ids_valid, weights=flooded_pop[valid], minlength=int(admin.max()) + 1)
        for adm_id in admin_ids_present:
            aid = int(adm_id)
            rows.append({
                "adm3_id":     aid,
                "adm3_name":   id_to_name.get(aid, str(aid)),
                "depth_thr_m": float(thr),
                "affected_pop": float(sums[aid]) if aid < len(sums) else 0.0,
            })
    return pd.DataFrame(rows)


def depth_thr_to_col(thr_m: float) -> str:
    return f"PopAffected_{int(round(thr_m * 1000))}mm"


def safe_write(df: pd.DataFrame, base: Path) -> None:
    base.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(base.with_suffix(".csv"), index=False)
    try:
        df.to_parquet(base.with_suffix(".parquet"), index=False)
    except Exception:
        pass


# ============================================================
# HELPERS: CLIMADA depth engine  (NB3-mirror, self-contained)
# ============================================================

def _ensure_lon_lat_coords(da: xr.DataArray) -> xr.DataArray:
    if "lon" not in da.coords and "longitude" in da.coords:
        da = da.assign_coords(lon=da["longitude"])
    if "lat" not in da.coords and "latitude" in da.coords:
        da = da.assign_coords(lat=da["latitude"])
    return da


def _match_coord_order(source: xr.DataArray, target: xr.DataArray) -> xr.DataArray:
    for coord in ("latitude", "longitude"):
        src_desc = source[coord].values[0] > source[coord].values[-1]
        tgt_desc = target[coord].values[0] > target[coord].values[-1]
        if src_desc != tgt_desc:
            source = source.sortby(coord, ascending=not tgt_desc)
    return source


def _sanitize_rp(da: xr.DataArray) -> xr.DataArray:
    return da.where(da >= 1.0)


def _sel_lon_lat_slice(target: xr.DataArray, source: xr.DataArray) -> xr.DataArray:
    bounds = {}
    for coord in ("longitude", "latitude"):
        lo = float(source[coord].min()); hi = float(source[coord].max())
        vals = source[coord].values
        res = float(np.median(np.abs(np.diff(vals)))) if len(vals) > 1 else 0.05
        lo -= res / 2; hi += res / 2
        tgt_vals = target[coord].values
        descending = tgt_vals[0] > tgt_vals[-1]
        bounds[coord] = slice(hi, lo) if descending else slice(lo, hi)
    return target.sel(bounds)


def compute_depth_from_rp_nb3(
    rp_da_2d:     xr.DataArray,
    event_id:     str,
    apply_flopros: bool,
    flood_maps:   xr.DataArray,
) -> xr.DataArray:
    if not _CLIMADA_OK:
        raise ImportError(
            "climada-petals is required for depth computation.\n"
            "Install: pip install climada-petals"
        )
    rp_da_3d = rp_da_2d.expand_dims({"event": [event_id]})
    rp_da_3d = _ensure_lon_lat_coords(rp_da_3d)
    rp_da_3d = _sanitize_rp(rp_da_3d)

    flood_maps_sel = _sel_lon_lat_slice(flood_maps, rp_da_3d)
    flood_maps_sel = _ensure_lon_lat_coords(flood_maps_sel)

    if flood_maps_sel.sizes.get("latitude", 0) == 0 or flood_maps_sel.sizes.get("longitude", 0) == 0:
        raise ValueError("No overlap between RP grid and JRC flood maps. Check lat/lon bounds.")

    rp_da_3d   = _match_coord_order(rp_da_3d, flood_maps_sel)
    rp_regrid  = _petals_regrid(rp_da_3d, flood_maps_sel, method="bilinear")

    # Reindex onto the full JRC subset; fill fringe half-cells with boundary RP values
    rp_regrid  = rp_regrid.reindex(
        latitude=flood_maps_sel.latitude, longitude=flood_maps_sel.longitude, method=None
    )
    lat_lo = float(rp_da_3d.latitude.min());  lat_hi = float(rp_da_3d.latitude.max())
    lon_lo = float(rp_da_3d.longitude.min()); lon_hi = float(rp_da_3d.longitude.max())
    rp_fringe = (rp_regrid
                 .ffill("latitude").bfill("latitude")
                 .ffill("longitude").bfill("longitude"))
    in_domain = (
        (rp_regrid.latitude  >= lat_lo) & (rp_regrid.latitude  <= lat_hi) &
        (rp_regrid.longitude >= lon_lo) & (rp_regrid.longitude <= lon_hi)
    )
    rp_regrid = rp_regrid.where(in_domain, rp_fringe)
    rp_regrid = _sanitize_rp(rp_regrid)

    # apply_flopros is False by default — skip silently
    depth = _petals_flood_depth(rp_regrid, flood_maps_sel).isel(event=0)
    return depth


def subset_to_depth_grid(
    depth_da:          xr.DataArray,
    flood_maps_ev:     xr.DataArray,
    pop_ev:            np.ndarray,
    admin_id_raster_ev: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    tmpl   = flood_maps_ev.isel(return_period=0)
    pop_da = xr.DataArray(pop_ev,              coords={"latitude": tmpl["latitude"].values,
                                                        "longitude": tmpl["longitude"].values},
                          dims=("latitude", "longitude"))
    adm_da = xr.DataArray(admin_id_raster_ev,  coords={"latitude": tmpl["latitude"].values,
                                                        "longitude": tmpl["longitude"].values},
                          dims=("latitude", "longitude"))
    pop_sub = pop_da.sel(latitude=depth_da["latitude"], longitude=depth_da["longitude"]).values
    adm_sub = adm_da.sel(latitude=depth_da["latitude"], longitude=depth_da["longitude"]).values.astype("int32")
    ids = np.unique(adm_sub); ids = ids[ids > 0]
    return pop_sub, adm_sub, ids


# ============================================================
# CHECKPOINT LOADER
# ============================================================

def load_checkpoint(ckpt_dir: Path) -> dict:
    p = Path(ckpt_dir)
    d: dict = {}
    if (p / "flood_maps_ev.nc").exists():
        d["flood_maps_ev"] = xr.open_dataarray(p / "flood_maps_ev.nc").load()
    if (p / "pop_ev.npy").exists():
        d["pop_ev"] = np.load(p / "pop_ev.npy", allow_pickle=False)
    if (p / "admin_id_raster_ev.npy").exists():
        d["admin_id_raster_ev"] = np.load(p / "admin_id_raster_ev.npy", allow_pickle=False)
    if (p / "admin_ids_present_ev.npy").exists():
        d["admin_ids_present_ev"] = np.load(p / "admin_ids_present_ev.npy", allow_pickle=False)
    if (p / "admin_id_to_name.json").exists():
        with open(p / "admin_id_to_name.json", encoding="utf-8") as f:
            d["admin_id_to_name"] = {int(k): v for k, v in json.load(f).items()}
    if (p / "support_cells_present.json").exists():
        with open(p / "support_cells_present.json", encoding="utf-8") as f:
            d["support_cells_present"] = json.load(f)
    if (p / "evt_params.parquet").exists():
        d["evt_params"] = pd.read_parquet(p / "evt_params.parquet")
    if (p / "runtime_config.json").exists():
        with open(p / "runtime_config.json", encoding="utf-8") as f:
            d["runtime_config"] = json.load(f)
    return d


# ============================================================
# MAIN
# ============================================================

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Process one month of GloFAS reforecast GRIB for PhilFlood impact pipeline."
    )
    parser.add_argument("--year",           type=int, required=True,
                        help="Year to process (e.g. 2008)")
    parser.add_argument("--month",          type=int, required=True,
                        help="Month to process (1–12)")
    parser.add_argument("--grib-root",      type=str, required=True,
                        help="Root dir for GRIB. Script looks for: "
                             "{grib_root}/{year}/_staging/extract/{year}_{month:02d}/data.grib")
    parser.add_argument("--checkpoint-dir", type=str, required=True,
                        help="Dir with checkpoint artifacts saved by notebook Cell 19: "
                             "flood_maps_ev.nc, pop_ev.npy, admin_id_raster_ev.npy, "
                             "admin_id_to_name.json, support_cells_present.json, evt_params.parquet")
    parser.add_argument("--evt-params",     type=str, default=None,
                        help="Path to evt_pot_calibration.parquet. "
                             "Overrides checkpoint evt_params.parquet if provided.")
    parser.add_argument("--output-dir",     type=str, required=True,
                        help="Output directory. Writes: "
                             "event_registry_reforecast_library_{Y}_{MM}.parquet, "
                             "impacts_by_admin_{Y}_{MM}.parquet")
    # Debug / acceptance-test knobs
    parser.add_argument("--max-members",    type=int, default=None,
                        help="Limit ensemble members (debug, e.g. 2)")
    parser.add_argument("--max-steps",      type=int, default=None,
                        help="Limit forecast steps (debug, e.g. 3)")
    parser.add_argument("--max-inits",      type=int, default=None,
                        help="Limit init times per file (debug)")

    args = parser.parse_args()

    year  = int(args.year)
    month = int(args.month)
    grib_root      = Path(args.grib_root)
    checkpoint_dir = Path(args.checkpoint_dir)
    output_dir     = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    _log(f"=== run_reforecast_month  year={year}  month={month:02d} ===")
    _log(f"  grib_root:      {grib_root}")
    _log(f"  checkpoint_dir: {checkpoint_dir}")
    _log(f"  output_dir:     {output_dir}")

    # ── pygrib (fail fast) ──────────────────────────────────────────────
    try:
        import pygrib
    except ImportError:
        _log("ERROR: pygrib not found. Install: conda install -c conda-forge pygrib eccodes")
        return 1

    # ── Load checkpoint ─────────────────────────────────────────────────
    _log("Loading checkpoint artifacts ...")
    ckpt = load_checkpoint(checkpoint_dir)
    for key in ("flood_maps_ev", "pop_ev", "admin_id_raster_ev",
                "admin_id_to_name", "support_cells_present"):
        if key not in ckpt:
            _log(f"ERROR: '{key}' not found in checkpoint_dir={checkpoint_dir}")
            return 1

    flood_maps_ev         = ckpt["flood_maps_ev"]
    pop_ev                = ckpt["pop_ev"]
    admin_id_raster_ev    = ckpt["admin_id_raster_ev"]
    admin_id_to_name      = ckpt["admin_id_to_name"]
    support_cells_present = ckpt["support_cells_present"]
    _log(f"Checkpoint: {len(support_cells_present)} support cells, "
         f"flood_maps dims={dict(flood_maps_ev.dims)}")

    # ── Load EVT1 params ─────────────────────────────────────────────────
    if args.evt_params:
        _log(f"Loading EVT1 params from CLI: {args.evt_params}")
        evt_params = pd.read_parquet(args.evt_params)
        evt_params = evt_params.rename(columns=EVT_COLUMN_RENAME)
    elif "evt_params" in ckpt:
        evt_params = ckpt["evt_params"]
    else:
        _log("ERROR: No evt_params.parquet in checkpoint and --evt-params not given")
        return 1
    _log(f"EVT params: {len(evt_params)} rows, columns={list(evt_params.columns)}")

    # ── Setup detection cells ─────────────────────────────────────────────
    cell_ids_available = set(evt_params["cell_id"].values)
    det_cells = [c for c in support_cells_present if c in cell_ids_available]
    if not det_cells:
        _log("ERROR: No detection cells found (support_cells_present ∩ evt_params)")
        return 1

    p_det      = evt_params.set_index("cell_id").loc[det_cells].copy()
    det_lats   = p_det["lat"].astype(float).values
    det_lons   = p_det["lon"].astype(float).values
    u_det      = p_det["u"].astype(float).values[None, :]
    xi_det     = p_det["xi"].astype(float).values[None, :]
    sigma_det  = p_det["sigma"].astype(float).values[None, :]
    lam_det    = p_det["lam"].astype(float).values[None, :]

    # Footprint cells == detection cells (NB3 parity)
    p_fp       = p_det
    fp_lats    = det_lats; fp_lons = det_lons
    u_fp       = u_det;    xi_fp   = xi_det
    sigma_fp   = sigma_det; lam_fp = lam_det

    structure = generate_binary_structure(2, CC_CONNECTIVITY)

    # ── Discover GRIB file ───────────────────────────────────────────────
    extract_root = grib_root / str(year) / "_staging" / "extract"
    grib_file    = extract_root / f"{year}_{month:02d}" / "data.grib"
    if not grib_file.exists():
        _log(f"ERROR: GRIB file not found: {grib_file}")
        return 1
    _log(f"GRIB file: {grib_file}  ({grib_file.stat().st_size / 1e9:.2f} GB)")

    # ── STEP 7A — Event detection ────────────────────────────────────────
    _log(f"Step 7A: detecting events in {year}-{month:02d} ...")
    raw_events: List[dict] = []

    grbs = pygrib.open(str(grib_file))
    msg_index, inits, steps_hours, members, template_msgnum = _build_msg_index(grbs, RFC_SHORTNAME)

    if args.max_inits   is not None: inits       = inits[:args.max_inits]
    if args.max_steps   is not None: steps_hours = steps_hours[:args.max_steps]
    if args.max_members is not None: members     = members[:args.max_members]

    # Grid coordinates from template message
    tmpl   = grbs.message(int(template_msgnum))
    lats2d, lons2d = tmpl.latlons()
    lat1d  = lats2d[:, 0].astype(float)
    lon1d  = lons2d[0, :].astype(float)

    # Snap detection cells to GRIB grid
    det_lons_use = _ensure_360(det_lons, lon1d)
    det_i = _nearest_index_1d(lat1d, det_lats)
    det_j = _nearest_index_1d(lon1d, det_lons_use)

    # Build grid_index and area_grid_km2 (needed for connected-component metric)
    lat_vals = np.sort(np.unique(lat1d)); lon_vals = np.sort(np.unique(lon1d))
    nlat, nlon = len(lat_vals), len(lon_vals)
    dlat = float(np.median(np.abs(np.diff(lat_vals)))) if nlat > 1 else 0.05
    dlon = float(np.median(np.abs(np.diff(lon_vals)))) if nlon > 1 else 0.05

    lat_to_i = {round(float(v), 6): i for i, v in enumerate(lat_vals)}
    lon_to_j = {round(float(v), 6): j for j, v in enumerate(lon_vals)}
    grid_index = -np.ones((nlat, nlon), dtype=int)
    for k, (la, lo) in enumerate(zip(det_lats, det_lons_use)):
        i = lat_to_i.get(round(la, 6), int(_nearest_index_1d(lat_vals, [la])[0]))
        j = lon_to_j.get(round(lo, 6), int(_nearest_index_1d(lon_vals, [lo])[0]))
        grid_index[i, j] = k

    area_lat_km2  = _earth_cell_area_km2(lat_vals, dlat, dlon)
    area_grid_km2 = area_lat_km2[:, None] * np.ones((1, nlon))
    valid_mask    = (grid_index >= 0)

    def _compute_amax(active_vec: np.ndarray) -> float:
        """Connected-component area (km²) of largest patch where active_vec is True."""
        if not np.any(active_vec):
            return 0.0
        g = np.zeros(grid_index.shape, dtype=bool)
        g[valid_mask] = active_vec[grid_index[valid_mask]]
        if not g.any():
            return 0.0
        ai = np.argwhere(g)
        r0 = max(int(ai[:, 0].min()) - 1, 0); r1 = min(int(ai[:, 0].max()) + 2, nlat)
        c0 = max(int(ai[:, 1].min()) - 1, 0); c1 = min(int(ai[:, 1].max()) + 2, nlon)
        g_sub, a_sub = g[r0:r1, c0:c1], area_grid_km2[r0:r1, c0:c1]
        labs, nlab = label(g_sub, structure=structure)
        if nlab == 0:
            return 0.0
        areas = np.bincount(labs.ravel(), weights=a_sub.ravel())
        return float(np.max(areas[1:])) if len(areas) > 1 else 0.0

    steps_arr = np.asarray(steps_hours, dtype=int)

    for (dd, tt) in inits:
        init_dt = _dt_from_grib(dd, tt)
        vt = pd.DatetimeIndex(init_dt + pd.to_timedelta(steps_arr, unit="h"))

        for pn in members:
            amax     = np.zeros(len(steps_arr))
            n_active = np.zeros(len(steps_arr), dtype=int)
            rp_p50   = np.zeros(len(steps_arr)); rp_p90 = np.zeros(len(steps_arr))
            rp_p99   = np.zeros(len(steps_arr))
            frac_ge10 = np.zeros(len(steps_arr)); frac_ge20 = np.zeros(len(steps_arr))
            msgnum_by_step: dict = {}

            for si, step_h in enumerate(steps_arr):
                key    = (int(dd), int(tt), int(step_h), int(pn))
                msgnum = msg_index.get(key)
                if msgnum is None:
                    continue
                msgnum_by_step[int(step_h)] = int(msgnum)

                msg  = grbs.message(int(msgnum))
                vals = msg.values
                q    = vals[det_i, det_j].astype("float32")
                rp   = discharge_to_return_period(
                    q[None, :], u_det, sigma_det, xi_det, lam_det, RP_CAP
                ).ravel()
                active_vec     = (rp >= float(T0_YEARS))
                n_active[si]   = int(np.sum(active_vec))
                amax[si]       = _compute_amax(active_vec)
                rp_p50[si]     = float(np.nanpercentile(rp, 50))
                rp_p90[si]     = float(np.nanpercentile(rp, 90))
                rp_p99[si]     = float(np.nanpercentile(rp, 99))
                frac_ge10[si]  = float(np.mean(rp >= 10.0))
                frac_ge20[si]  = float(np.mean(rp >= 20.0))
                del vals, q, rp, active_vec, msg

            A_series = pd.Series(amax, index=vt, name="Amax_km2").sort_index()
            peaks    = peak_pick(A_series, threshold=float(A_MIN_KM2), decluster_days=int(DECLUSTER_DAYS))

            for pk in peaks:
                pk64   = np.datetime64(pd.to_datetime(pk))
                diffs  = np.abs((vt.values - pk64).astype("timedelta64[s]").astype(np.int64))
                si_pk  = int(np.argmin(diffs))
                sh_pk  = int(steps_arr[si_pk])
                mn_pk  = msgnum_by_step.get(sh_pk)
                raw_events.append({
                    "source":             "reforecast_candidate",
                    "year":               year,
                    "month":              month,
                    "grib_path":          str(grib_file),
                    "init_time":          pd.to_datetime(init_dt),
                    "member":             int(pn),
                    "valid_time":         pd.to_datetime(pk),
                    "lead_time_days":     float(sh_pk / 24.0),
                    "lead_time_hours":    int(sh_pk),
                    "step_index":         int(si_pk),
                    "grib_msgnum":        int(mn_pk) if mn_pk is not None else np.nan,
                    "W_peak":             float(A_series.iloc[si_pk]),
                    "Amax_km2_peak":      float(A_series.iloc[si_pk]),
                    "n_active_cells_peak": int(n_active[si_pk]),
                    "rp_p50":             float(rp_p50[si_pk]),
                    "rp_p90":             float(rp_p90[si_pk]),
                    "rp_p99":             float(rp_p99[si_pk]),
                    "frac_rp_ge10":       float(frac_ge10[si_pk]),
                    "frac_rp_ge20":       float(frac_ge20[si_pk]),
                    "T0_years":           float(T0_YEARS),
                    "A_min_km2":          float(A_MIN_KM2),
                    "decluster_days":     int(DECLUSTER_DAYS),
                    "cc_connectivity":    int(CC_CONNECTIVITY),
                })
            del amax, n_active, rp_p50, rp_p90, rp_p99, frac_ge10, frac_ge20, A_series

    grbs.close()
    gc.collect()

    raw_df = pd.DataFrame(raw_events)
    _log(f"Step 7A: {len(raw_df):,} candidate peaks detected")

    # ── STEP 7B — Deduplication ──────────────────────────────────────────
    _log("Step 7B: deduplication ...")
    empty_output = raw_df.empty
    if empty_output:
        _log("WARNING: No events detected in this month.")

    safe_write(
        raw_df,
        output_dir / f"event_registry_reforecast_candidates_raw_{year}_{month:02d}",
    )

    if empty_output:
        for stem in (
            f"event_registry_reforecast_library_{year}_{month:02d}",
            f"impacts_by_admin_{year}_{month:02d}",
        ):
            safe_write(pd.DataFrame(), output_dir / stem)
        return 0

    raw_df["peak_date"]      = pd.to_datetime(raw_df["valid_time"])
    raw_df["verifying_date"] = raw_df["peak_date"].dt.floor("D")
    raw_df = raw_df.sort_values(["verifying_date", "W_peak"], ascending=[True, False])
    library = (raw_df.groupby("verifying_date")
               .head(int(DEDUP_TOPK))
               .reset_index(drop=True)
               .sort_values(["verifying_date", "W_peak"], ascending=[True, False])
               .reset_index(drop=True))
    library["event_id"] = [f"RFC_{year}_{month:02d}_{i:05d}" for i in range(len(library))]
    library["source"]   = "reforecast_library"
    event_reg = library.copy()
    _log(f"Step 7B: {len(event_reg):,} events after dedup (topK={DEDUP_TOPK})")
    safe_write(event_reg, output_dir / f"event_registry_reforecast_library_{year}_{month:02d}")

    # ── STEP 7C — Impact calculation ─────────────────────────────────────
    _log("Step 7C: computing flood depth + population impact ...")
    fp_lons_use = _ensure_360(fp_lons, lon1d)
    fp_i = _nearest_index_1d(lat1d, fp_lats)
    fp_j = _nearest_index_1d(lon1d, fp_lons_use)

    pop_summary: List[dict] = []
    month_frames: List[pd.DataFrame] = []

    grbs = pygrib.open(str(grib_file))
    msg_index, _, _, _, _ = _build_msg_index(grbs, RFC_SHORTNAME)

    for _, ev in event_reg.iterrows():
        eid    = str(ev["event_id"])
        msgnum = ev.get("grib_msgnum", np.nan)

        if msgnum is None or (isinstance(msgnum, float) and not np.isfinite(msgnum)):
            init_ev = pd.to_datetime(ev["init_time"])
            dd_ev   = int(init_ev.strftime("%Y%m%d"))
            tt_ev   = int(init_ev.strftime("%H%M"))
            sh_ev   = int(ev["lead_time_hours"])
            pn_ev   = int(ev["member"])
            msgnum  = msg_index.get((dd_ev, tt_ev, sh_ev, pn_ev))

        if msgnum is None:
            _log(f"  WARNING: no GRIB message for {eid}, skipping impact")
            continue

        msg    = grbs.message(int(msgnum))
        vals   = msg.values
        q_fp   = vals[fp_i, fp_j].astype("float32")[None, :]
        rp_vals = discharge_to_return_period(
            q_fp, u_fp, sigma_fp, xi_fp, lam_fp, RP_CAP
        ).ravel()

        rp_df     = pd.DataFrame({
            "lat": p_fp["lat"].values.astype(float),
            "lon": p_fp["lon"].values.astype(float),
            "rp":  rp_vals.astype(float),
        })
        rp_grid_2d = (build_rp_grid_from_values(rp_df, value_col="rp", fill=np.nan)
                      .sortby("latitude").sortby("longitude"))
        depth_da   = compute_depth_from_rp_nb3(
            rp_da_2d=rp_grid_2d, event_id=eid,
            apply_flopros=USE_FLOPROS, flood_maps=flood_maps_ev,
        )
        pop_use, admin_use, ids_use = subset_to_depth_grid(
            depth_da, flood_maps_ev, pop_ev, admin_id_raster_ev,
        )
        df_imp = aggregate_affected_population_nb3_fast(
            pop_grid=pop_use, depth_grid=depth_da.values,
            admin_id_raster=admin_use, admin_ids_present=ids_use,
            thresholds_m=DEPTH_THRESHOLDS, id_to_name=admin_id_to_name,
        )
        df_imp["event_id"] = eid
        df_imp["source"]   = "reforecast_library"
        df_imp["year"]     = year
        df_imp["month"]    = month
        month_frames.append(df_imp)

        tot = df_imp.groupby("depth_thr_m")["affected_pop"].sum()
        row: dict = {"event_id": eid}
        row.update({depth_thr_to_col(thr): float(tot.get(thr, 0.0)) for thr in DEPTH_THRESHOLDS})
        row["PopAffected_op"]  = float(tot.get(DEPTH_PRIMARY, 0.0))
        row["PopAffected_sat"] = float(tot.get(DEPTH_SAT,     0.0))
        pop_summary.append(row)
        del vals, q_fp, rp_vals, msg

    grbs.close()
    gc.collect()

    # Write admin-level impacts
    if month_frames:
        df_month = pd.concat(month_frames, ignore_index=True)
        safe_write(df_month, output_dir / f"impacts_by_admin_{year}_{month:02d}")
        _log(f"Step 7C: wrote {len(df_month):,} admin-impact rows")
    else:
        safe_write(pd.DataFrame(), output_dir / f"impacts_by_admin_{year}_{month:02d}")

    # Merge event-level totals back into registry
    if pop_summary:
        pop_df   = pd.DataFrame(pop_summary).drop_duplicates(subset=["event_id"])
        event_reg = event_reg.merge(pop_df, on="event_id", how="left")
    safe_write(event_reg, output_dir / f"event_registry_reforecast_library_{year}_{month:02d}")

    # ── STEP 7D — QA ────────────────────────────────────────────────────
    miss = (int(event_reg["PopAffected_op"].isna().sum())
            if "PopAffected_op" in event_reg.columns else len(event_reg))
    _log(f"Step 7D QA: events={len(event_reg):,}  missing_PopAffected_op={miss}")
    _log(f"Done: year={year}  month={month:02d}  output_dir={output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
