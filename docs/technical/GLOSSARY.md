# Technical Glossary

Definitions of technical terms used throughout PhilFlood documentation and code.

---

## Statistical & Hydrological Terms

### AEP (Annual Exceedance Probability)
Expected number of people affected per year on average, across the entire historical record. Calculated as `average annual people affected` from synthetic event simulations. Used for long-term risk assessment.

**Formula**: AEP = (Sum of affected people across all years) / (Number of years in dataset)

**Example**: AEP = 50,000 people/year means on average 50K people per year would be affected in baseline scenario.

### BCI (Before Climate Index)
*Not used in current version*. Historical meteorological adjustment factor; planned for future impact adjustments.

### Bootstrap
Statistical resampling technique: repeatedly sample from empirical data with replacement to quantify parameter uncertainty. In PhilFlood:
- Draw 20 random resamples from POT exceedances
- Fit GPD to each resample
- Compute return levels for all resamples
- Extract 95% confidence intervals (q5, q95)

Provides uncertainty bounds on calibrated return periods.

### CF-compliant (Climate and Forecast)
NetCDF files that follow CF Conventions for metadata/structure. Ensures compatibility with GIS/analysis tools. PhilFlood generates CF-1.8 compliant output.

### CV (Coefficient of Variation)
Normalized measure of uncertainty: `CV = std / mean`. For return levels, CV typically 0.02-0.30 (2-30%) indicates reasonable uncertainty bounds.

### EVT (Extreme Value Theory)
Statistical framework for modeling rare events using distribution theory. PhilFlood uses **Generalized Pareto Distribution (GPD)** as its EVT model.

See also: POT, GPD.

### FLOPROS (FLood PROtection Standards)
Infrastructure protection levels applied to flood hazards. Accounts for levees, dikes, flood walls. Not fully implemented in v0.3.0 (placeholder in Notebook 2).

### GPD (Generalized Pareto Distribution)
Probability distribution fit to discharge exceedances above a threshold. Defined by three parameters:
- **ξ (xi)**: Shape parameter (tail heaviness)
- **σ (sigma)**: Scale parameter (spread)
- **u**: Threshold location (fixed, not fitted)

**CDF**: $F(x) = 1 - (1 + \xi (x-u) / \sigma)^{-1/\xi}$ for $x > u$

Used because it accurately captures rare event behavior without modeling the entire distribution.

### Lead Time
Days between forecast issue and forecast valid period. E.g., "3-day lead time" = forecast issued for conditions 3 days in future. PhilFlood checks: lead_time ≤ 7 days for trigger.

### OEP (Occurrence Exceedance Probability)
Largest single event impact observed in historical/synthetic dataset. Represents maximum plausible loss from a single flood event. Complement to AEP.

**Example**: OEP = 500,000 people means historically the largest observed/synthesized single flood affected 500K people.

### POT (Peaks Over Threshold)
Extreme Value approach: select high threshold, model only exceedances above it with GPD. Advantages:
- Uses more data than block maxima approach
- Requires fewer assumptions
- Better for rare events

Selection in Notebook 1 Section 10 using diagnostic plots (MRL, parameter stability).

### Quantile
Percentile values: q5 = 5th percentile, q95 = 95th percentile. Bootstrap return levels report credible intervals as q5-q95.

### Return Period (Recurrence Interval)
Average number of years between exceedances of a given magnitude. E.g., 100-year flood = expected to be exceeded once every 100 years (1% annual probability).

**Calculation**: $T = 1 / P(X > x)$ where P = tail probability from GPD.

### Threshold
Discharge level above which POT exceedances are modeled. Selected in Notebook 1 using Mean Residual Life plot. Example: 1500 m³/s.

---

## Spatial & Geographic Terms

### AOI (Area of Interest)
Geographic region for analysis. In Notebook 1:
- **Basin mode**: River basin polygon from HydroBASINS
- **Municipality mode**: Union of selected municipality boundaries

Used for tile selection, gauge extraction, population exposure.

