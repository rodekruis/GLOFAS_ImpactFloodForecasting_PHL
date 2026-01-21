#!/usr/bin/env python
"""
Quick test script to demonstrate the year selector and date validation.

Run this to verify the changes work before running the full notebook.
"""

from pathlib import Path
import sys

# Add src to path
repo_root = Path(__file__).parent
src = repo_root / "src"
sys.path.insert(0, str(src))

from philflood.adapters.glofas_grib_v4 import discover_grib_year_files

# Path to GRIB root
glofas_root = repo_root / "data" / "raw" / "glofas" / "historical" / "version_4_0" / "consolidated" / "discharge" / "grib2" / "area_35_63_4_131"

print("=" * 70)
print("YEAR SELECTOR TEST SCRIPT")
print("=" * 70)

# Test 1: Discover all years
print("\n[TEST 1] Discover all available years (selected_years=None):")
try:
    all_years = discover_grib_year_files(glofas_root, selected_years=None)
    print(f"✓ Found {len(all_years)} years: {all_years[0].year}..{all_years[-1].year}")
    print(f"  Paths: {[str(item.grib_path) for item in all_years[:3]]} ...")
except Exception as e:
    print(f"✗ Error: {e}")

# Test 2: Discover only 2014
print("\n[TEST 2] Discover only 2014 (selected_years=[2014]):")
try:
    year_2014 = discover_grib_year_files(glofas_root, selected_years=[2014])
    print(f"✓ Found {len(year_2014)} year")
    for item in year_2014:
        print(f"  Year {item.year}: {item.grib_path}")
except Exception as e:
    print(f"✗ Error: {e}")

# Test 3: Discover range of years
print("\n[TEST 3] Discover range 2010-2015 (selected_years=list(range(2010, 2016))):")
try:
    years_range = discover_grib_year_files(glofas_root, selected_years=list(range(2010, 2016)))
    print(f"✓ Found {len(years_range)} years: {[item.year for item in years_range]}")
except Exception as e:
    print(f"✗ Error: {e}")

# Test 4: Try to discover non-existent year
print("\n[TEST 4] Try non-existent year (selected_years=[1900]):")
try:
    no_year = discover_grib_year_files(glofas_root, selected_years=[1900])
    print(f"✗ Unexpected success: {len(no_year)} years")
except RuntimeError as e:
    print(f"✓ Correctly raised error: {e}")
except Exception as e:
    print(f"✗ Wrong error type: {e}")

print("\n" + "=" * 70)
print("TEST COMPLETE")
print("=" * 70)
print("\nNext steps:")
print("  1. In the notebook, set SELECTED_YEARS = [2014]")
print("  2. Run cell 21 to test GRIB extraction for 2014 only")
print("  3. Check for ECCODES warnings and invalid date messages")
print("  4. If it succeeds, try other years to isolate the issue")
