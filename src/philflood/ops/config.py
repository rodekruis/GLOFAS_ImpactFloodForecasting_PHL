"""Configuration loader for operational notebooks.

This module provides utilities for loading and managing run configurations
across calibration notebooks (NB01–NB04). It automatically discovers the
latest NB01 run configuration and derives standard paths for downstream use.

Usage:
    from philflood.ops.config import load_run_config, print_config_summary
    
    config = load_run_config(search_processed_root, auto_select_latest=True)
    print_config_summary(config, title="NB1 Configuration")

Key concepts:
    - NB01 saves a run_config.json in: data/processed/calibration/evt_pot/{basin_id}/{run_tag}/
    - Auto-discovery searches all such directories and selects the most recent
    - Downstream notebooks (NB02–NB04) use this config to resolve data paths
    - Manual paths can override auto-discovered values
"""

import json
import warnings
from pathlib import Path
from typing import Dict, Optional, Any


def find_repo_root(start: Optional[Path] = None) -> Path:
    """Locate repository root by searching for canonical markers.
    
    Searches upward from `start` directory (or current directory) for:
    - pyproject.toml
    - .git/
    - src/ folder
    
    Parameters
    ----------
    start : Path, optional
        Starting directory for search. Defaults to current working directory.
        
    Returns
    -------
    Path
        Repository root directory path.
        
    Raises
    ------
    RuntimeError
        If no repository markers are found.
        
    Examples
    --------
    >>> repo = find_repo_root()
    >>> print(repo)
    /home/user/GLOFAS_ImpactFloodForecasting_PHL
    """
    p = Path.cwd().resolve() if start is None else Path(start).resolve()
    
    for parent in (p, *p.parents):
        markers = ['pyproject.toml', '.git', 'src']
        if any((parent / marker).exists() for marker in markers):
            return parent
    
    raise RuntimeError(
        f'Could not find repo root starting from {p}. '
        'Expected to find pyproject.toml, .git, or src/ directory.'
    )


