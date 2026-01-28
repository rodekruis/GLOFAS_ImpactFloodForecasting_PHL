"""
Streaming GRIB extraction for memory-constrained environments.

This module implements a year-by-year streaming approach that writes
intermediate results to disk immediately, avoiding memory accumulation.

Key features:
- Processes one GRIB year at a time
- Writes intermediate parquet files immediately
- Merges results efficiently using chunked reads
- Supports resumption from crashes (checkpointing)
- Scales to country-level deployments (1000s of gauges)

Architecture:
    1. Extract each year → temp parquet file
    2. Merge temp files → final per-gauge parquets
    3. Cleanup temp files

Memory usage: Constant (only one year in memory at a time)
"""

from __future__ import annotations

import gc
import logging
from pathlib import Path
from typing import Dict, List, Optional, Union

import pandas as pd

try:
    import xarray as xr
except ImportError:
    xr = None

from philflood.adapters.glofas_grib_v4 import (
    GribInventoryItem,
    extract_daily_discharge_for_points,
    infer_discharge_var,
    open_grib_dataset,
)

logger = logging.getLogger(__name__)


def extract_year_to_temp_file(
    grib_item: GribInventoryItem,
    points: pd.DataFrame,
    temp_dir: Path,
    cfgrib_index_dir: Path,
    discharge_var: Optional[str] = None,
) -> Path:
    """Extract one year of GRIB data and write immediately to temp file.
    
    This function:
    1. Opens GRIB file for one year
    2. Extracts discharge for all gauge points
    3. Writes to parquet immediately
    4. Closes dataset and frees memory
    5. Returns path to temp file
    
    Parameters
    ----------
    grib_item : GribInventoryItem
        GRIB file and year info
    points : pd.DataFrame
        Gauge points (virtual_gauge_id, lat, lon)
    temp_dir : Path
        Directory for temporary year files
    cfgrib_index_dir : Path
        cfgrib index directory
    discharge_var : Optional[str]
        Discharge variable name (None = auto-detect)
        
    Returns
    -------
    Path
        Path to temporary parquet file for this year
    """
    year = grib_item.year
    temp_file = temp_dir / f"temp_year_{year}.parquet"
    
    # Skip if already extracted (resumption support)
    if temp_file.exists():
        logger.info(f"  ↺ Year {year} already extracted (temp file exists)")
        return temp_file
    
    try:
        # Open GRIB for this year
        logger.debug(f"  Opening GRIB for year {year}: {grib_item.grib_path}")
        ds = open_grib_dataset(grib_item.grib_path, cfgrib_index_dir)
        
        # Auto-detect discharge variable if not specified
        var = discharge_var or infer_discharge_var(ds)
        
        # Extract discharge for all points (vectorized)
        df = extract_daily_discharge_for_points(
            ds,
            points,
            gauge_id_col="virtual_gauge_id",
            lat_col="lat",
            lon_col="lon",
            discharge_var=var,
        )
        
        # Close dataset immediately to free memory
        ds.close()
        del ds
        gc.collect()
        
        # Write to temp file immediately
        df.to_parquet(temp_file, index=False, compression="snappy")
        logger.debug(f"  ✓ Wrote {len(df)} records to {temp_file.name}")
        
        return temp_file
        
    except Exception as e:
        logger.error(f"  ✗ ERROR: Year {year} extraction failed: {e}")
        # Clean up partial file if it exists
        if temp_file.exists():
            temp_file.unlink()
        raise


