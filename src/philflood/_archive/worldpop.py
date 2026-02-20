from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

import numpy as np

try:
    import rasterio
    from rasterio.mask import mask
except Exception:  # pragma: no cover
    rasterio = None
    mask = None

try:
    from shapely.geometry import Point
except Exception:  # pragma: no cover
    Point = None


@dataclass(frozen=True)
class WeightedCentroidResult:
    """Result of population-weighted centroid calculation.
    
    Attributes
    ----------
    point : Point
        The computed population-weighted centroid (lon, lat).
    total_population : float
        Sum of population in pixels used for centroid calculation.
        When top_n_pixels is specified, this is the sum of only the top N pixels.
        When top_n_pixels is None, this is the sum of all valid pixels in the polygon.
    valid_pixel_count : int
        Number of valid (positive population) pixels used in centroid calculation.
        When top_n_pixels is specified, this is min(top_n_pixels, available_valid_pixels).
        When top_n_pixels is None, this is the count of all valid pixels in the polygon.
    """
    point: "Point"
    total_population: float
    valid_pixel_count: int


def population_weighted_centroid(
    polygon,
    worldpop_raster_path: Union[str, Path],
    nodata_values: Optional[tuple] = None,
    top_n_pixels: Optional[int] = 100,
) -> WeightedCentroidResult:
    """DEPRECATED: This function computes a population-weighted centroid inside a polygon.
    
    As of February 2026, this function is deprecated in favor of direct municipality-watershed
    intersection without population weighting. Population-weighted centroids were causing
    issues with sparse population distributions that moved the centroid to unimportant areas.
    
    This function is retained for backward compatibility only and should not be used in
    new workflows.
    
    Parameters
    ----------
    polygon:
        (Deprecated)
    worldpop_raster_path:
        (Deprecated)
    nodata_values:
        (Deprecated)
    top_n_pixels:
        (Deprecated)

    Raises
    ------
    NotImplementedError
        Always raises NotImplementedError to signal deprecated status.
    """
    raise NotImplementedError(
        "population_weighted_centroid() is deprecated. Use direct L12 selection by municipality "
        "polygon intersection instead (without population weighting). This change addresses issues "
        "with sparse population distributions causing centroid misalignment."
    )

