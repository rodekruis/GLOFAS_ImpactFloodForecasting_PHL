# Notebook 1: Calibration Workflow Guide

This guide walks through the EVT calibration process in Notebook 1 (`calibration/notebooks/01_evt_pot_calibration_workflow.ipynb`).

## Overview

Notebook 1 transforms 47 years of historical GloFAS discharge data into fitted EVT (Extreme Value Theory) parameters for your basin of interest. Output: YAML configuration file with calibrated flood triggers.

**Duration**: ~2-3 hours per basin  
**Inputs**: Historical GloFAS GRIB files (automatic download from CDS)  
**Outputs**: Calibrated YAML config, bootstrap return levels, diagnostic plots

---

## Key Sections

### Setup (Sections 1-4)
Choose operation mode and configure your basin:

- **Section 1**: Select basin or municipalities  
  - Option A: `USE_MUNI_AOI = False` → Single basin (Cagayan_01 example)
  - Option B: `USE_MUNI_AOI = True` → Multiple municipalities (interactive selection)
  
- **Section 2**: Download historical GloFAS data  
- **Section 3**: Load basin geometry, configure gauges  
- **Section 4**: Validate data paths and file existence

### Gauge Extraction (Sections 5-8)
Extract virtual gauge discharge timeseries:

- **Section 5**: Create virtual gauge network (automatically or manual)
- **Section 6**: Extract discharge at pour point (basin outlet)
- **Section 7**: Extract discharge from all cells (optional, detailed spatial analysis)
- **Section 8**: Quality checks on extracted timeseries

**Key option** (Section 1):
```python
USE_CELL_EXTRACTION = False  # True = all cells, False = pour point only
```

### POT Threshold Selection (Sections 9-10)
Fit Generalized Pareto Distribution above threshold:

- **Section 9**: Calculate basic statistics (percentiles, exceedance rates)
- **Section 10**: Mean Residual Life (MRL) plot  
  - Look for inflection point where slope changes
  - This indicates optimal threshold
  - Select threshold where MRL becomes approximately linear

**Diagnostic**: Check MRL plot carefully! Threshold selection critical for accuracy.

### EVT Fitting & Bootstrap (Sections 11-12)
Calibrate statistical model:

- **Section 11A**: Fit GPD (Generalized Pareto Distribution)
  - Estimates shape (ξ) and scale (σ) parameters
  - Validates that parameters stable above threshold
  
- **Section 11B**: Parameter stability plot  
  - Plot shape/scale vs. threshold
  - Good: parameters stabilize above conservative threshold
  - Bad: parameters wildly varying (threshold too low)
  
- **Section 11C**: Bootstrap return levels  
  - Resample from POT exceedances 20 times
  - Generates 95% confidence intervals on return periods
  - Returns 1, 10, 20, 50, 75, 100, 200, 500-year levels
  - Report CV (coefficient of variation) - should be 0.02-0.30

### NetCDF Output (Section 13)
Generate hazard-ready output:

- **Section 13**: Write return periods to CF-compliant NetCDF
  - Structure: gauge_id × return_period × 1  
  - Variables: intensity (discharge), frequency (1/T), intensity_std
  - Ready for CLIMADA import
  - Used by Notebook 2

---

## Typical Workflow

```python
# 1. Configuration
USE_MUNI_AOI = False  # Basin mode
BASIN_ID = "Cagayan_01"
GLOFAS_POINT_IDS = ["PHL_12345"]  # Your gauge ID(s)

# 2. Run Sections 1-8
# (Download data, extract gauges)

# 3. Review plots in Section 9
# (Check raw discharge distribution)

# 4. Section 10:  Plot MRL, select threshold
# (Interactive: drag/click to set)

# 5. Section 10 continued: Plot parameter stability
# (Verify shape & scale stabilize above threshold)

# 6. Section 11: Bootstrap
# (Automatic, takes 5-10 minutes)

# 7. Section 11C: review return levels
# (Should show increasing discharge with return period)

# 8. Section 13: NetCDF export
# (Automatic, ready for Notebook 2)

# 9. Save configuration YAML
# (Use script: generate_basin_config_from_calibration.py)
```

---

## Important Parameters

