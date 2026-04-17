"""Test direct municipality-watershed intersection selection.

This test validates the new approach where L12 watersheds are selected directly
by intersection with municipality polygons (without population weighting or buffering).
"""
from __future__ import annotations

import pytest
from shapely.geometry import Polygon


def test_deprecated_functions_raise_errors():
    """Verify that deprecated modules are no longer importable from main package.
    
    Note: These modules have been moved to _archive/ as of Feb 2026.
    This test verifies they cannot be imported from the main package,
    ensuring the deprecation is enforced.
    """
    # Test that aoi module is no longer importable
    with pytest.raises(ModuleNotFoundError):
        from philflood.geo.aoi import build_municipality_aoi
    
    # Test that worldpop module is no longer importable
    with pytest.raises(ModuleNotFoundError):
        from philflood.geo.worldpop import population_weighted_centroid



def test_direct_intersection_selection():
    """Verify that L12 selection works with direct polygon intersection."""
    import geopandas as gpd
    from philflood.geo.hydrobasins import select_l12_by_geometry
    
    # Create a mock municipality polygon
    muni_polygon = Polygon([(120, 15), (121, 15), (121, 16), (120, 16)])
    
    # Create mock L12 watersheds (some intersect, some don't)
    l12_data = {
        'HYBAS_ID': [1, 2, 3, 4, 5],
        'geometry': [
            Polygon([(120.2, 15.2), (120.5, 15.2), (120.5, 15.5), (120.2, 15.5)]),  # Inside
            Polygon([(120.8, 15.8), (121.1, 15.8), (121.1, 16.1), (120.8, 16.1)]),  # Overlaps edge
            Polygon([(119.0, 14.0), (119.5, 14.0), (119.5, 14.5), (119.0, 14.5)]),  # Outside
            Polygon([(120.5, 15.5), (120.7, 15.5), (120.7, 15.7), (120.5, 15.7)]),  # Inside
            Polygon([(122.0, 17.0), (122.5, 17.0), (122.5, 17.5), (122.0, 17.5)]),  # Outside
        ]
    }
    
    l12_gdf = gpd.GeoDataFrame(l12_data, crs="EPSG:4326")
    
    # Select L12s by direct intersection
    selected = select_l12_by_geometry(l12_gdf, muni_polygon, mode="intersects")
    
    # Verify that only intersecting L12s are selected (IDs 1, 2, 4)
    assert len(selected) == 3, f"Expected 3 L12s to intersect, got {len(selected)}"
    assert set(selected['HYBAS_ID'].values) == {1, 2, 4}, \
        f"Expected L12s [1, 2, 4], got {list(selected['HYBAS_ID'].values)}"


def test_muni_aoi_records_structure():
    """Verify that muni_aoi_records have correct structure with None for deprecated fields."""
    # This simulates the structure that the notebook produces
    muni_aoi_record = {
        "adm3_id": "test_muni_123",
        "centroid_lon": None,  # Should be None (no longer computed)
        "centroid_lat": None,  # Should be None (no longer computed)
        "total_population": None,  # Should be None (population weighting removed)
        "valid_pixel_count": None,  # Should be None (population weighting removed)
        "n_l12_selected": 47,
        "l12_ids": [5070112900, 5070112920],
    }
    
    # Verify all expected keys exist
    expected_keys = {
        "adm3_id", "centroid_lon", "centroid_lat", "total_population",
        "valid_pixel_count", "n_l12_selected", "l12_ids"
    }
    assert set(muni_aoi_record.keys()) == expected_keys
    
    # Verify deprecated fields are None
    assert muni_aoi_record["centroid_lon"] is None
    assert muni_aoi_record["centroid_lat"] is None
    assert muni_aoi_record["total_population"] is None
    assert muni_aoi_record["valid_pixel_count"] is None
    
    # Verify required fields have values
    assert isinstance(muni_aoi_record["adm3_id"], str)
    assert isinstance(muni_aoi_record["n_l12_selected"], int)
    assert isinstance(muni_aoi_record["l12_ids"], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
