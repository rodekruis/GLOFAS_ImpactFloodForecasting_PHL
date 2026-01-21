from __future__ import annotations

import hashlib
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple, Union

import pandas as pd

try:
    import xarray as xr
except Exception:  # pragma: no cover
    xr = None

# Suppress ECCODES warnings about invalid dates (year=0 month=0 day=0)
# These are handled gracefully in extract_daily_discharge_for_points via pd.to_datetime errors='coerce'
warnings.filterwarnings("ignore", category=UserWarning, message=".*g2date.*unpack.*")
warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*g2date.*unpack.*")


@dataclass(frozen=True)
class GribInventoryItem:
    year: int
    grib_path: Path


def _require_xr():
    if xr is None:
        raise ImportError("xarray is required to read GRIB files")


def discover_grib_year_files(grib_root: Union[str, Path], selected_years: Optional[List[int]] = None) -> List[GribInventoryItem]:
    """Discover GRIB files under a root directory organized by year.

    Expected pattern (locked decision): <root>/YYYY/data.grib (or .grib2).
    If multiple GRIBs exist in a year folder, prefers files named like 'data.grib*'.
    
    Args:
        grib_root: Root directory containing year folders
        selected_years: If provided, only include these years (useful for debugging)
    """
    grib_root = Path(grib_root)
    if not grib_root.exists():
        raise FileNotFoundError(f"GloFAS GRIB root not found: {grib_root}")

    items: List[GribInventoryItem] = []
    for p in sorted(grib_root.glob("[0-9][0-9][0-9][0-9]")):
        if not p.is_dir():
            continue
        year = int(p.name)
        
        # Skip if year not in selected_years (if filtering is enabled)
        if selected_years is not None and year not in selected_years:
            continue
            
        candidates = list(p.glob("*.grib*"))
        if not candidates:
            continue
        preferred = [c for c in candidates if c.name.lower().startswith("data.grib")]
        chosen = preferred[0] if len(preferred) == 1 else (preferred[0] if preferred else None)
        if chosen is None:
            if len(candidates) == 1:
                chosen = candidates[0]
            else:
                raise RuntimeError(
                    f"Multiple GRIB files found for year {year} in {p}, and none named 'data.grib*'. "
                    f"Found: {[c.name for c in candidates]}"
                )
        items.append(GribInventoryItem(year=year, grib_path=chosen))

    if not items:
        filter_msg = f" for years {selected_years}" if selected_years else ""
        raise RuntimeError(f"No year GRIB files discovered under: {grib_root}{filter_msg}")
    return items


def _stable_idx_name(grib_path: Path) -> str:
    h = hashlib.sha1(str(grib_path.resolve()).encode("utf-8")).hexdigest()[:16]
    return f"cfgrib_{h}.idx"


def open_grib_dataset(grib_path: Union[str, Path], index_dir: Union[str, Path], backend_kwargs: Optional[dict] = None) -> "xr.Dataset":
    """Open a GRIB file using xarray+cfgrib with a stable on-disk index.

    cfgrib uses an index file ('.idx') to speed up repeated reads. We keep those indices
    under data/processed to avoid polluting raw inputs.
    
    Note: cfgrib doesn't support chunks directly, but we can use xarray's chunks parameter
    to lazily evaluate after opening.
    """
    import logging
    
    _require_xr()
    logger = logging.getLogger(__name__)
    
    grib_path = Path(grib_path)
    index_dir = Path(index_dir)
    index_dir.mkdir(parents=True, exist_ok=True)

    idx_name = _stable_idx_name(grib_path)
    indexpath = str(index_dir / idx_name)

    # Backend kwargs (cfgrib-specific, no chunks here)
    bk = {"indexpath": indexpath}
    
    if backend_kwargs:
        # Remove 'chunks' if present (cfgrib doesn't support it)
        backend_kwargs = {k: v for k, v in backend_kwargs.items() if k != "chunks"}
        bk.update(backend_kwargs)

    try:
        logger.debug(f"Opening GRIB: {grib_path} with index at {indexpath}")
        ds = xr.open_dataset(grib_path, engine="cfgrib", backend_kwargs=bk)
        logger.debug(f"Successfully opened {grib_path}")
        return ds
    except Exception as e:
        logger.error(f"Failed to open GRIB {grib_path}: {e}")
        raise


def infer_lat_lon_names(ds: "xr.Dataset") -> Tuple[str, str]:
    """Infer latitude/longitude coordinate names from a dataset."""
    candidates_lat = ["latitude", "lat", "y"]
    candidates_lon = ["longitude", "lon", "x"]

    lat_name = next((c for c in candidates_lat if c in ds.coords), None)
    lon_name = next((c for c in candidates_lon if c in ds.coords), None)
    if lat_name is None or lon_name is None:
        raise KeyError(f"Could not infer lat/lon names from coords: {list(ds.coords)}")
    return lat_name, lon_name


