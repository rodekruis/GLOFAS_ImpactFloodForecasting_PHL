# Notebook 2 Flood Hazard Workflow Quick Start

## 5-Minute Quick Start

### Option 1: Automatic Mode Detection (Recommended)

1. **Run Notebook 1 first** (either basin or municipality mode)
2. **Open Notebook 2**
3. **Leave configuration as default**:
   ```python
   AUTO_DETECT = True
   basin_id_input = None
   run_tag_input = None
   ```
4. **Run all cells** - Everything auto-configures!

### Option 2: Manual Configuration

1. **Edit Configuration cell**:
   ```python
   AUTO_DETECT = False
   basin_id_input = "Cagayan_01"        # Your basin ID
   run_tag_input = "2026-01-19_calib-test"  # Your run tag
   ```
2. **Run all cells**

---

## What Changed?

| Aspect | Before | After |
|--------|--------|-------|
| **Configuration** | Hardcoded BASIN_ID | Auto-detects from Notebook 1 |
| **Output paths** | Always `climada_hazard/{BASIN_ID}/` | `climada_hazard/{BASIN_ID or MUNI_SELECTION}/` |
| **Tile selection** | Fixed basin extent | Uses flood_zone_boundary |
| **Mode support** | Basin only | Basin + Municipality |
| **User effort** | Manual path editing | Zero manual path editing |

---

## Mode Detection Output

### When running successfully, you'll see:

**Basin mode**:
```
✓ Detected BASIN mode with basin_id: Cagayan_01
✓ Detected mode: BASIN
  Basin ID/Selection: Cagayan_01
  Run tag: 2026-01-20_calib-test
```

**Municipality mode**:
```
✓ Detected MUNICIPALITY mode with 3 municipalities
✓ Detected mode: MUNICIPALITY
  Basin ID/Selection: MUNI_SELECTION
  Run tag: 2026-01-20_calib-test
```

---

## Output Locations

| Mode | Output Path |
|------|-------------|
| **Basin** | `data/processed/climada_hazard/Cagayan_01/{RUN_TAG}/` |
| **Municipality** | `data/processed/climada_hazard/MUNI_SELECTION/{RUN_TAG}/` |

Both modes generate:
- `climada_hazard_*.hdf5` (CLIMADA object)
- `flood-depth_all.nc` (Interpolated depths)
- `return-period_regrid_all.nc` (Regridded return periods)
- `visualizations/` folder (Maps and charts)

---

## Common Issues & Fixes

### "Return period file not found"
→ Run Notebook 1 first
→ Verify `data/processed/calibration/evt_pot/` exists

### "Cannot detect calibration mode"
→ Notebook 1 outputs missing
→ Check folder structure: should have either `Cagayan_01/` or `MUNI_SELECTION/` subfolder

### "Basin config not found"
→ Missing: `ops/configs/basins/Cagayan_01.yaml`
→ (Or your custom basin ID)

### "No tiles selected"
→ Geographic boundary might be outside JRC coverage
→ Check that your analysis region is valid

---

## Running Both Modes Back-to-Back

```python
# Run Notebook 1 in BASIN mode → generates Cagayan_01 outputs
# Then run Notebook 2:
AUTO_DETECT = True
# → Detects Cagayan_01, creates climada_hazard/Cagayan_01/... ✓

# Later, run Notebook 1 in MUNICIPALITY mode → generates MUNI_SELECTION outputs
# Then run Notebook 2 again:
AUTO_DETECT = True
# → Detects MUNI_SELECTION, creates climada_hazard/MUNI_SELECTION/... ✓

# Both outputs preserved side-by-side, no conflicts!
```

---

## Advanced: Manual Override

If auto-detection needs overriding:

```python
# Force basin mode even if MUNI_SELECTION exists:
AUTO_DETECT = False
basin_id_input = "Cagayan_01"
run_tag_input = "2026-01-19_calib-test"
```

---

## Next Steps After Notebook 2

1. **Hazard object ready**: 
   ```python
   from climada.hazard import Hazard
   haz = Hazard.from_hdf5("data/processed/climada_hazard/.../climada_hazard_*.hdf5")
   ```

2. **Visualizations generated**: Check `visualizations/` folder for maps

3. **Ready for impact modeling**: Use hazard in Notebook 3 (or custom analysis)

---

## Need Help?

See [notebook02-refactoring.md](../technical/notebook02-refactoring.md) for:
- Detailed architecture
- Complete verification checklist
- Troubleshooting guide
- Testing procedures