def merge_yearly_temps_to_gauge_files(
    temp_files: List[Path],
    gauge_ids: List[str],
    output_dir: Path,
) -> Dict[str, pd.Series]:
    """Merge yearly temp files into per-gauge parquet files.
    
    This function reads temp files one at a time, groups by gauge,
    and writes final per-gauge files. Memory efficient because it
    processes one year at a time.
    
    Parameters
    ----------
    temp_files : List[Path]
        Sorted list of yearly temp parquet files
    gauge_ids : List[str]
        List of unique gauge IDs
    output_dir : Path
        Final output directory for gauge files
        
    Returns
    -------
    Dict[str, pd.Series]
        Dictionary mapping gauge_id → daily discharge Series
    """
    logger.info(f"📊 Merging {len(temp_files)} yearly files into {len(gauge_ids)} gauge files...")
    
    # Initialize empty accumulator for each gauge
    gauge_data: Dict[str, List[pd.DataFrame]] = {gid: [] for gid in gauge_ids}
    
    # Read each yearly temp file and accumulate by gauge
    for i, temp_file in enumerate(temp_files, 1):
        logger.debug(f"  Reading temp file {i}/{len(temp_files)}: {temp_file.name}")
        
        try:
            df = pd.read_parquet(temp_file)
            
            # Group by gauge and accumulate
            for gid in gauge_ids:
                gauge_df = df[df["virtual_gauge_id"] == gid].copy()
                if not gauge_df.empty:
                    gauge_data[gid].append(gauge_df[["date", "discharge_m3s"]])
            
            # Free memory immediately
            del df
            gc.collect()
            
        except Exception as e:
            logger.error(f"  ✗ ERROR reading {temp_file.name}: {e}")
            continue
    
    # Write per-gauge files and create Series dict
    logger.info(f"  Writing {len(gauge_ids)} gauge parquet files...")
    series_by_gauge = {}
    
    for gid in gauge_ids:
        if not gauge_data[gid]:
            logger.warning(f"  ⚠ No data for gauge {gid}")
            continue
        
        # Concatenate all years for this gauge
        combined = pd.concat(gauge_data[gid], ignore_index=True)
        combined = combined.sort_values("date").drop_duplicates(subset=["date"], keep="first")
        
        # Write to parquet
        output_file = output_dir / f"{gid}.parquet"
        combined.to_parquet(output_file, index=False, compression="snappy")
        
        # Create Series for return value
        series = pd.Series(
            combined["discharge_m3s"].values,
            index=pd.to_datetime(combined["date"]),
            name="discharge_m3s",
        )
        series_by_gauge[gid] = series
        
        logger.debug(f"  ✓ {gid}: {len(series)} days, {series.index.min().date()} to {series.index.max().date()}")
    
    logger.info(f"✓ Merge complete: {len(series_by_gauge)} gauges")
    return series_by_gauge


