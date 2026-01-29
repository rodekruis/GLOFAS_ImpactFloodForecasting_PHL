"""Memory monitoring and optimization utilities for large data processing."""

import logging
from pathlib import Path
from typing import Optional, Tuple
import tempfile
import shutil

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    psutil = None

try:
    import pyarrow as pa
    import pyarrow.parquet as pq
    HAS_PYARROW = True
except ImportError:
    HAS_PYARROW = False
    pa = None
    pq = None

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
        
        Handles both ascending and descending coordinate orders by detecting
        the monotonicity of the coordinates and adjusting slice bounds accordingly.
        
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
            
        Notes
        -----
        This function detects coordinate order by comparing the first and last values.
        Coordinates are treated as ascending if first <= last, and descending otherwise.
        The function assumes coordinate arrays are monotonic (consistently increasing or
        decreasing). Non-monotonic coordinates (e.g., wrapping around longitude boundaries
        or irregular ordering) may produce unexpected results.
        """
        min_lat, max_lat, min_lon, max_lon = bbox
        
        # Detect coordinate order for latitude
        lat_coords = ds[lat_col].values
        if len(lat_coords) > 1:
            # Use <= to handle edge case where first == last (treat as ascending)
            lat_ascending = lat_coords[0] <= lat_coords[-1]
        else:
            lat_ascending = True  # Default to ascending for single value
        
        # Detect coordinate order for longitude
        lon_coords = ds[lon_col].values
        if len(lon_coords) > 1:
            # Use <= to handle edge case where first == last (treat as ascending)
            lon_ascending = lon_coords[0] <= lon_coords[-1]
        else:
            lon_ascending = True  # Default to ascending for single value
        
        # For slice(), bounds must be in the same order as the coordinate
        # If descending, swap the slice bounds
        if lat_ascending:
            lat_slice = slice(min_lat, max_lat)
        else:
            lat_slice = slice(max_lat, min_lat)
        
        if lon_ascending:
            lon_slice = slice(min_lon, max_lon)
        else:
            lon_slice = slice(max_lon, min_lon)
        
        # Clip to bounding box
        clipped = ds.sel({
            lat_col: lat_slice,
            lon_col: lon_slice
        })
        
        return clipped


class ParquetIncrementalWriter:
    """Memory-efficient parquet file operations using pyarrow's batch processing."""
    
    @staticmethod
    def append_to_parquet(filepath: Path, data_df, compression: str = 'snappy') -> int:
        """
        Append data to an existing parquet file using batch processing for memory efficiency.
        
        This implementation uses pyarrow.parquet.ParquetFile.iter_batches() to read
        existing data in small batches (default 10,000 rows) rather than loading the
        entire file into memory at once. The data is written to a temporary file and
        then atomically moved to replace the original.
        
        While this approach still reads and rewrites the entire file, it does so in
        a memory-efficient manner by streaming batches through Arrow's zero-copy
        memory model, significantly reducing peak memory usage compared to loading
        the full DataFrame into pandas.
        
        Parameters
        ----------
        filepath : Path
            Path to parquet file
        data_df : pd.DataFrame
            Data to append (must have compatible schema with existing file if it exists)
        compression : str
            Compression algorithm ('snappy', 'gzip', 'brotli', or None)
        
        Returns
        -------
        int
            Total number of rows after append
        
        Raises
        ------
        ValueError
            If schema compatibility cannot be resolved
        RuntimeError
            If append operation fails and fallback cannot be performed
        """
        if not HAS_PYARROW:
            raise RuntimeError(
                "pyarrow is required for ParquetIncrementalWriter but is not installed. "
                "Install with: pip install pyarrow>=14.0"
            )
        
        # Convert DataFrame to Arrow Table
        table = pa.Table.from_pandas(data_df, preserve_index=False)
        
        if filepath.exists():
            # Read existing file's metadata to get schema and row count
            existing_file = pq.ParquetFile(str(filepath))
            existing_schema = existing_file.schema_arrow
            existing_rows = existing_file.metadata.num_rows
            
            # Validate schema compatibility and cast if needed
            if not table.schema.equals(existing_schema, check_metadata=False):
                try:
                    table = table.cast(existing_schema)
                    logger.info(f"Successfully cast new data to match existing schema for {filepath}")
                except Exception as cast_error:
                    raise ValueError(
                        f"Schema mismatch when appending to {filepath} and automatic "
                        f"casting failed. Error: {cast_error}"
                    ) from cast_error
            
            # Create a temporary file for the combined parquet
            with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.parquet') as tmp_file:
                tmp_path = tmp_file.name
            
            try:
                # Use ParquetWriter to write both existing and new data in batches
                with pq.ParquetWriter(
                    tmp_path,
                    existing_schema,
                    compression=compression,
                    version='2.6',
                ) as writer:
                    # Write existing data in batches to control memory usage
                    for batch in existing_file.iter_batches(batch_size=10000):
                        writer.write_batch(batch)
                    
                    # Write new data
                    writer.write_table(table)
                
                # Replace original file with new file (atomic on most systems)
                shutil.move(tmp_path, str(filepath))
                total_rows = existing_rows + len(data_df)
                
            except Exception as e:
                # Clean up temp file if it still exists
                if Path(tmp_path).exists():
                    Path(tmp_path).unlink()
                
                # Only attempt fallback if original file still exists
                if filepath.exists():
                    logger.error(
                        f"Failed to append to {filepath}: {e}. "
                        f"Original file is intact but append failed."
                    )
                    raise RuntimeError(
                        f"Failed to append data to {filepath}. Original file is intact."
                    ) from e
                else:
                    # Original file was moved/deleted - this is critical
                    raise RuntimeError(
                        f"Critical error: append failed and original file {filepath} "
                        f"was lost. Data may be in temporary file: {tmp_path}"
                    ) from e
        else:
            # Create new file
            pq.write_table(table, str(filepath), compression=compression, version='2.6')
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
