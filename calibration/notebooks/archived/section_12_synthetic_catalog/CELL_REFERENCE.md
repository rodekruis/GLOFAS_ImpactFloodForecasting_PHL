# Section 12 Cell Reference

This document lists the Cell IDs from Section 12 for reference.

## Section 12 Cells (To Be Deleted from Main Notebook)

From the notebook `01_evt_pot_calibration_workflow.ipynb`:

1. **Cell #VSC-fd4980cb** (Markdown) - Lines ~1845-1852
   - Section header: "## 12) Synthetic Event Catalog Generation"
   
2. **Cell #VSC-1b70fe6d** (Python) - Lines ~1855-1920
   - Section 12A: Configuration for synthetic event generation
   - Variables: SIM_YEARS, MAX_RETURN_PERIOD_YEARS, RETURN_PERIODS_REPORT, etc.
   
3. **Cell #VSC-236d8b24** (Python) - Lines ~1923-2222
   - Section 12B: Main synthetic event generation loop
   - Monte Carlo sampling with Poisson/GPD
   
4. **Cell #VSC-1153f066** (Python) - Lines ~2216-2236
   - Section 12B continuation: Return level computation
   
5. **Cell #VSC-cf918783** (Python) - Lines ~2239-2390
   - Section 12C: Summary statistics and catalog aggregation
   
6. **Cell #VSC-622c2b3b** (Python) - Lines ~2393-2461
   - Section 12D/E: Summary and deliverables listing
   
7. **Cell #VSC-e8accf50** (Python) - Lines ~2464-2501
   - Section 12: Figure 5 - Return level curves (enhanced)
   
8. **Cell #VSC-0b64b820** (Python) - Lines ~2504-2618
   - Section 12: Figure 6 - Deep dive single station analysis

## Total: 8 cells to delete

## Replacement

These cells are replaced by:
- **Section 11C** (Cell #VSC-5d5f3809): Bootstrap return levels (formula-based)
- **Section 13** (Cell #VSC-72401417): CLIMADA-compatible NetCDF generation

## Deletion Strategy

Use notebook edit tools to delete cells in reverse order (from bottom to top) to preserve line numbers:
1. Delete Cell #VSC-0b64b820
2. Delete Cell #VSC-e8accf50
3. Delete Cell #VSC-622c2b3b
4. Delete Cell #VSC-cf918783
5. Delete Cell #VSC-1153f066
6. Delete Cell #VSC-236d8b24
7. Delete Cell #VSC-1b70fe6d
8. Delete Cell #VSC-fd4980cb

After deletion, insert a markdown cell explaining the removal and pointing to the archive.