def infer_time_name(ds: "xr.Dataset") -> str:
    for c in ["time", "valid_time", "step"]:
        if c in ds.coords:
            return c
    # xarray sets time as dimension sometimes
    for d in ds.dims:
        if d in {"time", "valid_time"}:
            return d
    raise KeyError(f"Could not infer time coordinate from dataset. dims={list(ds.dims)} coords={list(ds.coords)}")


def infer_discharge_var(ds: "xr.Dataset") -> str:
    """Pick the most likely discharge variable.

    Heuristic: choose the first data_var with a time dimension.
    """
    t = infer_time_name(ds)
    for v in ds.data_vars:
        if t in ds[v].dims:
            return v
    # fallback: first var
    if ds.data_vars:
        return list(ds.data_vars)[0]
    raise KeyError("No data variables found in GRIB dataset")


def _check_bounds(ds: "xr.Dataset", lat_name: str, lon_name: str, lat: float, lon: float) -> None:
    """Guard against xarray .sel(method='nearest') snapping points outside dataset extent."""
    lats = ds[lat_name].values
    lons = ds[lon_name].values
    lat_min, lat_max = float(lats.min()), float(lats.max())
    lon_min, lon_max = float(lons.min()), float(lons.max())

    if not (min(lat_min, lat_max) <= lat <= max(lat_min, lat_max)):
        raise ValueError(f"Latitude {lat} is outside dataset bounds [{lat_min}, {lat_max}]")
    if not (min(lon_min, lon_max) <= lon <= max(lon_min, lon_max)):
        raise ValueError(f"Longitude {lon} is outside dataset bounds [{lon_min}, {lon_max}]")


def nearest_grid_cell(ds: "xr.Dataset", lat: float, lon: float) -> Tuple[float, float]:
    """Return nearest grid cell center coordinates for a given point."""
    lat_name, lon_name = infer_lat_lon_names(ds)
    _check_bounds(ds, lat_name, lon_name, lat, lon)
    da = ds[infer_discharge_var(ds)]
    sel = da.sel({lat_name: lat, lon_name: lon}, method="nearest")
    lat0 = float(sel[lat_name].values)
    lon0 = float(sel[lon_name].values)
    return lat0, lon0


