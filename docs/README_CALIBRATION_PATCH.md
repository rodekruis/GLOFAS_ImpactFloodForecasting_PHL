# PhilFlood EVT/POT Calibration Patch

This patch adds an **operator-friendly, end-to-end EVT/POT calibration workflow** aligned with the locked methodology:

- Select HydroBASINS L12 impact units via either:
  - Municipality AOI (population-weighted centroid + 5 km geodesic buffer), or
  - Context basin polygon (from existing basin YAML)
- Assign each selected L12 to a **virtual gauge**: L12 pour point -> nearest GloFAS v4 grid cell
- Detect/flag **collisions** (multiple L12 mapping to the same GloFAS cell)
- Extract discharge time series from **GloFAS v4 consolidated discharge GRIB** (cached)
- Extract declustered POT events using **pyextremes EVA** and compute Poisson rate λ

## What to copy into your repo

Copy these folders (merge if they already exist):

- `src/philflood/` (new modules; additive)
- `notebooks/01_evt_pot_calibration_workflow.ipynb` (new canonical calibration notebook)
- `ops/configs/run_specs/run_spec_template.yaml` (optional)
- `docs/README_CALIBRATION_PATCH.md` (this file)

## Outputs

The notebook writes run-scoped outputs under:

```
data/processed/calibration/evt_pot/{basin_id}/{run_tag}/
```

and caches time series under:

```
data/processed/glofas/v4/{area_name}/timeseries/virtual_gauges/
```

## Dependencies

Minimum required packages (most are likely already in your env):

- geopandas, shapely, rasterio, pyproj
- xarray, cfgrib (plus ECMWF ecCodes)
- pandas, numpy
- pyextremes

If `ipywidgets` is available, the notebook enables interactive gauge browsing; otherwise it falls back to non-interactive cells.