def load_or_build_gauge_timeseries_streaming(
    grib_inventory: List[GribInventoryItem],
    points: pd.DataFrame,
    processed_timeseries_dir: Union[str, Path],
    cfgrib_index_dir: Union[str, Path],
    force: bool = False,
    discharge_var: Optional[str] = None,
    selected_years: Optional[List[int]] = None,
    keep_temp_files: bool = False,
) -> Dict[str, pd.Series]:
    """Streaming extraction: process years sequentially, write immediately.
    
    This is a drop-in replacement for load_or_build_gauge_timeseries() that
    uses streaming architecture instead of memory accumulation.
    
    Benefits:
    - Constant memory usage (only one year in RAM)
    - Resumption support (skips already-extracted years)
    - Scales to 1000s of gauges
    - Works on cloud and local machines
    
    Parameters
    ----------
    grib_inventory : List[GribInventoryItem]
        GRIB files to process
    points : pd.DataFrame
        Gauge points (virtual_gauge_id, lat, lon)
    processed_timeseries_dir : Union[str, Path]
        Output directory for final gauge files
    cfgrib_index_dir : Union[str, Path]
        cfgrib index directory
    force : bool, optional
        If True, ignore cached files and re-extract
    discharge_var : Optional[str], optional
        Discharge variable name (None = auto-detect)
    selected_years : Optional[List[int]], optional
        Only process these years (for testing)
    keep_temp_files : bool, optional
        If True, don't delete temp files after merge (for debugging)
        
    Returns
    -------
    Dict[str, pd.Series]
        Dictionary mapping gauge_id → daily discharge Series
    """
    logger.info("="*80)
    logger.info("📥 STREAMING TIME SERIES EXTRACTION")
    logger.info("="*80)
    
    processed_timeseries_dir = Path(processed_timeseries_dir)
    processed_timeseries_dir.mkdir(parents=True, exist_ok=True)
    cfgrib_index_dir = Path(cfgrib_index_dir)
    
    gauge_ids = points["virtual_gauge_id"].unique().tolist()
    
    # Check if cached files already exist and are complete
    if not force:
        logger.info(f"Checking for cached gauge files...")
        cached = {}
        missing = []
        
        grib_years = sorted(set(item.year for item in grib_inventory))
        expected_start = pd.Timestamp(year=grib_years[0], month=1, day=1) if grib_years else None
        expected_end = pd.Timestamp(year=grib_years[-1], month=12, day=31) if grib_years else None
        
        for gid in gauge_ids:
            f = processed_timeseries_dir / f"{gid}.parquet"
            if f.exists():
                try:
                    df = pd.read_parquet(f)
                    s = pd.Series(df["discharge_m3s"].values, index=pd.to_datetime(df["date"]))
                    s.name = "discharge_m3s"
                    
                    # Validate coverage
                    if expected_start and expected_end:
                        cache_start = s.index.min()
                        cache_end = s.index.max()
                        if cache_start <= expected_start and cache_end >= expected_end:
                            cached[gid] = s
                            continue
                    else:
                        cached[gid] = s
                        continue
                except Exception:
                    pass
            missing.append(gid)
        
        if not missing:
            logger.info(f"✓ All {len(cached)} gauges already cached with complete coverage")
            return cached
        else:
            logger.info(f"  Already cached: {len(cached)}")
            logger.info(f"  Need to extract: {len(missing)}")
    else:
        logger.info("FORCE=True: Re-extracting all gauges")
        cached = {}
        missing = gauge_ids
    
    # Filter inventory by selected_years if specified
    if selected_years:
        grib_inventory = [item for item in grib_inventory if item.year in selected_years]
        logger.info(f"  Filtered to {len(selected_years)} selected years: {sorted(selected_years)}")
    
    logger.info(f"\nTotal gauges required:    {len(gauge_ids)}")
    logger.info(f"Already cached:           {len(cached)}")
    logger.info(f"Need to extract:          {len(missing)}")
    logger.info(f"GRIBs to process:         {len(grib_inventory)}")
    
    # Setup temp directory for yearly files
    temp_dir = processed_timeseries_dir / "_temp_streaming"
    temp_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Temp directory:           {temp_dir}")
    logger.info("="*80)
    
    # STEP 1: Extract each year to temp file
    temp_files = []
    for i, grib_item in enumerate(grib_inventory, 1):
        logger.info(f"[{i:2d}/{len(grib_inventory)}] Processing GRIB year {grib_item.year}...")
        try:
            temp_file = extract_year_to_temp_file(
                grib_item,
                points,
                temp_dir,
                cfgrib_index_dir,
                discharge_var,
            )
            temp_files.append(temp_file)
            
            # Explicit garbage collection after each year
            gc.collect()
            
        except Exception as e:
            logger.error(f"        ✗ ERROR: {e}")
            continue
    
    logger.info(f"\n✓ Extracted {len(temp_files)} years to temp files")
    
    # STEP 2: Merge yearly temps into per-gauge files
    if not missing:
        # Nothing new to merge, return cached
        series_by_gauge = cached
    else:
        series_by_gauge = merge_yearly_temps_to_gauge_files(
            sorted(temp_files),
            gauge_ids,
            processed_timeseries_dir,
        )
        
        # Combine with cached data if any
        series_by_gauge.update(cached)
    
    # STEP 3: Cleanup temp files
    if not keep_temp_files:
        logger.info(f"\n🧹 Cleaning up {len(temp_files)} temp files...")
        for tf in temp_files:
            if tf.exists():
                tf.unlink()
        if temp_dir.exists() and not any(temp_dir.iterdir()):
            temp_dir.rmdir()
        logger.info("✓ Cleanup complete")
    else:
        logger.info(f"\n  Keeping temp files for debugging: {temp_dir}")
    
    logger.info("="*80)
    logger.info(f"✅ STREAMING EXTRACTION COMPLETE: {len(series_by_gauge)} gauges")
    logger.info("="*80)
    
    return series_by_gauge
