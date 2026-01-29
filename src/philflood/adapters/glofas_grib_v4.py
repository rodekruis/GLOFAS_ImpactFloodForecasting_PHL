from __future__ import annotations

import hashlib
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import pandas as pd

try:
    import xarray as xr
except Exception:  # pragma: no cover
    xr = None

# Suppress ECCODES warnings about invalid dates (year=0 month=0 day=0)
# These are handled gracefully in extract_daily_discharge_for_points via pd.to_datetime errors='coerce'
warnings.filterwarnings("ignore", category=UserWarning, message=".*g2date.*unpack.*")
warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*g2date.*unpack.*")

# Default return periods for flood forecasting (in years)
DEFAULT_RETURN_PERIODS = [1, 2, 5, 10, 20, 50, 100, 200, 500]


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


def cells_within_polygon(
    ds: "xr.Dataset",
    polygon,
    discharge_var: Optional[str] = None,
) -> pd.DataFrame:
    """Extract all GloFAS grid cell centers that intersect a polygon.
    
    Args:
        ds: xarray Dataset (opened GRIB)
        polygon: shapely.geometry.Polygon (in EPSG:4326)
        discharge_var: Variable name in dataset (None = auto-detect)
    
    Returns:
        DataFrame with columns: [cell_lat, cell_lon, cell_idx, cell_idy]
        where idx/idy are the array indices in the GRIB grid.
    """
    _require_xr()
    import logging
    logger = logging.getLogger(__name__)
    
    lat_name, lon_name = infer_lat_lon_names(ds)
    lats = ds[lat_name].values
    lons = ds[lon_name].values
    
    # Build a list of cell centers that intersect the polygon
    cells = []
    for i, lat in enumerate(lats):
        for j, lon in enumerate(lons):
            from shapely.geometry import Point
            pt = Point(lon, lat)
            if polygon.intersects(pt):
                cells.append({
                    'cell_lat': float(lat),
                    'cell_lon': float(lon),
                    'cell_idx': int(i),
                    'cell_idy': int(j),
                })
    
    if not cells:
        logger.warning(f"No grid cells found within polygon bounds")
        return pd.DataFrame(columns=['cell_lat', 'cell_lon', 'cell_idx', 'cell_idy'])
    
    return pd.DataFrame(cells)