### Buffer
Spatial dilation: expand geometry by fixed distance. Used to ensure tile coverage beyond basin boundary. Example: `flood_zone_boundary.buffer(0.1)` adds 0.1° (~11 km at equator).

### Centroid
Point location representing center of a grid cell. CLIMADA uses centroids to store hazard intensity values. Example: 100m×100m grid cell represented by single lat/lon centroid.

### EPSG Code
Unique identifier for coordinate reference system (CRS). Examples:
- **EPSG:4326**: WGS 84 (lat/lon, what PhilFlood uses)
- **EPSG:3857**: Web Mercator (for visualization)
- **EPSG:32651**: UTM Zone 51N (survey/local use)

PhilFlood assumes all data in **EPSG:4326**.

### GIS (Geographic Information System)
Software/framework for spatial data analysis. QGIS, ArcGIS used to visualize/validate PhilFlood outputs.

### HydroBASINS
Global watershed boundary dataset at multiple scales. PhilFlood uses Level 5 (~3,000-10,000 km²) to extract basin polygons. Open data from HydroSHEDS.

### Raster
Grid-based spatial data (pixel-oriented). JRC flood maps, WorldPop, output GeoTIFFs are rasters. Contrast with **vector** (polygon, point, polyline).

### Vector
Geometry-based spatial data (vector geometries). Boundaries in GeoJSON/shapefile format. Basin boundaries, municipality boundaries are vectors.

### WorldPop
Global gridded population dataset at ~100m resolution. Used for population exposure calculations and vulnerability assessment.

---

## Data & GloFAS Terms

### EPS (Ensemble Prediction System)
Probabilistic weather/hydrological forecast with multiple members (e.g., 50 members). GloFAS provides 50-member ensemble for discharge. Enables probability distribution of impacts.

### GloFAS (Global Flood Awareness System)
ECMWF operational flood forecasting system providing:
- **Reforecasts**: hindcasts of historical period for calibration
- **Historical**: observed discharge 1979-2025
- **Forecasts**: real-time ensemble discharge 10-day ahead

See [methods-overview.md](../technical/methods-overview.md) for architecture.

### GRIB (Gridded Binary)
Binary file format for meteorological/hydrological data (GRIB1, GRIB2). GloFAS data distributed as GRIB. PhilFlood extracts via streaming to minimize memory.

### NetCDF (Network Common Data Form)
Self-describing scientific data format supporting arbitrary dimensions, metadata, CF compliance. PhilFlood uses NetCDF for:
- Return period grids (Notebook 1 output)
- Regridded return periods (Notebook 2 output)
- Flood depth layers (intermediate, Notebook 2)

### Regridding
Interpolation from one grid to another. Notebook 2 regrids from JRC grid (irregular, multiple RPs) to regular lat/lon grid for CLIMADA.

---

## CLIMADA & Impact Modeling

### Centroids
Grid points in CLIMADA hazard object representing asset locations. PhilFlood creates centroids at regular lat/lon grid, stores intensity (flood depth) per centroid per event.

### Event
Single scenario in CLIMADA: one return period = one event (e.g., "100-year flood" = one event). Notebook 2 creates 8 events (RP1, 10, 20, 50, 75, 100, 200, 500yr).

### Exposure
Asset values at risk. In PhilFlood:
- **Exposure layer**: Population count per grid cell
- Overlaid with flood depth to calculate impacts

WorldPop data provides exposure.

### Frequency
Annual exceedance probability of an event. For return period T: `frequency = 1/T`. Example: 100-year flood has frequency 0.01 (1% annual probability).

### Hazard
Probabilistic representation of flood risk. CLIMADA Hazard object contains:
- **Centroids**: grid points (lat/lon)
- **Intensity**: flood depth (m) per centroid per event
- **Frequency**: exceedance probability per event

Stored in HDF5 format for efficiency.

### Impact (Exposure × Vulnerability)
Expected loss/affect from flood. Calculated as:
`Impact = Exposure × Vulnerability × Hazard_Intensity`

PhilFlood calculates impact as people affected (vulnerability threshold = >0.5m depth).

