from __future__ import annotations

from pathlib import Path
from typing import Optional, Sequence, Union

try:
    import geopandas as gpd
except Exception:  # pragma: no cover
    gpd = None


def _require_gpd():
    if gpd is None:
        raise ImportError("geopandas is required for HydroBASINS operations")


def read_vector(path: Union[str, Path], enforce_epsg4326: bool = True) -> "gpd.GeoDataFrame":
    """Read a vector dataset and optionally enforce EPSG:4326."""
    _require_gpd()
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Vector file not found: {path}")
    gdf = gpd.read_file(path)
    if enforce_epsg4326:
        if gdf.crs is None:
            raise ValueError(f"Vector CRS is undefined for: {path}")
        if int(gdf.crs.to_epsg() or 0) != 4326:
            # Locked decision: keep everything in EPSG:4326.
            gdf = gdf.to_crs(epsg=4326)
    return gdf


def get_id_field(gdf: "gpd.GeoDataFrame", candidates: Sequence[str] = ("HYBAS_ID", "HYBASID", "BASIN_ID")) -> str:
    for c in candidates:
        if c in gdf.columns:
            return c
    raise KeyError(f"Could not find an ID field in columns. Tried: {candidates}. Available: {list(gdf.columns)}")


def select_context_polygon(context_gdf: "gpd.GeoDataFrame", hydrobasins_id: int, id_field: Optional[str] = None) -> "gpd.GeoDataFrame":
    """Return the single-row GeoDataFrame for the context basin polygon."""
    _require_gpd()
    if id_field is None:
        id_field = get_id_field(context_gdf)
    sel = context_gdf[context_gdf[id_field].astype("int64") == int(hydrobasins_id)]
    if len(sel) != 1:
        raise ValueError(f"Expected exactly 1 context basin with {id_field}={hydrobasins_id}, found {len(sel)}")
    return sel


def select_l12_by_geometry(
    l12_gdf: "gpd.GeoDataFrame",
    geom,
    mode: str = "intersects",
) -> "gpd.GeoDataFrame":
    """Select L12 polygons by geometry.

    mode: 'intersects' or 'within'.
    """
    _require_gpd()
    if mode not in {"intersects", "within"}:
        raise ValueError("mode must be 'intersects' or 'within'")

    if mode == "intersects":
        mask = l12_gdf.intersects(geom)
    else:
        mask = l12_gdf.within(geom)

    out = l12_gdf[mask].copy()
    if out.empty:
        raise RuntimeError("No L12 polygons were selected. Check AOI/context basin geometry.")
    return out
