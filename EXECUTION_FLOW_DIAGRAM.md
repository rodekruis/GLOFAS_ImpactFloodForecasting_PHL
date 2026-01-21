# Execution Flow with Enhanced Logging

## Cell 21 Execution Timeline

```
┌─────────────────────────────────────────────────────────────────────┐
│ USER RUNS: Cell 21 (Time Series Extraction)                         │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ SETUP PHASE                                                          │
├─────────────────────────────────────────────────────────────────────┤
│ ✓ Load inventory of 47 GRIBs (1979-2025)                            │
│ ✓ Check which gauges are already cached                             │
│                                                                      │
│ 📥 PRINTS:                                                           │
│ ┌──────────────────────────────────────────────────────────────┐   │
│ │ ================================================================================
│ │ 📥 TIME SERIES EXTRACTION - Processing Summary
│ │ ================================================================================
│ │ Total gauges required:    4
│ │ Already cached:           0
│ │ Need to extract:          4
│ │ GRIBs to process:         47
│ │ ================================================================================
│ │ (with or without year filtering indicator)
│ └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ PROCESSING LOOP: For each GRIB year (1979-2025)                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  [01/47] Processing GRIB year 1979...                               │
│  ├─ Open GRIB file                                                  │
│  ├─ Extract discharge at 4 gauge locations                          │
│  │                                                                  │
│  │  ┌─ Date Parsing ────────────────────────────────┐              │
│  │  │ Check: Does 1979 have invalid dates?         │              │
│  │  │ Result: NO → Continue                        │              │
│  │  └───────────────────────────────────────────────┘              │
│  │                                                                  │
│  │  ┌─ 📊 No issues found, proceed silently       ┐               │
│  │  │ (No ⚠️ warning printed)                       │               │
│  │  └────────────────────────────────────────────────┘               │
│  │                                                                  │
│  ├─ Save 365 records × 4 gauges = 1,460 discharge values           │
│  └─ Close file, collect garbage                                    │
│          ✓ Extracted 365 discharge values for 4 unique gauge(s)    │
│                                                                      │
│  [02/47] Processing GRIB year 1980...                               │
│  ... (repeat, all clean years) ...                                 │
│                                                                      │
│  [36/47] Processing GRIB year 2014...                               │
│  ├─ Open GRIB file                                                 │
│  ├─ Extract discharge at 4 gauge locations                         │
│  │                                                                  │
│  │  ┌─ Date Parsing ────────────────────────────────┐              │
│  │  │ Check: Does 2014 have invalid dates?         │              │
│  │  │ Result: YES! (year=0 month=0 day=0)         │              │
│  │  │ Invalid count: 365 out of 365 (100%!)        │              │
│  │  └───────────────────────────────────────────────┘              │
│  │                                                                  │
│  │  ┌─ 📊 ISSUE DETECTED! Print warning ────────────┐              │
│  │  │                                               │              │
│  │  │ 📤 PRINTS LOUDLY:                             │              │
│  │  │ ┌─────────────────────────────────────────┐   │              │
│  │  │ │ ==========================================
│  │  │ │ ⚠️  DATA LOSS WARNING: Invalid dates...
│  │  │ │ ==========================================
│  │  │ │ Total time steps:       365
│  │  │ │ Invalid date values:    365 (100.0%)
│  │  │ │ Valid date values:      0 (0.0%)
│  │  │ │ Reason: ECCODES warning (year=0...)
│  │  │ │ ==========================================
│  │  │ │
│  │  │ │ ==========================================
│  │  │ │ 📊 DROPPED ROWS - Detailed Analysis
│  │  │ │ ==========================================
│  │  │ │ Total rows before filtering: 1460
│  │  │ │ Total rows with NaT dates:  1460
│  │  │ │ Total rows after filtering: 0
│  │  │ │
│  │  │ │ Dropped records per gauge:
│  │  │ │   - VG__lat_15.1234__lon_122.5678: 365
│  │  │ │   - VG__lat_15.1250__lon_122.5800: 365
│  │  │ │   - VG__lat_15.1290__lon_122.5900: 365
│  │  │ │   - VG__lat_15.1350__lon_122.6000: 365
│  │  │ │ ==========================================
│  │  │ └─────────────────────────────────────────┘   │              │
│  │  │                                               │              │
│  │  └───────────────────────────────────────────────┘              │
│  │                                                                  │
│  ├─ Save 0 valid records (all dropped as NaT)                      │
│  └─ Close file, collect garbage                                    │
│          ✓ Extracted 0 discharge values for 4 unique gauge(s)      │
│                                                                      │
│  [37/47] Processing GRIB year 2015...                               │
│  ... (resume normal processing) ...                                │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ FINALIZATION PHASE                                                   │
├─────────────────────────────────────────────────────────────────────┤
│ ✓ For each gauge, concatenate all years' data                       │
│ ✓ Remove any remaining NaN values                                   │
│ ✓ Write to parquet file                                             │
│ ✓ Load back into memory                                             │
│                                                                      │
│ 📤 PRINTS:                                                           │
│ ┌──────────────────────────────────────────────────────────────┐   │
│ │ ==========================================
│ │ 💾 FINALIZING - Writing time series to disk
│ │ ==========================================
│ │
│ │   VG__lat_15.1234__lon_122.5678
│ │     - Initial records:  16790 (46 years × ~365 days)
│ │     - Dropped (NaN):    365 (2014 was all NaT)
│ │     - Final records:    16425
│ │     - Date range:       1979-01-01 to 2025-12-31
│ │     - File:             VG__lat_15.1234__lon_122.5678.parquet
│ │
│ │   VG__lat_15.1250__lon_122.5800
│ │     - Initial records:  16790
│ │     - Dropped (NaN):    365
│ │     - Final records:    16425
│ │     - Date range:       1979-01-01 to 2025-12-31
│ │     - File:             VG__lat_15.1250__lon_122.5800.parquet
│ │
│ │   ... (2 more gauges with same pattern)
│ │
│ │ ==========================================
│ │ ✅ EXTRACTION COMPLETE
│ │ ==========================================
│ │ Total gauges processed:   4
│ │ Total records written:    65700
│ │ Total records dropped:    1460
│ │ ==========================================
│ └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ COMPLETION                                                           │
├─────────────────────────────────────────────────────────────────────┤
│ Return dict of 4 Series objects (series_by_gauge)                   │
│                                                                      │
│ 📤 PRINTS:                                                           │
│ └─ ✓ Successfully loaded/extracted gauges: 4                        │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Legend

| Symbol | Meaning |
|--------|---------|
| ✓ | Success - data processed normally |
| ✗ | Error - something went wrong |
| ⚠️ | Warning - data lost or issue detected |
| 📊 | Analysis - detailed breakdown shown |
| 💾 | Save - writing to disk |
| ✅ | Complete - execution finished |
| 📥 | Input/Start |
| 📤 | Output/Result |

---

## Key Points

### What Gets Printed (LOUD):
- ✅ Initial summary (what needs to be processed)
- [XX/47] Progress indicators for each GRIB
- ✓ Success counts per year
- ⚠️ **LOUD warnings** when invalid dates found
- 📊 Per-gauge impact analysis
- 💾 Final output statistics
- ✅ Completion summary

### What Only Gets Logged (DEBUG):
- Dataset dimensions
- Cache hit/miss details
- File closing operations
- Memory collection calls

### What You See in Console:
```
Everything with ✓ ⚠️ 📊 💾 ✅ symbols plus the box borders (═══)
```

---

## Example: Full 47-Year Run

```
================================================================================
📥 TIME SERIES EXTRACTION - Processing Summary
================================================================================
Total gauges required:    4
Already cached:           0
Need to extract:          4
GRIBs to process:         47
================================================================================

