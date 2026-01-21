# Enhanced Logging Guide - Data Loss Visibility

## Overview
The time series extraction code now provides **loud, prominent output** to show exactly what data is being dropped and why.

## What You'll See When Running Cell 21

### 1. **Summary at Start**
```
================================================================================
📥 TIME SERIES EXTRACTION - Processing Summary
================================================================================
Total gauges required:    4
Already cached:           0
Need to extract:          4
GRIBs to process:         47
================================================================================
```
This tells you how many gauges need to be processed and how many GRIB files will be loaded.

---

### 2. **Per-GRIB Progress**
```
[01/47] Processing GRIB year 1979...
        ✓ Extracted 365 discharge values for 4 unique gauge(s)

[02/47] Processing GRIB year 1980...
        ✓ Extracted 366 discharge values for 4 unique gauge(s)

...

[36/47] Processing GRIB year 2014...
        ✓ Extracted 300 discharge values for 4 unique gauge(s)
```
Shows each year being processed and how many discharge values were extracted.

---

### 3. **DATA LOSS WARNING (if invalid dates found)**
If a GRIB file has corrupted date metadata:

```
================================================================================
⚠️  DATA LOSS WARNING: Invalid dates detected in GRIB file!
================================================================================
Total time steps:       365
Invalid date values:    15 (4.1%)
Valid date values:      350 (95.9%)
Reason: ECCODES warning (year=0 month=0 day=0) - these rows will be DROPPED
================================================================================

================================================================================
📊 DROPPED ROWS - Detailed Analysis by Gauge:
================================================================================
Total rows before filtering: 1460 (365 time steps × 4 gauges)
Total rows with NaT dates:  60
Total rows after filtering: 1400

Dropped records per gauge:
  - VG__lat_15.1234__lon_122.5678: 15 records
  - VG__lat_15.1250__lon_122.5800: 15 records
  - VG__lat_15.1290__lon_122.5900: 15 records
  - VG__lat_15.1350__lon_122.6000: 15 records
================================================================================
```

**This tells you:**
- How many time steps were corrupted (in this example, 15 out of 365)
- The percentage of data loss (4.1%)
- Which gauges are affected and how many records per gauge
- Total records after filtering

---

### 4. **Finalization Summary**
```
================================================================================
💾 FINALIZING - Writing time series to disk
================================================================================

  VG__lat_15.1234__lon_122.5678
    - Initial records:  2920 (8 years × 365 days)
    - Dropped (NaN):    120
    - Final records:    2800
    - Date range:       1979-01-01 to 2014-12-31
    - File:             VG__lat_15.1234__lon_122.5678.parquet

  VG__lat_15.1250__lon_122.5800
    - Initial records:  2920
    - Dropped (NaN):    120
    - Final records:    2800
    - Date range:       1979-01-01 to 2014-12-31
    - File:             VG__lat_15.1250__lon_122.5800.parquet

  ... (2 more gauges)

================================================================================
✅ EXTRACTION COMPLETE
================================================================================
Total gauges processed:   4
Total records written:    11200
Total records dropped:    480
================================================================================
```

**This tells you:**
- Initial record count for each gauge
- How many records were dropped due to NaN discharge values
- Final record count per gauge
- Date range covered
- Where files are saved
- Overall summary of what was written vs dropped

---

## Interpreting the Output

### Case 1: No Data Loss
```
Total time steps:       365
Invalid date values:    0 (0.0%)
Valid date values:      365 (100.0%)
```
✅ All data is valid. Nothing was dropped.

---

### Case 2: Significant Data Loss from 2014
```
[36/47] Processing GRIB year 2014...
⚠️  DATA LOSS WARNING: Invalid dates detected in GRIB file!
================================================================================
Total time steps:       365
Invalid date values:    365 (100.0%)
Valid date values:      0 (0.0%)
================================================================================
```
🚨 **This year has corrupted date metadata. All 365 records from 2014 were dropped.**

This confirms that 2014's GRIB file has systematically bad dates (year=0 month=0 day=0 from ECCODES).

---

### Case 3: Partial Data Loss from Multiple Years
```
Total records written:    11200
Total records dropped:    480
```
This means:
- Written: 11,200 valid discharge records across all gauges and years
- Dropped: 480 records due to NaN or invalid dates
- **Data loss rate: ~4.1%**

---

## Troubleshooting Based on Output

### "Why did my 2014 data disappear?"
Check the finalization output. If you see:
```
Dropped records per gauge:
  - VG__lat_15.1234__lon_122.5678: 365 records
```
This means all 365 days from 2014 had invalid dates and were dropped.

### "I have very different record counts per gauge"
This is normal if gauges are missing from certain years or if different GRIBs cover different date ranges. The output shows the date range per gauge:
```
- Date range: 1979-01-01 to 2014-12-31
```

### "Should I worry about the 480 dropped records?"
- **<1% dropped**: Acceptable, likely single corrupted time steps
- **1-5% dropped**: Noteworthy, check which years in the detailed output
- **>10% dropped**: Significant, may want to investigate the GRIB source

---

## Key Takeaways

1. **Look for the ⚠️ warning** - If you see it, that year has date issues
2. **Check the percentage** - Understand how much data was lost
3. **Per-gauge breakdown** - See if certain gauges have more issues
4. **Final summary** - Confirms total records written and available for calibration
5. **Date range** - Verify you have the years you expected

---

## Example: Debugging 2014 Issue

**Run with `SELECTED_YEARS = [2014]` and watch for:**

If you see:
```
[01/01] Processing GRIB year 2014...
⚠️  DATA LOSS WARNING: Invalid dates detected in GRIB file!
Total time steps:       365
Invalid date values:    365 (100.0%)
```
→ **2014 is completely corrupted, all 365 days dropped**

Then try:
```python
SELECTED_YEARS = [2013, 2014, 2015]
```

If output shows:
```
[01/03] Processing GRIB year 2013...
        ✓ Extracted 365 discharge values

[02/03] Processing GRIB year 2014...
⚠️  DATA LOSS WARNING...
        ✓ Extracted 0 discharge values  # All were dropped!

[03/03] Processing GRIB year 2015...
        ✓ Extracted 365 discharge values
```

→ **2014 is isolated as the problem. Proceed without it.**

---

## Console vs. Log Files

- **Console output** (what you see): High-level summaries, ⚠️ warnings, ✅ success messages
- **Log files**: Detailed debug-level messages at `~/.jupyter/logs/` (if configured)

Both are always written so you can review later.
