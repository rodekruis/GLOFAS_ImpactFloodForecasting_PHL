# Frequently Asked Questions (FAQ)

## Installation & Setup

### Q: How do I install PhilFlood?

**A:** See the [Quick Start Guide](../getting-started/quickstart.md#step-1-installation). TL;DR:

```bash
git clone https://github.com/rodekruis/GLOFAS_ImpactFloodForecasting_PHL.git
cd GLOFAS_ImpactFloodForecasting_PHL
mamba create -n PHLFlood -c conda-forge python=3.11 -y
mamba activate PHLFlood
pip install -e .
```

### Q: Do I need to install numpy, pandas, rasterio, etc. separately?

**A:** No! These are included by the 4 core dependencies. Installing them separately causes version conflicts. Just install: `climada`, `climada-petals`, `ipywidgets`, `pyextremes`.

### Q: I get "ImportError: No module named rasterio" on Windows

**A:** Install geo dependencies via conda-forge instead of pip:

```bash
mamba install -c conda-forge rasterio geopandas
pip install -e . --no-deps
```

### Q: How do I verify installation worked?

**A:** Run:
```bash
philflood --help
```
You should see the CLI help menu.

---

## CLIMADA & Hazard Integration

### Q: What's the status of CLIMADA integration in v0.3.0?

**A:** Notebook 2 (02_HazardOnly_Workflow_v2.ipynb) includes **working CLIMADA integration** for:
- JRC flood depth map processing (all 8 return periods)
- Regridding to regular grids
- Flood depth interpolation
- CLIMADA hazard object creation (HDF5 export)

**Not yet implemented** (v1.0):
- Full population exposure calculation
- Impact modeling (people affected)
- Operational hazard integration

See [methods-overview.md](../technical/methods-overview.md) for details.

### Q: Why do I see only 1 return period instead of 8?

**A:** This was fixed in v0.3.0. All 8 return periods now flow through processing correctly. If you're seeing this issue, you're using old code. Update to latest version with `pip install -e . --upgrade`.

### Q: Can I use CLIMADA with my own flood maps?

**A:** Yes! Implement a new adapter in `src/philflood/adapters/`. See [ARCHITECTURE.md](../technical/ARCHITECTURE.md) for pattern. Contact maintainers for guidance.

---

## EVT & Calibration

### Q: What's the difference between POT and EVT?

**A:** 
- **EVT** (Extreme Value Theory): General statistical approach for modeling rare events
- **POT** (Peaks Over Threshold): Specific EVT method using a threshold. PhilFlood uses POT.

See [GLOSSARY.md](../technical/GLOSSARY.md) and [methods-overview.md](../technical/methods-overview.md) for details.

### Q: How do I select a POT threshold?

**A:** Use the diagnostic plots in Notebook 1, Section 10:
1. **Mean Residual Life Plot**: Find inflection point where slope changes
2. **Parameter Stability Plot**: Verify GPD parameters stable above threshold
3. Choose threshold where both are satisfied

See Notebook 1 Section 10 for interactive selection.

### Q: What if I don't have 10+ years of data?

**A:** EVT requires sufficient exceedances (typically 50+) above the threshold. For < 5 years, consider:
- Lowering the threshold (more exceedances but noisier estimates)
- Using adjacent basin data
- Using expert judgment instead of data-driven threshold

Contact maintainers for guidance on specific situations.

### Q: Can I calibrate multiple basins at once?

**A:** Not yet. Current workflow is one basin per Notebook 1 run. For batch calibration, use the calibration API directly (advanced).

---

## Operational Monitoring

### Q: How often should I run monitoring?

**A:** Daily, typically 1-2 hours after GloFAS data is released (usually 06:00-12:00 UTC). See [deployment guide](../operations/deployment.md) for scheduling setup.

### Q: What if GloFAS data is unavailable?

**A:** Monitoring will fail. Set up:
- Retry logic (e.g., try every hour for 6 hours)
- Alert notifications
- Manual data download as fallback

Example retry script in [deployment guide](../operations/deployment.md).

### Q: How do I integrate monitoring with my early warning system?

**A:** Use JSON output format:

```bash
philflood monitor --basin-dir ops/configs/basins --format json --output today.json
```

Parse `today.json` and integrate with your system (email, SMS, dashboard, etc.)

### Q: What do trigger probabilities mean?

**A:** Probability that the forecast will exceed the impact threshold (e.g., 30% chance of 500K+ people affected). Higher probability = more confident trigger.

---

## Notebooks & Data

### Q: Can I run Notebook 2 without Notebook 1?

**A:** No. Notebook 2 requires outputs from Notebook 1:
- Return period NetCDF file
- Basin geometry (YAML or geojson)

Run Notebook 1 first with your basin/municipalities of interest.

### Q: What's the difference between basin mode and municipality mode?

**A:** 
- **Basin mode**: Single predefined river basin (e.g., Cagayan)
- **Municipality mode**: User selects municipalities, system computes unified AOI

See Notebook 1 Section 1 for configuration. Notebook 2 auto-detects which was used.

### Q: How much data do I need?

**A:** Minimum 5 years for EVT calibration (though 10+ recommended). Download from:
- [GloFAS Archive](https://cds.climate.copernicus.eu/) for historical data
- GloFAS website for forecasts

### Q: My Notebook 1 run is taking forever (>2 hours for 47 years)

**A:** Check memory settings in Section 3.5:
- Should auto-detect LOW_RAM_MODE if < 8 GB
- Check system logs for crashes (killed by OS)
- Consider processing year ranges separately

See [Notebook 1 Calibration Guide](../user-guides/notebook01-calibration-guide.md) for memory tuning.

---

## Troubleshooting Common Errors

### Q: "MemoryError: Unable to allocate X GB for an array"

**A:** GRIB data too large for available RAM. Solutions:
- Use streaming extraction (default, should already be enabled)
- Run on computer with more RAM
- Process year-by-year instead of all 47 years at once

See [methods-overview.md](../technical/methods-overview.md#streaming-grib-extraction-architecture).

### Q: "ModuleNotFoundError: No module named 'climada'"

**A:** Optional dependency not installed. Install it:

```bash
pip install climada>=3.0.0
```

Or use requirements-full.txt:
```bash
pip install -r requirements-full.txt
```

### Q: "ValidationError: 'threshold' must be numeric"

**A:** Basin config YAML has wrong data types. Check ops/configs/basins/your_basin.yaml:

```yaml
evt_parameters:
  threshold_m3s: 1500.0     # Must be float, not string
  shape_xi: -0.15           # Must be numeric
```

Fix formatting and retry.

### Q: "No tiles selected" in Notebook 2

**A:** JRC flood map tiles don't cover your basin. Check:
1. Basin coordinates are correct (in EPSG:4326, i.e., lat/lon)
2. Basin is within Philippines (or JRC coverage area)
3. Basin boundary in YAML is buffered slightly

Try expanding boundary:
```python
flood_zone_boundary = flood_zone_boundary.buffer(0.1)  # 0.1° buffer
```

### Q: "Cannot detect calibration mode" in Notebook 2

**A:** Notebook 1 outputs not found. Verify:
- Notebook 1 completed successfully
- `data/processed/calibration/evt_pot/` exists
- Either `Cagayan_01/` or `MUNI_SELECTION/` subfolder exists

Re-run Notebook 1 and retry.

---

## Performance & Scaling

### Q: How many basins can I monitor?

**A:** ~1 per second per core. On a 4-core machine: ~240 basins/minute sequential, ~960/minute parallel (4 workers).

Memory: ~100-150 MB per basin. Adjust `--max-workers` for available RAM.

### Q: Does PhilFlood support real-time forecasts (seasonal)?

**A:** Not yet (v1.0 feature). Currently requires pre-downloaded GRIB files.

### Q: Can I parallelize Notebook 1 calibration?

**A:** Not built-in yet. For multiple basins, run Notebook 1 separately per basin or custom Python script. Contact maintainers for guidance.

---

## Contributing & Development

### Q: How do I report a bug?

**A:** Create GitHub issue with:
- Python version & OS
- Steps to reproduce
- Error message (full traceback)
- Environment (conda env dump useful)

### Q: Can I add a new basin?

**A:** Yes! Copy and calibrate:

```bash
cp ops/configs/basins/example_basin.yaml ops/configs/basins/your_basin.yaml
# Edit your_basin.yaml with your basin parameters
python calibration/scripts/generate_basin_config_from_calibration.py ...
```

### Q: How do I contribute code?

**A:** See [CONTRIBUTING.md](../contributing/CONTRIBUTING.md) for full guide. TL;DR:

1. Fork repository
2. Create feature branch
3. Add tests for your changes
4. Submit PR

---

## Citation & Acknowledgments

### Q: How do I cite PhilFlood?

**A:** Use:

```
PhilFlood: Open-source early action flood trigger for the Philippines
Repository: https://github.com/rodekruis/GLOFAS_ImpactFloodForecasting_PHL
```

### Q: Who maintains PhilFlood?

**A:** IBF Philippines team (Red Cross Red Crescent Climate Centre). Contact via GitHub issues.

---

## Additional Resources

- [Getting Started](../getting-started/quickstart.md)
- [Methods & Theory](../technical/methods-overview.md)
- [ARCHITECTURE.md](../technical/ARCHITECTURE.md)
- [Deployment Guide](../operations/deployment.md)
- [Glossary](GLOSSARY.md)
- [Contributing Guide](../contributing/CONTRIBUTING.md)

---

**Didn't find your answer?** [Open an issue on GitHub](https://github.com/rodekruis/GLOFAS_ImpactFloodForecasting_PHL/issues/new) and we'll add it to the FAQ!
