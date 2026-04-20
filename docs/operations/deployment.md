# Deployment Guide

> **Status: Not yet implemented.**
> `run_monitoring()` in `src/philflood/pipelines/monitoring.py` currently raises
> `NotImplementedError`. No scheduled monitoring, Docker setup, or cloud deployment
> exists yet. This page is a placeholder — it will be filled in once the
> operational trigger pipeline is built.

---

## What Exists Right Now

The CLI entrypoint is wired up and can be called:

```bash
philflood monitor --basin ops/configs/basins/Cagayan_01.yaml
```

The `TriggerDecision` dataclass in `src/philflood/pipelines/monitoring.py` defines
the output structure. However, calling the command above will raise
`NotImplementedError` until `run_monitoring()` is implemented.

The `ops/pipeline/run_monitoring_once.py` script provides a minimal wrapper around
the CLI that can be used as a starting pattern once monitoring is working.

## What Needs to Be Built First

See [Trigger Pipeline Handover](trigger-pipeline-handover.md) for everything Phuoc
needs to implement the operational pipeline: the three-tier detection algorithm,
calibration artifacts required at runtime, reusable source modules, and the full
implementation checklist for `run_monitoring()`.

## Architecture Decision (Left to Phuoc)

Once `run_monitoring()` is working, it can be scheduled using whatever mechanism
fits the deployment environment:

- Windows Task Scheduler (batch script wrapping the CLI)
- Linux cron
- Azure Function (timer trigger)
- Prefect / Airflow DAG
- Any other orchestrator

No architecture is prescribed here — the choice depends on where this runs in
production. The Azure ML job definition in `ops/azure/job_reforecast_month.yml`
shows one pattern for Azure-based batch jobs (used for the reforecast pipeline),
but it is not yet configured for any specific workspace.

## What This Document Should Contain (Once Built)

Fill in these sections after `run_monitoring()` is implemented and tested:

- [ ] Prerequisites and environment setup for production
- [ ] Chosen scheduling mechanism with actual working commands
- [ ] Output format and integration with downstream early warning system (510 IBF)
- [ ] Log management and rotation
- [ ] Alert notifications — who gets alerted, at which tier, and how
- [ ] Health checks and failure recovery procedure
- [ ] Rollback and re-run instructions

---

**Questions?** Contact David Uruena — duruenaramirez@redcross.nl