### Intensity
Flood depth (meters) per grid cell for a given return period/event. CLIMADA stores intensity in sparse matrix format (many cells = 0).

---

## System & Operational Terms

### API (Application Programming Interface)
Programmatic interface for using PhilFlood. CLI is the main API. Python package API in development (v1.0).

**Example CLI**:
```bash
philflood monitor --basin-dir ops/configs/basins
```

### CLI (Command-Line Interface)
Text-based program interface. `philflood` command entry point implemented in [src/philflood/cli.py](../../src/philflood/cli.py).

**Available commands**:
- `philflood monitor` - Run operational monitoring
- `philflood validate` - Validate basin configurations
- `philflood calibrate` - (Planned v1.0)

### Configuration (Config)
Machine-readable parameters stored in YAML. Basin-specific configs in `ops/configs/basins/*.yaml`. Contains:
- Basin name, geometry, GloFAS stations
- EVT parameters (threshold, GPD ξ, σ)
- Trigger thresholds (impact, probability)

### Credentials
Authentication details (API keys, passwords, etc.). Never commit to git! Use environment variables or secret management system.

### Ensemble
Multiple weather forecast variants. GloFAS provides 50-member ensemble. PhilFlood processes all members to generate probability distributions of impacts.

### Forecast
Prospective prediction of future discharge/impacts. GloFAS releases forecast daily ~6-12 hrs after issue. Lead times typically 0-10 days.

### Latency
Delay between forecast issue and availability for decision-making. PhilFlood monitoring should run within hours of GloFAS release.

### Lag
Delay in receipt of real-time data. GloFAS lag typically 2-6 hours (data released 6-12 hrs after valid time).

### Metadata
"Data about data": descriptive information. PhilFlood NetCDF includes metadata:
- Basin name, basin ID
- Return period, bootstrap uncertainty
- Generation timestamp
- Projection/coordinate system

### Monitoring
Operational workflow: ingest forecast → apply calibrated model → evaluate trigger → issue alert. Notebook runs daily or on-demand.

### Operational
Related to routine, production use (vs. research/development). PhilFlood has:
- **Operational layer**: `src/philflood/ops/`, `src/philflood/pipelines/`
- **Calibration layer**: `calibration/` notebooks (research)

### Streaming (Data Processing)
Processing data piece-by-piece instead of loading all at once. PhilFlood uses streaming GRIB extraction:
- Load year → extract gauges → save → release memory → next year
- Reduces peak memory from 1.8 GB to ~50 MB

### Trigger
Decision rule for issuing flood alert. PhilFlood triggers when:
- Probability of exceeding impact threshold > 30% AND
- Expected affected people > half of impact threshold AND
- Lead time ≤ 7 days

---

## Validation & Metrics (Notebook 03)

### Bias
Ratio of predicted extent to observed extent. Used to diagnose systematic over/under-prediction.

**Formula**: Bias = (TP + FP) / (TP + FN)

**Interpretation**:
- **Bias > 1.0**: Model overpredicts (predicts more flood area than observed)
- **Bias < 1.0**: Model underpredicts (predicts less flood area than observed)
- **Bias ≈ 1.0**: Model extent matches observed (neutral)

**Range**: 0.0 to infinity. Values 0.8-1.2 considered "good" (within 20% area match).

### Confusion Matrix
2×2 table comparing predicted vs. observed flood extent at a given depth threshold:

|  | Flooded (Model) | Not Flooded (Model) |
|---|---|---|
| **Flooded (Observed)** | TP (True Positive) | FN (False Negative) |
| **Not Flooded (Observed)** | FP (False Positive) | TN (True Negative) |

**Components**:
- **TP**: Model predicted flood, observation confirmed flood → **Correct prediction** ✓
- **FP**: Model predicted flood, observation showed NO flood → **False alarm** (over-prediction) ✗
- **FN**: Model predicted NO flood, observation showed flood → **Missed** (under-prediction) ✗
- **TN**: Model predicted NO flood, observation confirmed NO flood → **Correct non-prediction** ✓

### F1 Score
Harmonic mean of precision and recall. Single metric balancing false positives and false negatives.

