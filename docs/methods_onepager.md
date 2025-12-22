# Methods Overview

This document provides a concise overview of the methodology implemented in this repository.  It is intended for practitioners and decision makers who want to understand how the flood trigger is constructed and why certain choices were made.

## Calibration Phase

During calibration we analyse historical discharge data from GloFAS to identify **extreme flow** events and fit a statistical model to their magnitudes.  We choose a high discharge threshold using diagnostic plots such as the *mean residual life* and *parameter stability* plots.  We decluster the time series to ensure that peaks are independent and fit a **Generalised Pareto Distribution (GPD)** to the exceedances.  The fitted shape and scale parameters, along with the estimated rate of exceedances, are stored in a configuration file.

We then convert simulated discharge peaks into flood depths using the open-source **CLIMADA fluvial flood model**.  Global river flood hazard maps from the **JRC Global Flood Model** provide depth layers for discrete return periods; we interpolate between these layers based on the return period of each synthetic discharge peak.  Exposure data (population grids) are overlaid on the depth maps, and a simple stepwise vulnerability function counts people as affected when water depth exceeds a threshold.  Aggregating impacts across simulated years produces **AEP/OEP curves** and the **AAPA** metric used in risk profiling.

## Operational Phase

In real time we ingest **GloFAS ensemble forecasts** for the calibrated GloFAS points and apply the same CLIMADA workflow to estimate the probability distribution of impacts over the forecast horizon.  We evaluate whether the probability of exceeding a pre-defined **impact threshold** is greater than a chosen **probability threshold** (e.g. 30%).  If both the expected number of people affected and the probability exceed their respective thresholds within the allowed lead time, the trigger activates.

## Reproducibility

All intermediate parameters (EVT threshold, GPD parameters, vulnerability settings and trigger thresholds) are stored in YAML files under `ops/configs/`.  The operational pipeline reads these files and uses the fixed parameters to ensure that decisions are reproducible and transparent.  Calibration notebooks contain detailed explanations and plots demonstrating how parameters were chosen.