def extract_daily_discharge_for_points(
    ds: "xr.Dataset",
    points: pd.DataFrame,
    gauge_id_col: str = "virtual_gauge_id",
    lat_col: str = "lat",
    lon_col: str = "lon",
    discharge_var: Optional[str] = None,
) -> pd.DataFrame:
    """Vectorized extraction of discharge for multiple points.

    points must include columns: gauge_id_col, lat_col, lon_col.

    Returns a long-format DataFrame with columns [time, virtual_gauge_id, discharge].

    The vectorized indexing approach is the intended xarray pattern for nearest-neighbor
    extraction at multiple sites.
    """
    _require_xr()
    if points.empty:
        raise ValueError("points DataFrame is empty")

    lat_name, lon_name = infer_lat_lon_names(ds)
    time_name = infer_time_name(ds)

    if discharge_var is None:
        discharge_var = infer_discharge_var(ds)

    # Bounds check for all points (fail early)
    for _, r in points.iterrows():
        _check_bounds(ds, lat_name, lon_name, float(r[lat_col]), float(r[lon_col]))

    # Vectorized selection ("points" output dimension)
    target_lats = xr.DataArray(points[lat_col].astype(float).values, dims="points")
    target_lons = xr.DataArray(points[lon_col].astype(float).values, dims="points")

    da = ds[discharge_var].sel({lat_name: target_lats, lon_name: target_lons}, method="nearest")

    # Create dataframe long
    # Note: Some GRIB files may have invalid date metadata (year=0, month=0, day=0 from ECCODES)
    # We handle this by catching coercion errors and filtering invalid dates
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        idx_time = pd.to_datetime(da[time_name].values, errors='coerce')
        invalid_count = idx_time.isna().sum()
        total_count = len(idx_time)
        
        if invalid_count > 0:
            print(f"\n{'='*80}")
            print(f"⚠️  DATA LOSS WARNING: Invalid dates detected in GRIB file!")
            print(f"{'='*80}")
            print(f"Total time steps:       {total_count}")
            print(f"Invalid date values:    {invalid_count} ({100*invalid_count/total_count:.1f}%)")
            print(f"Valid date values:      {total_count - invalid_count} ({100*(total_count-invalid_count)/total_count:.1f}%)")
            print(f"Reason: ECCODES warning (year=0 month=0 day=0) - these rows will be DROPPED")
            print(f"{'='*80}\n")
            logger.warning(f"Found {invalid_count}/{total_count} invalid dates in GRIB (year=0 or similar, {100*invalid_count/total_count:.1f}%). These will be dropped.")
    except Exception as e:
        logger.warning(f"Error parsing dates: {e}. Attempting fallback parsing...")
        try:
            idx_time = pd.to_datetime(da[time_name].values, errors='coerce', format='mixed')
        except Exception as e2:
            logger.error(f"Fallback parsing also failed: {e2}")
            raise
    
    out = pd.DataFrame(
        da.values,
        index=idx_time,
        columns=points[gauge_id_col].tolist(),
    )
    out.index.name = "date"

    # Drop rows with invalid dates and report per-gauge impact
    valid_rows = out.index.notna()
    rows_dropped = (~valid_rows).sum()
    if rows_dropped > 0:
        print(f"\n{'='*80}")
        print(f"📊 DROPPED ROWS - Detailed Analysis by Gauge:")
        print(f"{'='*80}")
        print(f"Total rows before filtering: {len(out)}")
        print(f"Total rows with NaT dates:  {rows_dropped}")
        print(f"Total rows after filtering: {len(out) - rows_dropped}")
        
        # Per-gauge impact analysis
        out_with_invalid = out.copy()
        dropped_per_gauge = {}
        for col in out.columns:
            # Count NaT values in this gauge
            nat_count = out_with_invalid[out_with_invalid.index.isna()][col].notna().sum()
            if nat_count > 0:
                dropped_per_gauge[col] = nat_count
        
        if dropped_per_gauge:
            print(f"\nDropped records per gauge:")
            for gauge_id, count in sorted(dropped_per_gauge.items(), key=lambda x: -x[1]):
                print(f"  - {gauge_id}: {count} records")
        
        print(f"{'='*80}\n")
        logger.info(f"Dropping {rows_dropped} rows with NaT (invalid) dates across {len(dropped_per_gauge)} gauge(s)")
        out = out[valid_rows]

    long = out.reset_index().melt(id_vars=["date"], var_name=gauge_id_col, value_name="discharge_m3s")
    return long


