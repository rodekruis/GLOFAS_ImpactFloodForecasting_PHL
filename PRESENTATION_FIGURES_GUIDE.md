# Presentation Figures Guide

## Synthetic Event Catalog Visualizations

Generated for stakeholder communication and decision-making in the GLOFAS Impact Flood Forecasting workflow.

---

## Figure 1: Return Level Curves

**Filename:** `01_return_level_curves.png`  
**Size:** 0.19 MB (300 DPI)

### What It Shows
- Return level (discharge in m³/s) vs. return period (years) for all 4 virtual gauges
- Log-scale x-axis to show wide range of return periods (2 to 200 years)

### How to Read It
- **Y-axis (Return Level):** Higher values = more extreme discharges
- **X-axis (Return Period):** Longer period = rarer event
- **Each line:** One gauge with different color/marker
- **Steep curves:** Discharge increases rapidly with return period
- **Flat curves:** Discharge plateaus (limited extrapolation confidence)

### Key Message for Stakeholders
> "This shows how rare discharge events scale with return period. A 100-year event at Gauge A has a discharge of ~X m³/s, while a 100-year event at Gauge B is ~Y m³/s. The differences reflect local basin characteristics and historical flood patterns."

### Technical Details
- Computed using GPD exceedances above thresholds
- Formula: x_rp = u + (σ/ξ) × [(1-F)^(-ξ) - 1] where F = 1/RP
- Based on ~400 years of synthetic events per gauge

---

## Figure 2: Discharge Distributions

**Filename:** `02_discharge_distributions.png`  
**Size:** 0.26 MB (300 DPI)

### What It Shows
- Histogram of peak discharge magnitudes for each of 4 gauges
- 50 bins showing frequency distribution
- Red dashed line marks the POT threshold for each gauge

### How to Read It
- **X-axis (Peak Discharge):** Range of discharge values in m³/s
- **Y-axis (Frequency):** Count of events in each discharge bin
- **Red dashed line:** Threshold—events below this line are NOT extracted
- **Distribution shape:** Indicates whether floods are frequent small events or rare large events

### Key Message for Stakeholders
> "These histograms show the range of peak discharges recorded synthetically at each gauge. The red line marks the flood threshold—only events above this are considered 'significant' flood events. Notice how different gauges have different threshold levels and discharge ranges."

### Technical Details
- 10,166 total synthetic peak discharge values
- Each histogram is for one gauge in the study area
- X-limits adjusted per gauge for clarity
- Thresholds derived from POT extraction (Section 11)

---

## Figure 3: Gauge Summary Table

**Filename:** `03_gauge_summary_table.png`  
**Size:** 0.14 MB (300 DPI)

### What It Shows
- Formatted table with key calibration parameters for all 4 gauges
- Blue header row, alternating light gray background for readability

### Columns Explained

| Column | Meaning |
|--------|---------|
| **Gauge ID** | Location identifier (latitude/longitude) |
| **Threshold (m³/s)** | Discharge level used to define "flood" events |
| **λ (events/yr)** | Average number of flood events per year |
| **GPD ξ** | Shape parameter (negative = bounded tail) |
| **GPD σ** | Scale parameter (dispersion of peaks above threshold) |
| **Synthetic Events** | Number of artificial flood events generated |

### How to Read It
- **Threshold range:** 38–3266 m³/s (varies by gauge)
- **λ range:** 6.2–6.8 events/year (fairly consistent)
- **ξ range:** -0.12 to +0.03 (mostly negative = moderate upper bound)
- **σ range:** 46–3301 m³/s (gauge variability in event magnitude scatter)

### Key Message for Stakeholders
> "This table summarizes the flood model for each location. Notice that despite similar event frequencies (λ ≈ 6/year), the thresholds and magnitudes vary significantly because each gauge has unique basin characteristics. The GPD parameters control how extreme the events become."

### Technical Details
- One row per gauge
- Parameters estimated from observed GloFAS historical discharge
- λ = events observed / coverage years
- GPD parameters fitted using pyextremes POT extraction

---