| Parameter | Location | Example | Notes |
|---|---|---|---|
| Basin ID | Section 1 | `Cagayan_01` | Must match YAML filename |
| POT threshold | Section 10 | 1500 m³/s | Selected from MRL plot |
| GPD shape (ξ) | Section 11 | -0.15 | Should be small & negative |
| GPD scale (σ) | Section 11 | 250 m³/s | Spread of exceedances |
| Annual exceedances | Section 11 | 2.5/year | Number exceeding threshold per year |
| Bootstrap resamples | Section 11C | 20 | Default, increase for more precision |
| Return periods | Section 11C | 1, 10, 20, 50, 75, 100, 200, 500 | 8 standard periods |

---

## Validation Checks

After running Notebook 1, verify:

### Section 10 (MRL):
- ✅ MRL plot shows clear inflection point
- ✅ Chosen threshold is where curve stabilizes
- ✅ Data above threshold appears linear

### Section 11 (GPD Fit):
- ✅ Parameter stability plot shows shape/scale stabilizing above threshold
- ✅ Shape parameter ξ between -0.5 and 0.5 (usually small & negative)
- ✅ Scale parameter σ > 0 and reasonable size

### Section 11C (Bootstrap):
- ✅ All 8 return periods have values (no NaNs)
- ✅ Return levels increase with return period (monotonicity)
- ✅ CV (coefficient of variation) between 0.02-0.30 (2-30%)
- ✅ 95% CI (q05, q95) reasonable width relative to mean

### Section 13 (NetCDF):
- ✅ File `return-period_all.nc` created
- ✅ File size reasonable (> 1 KB)
- ✅ Can open with xarray: `xr.open_dataset(...)`

---

## Troubleshooting

**"ValueError: Not enough exceedances above threshold"**
- Threshold too high (no data above it)
- Solution: Lower threshold in Section 10 and re-run

**"All return levels are NaN"**
- GPD fitting failed (likely numerical issue)
- Solution: Try different threshold or check discharge data quality

**"Parameter stability plot shows wild variation"**
- Threshold too low (including too much data in bulk)
- Solution: Increase threshold in Section 10, re-run calibration

**"Notebook takes >3 hours"**
- Likely processing ALL cells instead of pour point
- Check: `USE_CELL_EXTRACTION = True`?
- If yes: Change to False for faster iteration, use True only if needed

See [Troubleshooting Guide](troubleshooting.md) for more issues.

---

## Basin vs. Municipality Mode

### Basin Mode (Standard)
```python
USE_MUNI_AOI = False
BASIN_ID = "Cagayan_01"
```

**Pros**: 
- Single predefined watershed
- Simple configuration
- Well-defined boundaries

**Cons**:
- Limited to basins in HydroBASINS database

### Municipality Mode (Flexible)  
```python
USE_MUNI_AOI = True
# Interactive map selection in Section 1
```

**Pros**:
- Select arbitrary municipalities
- Custom geographic extent
- Useful for multi-basin regions

**Cons**:
- More setup (interactive selection)
- Requires municipality shapefile

**Notebook 2 detects mode automatically!** Run Notebook 1, then Notebook 2 will detect which mode and adapt output paths accordingly.

---

## Next Steps

1. **Review outputs**: Check diagnostic plots carefully
2. **Validate parameters**: See validation checklist above
3. **Save configuration**:
   ```bash
   python calibration/scripts/generate_basin_config_from_calibration.py \
       --period 2015-2025 \
       --output ops/configs/basins/your_basin.yaml
   ```
4. **Run Notebook 2** (if doing hazard analysis):
   ```
   jupyter notebook calibration/notebooks/02_HazardOnly_Workflow_v2.ipynb
   ```
5. **Deploy to operations** (see [Deployment Guide](../operations/deployment.md))

---

## References

- [Methods Overview](../technical/methods-overview.md) - EVT/POT/GPD theory
- [GLOSSARY](../technical/GLOSSARY.md) - Term definitions (POT, EVT, GPD, etc.)
- [Quick Start](../getting-started/quickstart.md) - Installation & first steps
- [FAQ](../getting-started/FAQ.md#evt--calibration) - Calibration Q&A

---

**Questions?** See [FAQ](../getting-started/FAQ.md) or [Troubleshooting](troubleshooting.md).