def extract_daily_discharge_for_cells(
    ds: "xr.Dataset",
    cells: pd.DataFrame,
    basin_id: Union[int, str],
    lat_col: str = "cell_lat",
    lon_col: str = "cell_lon",
    discharge_var: Optional[str] = None,
) -> pd.DataFrame:
    """Extract discharge for all grid cells in a basin, returning per-cell time series.
    
    Extracts discharge for all cells and returns discharge values for all cells at each timestep
    without aggregation. This preserves the spatial information by storing lat/lon for each
    extraction.
    
    Args:
        ds: xarray Dataset (opened GRIB)
        cells: DataFrame with columns [cell_lat, cell_lon, cell_idx, cell_idy]
        basin_id: Basin identifier (for synthetic gauge_id construction)
        lat_col: Column name for latitude
        lon_col: Column name for longitude
        discharge_var: Variable name in dataset (None = auto-detect)
    
    Returns:
        Long-format DataFrame with columns [date, basin_id, discharge_m3s, cell_lat, cell_lon]
        One row per cell per timestep, preserving spatial coordinates.
    """
    _require_xr()
    import logging
    logger = logging.getLogger(__name__)
    
    if cells.empty:
        raise ValueError("cells DataFrame is empty")
    
    lat_name, lon_name = infer_lat_lon_names(ds)
    time_name = infer_time_name(ds)
    
    if discharge_var is None:
        discharge_var = infer_discharge_var(ds)
    
    # Extract discharge at each cell
    all_rows = []
    for _, cell in cells.iterrows():
        lat = float(cell[lat_col])
        lon = float(cell[lon_col])
        
        # Extract single cell
        da = ds[discharge_var].sel({lat_name: lat, lon_name: lon}, method="nearest")
        
        # Build time series for this cell
        try:
            idx_time = pd.to_datetime(da[time_name].values, errors='coerce')
        except Exception:
            try:
                idx_time = pd.to_datetime(da[time_name].values, errors='coerce', format='mixed')
            except Exception as e:
                logger.error(f"Failed to parse dates for cell ({lat}, {lon}): {e}")
                raise
        
        discharge_vals = da.values
        
        # Build output for this cell (one row per timestep)
        cell_data = pd.DataFrame({
            'date': idx_time,
            'basin_id': str(basin_id),
            'discharge_m3s': discharge_vals,
            'cell_lat': lat,
            'cell_lon': lon,
        })
        all_rows.append(cell_data)
    
    # Concatenate all cells
    out = pd.concat(all_rows, ignore_index=True)
    out = out.sort_values(['date', 'cell_lat', 'cell_lon']).reset_index(drop=True)
    
    return out


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
    use_memory_optimization: bool = True,
    gauge_batch_size: int = 2,
    use_streaming: bool = False,
) -> Dict[str, pd.Series]:
    """Load or extract daily discharge time series for virtual gauges.
    
    Parameters
    ----------
    grib_inventory : List[GribInventoryItem]
        List of GRIB files with year information
    points : pd.DataFrame
        Points to extract (must have 'virtual_gauge_id', 'lat', 'lon')
    processed_timeseries_dir : Union[str, Path]
        Where to cache extracted time series (parquet format)
    cfgrib_index_dir : Union[str, Path]
        Where cfgrib stores its index files
    force : bool, optional
        If True, skip cached files and re-extract everything
    discharge_var : Optional[str]
        Discharge variable name in GRIB (None = auto-detect)
    selected_years : Optional[List[int]]
        If provided, only process these years (useful for testing)
    use_streaming : bool, optional
        If True (recommended), use streaming extraction that processes years
        sequentially and writes immediately. This eliminates memory accumulation
        and scales to country-level deployments. Default False for backward compatibility.
    use_memory_optimization : bool, optional
        If True (default), use memory-optimized extraction with geographic chunking
        and gauge batching. Reduces memory usage by 80-90%.
    gauge_batch_size : int, optional
        Number of gauges to extract per batch when use_memory_optimization=True.
        Smaller values = less memory but slower. Default 2.
    
    Returns
    -------
    Dict[str, pd.Series]
        Dictionary mapping gauge_id → daily discharge Series
    
    Notes
    -----
    **Memory Optimization (NEW):**
    - Geographic chunking: clips GRIB to bounding box of gauge points
    - Gauge batching: extracts gauges in small batches (2-4 at a time)
    - Memory monitoring: logs warnings at 70% and stops at 85% system memory
    
    **Cache Validation:**
    - Cached files are checked for completeness
    - If a cached file doesn't cover the full GRIB date range, it is re-extracted
    - This prevents silently using incomplete time series from previous partial runs
    
    **Example:**
    Previous run with SELECTED_YEARS=[2010, 2011, ...] created cached files for 2010-2025.
    Next run with SELECTED_YEARS=None (all years, 1979-2025) will detect the gap and
    automatically re-extract to fill years 1979-2009.
    """
    import gc
    import logging
    
    logger = logging.getLogger(__name__)
    
    # ✅ NEW: Route to streaming extraction if enabled
    if use_streaming:
        logger.info("Using streaming extraction (year-by-year with immediate writes)")
        from philflood.adapters.glofas_grib_streaming import load_or_build_gauge_timeseries_streaming
        return load_or_build_gauge_timeseries_streaming(
            grib_inventory=grib_inventory,
            points=points,
            processed_timeseries_dir=processed_timeseries_dir,
            cfgrib_index_dir=cfgrib_index_dir,
            force=force,
            discharge_var=discharge_var,
            selected_years=selected_years,
        )
    
    # Original implementation (with memory optimization)
    from philflood.utils.memory_utils import MemoryMonitor
    
    processed_timeseries_dir = Path(processed_timeseries_dir)
    processed_timeseries_dir.mkdir(parents=True, exist_ok=True)
    cfgrib_index_dir = Path(cfgrib_index_dir)
    cfgrib_index_dir.mkdir(parents=True, exist_ok=True)

    gauge_ids = points["virtual_gauge_id"].unique().tolist()

    # If already cached and not force, load directly.
    cached = {}
    missing = []
    # Determine expected date range from GRIB inventory
    grib_years = sorted(set(item.year for item in grib_inventory))
    if grib_years:
        expected_start = pd.Timestamp(year=grib_years[0], month=1, day=1)
        expected_end = pd.Timestamp(year=grib_years[-1], month=12, day=31)
    else:
        expected_start = None
        expected_end = None

    for gid in gauge_ids:
        f = processed_timeseries_dir / f"{gid}.parquet"
        is_valid_cache = False
        
        if f.exists() and not force:
            try:
                df = pd.read_parquet(f)
                s = pd.Series(df["discharge_m3s"].values, index=pd.to_datetime(df["date"]))
                s.name = "discharge_m3s"
                
                # ✅ NEW: Validate date coverage
                if expected_start is not None and expected_end is not None:
                    cache_start = s.index.min()
                    cache_end = s.index.max()
                    
                    # Check if cached file covers the full GRIB range
                    coverage_ok = (cache_start <= expected_start) and (cache_end >= expected_end)
                    
                    if not coverage_ok:
                        logger.warning(
                            f"  Cached file {gid}: incomplete coverage\n"
                            f"    Expected: {expected_start.date()} to {expected_end.date()}\n"
                            f"    Got:      {cache_start.date()} to {cache_end.date()}\n"
                            f"    → Will re-extract to fill gaps"
                        )
                        is_valid_cache = False
                    else:
                        logger.info(f"  {gid}: cache valid (covers {cache_start.date()} to {cache_end.date()})")
                        is_valid_cache = True
                else:
                    is_valid_cache = True
                
                if is_valid_cache:
                    cached[gid] = s
                else:
                    missing.append(gid)
                    
            except Exception as e:
                logger.warning(f"  Could not load cached file for {gid}: {e}. Will re-extract.")
                missing.append(gid)
        else:
            missing.append(gid)

    if not missing:
        return cached

    # ===== NEW: Incremental write strategy =====
    # Use temp directory to store partial extractions    
    # Create a unique temp directory per run to avoid mixing partial results from crashed runs
    temp_dir = Path(tempfile.mkdtemp(dir=processed_timeseries_dir, prefix="_temp_extraction_"))
    
    # Track which gauges have partial data in temp files
    partial_files = {gid: temp_dir / f"{gid}_partial.parquet" for gid in missing}
    
    print(f"\n{'='*80}")
    print(f"📥 TIME SERIES EXTRACTION - Processing Summary")
    print(f"{'='*80}")
    print(f"Total gauges required:    {len(gauge_ids)}")
    print(f"Already cached:           {len(cached)}")
    print(f"Need to extract:          {len(missing)}")
    print(f"GRIBs to process:         {len(grib_inventory)}")
    print(f"Temp directory:           {temp_dir}")
    if use_memory_optimization:
        print(f"Memory optimization:      ENABLED (batch size={gauge_batch_size})")
    else:
        print(f"Memory optimization:      DISABLED (standard extraction)")
    print(f"{'='*80}\n")

    # Initialize memory monitor
    memory_monitor = MemoryMonitor(warning_threshold_percent=70.0, error_threshold_percent=85.0)

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
            
            # Use optimized extraction if enabled
            if use_memory_optimization:
                from philflood.adapters.glofas_grib_v4_optimized import extract_daily_discharge_with_memory_safety
                long = extract_daily_discharge_with_memory_safety(
                    ds, 
                    subset_points, 
                    discharge_var=discharge_var,
                    gauge_batch_size=gauge_batch_size,
                    memory_monitor=memory_monitor,
                )
            else:
                long = extract_daily_discharge_for_points(ds, subset_points, discharge_var=discharge_var)
            
            extracted_count = len(long)
            gauge_count = long['virtual_gauge_id'].nunique()
            print(f"        ✓ Extracted {extracted_count} discharge values for {gauge_count} unique gauge(s)")
            logger.info(f"  Extracted {extracted_count} discharge values for {gauge_count} gauges")
            
            # ===== NEW: Write incrementally to temp files =====
            for gid, sub in long.groupby("virtual_gauge_id"):
                year_data = sub[["date", "discharge_m3s"]].copy()
                temp_file = partial_files[gid]
                
                if temp_file.exists():
                    # Append to existing partial file
                    existing = pd.read_parquet(temp_file)
                    combined = pd.concat([existing, year_data], ignore_index=True)
                    combined.to_parquet(temp_file, index=False, compression="snappy")
                    logger.debug(f"    {gid}: appended {len(year_data)} records (total: {len(combined)})")
                else:
                    # Create new partial file
                    year_data.to_parquet(temp_file, index=False, compression="snappy")
                    logger.debug(f"    {gid}: created partial file with {len(year_data)} records")
            
            # Clear the long dataframe from memory immediately
            del long
                
        except Exception as e:
            print(f"        ✗ ERROR: {str(e)[:100]}")
            logger.error(f"  Error processing {item.grib_path}: {e}", exc_info=True)
            # Clean up temp files on error
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
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

    # ===== NEW: Finalize from temp files =====
    print(f"\n{'='*80}")
    print(f"💾 FINALIZING - Writing time series to disk")
    print(f"{'='*80}\n")
    
    final_records_summary = {}
    for gid in missing:
        temp_file = partial_files[gid]
        
        if not temp_file.exists():
            raise RuntimeError(f"No discharge values extracted for gauge {gid}")
        
        logger.debug(f"Finalizing {gid} from temp file")
        df = pd.read_parquet(temp_file)
        
        initial_count = len(df)
        df = df.dropna(subset=["discharge_m3s"])
        dropped_na = initial_count - len(df)
        
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")
        df = df.drop_duplicates(subset=["date"], keep="last")  # Remove any duplicate dates
        
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
        
        # Clean up temp file
        temp_file.unlink()
    
    # Remove temp directory
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)
    
    print(f"{'='*80}")
    print(f"✅ EXTRACTION COMPLETE")
    print(f"{'='*80}")
    print(f"Total gauges processed:   {len(final_records_summary)}")
    print(f"Total records written:    {sum(r['final'] for r in final_records_summary.values())}")
    print(f"Total records dropped:    {sum(r['dropped_na'] for r in final_records_summary.values())}")
    print(f"{'='*80}\n")

    return cached

