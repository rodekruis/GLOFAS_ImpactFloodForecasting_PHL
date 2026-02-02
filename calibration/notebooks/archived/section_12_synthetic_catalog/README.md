# Section 12: Synthetic Event Catalog (ARCHIVED)

## Reason for Archival

This section has been **deprecated** and replaced with a more efficient formula-based approach in **Section 11C**.

### Old Approach (Section 12 - Archived)
- Generated ~350,000 synthetic flood events per gauge using Monte Carlo simulation
- Memory-intensive: Required storing large event catalogs on disk
- Computationally expensive: ~5-10 seconds per gauge for event generation
- Indirect: Return levels computed from empirical distribution of synthetic events

### New Approach (Section 11C - Active)
- **Formula-based:** Direct computation from POT/GPD parameters using analytical formula
  - $q_T = u + \frac{\sigma}{\xi}[(\lambda T)^\xi - 1]$ for $\xi \neq 0$
  - $q_T = u + \sigma \ln(\lambda T)$ for $\xi \approx 0$
- **Bootstrap uncertainty:** 20 iterations with resampling for confidence intervals
- **Fast:** <1 second per gauge (5-10x speedup)
- **Memory-efficient:** Output is ~5KB per gauge (vs. ~1MB for synthetic catalogs)
- **Deterministic:** Given fixed random seed, results are reproducible

## Migration Guide

If you need to reproduce old synthetic catalog results:

1. Use this archived notebook section with the original configuration
2. Set `SIM_YEARS = MAX_RETURN_PERIOD_YEARS * YEARS_PER_RETURN_PERIOD`
3. Run Section 12A-E sequentially

## Contents

This archive contains the complete Section 12 code cells from the calibration workflow notebook:
- **12A:** Configuration for synthetic event generation
- **12B:** Monte Carlo event generation with Poisson/GPD sampling
- **12C:** Summary statistics and validation
- **12D:** Presentation-quality figures for stakeholders
- **12E:** Final summary and next steps

## Archived Date
- **Date:** 2026-01-XX (insert current date)
- **Reason:** Replaced with formula-based bootstrap approach (Section 11C)
- **Status:** Functional but no longer actively maintained

## Contact
For questions about this archival decision, see `IMPLEMENTATION_PROGRESS.md` in the project root.
