# Philippines Flood Trigger Project

Welcome! This repository contains all of the code, data templates and documentation needed to develop an open‑source early action flood trigger for the Philippines.

## Structure

The project is divided into two clearly defined layers:

1. **Calibration (`calibration/`)** – notebooks and scripts used to explore, test and calibrate the models. This is your *playground*; it contains exploratory notebooks for fitting extreme value theory (EVT) models, tuning hazard/impact assumptions and assessing risk metrics. Outputs from calibration (e.g. fitted parameters, selected thresholds, vulnerability settings) are written into machine‑readable YAML files under `ops/configs/`, together with human‑readable calibration reports in `docs/`.

2. **Operations (`ops/`)** – a lean, reproducible pipeline that reads the pre‑calibrated configuration and uses it to monitor real‑time forecasts and issue trigger decisions. The operational code never re‑fits statistical models; it simply applies the calibrated parameters to new forecast data.

All reusable code lives in `src/philflood/`, which is organised by functional domain. Calibration notebooks and operational scripts import from this package. By keeping code in a package rather than in notebooks, we avoid duplication when scaling up to multiple basins or countries.

## Getting Started

1. **Clone the repository** and install the Python dependencies (see `requirements.txt` if provided). The recommended way is to set up a virtual environment and install packages using pip.

2. **Explore the calibration notebooks** under `calibration/notebooks/`. Each notebook focuses on one step of the modelling pipeline and includes rich markdown explanations aimed at humanitarian practitioners. For example:

   * `01_evt_threshold_basin_X.ipynb` – shows how to load a GloFAS time series, explore the extremes, and choose an appropriate POT threshold using diagnostic plots.
   * `02_evt_threshold_basin_X_gpd_fit.ipynb` – fits a Generalised Pareto Distribution to the peaks over threshold, evaluates the fit and summarises the results.
   * `10_synthetic_impacts_AEP_OEP.ipynb` – demonstrates how to generate synthetic events, convert them into flood impacts using CLIMADA and compute AEP/OEP/AAPA curves.

   When you run these notebooks, fill in the placeholder code with your own functions from `src/philflood/` and document your decisions using the markdown cells provided.

3. **Write calibration outputs to YAML** using the script `calibration/scripts/generate_basin_config_from_calibration.py`. This will collect the EVT parameters, hazard/impact settings and trigger thresholds into a single `BasinConfig` file (see `ops/configs/basins/example_basin.yaml`).

4. **Run the operational pipeline** via `ops/pipeline/run_monitoring_once.py`, which reads the YAML configuration, fetches forecast data, computes predicted impacts and evaluates the trigger conditions. For automated monitoring, use `ops/pipeline/run_monitoring_scheduled.py` to schedule recurring checks.

## Contributing

This repository follows common Python best practices. New functions should live in the appropriate module under `src/philflood/` and include docstrings describing inputs, outputs and context. If you add new notebooks or scripts, please explain what they do and who the intended audience is. All contributions should consider the needs of humanitarian practitioners: clarity, transparency and reproducibility are paramount.

Please see the `docs/` folder for additional background, references and detailed methodology descriptions.
