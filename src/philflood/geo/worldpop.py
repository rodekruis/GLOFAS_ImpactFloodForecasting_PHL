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
    point: "Point"
    total_population: float
    valid_pixel_count: int


def population_weighted_centroid(
    polygon,
    worldpop_raster_path: Union[str, Path],
    nodata_values: Optional[tuple] = None,
    top_n_pixels: Optional[int] = 100,
) -> WeightedCentroidResult:
    """Compute a population-weighted centroid inside a polygon.

    This implements the locked decision: centroid must be computed using WorldPop
    population counts (people per pixel) within the municipality polygon.

    Fails loudly if no valid population exists within the polygon.

    Parameters
    ----------
    polygon:
        Any GeoJSON-like geometry or shapely geometry accepted by rasterio.mask.
    worldpop_raster_path:
        Path to WorldPop raster in EPSG:4326.
    nodata_values:
        Optional tuple of values to treat as nodata in addition to the raster's nodata.
    top_n_pixels:
        Optional number of most-populated pixels to use for computing the centroid.
        Defaults to 100. The total_population in the result reflects only these top N pixels.

    Returns
    -------
    WeightedCentroidResult
        point is a shapely Point (lon, lat).
    """
    if rasterio is None or mask is None:
        raise ImportError("rasterio is required to compute the population-weighted centroid")
    if Point is None:
        raise ImportError("shapely is required to compute the population-weighted centroid")

    worldpop_raster_path = Path(worldpop_raster_path)
    if not worldpop_raster_path.exists():
        raise FileNotFoundError(f"WorldPop raster not found: {worldpop_raster_path}")

    with rasterio.open(worldpop_raster_path) as src:
        out_image, out_transform = mask(src, [polygon], crop=True, filled=False)
        data = out_image[0].astype("float64")

        # rasterio returns a masked array if filled=False
        if hasattr(data, "mask"):
            m = np.array(data.mask)
            values = np.array(data.data)
        else:
            m = np.zeros_like(data, dtype=bool)
            values = data

        # Apply nodata rules
        nodata = src.nodata
        if nodata is not None:
            m |= values == nodata
        if nodata_values:
            for v in nodata_values:
                m |= values == v

        # Only positive populations are meaningful weights
        m |= ~np.isfinite(values)
        weights = np.where(~m, values, 0.0)
        weights = np.where(weights > 0, weights, 0.0)

        total_pop = float(weights.sum())
        valid_n = int((weights > 0).sum())

        if total_pop <= 0 or valid_n == 0:
            raise RuntimeError(
                "Population-weighted centroid could not be computed: municipality contains no valid population "
                "pixels (all nodata/zero). This is a hard stop by design."
            )

        # Build per-pixel lon/lat of pixel centers using affine transform.
        rows, cols = weights.shape
        rr, cc = np.meshgrid(np.arange(rows), np.arange(cols), indexing="ij")
        # pixel center coordinates
        x = out_transform.c + (cc + 0.5) * out_transform.a + (rr + 0.5) * out_transform.b
        y = out_transform.f + (cc + 0.5) * out_transform.d + (rr + 0.5) * out_transform.e

        # Filter to top N most-populated pixels only
        flat_weights = weights.flatten()
        flat_x = x.flatten()
        flat_y = y.flatten()
        
        # Find indices of top N pixels by population
        top_indices = np.argsort(flat_weights)[-top_n_pixels:]
        
        # Keep only top pixels
        weights_filtered = flat_weights[top_indices]
        x_filtered = flat_x[top_indices]
        y_filtered = flat_y[top_indices]
        
        # Recalculate total with filtered weights
        total_pop_filtered = float(weights_filtered.sum())
        valid_n_filtered = int((weights_filtered > 0).sum())
        
        if total_pop_filtered <= 0:
            raise RuntimeError(
                f"After filtering to top {top_n_pixels} pixels, no valid population remains. "
                "Try reducing top_n_pixels or check your data."
            )
        
        # Compute weighted centroid using only top pixels
        xw = float((x_filtered * weights_filtered).sum() / total_pop_filtered)
        yw = float((y_filtered * weights_filtered).sum() / total_pop_filtered)
        
        return WeightedCentroidResult(
            point=Point(xw, yw), 
            total_population=total_pop_filtered,      # Sum of top N pixels only
            valid_pixel_count=valid_n_filtered
        )