def write_return_period_netcdf(
    output_path: Union[str, Path],
    gauges_data: Dict[str, dict],
    global_attrs: Optional[dict] = None,
    return_levels_dir: Optional[Union[str, Path]] = None,
) -> None:
    """Write return period and discharge data to a NetCDF file.
    
    Parameters
    ----------
    output_path : Union[str, Path]
        Path where the NetCDF file will be written (e.g., 'return-period.nc')
    gauges_data : Dict[str, dict]
        Dictionary mapping gauge_id → dict with keys:
        - 'lat': float (latitude)
        - 'lon': float (longitude)
        - 'discharge_m3s': float (representative discharge - used if no return_levels_dir)
        - 'return_period': float (years)
        - Additional metadata (threshold_m3s, lambda, xi, sigma, etc.)
    global_attrs : Optional[dict]
        Global attributes for the NetCDF file (e.g., title, source, etc.)
    return_levels_dir : Optional[Union[str, Path]]
        Path to directory containing return level parquet files (e.g., 'synthetic_catalog/return_levels')
        If provided, actual return period discharge values will be loaded from these files.
        If not provided, the same discharge value will be used for all return periods.
    
    Notes
    -----
    Creates a NetCDF file with:
    - Dimensions: gauge (number of gauges), return_period (number of return periods)
    - Coordinates: gauge (string IDs), return_period (years)
    - Data variables: 
        - latitude (gauge) → latitude
        - longitude (gauge) → longitude
        - discharge_m3s (gauge, return_period) → discharge at each return period
        - threshold_m3s (gauge) → POT threshold
        - lambda_events_per_year (gauge) → event rate parameter
    - Attributes: metadata for each variable and global attributes
    """
    _require_xr()
    
    if not gauges_data:
        raise ValueError("gauges_data is empty")
    
    import logging
    import pandas as pd
    logger = logging.getLogger(__name__)
    
    # Extract gauge metadata
    gauge_ids = list(gauges_data.keys())
    lats = [gauges_data[gid].get('lat', None) for gid in gauge_ids]
    lons = [gauges_data[gid].get('lon', None) for gid in gauge_ids]
    thresholds = [gauges_data[gid].get('threshold_m3s', None) for gid in gauge_ids]
    lambdas = [gauges_data[gid].get('lambda_events_per_year', None) for gid in gauge_ids]
    
    # Try to load actual return period discharge values from parquet files
    discharge_2d = []
    return_period_values = None
    
    if return_levels_dir is not None:
        return_levels_dir = Path(return_levels_dir)
        if return_levels_dir.exists():
            logger.info(f"Loading return level parquet files from {return_levels_dir}")
            
            # Load return levels for each gauge
            for gid in gauge_ids:
                rl_file = return_levels_dir / f"{gid}__return_levels.parquet"
                if rl_file.exists():
                    rl_df = pd.read_parquet(rl_file)
                    
                    # Extract return periods and discharges
                    if return_period_values is None:
                        return_period_values = sorted(rl_df['return_period_years'].unique())
                    
                    # Map discharge values to return periods
                    discharge_by_rp = rl_df.set_index('return_period_years')['return_level_m3s'].to_dict()
                    discharge_for_rps = [discharge_by_rp.get(rp, None) for rp in return_period_values]
                    discharge_2d.append(discharge_for_rps)
                else:
                    logger.warning(f"Return level file not found: {rl_file.name}, using placeholder")
                    # Fallback: repeat the discharge value
                    if return_period_values is None:
                        return_period_values = DEFAULT_RETURN_PERIODS
                    discharge_for_rps = [gauges_data[gid].get('discharge_m3s', None) for _ in return_period_values]
                    discharge_2d.append(discharge_for_rps)
    
    # If no parquet files, use default return periods and repeat the discharge value
    if return_period_values is None:
        return_period_values = DEFAULT_RETURN_PERIODS
        discharge_2d = []
        for gid in gauge_ids:
            discharge_for_rps = [gauges_data[gid].get('discharge_m3s', None) for _ in return_period_values]
            discharge_2d.append(discharge_for_rps)
    
    # Create xarray Dataset with return_period as a dimension
    # Validate that discharge_2d matches the expected shape: (n_gauge, n_return_period)
    expected_gauges = len(gauge_ids)
    expected_rps = len(return_period_values) if return_period_values is not None else 0
    actual_gauges = len(discharge_2d)
    if actual_gauges != expected_gauges or any(len(row) != expected_rps for row in discharge_2d):
        raise ValueError(
            f"Mismatch between discharge_2d shape and coordinates: "
            f"got {actual_gauges} gauges with return period lengths "
            f"{[len(row) for row in discharge_2d]}, expected "
            f"{expected_gauges} gauges and {expected_rps} return periods."
        )
    ds = xr.Dataset(
        data_vars={
            'latitude': (('gauge',), lats, {'units': 'degrees_north', 'long_name': 'Latitude'}),
            'longitude': (('gauge',), lons, {'units': 'degrees_east', 'long_name': 'Longitude'}),
            'discharge_m3s': (('gauge', 'return_period'), discharge_2d, {'units': 'm3 s-1', 'long_name': 'Discharge at Return Period'}),
            'threshold_m3s': (('gauge',), thresholds, {'units': 'm3 s-1', 'long_name': 'POT Threshold'}),
            'lambda_events_per_year': (('gauge',), lambdas, {'units': '1', 'long_name': 'Event Rate'}),
        },
        coords={
            'gauge': gauge_ids,
            'return_period': return_period_values,
        },
    )
    
    # Add global attributes
    if global_attrs:
        ds.attrs.update(global_attrs)
    else:
        ds.attrs['title'] = 'GloFAS Return Period Analysis'
        ds.attrs['source'] = 'GloFAS v4 discharge data'
        ds.attrs['institution'] = 'Disaster Management Centre'
    
    # Write to NetCDF
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Try to write with compression; fall back to no compression if backend doesn't support it
    try:
        ds.to_netcdf(output_path, engine='netcdf4', encoding={var: {'zlib': True, 'complevel': 4} for var in ds.data_vars})
    except (ValueError, ImportError):
        # Fall back to scipy backend without compression
        ds.to_netcdf(output_path)
    
    logger.info(f"Wrote return period NetCDF to {output_path}")
    
    # ⭐ CRITICAL: Close the dataset to release file handles
    try:
        ds.close()
    except Exception as e:
        logger.warning(f"Error closing dataset: {e}")
    
    return