## Figure 4: Events Per Year Distribution

**Filename:** `04_events_per_year_distribution.png`  
**Size:** 0.13 MB (300 DPI)

### What It Shows
- Bar chart showing the number of synthetic events generated in each simulation year
- All 4 gauges combined (10,166 total events across 400 years)
- Red dashed line shows the mean (average events per year)

### How to Read It
- **X-axis (Simulation Year):** Years 1862–2262 of synthetic data
- **Y-axis (Number of Events):** Count of flood events in that year
- **Bar heights:** Variable due to Poisson process randomness
- **Red line:** Long-term average (≈25 events/year for 4 gauges ≈ 6.3/gauge/year)

### Key Message for Stakeholders
> "This shows how flood events are randomly distributed over time. Some years have more floods than average, others have fewer. This variability is realistic—some years are quiet, others are active. The red line shows the long-term average we expect. This data helps us understand uncertainty in trigger design."

### Technical Details
- Generated using Poisson random draws with parameter λ per gauge
- GLOBAL_SEED=42 for reproducibility
- Synthetic period: BASE_YEAR=1862, SIM_YEARS=400
- Each bar represents one calendar year with all gauges' events combined
- Theoretical expected value = λ_total × SIM_YEARS / year count

---

## Using These Figures

### For Executive Briefings
- Use **Figure 1** to explain return periods and risk scaling
- Use **Figure 3** to show technical rigor and parameter consistency
- Use **Figure 4** to illustrate temporal variability and uncertainty

### For Technical Reports
- Include all 4 figures in appendix
- Reference Figure 3 when discussing calibration parameters
- Cite Figure 1 when justifying trigger thresholds

### For Peer Review
- Figures demonstrate:
  - Proper statistical methodology (GPD fitting)
  - Reasonable parameter ranges
  - Large synthetic sample (10K+ events)
  - Transparent gauge-by-gauge results

### For Community Engagement
- **Figure 1:** "Here's how extreme discharges scale"
- **Figure 2:** "Here's the range we see at each location"
- **Figure 3:** "Here are the technical details if you want them"
- **Figure 4:** "Some years have many floods, others have few"

---

## Data Source & Attribution

**Synthetic Events Generated By:**
- `01_evt_pot_calibration_workflow.ipynb`, Section 12
- Date: 2026-01-20
- Configuration:
  - MAX_RETURN_PERIOD_YEARS = 200
  - YEARS_PER_RETURN_PERIOD = 2 (400 total sim years)
  - GLOBAL_SEED = 42 (reproducible)
  
**Underlying Observations:**
- GloFAS v4 consolidated discharge (ECMWF)
- Virtual gauges: Nearest grid cells to HydroBASINS L12 pour points
- Run length: 5 days (POT declustering)

**Area:** Cagayan River Basin, Philippines (MUNI_SELECTION, Muni AOI)

---

## Questions & Interpretation

### "Why do thresholds differ so much (38 vs 3266 m³/s)?"
Different locations have different baseline discharge patterns. A 100 m³/s event is extreme in a small tributary but routine in the main stem. Each threshold is chosen to define local "floods" consistently.

### "Why is λ ≈ 6 events/year for all gauges?"
The threshold selection algorithm (Section 10) was tuned to target approximately 6 events per year per gauge. This is a deliberate design choice to balance statistical stability with meaningful event detection.

### "Why do events vary year to year?"
Floods follow a Poisson process—random, independent occurrences. Some years naturally have more events, others fewer. This is realistic and matches observed flood patterns.

### "Can these figures be used for operational forecasting?"
These synthetic catalogs support **trigger design** and **risk assessment**, not operational forecasting. Operational forecasts use real-time GloFAS data (Section 12D output is historical/synthetic).

---

## Contact & Further Information

For questions about these figures or the synthetic catalog generation, refer to:
- Notebook: `01_evt_pot_calibration_workflow.ipynb` (Sections 11–12)
- Summary: `SECTION_11_12_REFACTOR_SUMMARY.md`
- Code: `src/philflood/calibration/evt_pot.py` (POT extraction)

