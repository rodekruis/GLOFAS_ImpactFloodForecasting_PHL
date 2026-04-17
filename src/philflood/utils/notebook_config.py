"""Standardized configuration utilities for calibration notebooks.

This module provides shared configuration loading, path resolution, and validation
functions to ensure consistent handling of paths and config files across all
calibration notebooks (01–04).
"""

import json
import logging
import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

try:
    import geopandas as gpd
except ImportError:
    gpd = None

from .paths import find_repo_root, resolve_path

logger = logging.getLogger(__name__)


def load_run_config(
    run_config_path: Optional[Union[str, Path]] = None,
    search_processed_root: Union[str, Path] = None,
    auto_select_latest: bool = True,
) -> Dict[str, Any]:
    """Load Notebook 01 run configuration JSON with optional auto-discovery.
    
    Attempts to locate a run_config.json file by:
    1. Using explicit `run_config_path` if provided
    2. Searching in `search_processed_root` (usually data/processed/) for most recent
    3. Returning empty dict if none found (allows graceful fallback)
    
    Parameters
    ----------
    run_config_path : str or Path, optional
        Explicit path to run_config.json
    search_processed_root : str or Path, optional
        Root directory to search for run_config.json files (e.g., data/processed/)
    auto_select_latest : bool, default True
        If multiple configs found, select most recent by modification time
        
    Returns
    -------
    dict
        Configuration dict from JSON file. Empty dict if not found.
        
    Example
    -------
    >>> config = load_run_config(search_processed_root="data/processed")
    >>> evt_params_path = config.get('evt_params_parquet')
    """
    # Priority 1: Explicit path provided
    if run_config_path is not None:
        config_file = Path(run_config_path)
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load config from {config_file}: {e}")
                return {}
    
    # Priority 2: Search in processed_root for all run_config.json files
    if search_processed_root is not None:
        search_dir = Path(search_processed_root)
        if search_dir.exists():
            # Search recursively for run_config.json files
            config_files = list(search_dir.rglob('run_config.json'))
            if config_files:
                if auto_select_latest:
                    # Select the most recently modified
                    config_file = max(config_files, key=lambda p: p.stat().st_mtime)
                    logger.info(f"Auto-selected latest run_config.json: {config_file}")
                else:
                    config_file = config_files[0]
                
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        return json.load(f)
                except Exception as e:
                    logger.warning(f"Failed to load config from {config_file}: {e}")
    
    # No config found - return empty dict to allow graceful degradation
    logger.debug("No run_config.json found. Using empty defaults.")
    return {}


def get_nb_output_paths(
    run_tag: str,
    basin_id: Optional[str] = None,
    mode: str = "basin",
    processed_root: Union[str, Path] = None,
) -> Dict[str, Path]:
    """Derive standard notebook output paths following Notebook 01 convention.
    
    Constructs paths to EVT parameters, timeseries, and other outputs based on
    the run_tag and basin_id. This ensures consistent downstream path resolution
    across all notebooks.
    
    Parameters
    ----------
    run_tag : str
        Run identifier (e.g., "2026-01-19_calib-test")
    basin_id : str, optional
        Basin identifier (e.g., "Cagayan_01"). Required if mode="basin"
    mode : str, default "basin"
        Either "basin" or "municipality"
    processed_root : str or Path, optional
        Root path to processed data (e.g., "data/processed"). 
        If None, uses repo-relative "data/processed"
        
    Returns
    -------
    dict
        Dictionary with keys:
        - 'evt_params_parquet': Path to NB01 EVT parameters parquet file
        - 'timeseries_dir': Path to discharge timeseries directory
        - 'output_dir': Path to NB01 output directory
        - 'run_config_json': Path to run_config.json
        
    Example
    -------
    >>> paths = get_nb_output_paths(run_tag="2026-01-19_test", basin_id="Cagayan_01")
    >>> evt_params = pd.read_parquet(paths['evt_params_parquet'])
    """
    if processed_root is None:
        processed_root = Path("data/processed")
    else:
        processed_root = Path(processed_root)
    
    if mode == "basin" and basin_id is None:
        raise ValueError("mode='basin' requires basin_id parameter")
    
    # Standard NB01 output structure: data/processed/calibration/{basin_id}/{run_tag}/
    if mode == "basin":
        base_dir = processed_root / "calibration" / basin_id / run_tag
    else:
        # municipality mode: data/processed/calibration/municipality/{run_tag}/
        base_dir = processed_root / "calibration" / "municipality" / run_tag
    
    return {
        'evt_params_parquet': base_dir / 'evt_params.parquet',
        'timeseries_dir': base_dir / 'timeseries',
        'output_dir': base_dir,
        'run_config_json': base_dir / 'run_config.json',
    }


def validate_data_paths(
    paths_dict: Dict[str, Union[str, Path]],
    required_keys: Optional[List[str]] = None,
    raise_on_missing: bool = True,
) -> Dict[str, bool]:
    """Validate existence of paths in a dictionary.
    
    Parameters
    ----------
    paths_dict : dict
        Dictionary mapping names to paths (str or Path)
    required_keys : list, optional
        Keys that must exist. If None, checks all keys.
    raise_on_missing : bool, default True
        If True, raise error if any required paths are missing.
        If False, return status dict and log warnings.
        
    Returns
    -------
    dict
        Dictionary mapping path names to existence status (bool)
        
    Raises
    ------
    FileNotFoundError
        If raise_on_missing=True and any required paths are missing.
        
    Example
    -------
    >>> paths = {'admin_geojson': 'data/raw/vectors/phl_adm3.geojson'}
    >>> status = validate_data_paths(paths, required_keys=['admin_geojson'])
    """
    required_keys = required_keys or list(paths_dict.keys())
    status = {}
    missing = []
    
    for key in paths_dict:
        p = Path(paths_dict[key])
        exists = p.exists()
        status[key] = exists
        
        if not exists and key in required_keys:
            missing.append((key, str(p)))
    
    if missing:
        msg = "Missing required data paths:\n" + "\n".join(
            f"  {k}: {p}" for k, p in missing
        )
        if raise_on_missing:
            raise FileNotFoundError(msg)
        else:
            logger.warning(msg)
    
    return status


