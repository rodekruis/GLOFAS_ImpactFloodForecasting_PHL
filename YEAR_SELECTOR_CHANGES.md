# Year Selector & Date Validation Changes

## Summary
Added support for **dynamic year selection** to debug kernel crashes on specific datasets (e.g., 2014) and **robust date validation** to handle ECCODES warnings about invalid dates.

## Problem Statement
- Kernel was crashing when processing 2014 GRIB data
- ECCODES warning: `g2date:unpack_long: Date is not valid! year=0 month=0 day=0`
- Could be related to memory exhaustion OR date parsing errors
- Needed way to isolate which year(s) cause the crash

## Changes Made

### 1. **Notebook Cell 6 (Configuration Section)**
**File**: `calibration/notebooks/01_evt_pot_calibration_workflow.ipynb`

Added new year selector variable with clear usage documentation:

```python
# --- Year selector for debugging (test individual years) ---
SELECTED_YEARS = None  # Examples: None (all), [2014], [2010, 2011, 2012]

# Usage examples:
# - Test 2014 specifically: SELECTED_YEARS = [2014]
# - Test range 2010-2015: SELECTED_YEARS = list(range(2010, 2016))
# - Process all years: SELECTED_YEARS = None
```

### 2. **GRIB Discovery Function**
**File**: `src/philflood/adapters/glofas_grib_v4.py` → `discover_grib_year_files()`

**Change**: Added optional `selected_years` parameter to filter discovered GRIB files:

```python
def discover_grib_year_files(
    grib_root: Union[str, Path], 
    selected_years: Optional[List[int]] = None  # NEW
) -> List[GribInventoryItem]:
    """
    Now supports filtering to specific years for debugging.
    
    Args:
        grib_root: Root directory containing year folders
        selected_years: If provided, only include these years
    """
```

**Benefit**: When `selected_years=[2014]`, only the 2014 GRIB file is discovered and processed.

### 3. **Date Validation & Error Handling**
**File**: `src/philflood/adapters/glofas_grib_v4.py` → `extract_daily_discharge_for_points()`

**Change**: Added robust date parsing with ECCODES warning handling:

```python
# Gracefully handle invalid dates from ECCODES
idx_time = pd.to_datetime(da[time_name].values, errors='coerce')
invalid_count = idx_time.isna().sum()
if invalid_count > 0:
    logger.warning(f"Found {invalid_count} invalid dates (year=0 or similar). These will be dropped.")

# Drop rows with NaT (invalid) dates
valid_rows = out.index.notna()
if (~valid_rows).sum() > 0:
    logger.debug(f"Dropping {(~valid_rows).sum()} rows with NaT (invalid) dates")
    out = out[valid_rows]
```

**Benefit**: 
- Invalid dates from corrupted GRIB metadata no longer cause crashes
- They are logged and filtered out instead
- Processing continues with valid data

### 4. **Time Series Extraction Function**
**File**: `src/philflood/adapters/glofas_grib_v4.py` → `load_or_build_gauge_timeseries()`

**Changes**:
1. Added `selected_years` parameter (passed through to processing loop)
2. Added year filtering logic in the GRIB processing loop:

```python
def load_or_build_gauge_timeseries(
    grib_inventory: List[GribInventoryItem],
    points: pd.DataFrame,
    processed_timeseries_dir: Union[str, Path],
    cfgrib_index_dir: Union[str, Path],
    force: bool = False,
    discharge_var: Optional[str] = None,
    selected_years: Optional[List[int]] = None,  # NEW
) -> Dict[str, pd.Series]:
```

Loop filtering:
```python
for idx, item in enumerate(grib_inventory):
    # Skip if year filtering enabled and year not selected
    if selected_years is not None and item.year not in selected_years:
        logger.debug(f"Skipping {item.year} (not in selected_years={selected_years})")
        continue
```

### 5. **ECCODES Warning Suppression**
**File**: `src/philflood/adapters/glofas_grib_v4.py` (module-level)

Added warning filters to suppress ECCODES console noise while still handling the issue gracefully:

```python
# Suppress ECCODES warnings about invalid dates (year=0 month=0 day=0)
# These are handled gracefully in extract_daily_discharge_for_points via pd.to_datetime errors='coerce'
warnings.filterwarnings("ignore", category=UserWarning, message=".*g2date.*unpack.*")
warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*g2date.*unpack.*")
```

**Benefit**: Cleaner console output while maintaining graceful error handling.

### 6. **Notebook Cell 21 (Time Series Extraction)**
**File**: `calibration/notebooks/01_evt_pot_calibration_workflow.ipynb`

Updated to:
1. Check `SELECTED_YEARS` setting and display it
2. Pass `selected_years=SELECTED_YEARS` to function
3. Show user-friendly messaging about what's being processed

