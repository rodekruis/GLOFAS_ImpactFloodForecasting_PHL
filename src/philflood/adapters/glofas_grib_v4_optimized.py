"""Memory-optimized GRIB extraction with geographic chunking and gauge batching."""

import gc
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

try:
    import xarray as xr
except Exception:
    xr = None

from philflood.utils.memory_utils import MemoryMonitor, GribGeographicChunker

logger = logging.getLogger(__name__)


def _require_xr():
    if xr is None:
        raise ImportError("xarray is required to read GRIB files")


def extract_daily_discharge_with_memory_safety(
    ds: "xr.Dataset",
    points: pd.DataFrame,
    gauge_id_col: str = "virtual_gauge_id",
    lat_col: str = "lat",
    lon_col: str = "lon",
    discharge_var: Optional[str] = None,
    gauge_batch_size: int = 2,
    use_geographic_chunking: bool = True,
    memory_monitor: Optional[MemoryMonitor] = None,
) -> pd.DataFrame:
    """
    Extract discharge with memory optimization: geographic chunking + gauge batching.
    
    This is a drop-in replacement for extract_daily_discharge_for_points() that:
    1. Clips GRIB to bounding box of gauge points (reduce grid from 100k+ cells to few hundred)
    2. Batches gauge extractions (process 2-4 gauges at a time instead of all)
    3. Monitors memory and warns if approaching limits
    
    Parameters
    ----------
    ds : xr.Dataset
        GRIB dataset opened with xarray+cfgrib
    points : pd.DataFrame
        Points with gauge_id_col, lat_col, lon_col
    gauge_id_col : str
        Name of gauge ID column
    lat_col : str
        Name of latitude column
    lon_col : str
        Name of longitude column
    discharge_var : str, optional
        Discharge variable name (auto-detected if None)
    gauge_batch_size : int
        Number of gauges to extract simultaneously (default 2, reduces memory)
    use_geographic_chunking : bool
        If True, clip GRIB to bounding box around gauges (default True)
    memory_monitor : MemoryMonitor, optional
        Memory monitor instance (created if None)
    
    Returns
    -------
    pd.DataFrame
        Long-format extraction with columns [date, virtual_gauge_id, discharge_m3s]
    """
    _require_xr()
    
    from philflood.adapters.glofas_grib_v4 import (
        infer_lat_lon_names,
        infer_time_name,
        infer_discharge_var,
        _check_bounds,
    )
    
    if memory_monitor is None:
        memory_monitor = MemoryMonitor()
    
    # Check memory before starting
    can_continue, msg = memory_monitor.check_memory("Extract start")
    print(msg)
    if not can_continue:
        raise RuntimeError(f"Insufficient memory: {msg}")
    
    logger.info(f"Starting memory-safe extraction with gauge_batch_size={gauge_batch_size}")
    
    if points.empty:
        raise ValueError("points DataFrame is empty")
    
    lat_name, lon_name = infer_lat_lon_names(ds)
    time_name = infer_time_name(ds)
    
    if discharge_var is None:
        discharge_var = infer_discharge_var(ds)
    
    # Step 1: Geographic chunking - clip GRIB to gauge region
    if use_geographic_chunking:
        logger.info("Applying geographic chunking to reduce grid size...")
        bbox = GribGeographicChunker.compute_bbox(points, lat_col, lon_col, padding_degrees=0.5)
        min_lat, max_lat, min_lon, max_lon = bbox
        logger.debug(f"  Bounding box: lat [{min_lat:.2f}, {max_lat:.2f}], lon [{min_lon:.2f}, {max_lon:.2f}]")
        
        try:
            # Clip the dataset to the bounding box
            clipped_ds = GribGeographicChunker.clip_dataset_to_bbox(ds, bbox, lat_name, lon_name)
            original_size = ds[discharge_var].size
            clipped_size = clipped_ds[discharge_var].size
            reduction = 100 * (1 - clipped_size / original_size)
            logger.info(f"  Grid reduced: {original_size} → {clipped_size} cells ({reduction:.1f}% reduction)")
            print(f"  ✓ Grid reduced by {reduction:.1f}% (from {original_size} to {clipped_size} cells)")
            
            ds_to_use = clipped_ds
        except Exception as e:
            logger.warning(f"Geographic chunking failed: {e}. Proceeding with full grid.")
            print(f"  ⚠️  Geographic chunking failed: {e}. Using full grid.")
            ds_to_use = ds
    else:
        ds_to_use = ds
    
    # Step 2: Bounds check all points on the (potentially clipped) dataset
    logger.debug("Validating point locations...")
    for _, r in points.iterrows():
        try:
            _check_bounds(ds_to_use, lat_name, lon_name, float(r[lat_col]), float(r[lon_col]))
        except ValueError as e:
            logger.error(f"Point out of bounds: {r[gauge_id_col]} at ({r[lat_col]}, {r[lon_col]}): {e}")
            raise
    
    # Step 3: Batch extraction by gauge
    all_long_dfs = []
    gauge_ids = points[gauge_id_col].unique().tolist()
    n_batches = (len(gauge_ids) + gauge_batch_size - 1) // gauge_batch_size
    
    logger.info(f"Extracting {len(gauge_ids)} gauges in {n_batches} batches (size={gauge_batch_size})")
    print(f"  Processing {len(gauge_ids)} gauges in {n_batches} batch(es)...")
    
    for batch_idx in range(n_batches):
        start_i = batch_idx * gauge_batch_size
        end_i = min((batch_idx + 1) * gauge_batch_size, len(gauge_ids))
        batch_gauges = gauge_ids[start_i:end_i]
        
        logger.debug(f"  Batch {batch_idx + 1}/{n_batches}: {batch_gauges}")
        
        # Extract subset for this batch
        batch_points = points[points[gauge_id_col].isin(batch_gauges)].copy()
        
        # Vectorized extraction for batch
        target_lats = xr.DataArray(batch_points[lat_col].astype(float).values, dims="points")
        target_lons = xr.DataArray(batch_points[lon_col].astype(float).values, dims="points")
        
        da = ds_to_use[discharge_var].sel(
            {lat_name: target_lats, lon_name: target_lons}, 
            method="nearest"
        )
        
        # Parse time (same logic as original extract_daily_discharge_for_points)
        try:
            idx_time = pd.to_datetime(da[time_name].values, errors='coerce')
            invalid_count = idx_time.isna().sum()
            total_count = len(idx_time)
            
            if invalid_count > 0:
                print(f"    ⚠️  {invalid_count}/{total_count} invalid dates in this GRIB")
                logger.warning(f"Found {invalid_count}/{total_count} invalid dates ({100*invalid_count/total_count:.1f}%)")
        except Exception as e:
            logger.warning(f"Error parsing dates: {e}. Using fallback...")
            try:
                idx_time = pd.to_datetime(da[time_name].values, errors='coerce', format='mixed')
            except Exception as e2:
                logger.error(f"Fallback parsing failed: {e2}")
                raise
        
        # Build DataFrame for batch
        out = pd.DataFrame(
            da.values,
            index=idx_time,
            columns=batch_points[gauge_id_col].tolist(),
        )
        out.index.name = "date"
        
        # Drop NaT rows
        valid_rows = out.index.notna()
        if (~valid_rows).sum() > 0:
            logger.debug(f"    Dropping {(~valid_rows).sum()} rows with NaT dates")
            out = out[valid_rows]
        
        # Convert to long format
        batch_long = out.reset_index().melt(
            id_vars=["date"], 
            var_name=gauge_id_col, 
            value_name="discharge_m3s"
        )
        
        all_long_dfs.append(batch_long)
        
        # Memory check after batch
        can_continue, msg = memory_monitor.check_memory(f"After batch {batch_idx + 1}/{n_batches}")
        if "approaching" in msg or "WARNING" in msg:
            logger.warning(msg)
        
        # Free batch data
        del da, out, batch_long
        gc.collect()
    
    # Combine all batches
    logger.info("Combining batches...")
    result = pd.concat(all_long_dfs, ignore_index=True)
    
    # Final memory check
    can_continue, msg = memory_monitor.check_memory("Extract complete")
    print(msg)
    
    logger.info(f"Extraction complete: {len(result)} total values for {len(gauge_ids)} gauges")
    
    return result