**Formula**: F1 = 2 × (Precision × Recall) / (Precision + Recall)

**Interpretation**:
- **0.8-1.0**: Excellent model performance
- **0.6-0.8**: Good model performance (acceptable for most operational use)
- **0.4-0.6**: Fair performance (use with caution, document limitations)
- **0.0-0.4**: Poor performance (model needs refinement)

**Range**: 0 to 1 (higher is better).

**Why F1?** Precision alone ignores misses (dangerous for flood forecasting); Recall alone allows over-prediction (expensive false alarms). F1 balances both.

### False Negative (FN)
Grid cells where observed flood occurred but model predicted NO flood. Represents **missed flooding** or under-prediction. Critical for operational safety.

**Operational consequence**: Warnings not issued when they should have been → population at risk.

### False Positive (FP)
Grid cells where model predicted flood but observation showed NO flood. Represents **false alarms**. Common in probabilistic models.

**Operational consequence**: Unnecessary evacuations, resource deployment, economic disruption.

### Intersection over Union (IoU)
Ratio of overlap between predicted and observed extent to their union. Stricter spatial overlap metric.

**Formula**: IoU = TP / (TP + FP + FN)

**Interpretation**:
- **0.7-1.0**: Excellent spatial match
- **0.5-0.7**: Good spatial match
- **0.3-0.5**: Moderate spatial match (usable with caution)
- **0.0-0.3**: Poor spatial match

**Range**: 0 to 1 (higher is better).

**Comparison to F1**: IoU penalizes both false positives AND false negatives equally (stricter than F1).

### Precision
Fraction of model-predicted floods that actually flooded.

**Formula**: Precision = TP / (TP + FP)

**Interpretation**:
- **0.9-1.0**: 90-100% of predicted floods are accurate (few false alarms)
- **0.7-0.9**: 70-90% accurate (acceptable false alarm rate)
- **0.5-0.7**: 50-70% accurate (high false alarm rate)

**Range**: 0 to 1 (higher is better).

**Use**: Diagnose false positive problems (over-prediction). High precision = low false alarms = trust model predictions.

### Recall (Sensitivity)
Fraction of observed floods that model successfully predicted.

**Formula**: Recall = TP / (TP + FN)

**Interpretation**:
- **0.9-1.0**: 90-100% of actual floods caught (few misses)
- **0.7-0.9**: 70-90% caught (acceptable miss rate)
- **0.5-0.7**: 50-70% caught (high miss rate)

**Range**: 0 to 1 (higher is better).

**Use**: Diagnose false negative problems (under-prediction). High recall = few misses = safe operational use.

### True Negative (TN)
Grid cells where both observation and model correctly predicted NO flood. Represents **correct non-predictions**.

### True Positive (TP)
Grid cells where both observation and model predicted flood. Represents **correct positive predictions**.

---

## File Format Terms

### CSV (Comma-Separated Values)
Plain text tabular format. Used for:
- Configuration files
- Output results (optional)
- Monitoring logs

### GeoJSON
JSON format with geographic features. Used for:
- Municipality boundaries (Notebook 1)
- Visualization in web maps
- Integration with GIS

### GeoTIFF
GeoTIFF = GIS-enabled TIFF image. Raster format with embedded coordinate system. JRC flood maps distributed as GeoTIFF.

### HDF5 (Hierarchical Data Format)
Binary scientific data format optimized for large arrays. CLIMADA hazard objects stored as HDF5. Advantages:
- Efficient compression
- Fast access to subsets
- Supports metadata

### YAML (YAML Ain't Markup Language)
Human-readable data format. PhilFlood basin configs use YAML:

```yaml
basin_name: Cagayan_01
glofas_points:
  - [15.12, 122.56]
evt_parameters:
  threshold_m3s: 1500.0
```

Advantages: readable, version-controllable, schema-validatable.

---

## Model & Architecture Terms

### Adapter
Software design pattern: interface to external system. PhilFlood adapters in `src/philflood/adapters/`:
- GRIB extraction → GloFAS data access
- CLIMADA integration → flood hazard modeling
- Data loaders → configuration parsing

