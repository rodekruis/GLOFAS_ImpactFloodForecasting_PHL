from __future__ import annotations

from dataclasses import dataclass

try:
    from shapely.geometry import Point, Polygon
except Exception:  # pragma: no cover
    Point = None
    Polygon = None

try:
    from pyproj import Geod
except Exception:  # pragma: no cover
    Geod = None


@dataclass(frozen=True)
class AOIResult:
    centroid: "Point"
    buffer_km: float
    aoi_polygon: "Polygon"


def geodesic_buffer(point: "Point", radius_km: float, n: int = 72, ellps: str = "WGS84") -> "Polygon":
    """Create a geodesic buffer polygon around a point (returned as lon/lat in EPSG:4326).

    This avoids buffering in degrees while keeping the output geometry in EPSG:4326.

    Parameters
    ----------
    point:
        Shapely Point (lon, lat).
    radius_km:
        Buffer radius in kilometers.
    n:
        Number of vertices around the circle.
    ellps:
        Ellipsoid for geodesic computations.
    """
    if Point is None or Polygon is None:
        raise ImportError("shapely is required to build AOI buffers")
    if Geod is None:
        raise ImportError("pyproj is required to build geodesic buffers")

    if radius_km <= 0:
        raise ValueError("radius_km must be > 0")

    geod = Geod(ellps=ellps)
    lon, lat = float(point.x), float(point.y)

    # Evenly spaced bearings around the circle.
    step = 360.0 / float(n)
    azimuths = [i * step for i in range(n)]

    coords = []
    for az in azimuths:
        lon2, lat2, _ = geod.fwd(lon, lat, az, radius_km * 1000.0)
        coords.append((lon2, lat2))

    coords.append(coords[0])
    return Polygon(coords)


def build_municipality_aoi(muni_polygon: "Polygon", pop_centroid: "Point", buffer_km: float = 5.0) -> AOIResult:
    """DEPRECATED: This function builds an AOI using a population-weighted centroid and circular buffer.
    
    As of February 2026, this function is deprecated in favor of direct municipality-watershed
    intersection without population weighting. Use select_l12_direct_intersection() instead.
    
    This function is retained for backward compatibility only and should not be used in
    new workflows.
    """
    raise NotImplementedError(
        "build_municipality_aoi() is deprecated. Use direct L12 selection by municipality "
        "polygon intersection instead (without population centroid or buffering)."
    )
