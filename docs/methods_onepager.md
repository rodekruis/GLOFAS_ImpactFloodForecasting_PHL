# Methods & Technical Approach

This document provides a concise overview of PhilFlood's statistical methodology and system architecture for practitioners and decision-makers.

## Extreme Value Theory (EVT) Approach

### Threshold Selection

PhilFlood uses **Peaks Over Threshold (POT)** analysis to identify rare flood events in historical GloFAS discharge data:

1. **Peaks Over Threshold**: Select a high discharge threshold $Q_t$ (e.g., 1500 m³/s) from diagnostic plots
2. **Mean Residual Life Plot**: Identifies where the discharge distribution's tail behavior changes
3. **Parameter Stability Plot**: Validates that GPD parameters are stable above the chosen threshold
4. **Independence Check**: Declusters peaks to ensure each represents a distinct flood event

### Extreme Value Distribution

Above the threshold, discharge exceedances $X_i$ follow a **Generalized Pareto Distribution (GPD)**:

$$P(X > x) = \left(1 + \xi \frac{x - \mu}{\sigma}\right)^{-1/\xi}$$

Where:
- $\xi$ = shape parameter (tail heaviness)
- $\sigma$ = scale parameter (spread)
- $\mu$ = threshold location

**Key insight**: This distribution captures rare event frequency and magnitude without requiring data from entire historical record.

### Return Period Estimation

Given fitted GPD parameters, the return period of discharge magnitude $Q$ is:

$$T = \frac{1}{n_{\text{exceedances}} \times (1 - F_{\text{GPD}}(Q))}$$

Where $n_{\text{exceedances}}$ is the annual number of threshold crossings.

Example: If threshold is exceeded 2.5 times/year on average, and $P(X > 2000) = 0.02$:
$$T = \frac{1}{2.5 \times 0.02} = 20 \text{ years}$$

## Streaming GRIB Extraction Architecture

### Memory Optimization

Processing 47 years of global GloFAS GRIB data (3 GB total) requires careful memory management:

```
Input: 47 GRIB files (1979-2025) + 4 gauge points
       ↓
       Geographic Chunking
       └─ Clip ~87,500 grid cells → ~24,000 relevant cells (72% reduction)
       ↓
Year-by-Year Streaming
├─ Year 1979: Load GRIB → extract gauges → write temp parquet → release memory
├─ Year 1980: Load GRIB → extract gauges → write temp parquet → release memory
└─ ...
├─ Year 2024: Load GRIB → extract gauges → write temp parquet → release memory
└─ Year 2025: Load GRIB → extract gauges → write temp parquet → release memory
       ↓
Merge Yearly Files
└─ Concatenate temp parquets (one year at time) → final gauge timeseries
       ↓
Output: 4 parquet files (one per gauge, ~100 MB total)
```

**Memory footprint**: Single year at a time (~50 MB) instead of accumulating across 47 years (1.8 GB)

**Benefit**: Eliminates memory crashes; enables full historical processing on commodity hardware (8 GB RAM)

## Flood Depth to Impact Conversion

### CLIMADA Flood Model

Discharge forecasts are converted to flood impacts using a **depth-to-exposure model**:

1. **Global Flood Hazard Maps** (JRC Global Flood Model)
   - Depth layers for fixed return periods (10-year, 100-year, etc.)
   - Grid resolution: 100 m × 100 m
   - Covers Philippines and neighboring regions

2. **Interpolation to Forecast Return Period**
   - GloFAS discharge forecast $Q_{\text{forecast}}$ → return period $T_{\text{forecast}}$ via fitted GPD
   - Interpolate between fixed depth layers: $\text{Depth} = f(T_{\text{forecast}})$
   - Result: Continuous flood depth map