### Domain-Driven Design
Architecture pattern: organize code around business concepts (domain). PhilFlood separates:
- **Domain** (`domain/`): Basin, configuration entities, business rules
- **Models** (`models/`): Statistical models (EVT, impact)
- **Adapters** (`adapters/`): External system interfaces

### Middleware
Software layer between application and external system. PhilFlood config system is middleware between user and domain models.

### Monolithic vs. Modular
- **Monolithic**: All code in one file/module (avoid)
- **Modular**: Separate concerns into different modules (PhilFlood design)

PhilFlood is modular to enable:
- Testing each module independently
- Swapping implementations
- Clear dependencies

### OOP (Object-Oriented Programming)
Programming paradigm using objects (encapsulation, inheritance, polymorphism). PhilFlood uses OOP for:
- Basin class (domain)
- EVT model classes
- Adapter classes

### Reproducibility
Ability to re-run analysis and get identical results. PhilFlood ensures:
- Fixed random seed in Bootstrap
- Versioned data (historical GloFAS)
- Configuration as code (YAML)
- Deterministic algorithms

---

## Performance Terms

### Latency
Time delay for single operation (e.g., one forecast processing: 5 seconds per basin).

### Throughput
Number of operations per time unit (e.g., 10 basins per minute).

### Memory Footprint
Peak RAM usage during execution. PhilFlood:
- Streaming GRIB: ~50 MB per year (vs. 1.8 GB all-at-once)
- Notebook 2: 500 MB - 2 GB depending on tile count and mode (LOW/HIGH_RAM)

### Optimization
Improving speed/memory. PhilFlood optimizations:
- Streaming GRIB extraction (Section 4.1)
- Direct rasterio fast path (Section 4, Notebook 2)
- Scipy NetCDF engine (Section 4, Notebook 2)

---

## Related Standards/Systems

### ISO (International Organization for Standardization)
Standards body. PhilFlood related:
- ISO 19115: Geographic metadata
- ISO 19110: Feature catalog

### OGC (Open Geospatial Consortium)
Standards for geospatial data. PhilFlood outputs compatible with:
- OGC WMS (Web Map Service) for visualization
- OGC WCS (Web Coverage Service) for data access

### WMO (World Meteorological Organization)
UN agency for meteorology. GloFAS recognized WMO forecasting system.

---

## Acronyms Reference

| Acronym | Full Form | Context |
|---------|-----------|---------|
| AEP | Annual Exceedance Probability | Risk metric |
| AOI | Area of Interest | Spatial analysis |
| CRS | Coordinate Reference System | Geospatial |
| CSV | Comma-Separated Values | File format |
| EPS | Ensemble Prediction System | GloFAS |
| EVT | Extreme Value Theory | Statistical model |
| FLOPROS | Flood Protection Standards | Hazard adjustments |
| Bias | Ratio of predicted to observed extent | Validation metric |
| F1 Score | Harmonic mean of precision & recall | Validation metric |
| FN | False Negative: missed floods | Confusion matrix |
| FP | False Positive: false alarms | Confusion matrix |
| GPD | Generalized Pareto Distribution | EVT distribution |
| GIS | Geographic Information System | Software |
| GloFAS | Global Flood Awareness System | Forecast system |
| GRIB | Gridded Binary | File format |
| HDF5 | Hierarchical Data Format | File format |
| IoU | Intersection over Union | Validation metric |
| OEP | Occurrence Exceedance Probability | Risk metric |
| POT | Peaks Over Threshold | EVT method |
| Precision | Accuracy of positive predictions | Validation metric |
| Recall | Sensitivity / detection rate | Validation metric |
| TP | True Positive: correct predictions | Confusion matrix |
| TN | True Negative: correct non-predictions | Confusion matrix |
| YAML | YAML Ain't Markup Language | Config format |

---

**Questions on terminology?** Open an [issue on GitHub](https://github.com/rodekruis/GLOFAS_ImpactFloodForecasting_PHL/issues).