def load_run_config(
    search_processed_root: Optional[Path] = None,
    run_config_path: Optional[Path] = None,
    auto_select_latest: bool = False,
) -> Dict[str, Any]:
    """Load NB01 run configuration with optional auto-discovery.
    
    Searches for run_config.json files in the standard NB01 output structure:
        data/processed/calibration/evt_pot/{basin_id}/{run_tag}/run_config.json
    
    If multiple configs are found and auto_select_latest=True, returns the
    most recently modified one (by file mtime).
    
    Parameters
    ----------
    search_processed_root : Path, optional
        Root directory to search. Typically `{repo_root}/data/processed`.
        If None, uses current working directory.
        
    run_config_path : Path, optional
        Explicit path to run_config.json. If provided, takes precedence
        over auto-discovery.
        
    auto_select_latest : bool, optional
        If True and multiple configs found, select most recent by mtime.
        If False, returns empty dict when multiple configs exist.
        Default: False.
        
    Returns
    -------
    Dict[str, Any]
        Configuration dictionary loaded from run_config.json, or empty dict
        if no config is found.
        
        Expected keys (if present):
        - basin_id: str - Basin identifier
        - run_tag: str - Run timestamp/tag
        - selection_mode: str - 'basin' or 'municipality'
        - evt_params_parquet: str - Path to EVT parameters
        - timeseries_dir: str - Path to discharge timeseries directory
        - adm3_geojson: str - Path to administrative boundaries
        - worldpop_raster: str - Path to population raster
        - jrc_root: str - Path to JRC flood maps directory
        
    Examples
    --------
    Auto-discover latest run config:
    
    >>> from pathlib import Path
    >>> from philflood.ops.config import load_run_config
    >>> processed_root = Path('/data/processed')
    >>> config = load_run_config(processed_root, auto_select_latest=True)
    >>> print(config.get('basin_id'))
    Cagayan_01
    
    Load explicit config file:
    
    >>> config_path = Path('/data/processed/calibration/evt_pot/Cagayan_01/2026-01-19_calib/run_config.json')
    >>> config = load_run_config(run_config_path=config_path)
    
    Notes
    -----
    - Returns empty dict if no config found (no error raised)
    - User should check `if config:` before accessing keys
    - For NB02–NB04, typically use auto_select_latest=True to get most recent NB01 output
    """
    
    # Explicit path takes precedence
    if run_config_path is not None:
        run_config_path = Path(run_config_path)
        if run_config_path.exists():
            with open(run_config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            warnings.warn(f"Explicit run_config path does not exist: {run_config_path}")
            return {}
    
    # Auto-discover in processed root
    if search_processed_root is None:
        search_processed_root = Path.cwd()
    else:
        search_processed_root = Path(search_processed_root)
    
    if not search_processed_root.exists():
        warnings.warn(f"Search root does not exist: {search_processed_root}")
        return {}
    
    # Glob for all run_config.json files in evt_pot structure
    evt_dirs = list(search_processed_root.glob('calibration/evt_pot/*/*/run_config.json'))
    
    if not evt_dirs:
        return {}
    
    # If auto_select_latest, pick most recent by mtime
    if auto_select_latest:
        latest = max(evt_dirs, key=lambda p: p.stat().st_mtime)
        with open(latest, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    # If exactly one found, return it
    if len(evt_dirs) == 1:
        with open(evt_dirs[0], 'r', encoding='utf-8') as f:
            return json.load(f)
    
    # Multiple found and auto_select_latest=False
    warnings.warn(
        f"Found {len(evt_dirs)} run_config.json files in {search_processed_root}. "
        "Set auto_select_latest=True to pick the most recent, or provide explicit run_config_path."
    )
    return {}


def resolve_evt_paths(
    config: Dict[str, Any],
    fallback_evt_params: Optional[Path] = None,
    fallback_discharge_ts: Optional[Path] = None,
) -> tuple[Optional[Path], Optional[Path]]:
    """Resolve EVT1 data paths from config with optional fallbacks.
    
    Derives evt_params and discharge timeseries paths from:
    1. Explicit paths in config dict (if present)
    2. Fallback paths (if provided)
    3. Standard derived paths from basin_id + run_tag
    
    Parameters
    ----------
    config : Dict[str, Any]
        Configuration dict (typically from load_run_config)
        
    fallback_evt_params : Path, optional
        Fallback path if not found in config
        
    fallback_discharge_ts : Path, optional
        Fallback path if not found in config
        
    Returns
    -------
    tuple[Optional[Path], Optional[Path]]
        (evt_params_path, discharge_ts_path) or (None, None) if unresolvable
        
    Examples
    --------
    >>> config = load_run_config(processed_root, auto_select_latest=True)
    >>> evt_params, discharge_ts = resolve_evt_paths(config)
    >>> if evt_params:
    ...     df = pd.read_parquet(evt_params)
    """
    
    evt_params = None
    discharge_ts = None
    
    # Try explicit paths from config first
    if 'evt_params_parquet' in config:
        evt_params = Path(config['evt_params_parquet'])
        if not evt_params.exists():
            warnings.warn(f"Config evt_params_parquet does not exist: {evt_params}")
            evt_params = None
    
    if 'discharge_ts_parquet' in config:
        discharge_ts = Path(config['discharge_ts_parquet'])
        if not discharge_ts.exists():
            warnings.warn(f"Config discharge_ts_parquet does not exist: {discharge_ts}")
            discharge_ts = None
    
    # Fallback to provided paths
    if evt_params is None and fallback_evt_params is not None:
        evt_params = Path(fallback_evt_params)
    
    if discharge_ts is None and fallback_discharge_ts is not None:
        discharge_ts = Path(fallback_discharge_ts)
    
    return evt_params, discharge_ts


def print_config_summary(
    config_dict: Dict[str, Any],
    title: str = "Configuration",
    prefix: str = "",
) -> None:
    """Print formatted configuration dict to console.
    
    Useful for logging and debugging configuration resolution.
    
    Parameters
    ----------
    config_dict : Dict[str, Any]
        Configuration dictionary to display
        
    title : str, optional
        Title for the output section. Default: "Configuration"
        
    prefix : str, optional
        Prefix to add to each line (for nested logging). Default: ""
        
    Examples
    --------
    >>> config = load_run_config(processed_root, auto_select_latest=True)
    >>> print_config_summary(config, title="NB01 Run Configuration")
    
     NB01 Run Configuration
     ======================
       basin_id                       = Cagayan_01
       run_tag                        = 2026-01-19_calib-test
       ...
     ======================
    """
    
    print(f"\n{prefix} {title}")
    print(f"{prefix} {'=' * len(title)}")
    
    for key, val in config_dict.items():
        # Truncate long values for readability
        val_str = str(val)
        if len(val_str) > 70:
            val_str = val_str[:67] + "..."
        
        print(f"{prefix}   {key:30s} = {val_str}")
    
    print(f"{prefix} {'=' * len(title)}\n")


def get_standard_data_paths(
    repo_root: Optional[Path] = None,
) -> Dict[str, Path]:
    """Get standard data directory paths for the project.
    
    Parameters
    ----------
    repo_root : Path, optional
        Repository root. If None, auto-detected.
        
    Returns
    -------
    Dict[str, Path]
        Dictionary with keys: 'raw_root', 'processed_root', 'data_root'
        
    Examples
    --------
    >>> paths = get_standard_data_paths()
    >>> print(paths['raw_root'])
    /home/user/GLOFAS_ImpactFloodForecasting_PHL/data/raw
    """
    
    if repo_root is None:
        repo_root = find_repo_root()
    else:
        repo_root = Path(repo_root)
    
    data_root = repo_root / "data"
    
    return {
        'data_root': data_root,
        'raw_root': data_root / "raw",
        'processed_root': data_root / "processed",
    }