3. **Exposure & Vulnerability**
   - Overlay population grids (WorldPop or national census)
   - Apply vulnerability threshold: $\text{Affected} = \text{Population} \times \mathbb{1}[\text{Depth} > h_{\text{crit}}]$
   - Aggregate across river basin: $\text{Total Affected} = \sum \text{Affected}_{\text{grid cell}}$

### Risk Metrics

From synthetic events, three risk metrics are computed:

- **AEP** (Annual Exceedance Probability): Expected number of people affected per year (average)
- **OEP** (Occurrence Exceedance Probability): Largest single-event impact observed historically
- **AAPA** (Average Annual Affected People): Total affected people divided by years in dataset

These metrics inform trigger threshold selection and confidence levels.

## Real-Time Operational Flow

### Daily Workflow

```
GloFAS Forecast Release (06:00 UTC)
       ↓
Ingest Ensemble (50-member)
       ↓
Apply Fitted GPD Parameters
├─ Translate discharge → return period for each ensemble member
├─ Interpolate depth maps for each return period
└─ Convert to affected population via exposure
       ↓
Probability Distribution Analysis
├─ Calculate: P(affected > 500,000) = ?
├─ Calculate: E[affected people] = ?
└─ Check: P(affected > threshold) > 30%?
       ↓
Trigger Decision Logic
├─ IF: P(affected > impact_threshold) > 30% AND
│      E[affected people] > half-threshold AND
│      lead_time ≤ 7 days
├─ THEN: ✅ TRIGGER ACTIVATED
└─ ELSE: ⚠️ NO TRIGGER (monitor forecast)
       ↓
Issue Alert + Save Decision Metadata
└─ Record: trigger status, confidence, ensemble spread
```

### Configuration Files

All calibrated parameters stored in YAML (never re-fit in operations):

```yaml
basin_name: example_basin
glofas_points: [15.12, 122.56]  # lat, lon

evt_parameters:
  threshold_m3s: 1500.0          # POT threshold
  shape_xi: -0.15                # GPD shape
  scale_sigma: 250.0             # GPD scale
  exceedances_per_year: 2.5      # POT rate

impact_parameters:
  climada_hazard_file: "hazard_fluvial_phl.nc"
  population_grid: "worldpop_phl_2025.tif"
  depth_critical_m: 0.5          # Depth = affected

trigger_parameters:
  impact_threshold: 500000        # people affected
  probability_threshold: 0.30     # 30% chance
  max_lead_time_days: 7
  confidence_thresholds:
    high: 0.50
    medium: 0.35
    low: 0.20
```

## Data Flow Summary

| Stage | Input | Processing | Output |
|---|---|---|---|
| **Calibration** | GloFAS historical 1979-2025 | EVT fitting, synthetic generation | Fitted parameters (YAML) |
| **Ingestion** | GloFAS forecast ensemble | Translate to probability via GPD | Impact probability distribution |
| **Analysis** | Impact distribution | Assess vs. thresholds | Decision metadata |
| **Operations** | Decision metadata | Format for stakeholders | Alert message + data export |

## References

- **Extreme Value Theory**:
  - Coles, S. (2001). An Introduction to Statistical Modeling of Extreme Values. Springer.
  - Gilleland, E., & Katz, R. W. (2016). ExtremeS: A spatiotemporal modeling platform. JAMC.

- **Flood Hazard Modeling**:
  - Alfieri, L., et al. (2015). Global flood hazard mapping using the LISFLOOD-FP hydraulic model. JRC Technical Report.
  - Schumann, G., et al. (2016). A first large-scale flood inundation forecasting model. JAM.

- **GloFAS System**:
  - Emerton, R., et al. (2016). Developing a global operational seasonal hydro-meteorological forecasting system. HESS.
  - Harrigan, S., et al. (2020). GloFAS-Seasonal v4.0. Copernicus Climate Data Store.

- **CLIMADA Model**:
  - Aznar-Siguan, G., & Bresch, D. N. (2019). A probabilistic framework for modeling the vulnerability of buildings to climate hazards. NHESS.

---