```python
if SELECTED_YEARS is not None:
    print(f"⚠️  YEAR FILTERING ENABLED: Processing only {SELECTED_YEARS}")
    filtered_inventory = [i for i in inventory if i.year in SELECTED_YEARS]
    print(f"    Processing {len(filtered_inventory)}/{len(inventory)} GRIB files")
else:
    print(f"Extracting discharge for {len(vg_points)} unique virtual gauges from {len(inventory)} GRIB files (all years)...")

series_by_gauge = load_or_build_gauge_timeseries(
    grib_inventory=filtered_inventory,
    points=vg_points,
    processed_timeseries_dir=timeseries_dir,
    cfgrib_index_dir=index_dir,
    force=False,
    discharge_var=discharge_var,
    selected_years=SELECTED_YEARS,
)
```

## How to Use the Year Selector

### Test if 2014 is the problematic year:
```python
SELECTED_YEARS = [2014]  # Cell 6 configuration
```
Then run the notebook. If it crashes, the issue is specific to 2014.

### Test a range of years (e.g., 2010-2015):
```python
SELECTED_YEARS = list(range(2010, 2016))
```

### Test multiple specific years:
```python
SELECTED_YEARS = [2013, 2014, 2015]
```

### Process all years (default):
```python
SELECTED_YEARS = None
```

## Debugging Workflow

1. **Isolate the problematic year**:
   ```python
   SELECTED_YEARS = [2014]  # Test only 2014
   # Run cell 21
   # If kernel crashes, 2014 is problematic; if it succeeds, try another year
   ```

2. **Once isolated**, check the logs for date errors:
   - Look for: `Found N invalid dates (year=0 or similar). These will be dropped.`
   - This indicates the dataset has corrupted date metadata

3. **If crashes persist**, it's likely a memory issue (not date-related):
   - The year selector helps confirm this by running smaller subsets

4. **Test adjacent years**:
   ```python
   SELECTED_YEARS = [2013, 2014, 2015]  # Test around the problem year
   ```

## Expected Behavior

### With valid dates:
```
Processing GRIB 1/1: 2014 (/.../2014/data.grib2)
  Dataset opened. Dims: {...}
  Extracted N discharge values for 4 gauges
✓ Successfully loaded/extracted gauges: 4
```

### With invalid dates (corrupted GRIB):
```
Processing GRIB 1/1: 2014 (/.../2014/data.grib2)
  Dataset opened. Dims: {...}
  Found N invalid dates (year=0 or similar). These will be dropped.
  Extracted M discharge values for 4 gauges (after filtering)
✓ Successfully loaded/extracted gauges: 4
```

### Skipping unselected years:
```
Processing GRIB 1/47: 1979 (skipped - not in selected_years=[2014])
Processing GRIB 2/47: 1980 (skipped - not in selected_years=[2014])
...
Processing GRIB 36/47: 2014 (/.../2014/data.grib2)
  Dataset opened. Dims: {...}
  Extracted N discharge values for 4 gauges
✓ Successfully loaded/extracted gauges: 4
```

## Technical Details

### Date Coercion Strategy
- `pd.to_datetime(..., errors='coerce')` converts unparseable dates to NaT (Not a Time)
- These NaT values are then filtered out after DataFrame construction
- Preserves valid dates while gracefully handling corrupted metadata

### Why This Fixes the Issue

**Memory Exhaustion**: By testing individual years with `SELECTED_YEARS`, you process one ~100MB file instead of 47, confirming if memory is the issue.

**Date Parsing**: The `errors='coerce'` approach means the ECCODES warning (year=0, month=0, day=0) doesn't crash the kernel—it becomes a NaT and gets filtered.

**Both together**: You can now determine if the crash is:
- **Specific to 2014**: Likely corrupted GRIB metadata (now handled)
- **Happens every year**: Memory exhaustion issue (needs further optimization)
- **Happens in clusters**: Specific GRIB versions or time periods

## Files Modified

1. `calibration/notebooks/01_evt_pot_calibration_workflow.ipynb`
   - Cell 6: Added `SELECTED_YEARS` variable and documentation
   - Cell 21: Updated to use year filtering and pass parameter

2. `src/philflood/adapters/glofas_grib_v4.py`
   - Module level: Added ECCODES warning filters
   - `discover_grib_year_files()`: Added `selected_years` parameter
   - `extract_daily_discharge_for_points()`: Added date validation with `errors='coerce'`
   - `load_or_build_gauge_timeseries()`: Added `selected_years` parameter and filtering logic

## Next Steps

1. **Test with `SELECTED_YEARS = [2014]`** to confirm if 2014 is problematic
2. **Check the Jupyter console logs** for date validation warnings
3. **Report which year(s) fail** and whether it's a date parsing or memory issue
4. If still crashing on specific years, consider:
   - Reducing point batch size (process 1 gauge at a time)
   - Using `psutil` to monitor peak memory consumption
   - Alternative GRIB libraries (e.g., `rasterio`, `gdal`) as fallbacks
