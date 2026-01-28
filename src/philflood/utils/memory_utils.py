"""Memory monitoring and optimization utilities for large data processing."""

import logging
from pathlib import Path
from typing import Optional, Tuple

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    psutil = None

logger = logging.getLogger(__name__)


class MemoryMonitor:
    """Track and enforce memory usage limits during data processing."""
    
    def __init__(self, warning_threshold_percent: float = 70.0, error_threshold_percent: float = 85.0):
        """
        Initialize memory monitor.
        
        Parameters
        ----------
        warning_threshold_percent : float
            Warn when system memory usage exceeds this percentage (default 70%)
        error_threshold_percent : float
            Raise error when system memory usage exceeds this percentage (default 85%)
        """
        if not HAS_PSUTIL:
            logger.warning("psutil not installed. Memory monitoring disabled. Install with: pip install psutil")
        
        self.warning_threshold = warning_threshold_percent
        self.error_threshold = error_threshold_percent
        self.process = psutil.Process() if HAS_PSUTIL else None
    
    def get_memory_usage(self) -> dict:
        """Get current memory usage statistics.
        
        Returns
        -------
        dict
            Dictionary with keys:
            - process_mb: Current process memory usage in MB
            - system_percent: System-wide memory usage percentage
            - available_mb: Available system memory in MB
            - total_mb: Total system memory in MB
        """
        if not HAS_PSUTIL or self.process is None:
            # Return dummy values if psutil not available
            return {
                'process_mb': 0,
                'system_percent': 0,
                'available_mb': 0,
                'total_mb': 0,
            }
        
        try:
            mem = psutil.virtual_memory()
            process_mem = self.process.memory_info().rss / (1024 ** 2)  # Convert to MB
            
            return {
                'process_mb': process_mem,
                'system_percent': mem.percent,
                'available_mb': mem.available / (1024 ** 2),
                'total_mb': mem.total / (1024 ** 2),
            }
        except Exception as e:
            logger.warning(f"Could not read memory stats: {e}")
            return {
                'process_mb': 0,
                'system_percent': 0,
                'available_mb': 0,
                'total_mb': 0,
            }
    
    def check_memory(self, operation_name: str = "Operation") -> Tuple[bool, str]:
        """Check current memory usage and return status.
        
        Parameters
        ----------
        operation_name : str
            Name of the operation being checked (for logging)
        
        Returns
        -------
        Tuple[bool, str]
            (can_continue, message)
            - can_continue: True if within limits, False if over error threshold
            - message: Status message
        """
        stats = self.get_memory_usage()
        sys_percent = stats['system_percent']
        
        message = (
            f"{operation_name} - Memory: {sys_percent:.1f}% used "
            f"({stats['available_mb']:.0f}/{stats['total_mb']:.0f} MB available, "
            f"process: {stats['process_mb']:.1f} MB)"
        )
        
        if sys_percent >= self.error_threshold:
            return False, f"❌ {message} [OVER ERROR LIMIT {self.error_threshold}%]"
        elif sys_percent >= self.warning_threshold:
            return True, f"⚠️  {message} [WARNING: approaching limit]"
        else:
            return True, f"✓ {message}"
    
    def log_memory_status(self, operation_name: str = "Checkpoint"):
        """Log current memory status at an operation checkpoint."""
        can_continue, message = self.check_memory(operation_name)
        if can_continue:
            if "approaching" in message:
                logger.warning(message)
            else:
                logger.info(message)
        else:
            logger.error(message)
        return can_continue


class GribGeographicChunker:
    """Create geographic bounding boxes to chunk GRIB extraction."""
    
    @staticmethod
    def compute_bbox(points_df, lat_col: str = 'lat', lon_col: str = 'lon', 
                     padding_degrees: float = 0.5) -> Tuple[float, float, float, float]:
        """Compute a bounding box around gauge points with padding.
        
        Parameters
        ----------
        points_df : pd.DataFrame
            Points with lat/lon columns
        lat_col : str
            Name of latitude column
        lon_col : str
            Name of longitude column
        padding_degrees : float
            Add this much padding around the bounding box (in degrees)
        
        Returns
        -------
        Tuple[float, float, float, float]
            (min_lat, max_lat, min_lon, max_lon)
        """
        min_lat = points_df[lat_col].min() - padding_degrees
        max_lat = points_df[lat_col].max() + padding_degrees
        min_lon = points_df[lon_col].min() - padding_degrees
        max_lon = points_df[lon_col].max() + padding_degrees
        
        return min_lat, max_lat, min_lon, max_lon
    
    @staticmethod
    def clip_dataset_to_bbox(ds, bbox: Tuple[float, float, float, float], 
                            lat_col: str = 'latitude', lon_col: str = 'longitude'):
        """Clip an xarray dataset to a geographic bounding box.
        
        Parameters
        ----------
        ds : xr.Dataset
            Dataset to clip
        bbox : Tuple[float, float, float, float]
            (min_lat, max_lat, min_lon, max_lon)
        lat_col : str
            Name of latitude coordinate
        lon_col : str
            Name of longitude coordinate
        
        Returns
        -------
        xr.Dataset
            Clipped dataset
        """
        min_lat, max_lat, min_lon, max_lon = bbox
        
        # Clip to bounding box
        clipped = ds.sel({
            lat_col: slice(min_lat, max_lat),
            lon_col: slice(min_lon, max_lon)
        })
        
        return clipped


class ParquetIncrementalWriter:
    """Efficiently append rows to parquet files without reading entire file."""
    
    @staticmethod
    def append_to_parquet(filepath: Path, data_df, compression: str = 'snappy') -> int:
        """
        Append data to an existing parquet file or create new one.
        
        Parameters
        ----------
        filepath : Path
            Path to parquet file
        data_df : pd.DataFrame
            Data to append (must have same schema as existing file if it exists)
        compression : str
            Compression algorithm ('snappy', 'gzip', 'brotli', or None)
        
        Returns
        -------
        int
            Total number of rows after append
        """
        import pandas as pd
        
        if filepath.exists():
            try:
                # Read existing file
                existing = pd.read_parquet(filepath)
                # Concatenate
                combined = pd.concat([existing, data_df], ignore_index=True)
                # Write back
                combined.to_parquet(filepath, index=False, compression=compression)
                total_rows = len(combined)
            except Exception as e:
                logger.warning(f"Failed to append to {filepath}: {e}. Writing as new file.")
                data_df.to_parquet(filepath, index=False, compression=compression)
                total_rows = len(data_df)
        else:
            # Create new file
            data_df.to_parquet(filepath, index=False, compression=compression)
            total_rows = len(data_df)
        
        return total_rows


def get_available_memory_mb() -> float:
    """Get available system memory in MB."""
    if not HAS_PSUTIL:
        return 0.0
    try:
        mem = psutil.virtual_memory()
        return mem.available / (1024 ** 2)
    except Exception:
        return 0.0


def estimate_dataframe_memory_mb(df) -> float:
    """Estimate DataFrame memory usage in MB."""
    try:
        return df.memory_usage(deep=True).sum() / (1024 ** 2)
    except Exception:
        return 0.0
