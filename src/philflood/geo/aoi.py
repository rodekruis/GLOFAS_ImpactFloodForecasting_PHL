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
    """Build AOI = geodesic_buffer(centroid, buffer_km) ∩ municipality polygon."""
    buf = geodesic_buffer(pop_centroid, radius_km=buffer_km)
    aoi = buf.intersection(muni_polygon)
    if aoi.is_empty:
        raise RuntimeError("AOI buffer does not intersect municipality polygon. Check input geometries.")
    return AOIResult(centroid=pop_centroid, buffer_km=float(buffer_km), aoi_polygon=aoi)