def load_adm3_gdf(
    adm3_path: Union[str, Path],
    id_field: str = 'adm3_id',
    name_field: str = 'adm3_name',
) -> gpd.GeoDataFrame:
    """Load ADM3 administrative boundaries with standardized column names.
    
    Parameters
    ----------
    adm3_path : str or Path
        Path to ADM3 GeoJSON file
    id_field : str
        Name of column containing administrative unit IDs
    name_field : str
        Name of column containing administrative unit names
        
    Returns
    -------
    geopandas.GeoDataFrame
        GeoDataFrame with standardized columns: adm3_id, adm3_name, geometry
    """
    if gpd is None:
        raise ImportError("geopandas required for load_adm3_gdf. Install with: pip install geopandas")
    
    gdf = gpd.read_file(adm3_path)
    
    if id_field not in gdf.columns:
        raise ValueError(f"Column '{id_field}' not found in {adm3_path}")
    if name_field not in gdf.columns:
        raise ValueError(f"Column '{name_field}' not found in {adm3_path}")
    
    gdf = gdf[[id_field, name_field, 'geometry']].copy()
    gdf.columns = ['adm3_id', 'adm3_name', 'geometry']
    
    return gdf


def resolve_aoi_boundary(
    mode: str,
    basin_id: Optional[str] = None,
    aoi_admin_ids: Optional[List[str]] = None,
    admin_gdf: Optional[gpd.GeoDataFrame] = None,
    basin_config_path: Optional[Union[str, Path]] = None,
) -> 'shapely.geometry.base.BaseGeometry':
    """Resolve area of interest (AOI) boundary based on mode and inputs.
    
    Handles either basin-mode (select by basin ID) or municipality-mode
    (select by admin unit IDs).
    
    Parameters
    ----------
    mode : str
        Either "basin" or "municipality"
    basin_id : str, optional
        Basin identifier (required if mode="basin")
    aoi_admin_ids : list of str, optional
        List of admin unit IDs to include (required if mode="municipality")
    admin_gdf : geopandas.GeoDataFrame, optional
        GeoDataFrame with admin geometries. If None, loaded from standard path.
    basin_config_path : str or Path, optional
        Path to YAML basin config (used in basin mode)
        
    Returns
    -------
    shapely.geometry.base.BaseGeometry
        Boundary geometry (union of selected units)
    """
    if gpd is None:
        raise ImportError("geopandas required for resolve_aoi_boundary. Install with: pip install geopandas")
    
    from shapely.geometry import box
    
    if mode == "municipality":
        if admin_gdf is None:
            raise ValueError("admin_gdf required for mode='municipality'")
        if aoi_admin_ids is None:
            raise ValueError("aoi_admin_ids required for mode='municipality'")
        
        # Filter admin GDF to selected IDs
        aoi_gdf = admin_gdf[admin_gdf['adm3_id'].astype(str).isin([str(x) for x in aoi_admin_ids])]
        if len(aoi_gdf) == 0:
            raise ValueError(f"No matching admin IDs found: {aoi_admin_ids}")
        
        return aoi_gdf.unary_union
    
    elif mode == "basin":
        if basin_id is None:
            raise ValueError("basin_id required for mode='basin'")
        
        # Basin mode typically uses hydrobasins or other boundary source
        # For now, return a placeholder expecting downstream loading
        logger.warning(f"Basin boundary resolution for {basin_id} not yet fully implemented. "
                      "Ensure basin_config_path or basin boundary GeoJSON is loaded separately.")
        
        # Placeholder: return None (caller should handle)
        return None
    
    else:
        raise ValueError(f"Unknown mode: {mode}. Use 'basin' or 'municipality'")


def print_config_summary(
    config_dict: Dict[str, Any],
    title: str = "Configuration Summary",
    prefix: str = "[CONFIG]",
) -> None:
    """Print a formatted configuration summary to console.
    
    Parameters
    ----------
    config_dict : dict
        Configuration dictionary to print
    title : str
        Title of the summary section
    prefix : str
        Prefix for each output line (e.g., "[CONFIG]")
    """
    print(f"\n{prefix} {title}")
    print(f"{prefix} " + "=" * (len(title) + 1))
    
    for key, value in config_dict.items():
        if isinstance(value, Path):
            value_str = f"{value.resolve()}"
        elif isinstance(value, dict):
            value_str = "{...}"
        elif isinstance(value, list):
            if len(value) > 5:
                value_str = f"[{', '.join(str(v) for v in value[:5])} ... +{len(value)-5} more]"
            else:
                value_str = str(value)
        else:
            value_str = str(value)
        
        print(f"{prefix}   {key:30s} = {value_str}")
    
    print(f"{prefix} " + "=" * (len(title) + 1) + "\n")


__all__ = [
    'load_run_config',
    'get_nb_output_paths',
    'validate_data_paths',
    'load_adm3_gdf',
    'resolve_aoi_boundary',
    'print_config_summary',
]