[01/47] Processing GRIB year 1979...
        ✓ Extracted 365 discharge values for 4 unique gauge(s)
[02/47] Processing GRIB year 1980...
        ✓ Extracted 366 discharge values for 4 unique gauge(s)
[03/47] Processing GRIB year 1981...
        ✓ Extracted 365 discharge values for 4 unique gauge(s)
... [04-35] ...

[36/47] Processing GRIB year 2014...

================================================================================
⚠️  DATA LOSS WARNING: Invalid dates detected in GRIB file!
================================================================================
Total time steps:       365
Invalid date values:    365 (100.0%)
Valid date values:      0 (0.0%)
Reason: ECCODES warning (year=0 month=0 day=0) - these rows will be DROPPED
================================================================================

================================================================================
📊 DROPPED ROWS - Detailed Analysis by Gauge:
================================================================================
Total rows before filtering: 1460
Total rows with NaT dates:  1460
Total rows after filtering: 0

Dropped records per gauge:
  - VG__lat_15.1234__lon_122.5678: 365 records
  - VG__lat_15.1250__lon_122.5800: 365 records
  - VG__lat_15.1290__lon_122.5900: 365 records
  - VG__lat_15.1350__lon_122.6000: 365 records
================================================================================

        ✓ Extracted 0 discharge values for 4 unique gauge(s)

... [37-47] ...

================================================================================
💾 FINALIZING - Writing time series to disk
================================================================================

  VG__lat_15.1234__lon_122.5678
    - Initial records:  16790
    - Dropped (NaN):    365
    - Final records:    16425
    - Date range:       1979-01-01 to 2025-12-31
    - File:             VG__lat_15.1234__lon_122.5678.parquet

  VG__lat_15.1250__lon_122.5800
    - Initial records:  16790
    - Dropped (NaN):    365
    - Final records:    16425
    - Date range:       1979-01-01 to 2025-12-31
    - File:             VG__lat_15.1250__lon_122.5800.parquet

  VG__lat_15.1290__lon_122.5900
    - Initial records:  16790
    - Dropped (NaN):    365
    - Final records:    16425
    - Date range:       1979-01-01 to 2025-12-31
    - File:             VG__lat_15.1290__lon_122.5900.parquet

  VG__lat_15.1350__lon_122.6000
    - Initial records:  16790
    - Dropped (NaN):    365
    - Final records:    16425
    - Date range:       1979-01-01 to 2025-12-31
    - File:             VG__lat_15.1350__lon_122.6000.parquet

================================================================================
✅ EXTRACTION COMPLETE
================================================================================
Total gauges processed:   4
Total records written:    65700
Total records dropped:    1460
================================================================================

✓ Successfully loaded/extracted gauges: 4
```

This is what you'll see when you run cell 21 with the enhanced logging!
