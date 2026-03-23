"""Interpolation utilities for flood depth and return‑period grids.

This module collects helper functions for interpolating between
discrete return‑period layers and regridding point data (e.g., return
period values defined at GloFAS cell centroids) to a target raster
grid.  The functions are intentionally simple and self‑contained so
that they can be used both in exploratory notebooks and in automated
pipelines without depending on heavy external libraries.

Functions
---------
linear_interp_depth_from_rp(rp_grid, rp_levels, depth_stack)
    Given a grid of return periods, interpolate linearly between
    pre‑computed depth maps at discrete return‑period levels.

regrid_rp_to_grid(rp_by_cell, cell_meta, pop_arr, pop_transform)
    Interpolate irregularly spaced return‑period values to a raster
    grid using inverse‑distance weighting (IDW).  Intended for use
    when CLIMADA‑Petals is not available.

Notes
-----
In production, these functions may be superseded by CLIMADA‑Petals
utilities.  They are provided here to enable self‑tests and
environments where CLIMADA is not installed.
"""

from __future__ import annotations

from typing import Iterable, List

import numpy as np
import rasterio


def linear_interp_depth_from_rp(
    rp_grid: np.ndarray,
    rp_levels: Iterable[float],
    depth_stack: np.ndarray,
) -> np.ndarray:
    """Linearly interpolate flood depths between discrete return‑period layers.

    Parameters
    ----------
    rp_grid : numpy.ndarray
        2‑D array of return‑period values (years) for each grid cell.
    rp_levels : Iterable[float]
        Sorted list of discrete return‑period levels for which depth
        maps are available (e.g., [10, 20, 50, 75, 100, 200, 500]).
    depth_stack : numpy.ndarray
        3‑D array of shape (n_levels, height, width) containing
        flood depths corresponding to each return‑period level.

    Returns
    -------
    numpy.ndarray
        2‑D array of interpolated flood depths.

    Notes
    -----
    The return‑period values are clipped to the range of ``rp_levels``.
    Interpolation is linear in the return‑period dimension.  Values
    exactly equal to a level return the corresponding depth layer.
    """
    rp_levels = np.asarray(list(rp_levels), dtype=float)
    if not np.all(np.diff(rp_levels) > 0):
        raise ValueError("rp_levels must be strictly increasing")

    # Clip return periods to the available range
    rp = np.asarray(rp_grid, dtype=float)
    rp = np.clip(rp, rp_levels.min(), rp_levels.max())

    # Determine the interval indices for each cell
    idx_upper = np.searchsorted(rp_levels, rp, side="left")
    idx_upper = np.clip(idx_upper, 1, len(rp_levels) - 1)
    idx_lower = idx_upper - 1

    # Gather depths at the interval endpoints
    d0 = np.take_along_axis(depth_stack, idx_lower[None, ...], axis=0)[0]
    d1 = np.take_along_axis(depth_stack, idx_upper[None, ...], axis=0)[0]

    # Linear interpolation weight
    rp0 = rp_levels[idx_lower]
    rp1 = rp_levels[idx_upper]
    w = (rp - rp0) / (rp1 - rp0)
    depth = d0 + w * (d1 - d0)
    return depth


def regrid_rp_to_grid(
    rp_by_cell: np.ndarray,
    cell_meta,
    pop_arr: np.ndarray,
    pop_transform: rasterio.Affine,
) -> np.ndarray:
    """Interpolate return periods from point locations onto a raster grid using IDW.

    This function implements a simple inverse‑distance weighting (IDW)
    interpolation from irregularly spaced points (e.g., GloFAS cell
    centroids) to a regular raster grid (e.g., a population map).  It
    is intended as a fallback when more sophisticated regridding
    utilities (e.g. CLIMADA‑Petals) are unavailable.

    Parameters
    ----------
    rp_by_cell : numpy.ndarray
        1‑D array of return‑period values, one per cell.  The order
        should correspond to ``cell_meta.index``.
    cell_meta : pandas.DataFrame
        DataFrame with columns ``lat`` and ``lon`` giving the
        coordinates of each cell.  The index must align with
        ``rp_by_cell``.
    pop_arr : numpy.ndarray
        2‑D population raster array.  Only the shape is used here.
    pop_transform : rasterio.Affine
        Affine transform of the population raster; defines the
        coordinate system for the output grid.

    Returns
    -------
    numpy.ndarray
        2‑D array of interpolated return‑period values matching
        ``pop_arr`` shape.
    """
    # Pre‑compute coordinates of population raster cell centres
    H, W = pop_arr.shape
    xs = np.arange(W) + 0.5
    ys = np.arange(H) + 0.5
    # Use rasterio.transform.xy to get lat/lon of each pixel centre
    lon, lat = rasterio.transform.xy(pop_transform, ys, xs, offset="center")
    lon = np.array(lon)
    lat = np.array(lat)

    pts_lon = cell_meta["lon"].to_numpy()
    pts_lat = cell_meta["lat"].to_numpy()
    pts_val = np.asarray(rp_by_cell, dtype=float)

    if len(pts_val) == 0:
        return np.full((H, W), np.nan, dtype="float32")

    # Compute squared distances between grid points and cell centroids
    # Shape: (H, W, n_points)
    d2 = (lon[..., None] - pts_lon[None, None, :]) ** 2 + (
        lat[..., None] - pts_lat[None, None, :]
    ) ** 2
    # Inverse distance weights (avoid division by zero)
    w = 1.0 / (d2 + 1e-6)
    num = np.sum(w * pts_val[None, None, :], axis=2)
    den = np.sum(w, axis=2)
    return (num / den).astype("float32")