def load_or_build_gauge_timeseries(
    grib_inventory: List[GribInventoryItem],
    points: pd.DataFrame,
    processed_timeseries_dir: Union[str, Path],
    cfgrib_index_dir: Union[str, Path],
    force: bool = False,
    discharge_var: Optional[str] = None,
    selected_years: Optional[List[int]] = None,
) -> Dict[str, pd.Series]:
    """Extract (and cache) daily discharge per unique virtual gauge.

    Writes one parquet per virtual gauge under processed_timeseries_dir.
    Returns dict of gauge_id -> pandas Series (DatetimeIndex).
    
    Uses lazy evaluation with dask to prevent memory exhaustion on large GRIBs.
    
    Args:
        grib_inventory: List of GribInventoryItem with year and path
        points: DataFrame with columns [virtual_gauge_id, lat, lon]
        processed_timeseries_dir: Output directory for parquet files
        cfgrib_index_dir: Directory for cfgrib index files
        force: If True, reprocess even if cached
        discharge_var: Discharge variable name (None=auto-detect)
        selected_years: If provided, only process these years (useful for debugging specific problematic years)
    
    Handles:
    - Invalid date metadata in GRIB files (year=0 from ECCODES warnings)
    - Memory exhaustion via incremental processing and explicit gc.collect()
    """
    import gc
    import logging
    
    logger = logging.getLogger(__name__)
    
    processed_timeseries_dir = Path(processed_timeseries_dir)
    processed_timeseries_dir.mkdir(parents=True, exist_ok=True)
    cfgrib_index_dir = Path(cfgrib_index_dir)
    cfgrib_index_dir.mkdir(parents=True, exist_ok=True)

    gauge_ids = points["virtual_gauge_id"].unique().tolist()

    # If already cached and not force, load directly.
    cached = {}
    missing = []
    for gid in gauge_ids:
        f = processed_timeseries_dir / f"{gid}.parquet"
        if f.exists() and not force:
            df = pd.read_parquet(f)
            s = pd.Series(df["discharge_m3s"].values, index=pd.to_datetime(df["date"]))
            s.name = "discharge_m3s"
            cached[gid] = s
        else:
            missing.append(gid)

    if not missing:
        return cached

    # Accumulate per gauge in memory (append by year), then write.
    series_acc: Dict[str, List[pd.DataFrame]] = {gid: [] for gid in missing}
    
    print(f"\n{'='*80}")
    print(f"📥 TIME SERIES EXTRACTION - Processing Summary")
    print(f"{'='*80}")
    print(f"Total gauges required:    {len(gauge_ids)}")
    print(f"Already cached:           {len(cached)}")
    print(f"Need to extract:          {len(missing)}")
    print(f"GRIBs to process:         {len(grib_inventory)}")
    print(f"{'='*80}\n")

    for idx, item in enumerate(grib_inventory):
        # Skip if year filtering is enabled and this year is not selected
        if selected_years is not None and item.year not in selected_years:
            logger.debug(f"Skipping {item.year} (not in selected_years={selected_years})")
            continue
            
        print(f"[{idx+1:2d}/{len(grib_inventory)}] Processing GRIB year {item.year}...")
        logger.info(f"Processing GRIB {idx+1}/{len(grib_inventory)}: {item.year} ({item.grib_path})")
        ds = None
        try:
            # Open dataset (cfgrib doesn't support chunks, but data is still read efficiently)
            ds = open_grib_dataset(item.grib_path, index_dir=cfgrib_index_dir)
            logger.debug(f"  Dataset opened. Dims: {dict(ds.dims)}")
            
            # Filter to missing gauges only
            subset_points = points[points["virtual_gauge_id"].isin(missing)].copy()
            if len(subset_points) == 0:
                logger.debug(f"  No missing gauges to extract; skipping")
                ds.close()
                gc.collect()
                continue
            
            long = extract_daily_discharge_for_points(ds, subset_points, discharge_var=discharge_var)
            extracted_count = len(long)
            gauge_count = long['virtual_gauge_id'].nunique()
            print(f"        ✓ Extracted {extracted_count} discharge values for {gauge_count} unique gauge(s)")
            logger.info(f"  Extracted {extracted_count} discharge values for {gauge_count} gauges")
            
            # Save each gauge's year partition incrementally
            for gid, sub in long.groupby("virtual_gauge_id"):
                series_acc[gid].append(sub[["date", "discharge_m3s"]])
                
        except Exception as e:
            print(f"        ✗ ERROR: {str(e)[:100]}")
            logger.error(f"  Error processing {item.grib_path}: {e}", exc_info=True)
            raise
        finally:
            # Close dataset to free resources
            if ds is not None:
                try:
                    ds.close()
                except Exception as e:
                    logger.warning(f"  Error closing dataset: {e}")
            # Force garbage collection to prevent memory buildup
            gc.collect()

    # Write each gauge to parquet
    print(f"\n{'='*80}")
    print(f"💾 FINALIZING - Writing time series to disk")
    print(f"{'='*80}\n")
    
    final_records_summary = {}
    for gid, parts in series_acc.items():
        if not parts:
            raise RuntimeError(f"No discharge values extracted for gauge {gid}")
        
        logger.debug(f"Finalizing {gid}: {len(parts)} year(s)")
        df = pd.concat(parts, ignore_index=True)
        
        initial_count = len(df)
        df = df.dropna(subset=["discharge_m3s"])
        dropped_na = initial_count - len(df)
        
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")
        
        out_path = processed_timeseries_dir / f"{gid}.parquet"
        df.to_parquet(out_path, index=False, compression="snappy")
        
        final_count = len(df)
        final_records_summary[gid] = {
            'initial': initial_count,
            'dropped_na': dropped_na,
            'final': final_count
        }
        
        print(f"  {gid}")
        print(f"    - Initial records:  {initial_count}")
        if dropped_na > 0:
            print(f"    - Dropped (NaN):    {dropped_na} ({100*dropped_na/initial_count:.1f}%)")
        print(f"    - Final records:    {final_count}")
        print(f"    - Date range:       {df['date'].min().date()} to {df['date'].max().date()}")
        print(f"    - File:             {out_path.name}\n")
        
        logger.info(f"  Wrote {final_count} records to {out_path} (dropped {dropped_na} NaN values)")
        
        s = pd.Series(df["discharge_m3s"].values, index=df["date"])
        s.name = "discharge_m3s"
        cached[gid] = s
    
    print(f"{'='*80}")
    print(f"✅ EXTRACTION COMPLETE")
    print(f"{'='*80}")
    print(f"Total gauges processed:   {len(final_records_summary)}")
    print(f"Total records written:    {sum(r['final'] for r in final_records_summary.values())}")
    print(f"Total records dropped:    {sum(r['dropped_na'] for r in final_records_summary.values())}")
    print(f"{'='*80}\n")

    return cached
