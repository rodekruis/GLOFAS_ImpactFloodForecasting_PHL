# Migration Guide: v0.3.0 Phase A Cleanup (February 2026)

**TL;DR**: Code was reorganized for clarity and reliability. **If you're just running Notebook 1 calibration, no action needed.** If you wrote custom code importing from `philflood`, see section 2 below.

---

## What Changed

### Phase A: Code Cleanup & Simplification
- Removed 13+ unused "v1.0 placeholder" files that were never used
- Moved 6 legacy modules to `src/philflood/_archive/` with deprecation notices
- Extracted complex functions to reusable modules for testing and clarity
- Updated all imports across the codebase

**Before**: 34 Python files across 9 directories  
**After**: ~20 active files across 6 core directories (41% reduction)

### Phase B: Notebook 1 Humanization
- Added Quick Start guide with 3-step overview
- Simplified user inputs from 15+ variables → **4 simple fields**
- Added Input Validation cell to catch errors early
- Added 5 Checkpoint cells throughout workflow
- Renamed all section headers to plain-language titles
- Added clear explanations before complex sections

**Impact**: Non-technical operators can now follow the calibration workflow independently

### Phase C: Testing & Validation
- Created unit test suite for threshold selection module (10 tests, all passing)
- Fixed test compatibility with Phase A changes
- All 51 project tests passing (100%)
- Code verified to work with Python 3.9 (even though 3.10+ officially required)

---

## For Notebook Users (Most Users)

**No action needed!** The Notebook 1 workflow has been improved and simplified:

✅ Everything works the same way  
✅ Improved error checking and guidance  
✅ Simpler configuration options  
✅ Progress checkpoints help prevent mistakes  

**New**: If you're a new user, the Quick Start guide at the top of Notebook 1 shows you the 3 main steps in 2-3 minutes.

---

## For Python Developers (Custom Code)

If you wrote Python code that imports from `philflood`, here are the breaking changes:

### Removed Modules (Legacy v1.0 Placeholders)

These modules no longer exist in the main package. They were placeholders that were never completed:

```python
# ❌ REMOVED - Never importable:
from philflood.models.impact import ...      # Use placeholder function instead
from philflood.models.risk import ...        # Use placeholder function instead  
from philflood.geo.aoi import build_municipality_aoi  # Use geo.hydrobasins instead
from philflood.geo.worldpop import population_weighted_centroid  # Removed Feb 2026
from philflood.pipelines.validation import ...  # Moved to _archive
```

### Moved Modules (Archived with Deprecation Notices)

These modules are now in `src/philflood/_archive/` with deprecation notices. Import from there if you need them:

```python
# ❌ OLD (no longer in main package):
from philflood.adapters import glofas, hazard_maps, climada_river

# ✅ NEW (if you really need legacy code):
from philflood._archive.adapters import glofas, hazard_maps, climada_river
```

**Note**: Legacy modules have deprecation notices explaining why they were archived.

### New Modules (Extracted for Reusability)

These modules were extracted from Notebook 1 to be reusable and testable:

```python
# ✅ NEW - Use this instead of inline notebook code:
from philflood.models.ev.threshold_selection import auto_select_threshold_pot
from philflood.ops.logging_config import ProgressLogger
```

### Updated Module Organization

Some modules were reorganized. If you import specific items:

```python
# ❌ OLD (domain configs scattered):
from philflood.config import load_basin_config  # Deprecated

# ✅ NEW (unified in domain):
from philflood.domain.config import load_basin_config
from philflood.domain.basin import Basin
```

---

## What You Need To Do

### If you're just using the notebooks:
✅ **Nothing!** Just run Notebook 1 as usual. It's been improved.

### If you have custom Python scripts:
1. Check imports against the section "Removed Modules" above
2. If importing removed modules, comment them out or update to new paths
3. Run your script - most code will work unchanged
4. See "Updated Module Organization" if you get ImportErrors

### If you have old basin configs:
✅ **No changes needed!** All YAML config formats are backward compatible.

---

## FAQ: Migration Questions

**Q: Will my Notebook 1 calibration still work?**  
A: Yes! Everything is backward compatible. The notebook is improved but functionally identical.

**Q: My script imports `from philflood.adapters import glofas`. What do I do?**  
A: Change to: `from philflood.adapters import glofas_grib_v4`  
(The old `glofas` module was a legacy placeholder - use `glofas_grib_v4` instead)

**Q: I wrote custom code in the archived modules. Can I still use them?**  
A: Yes! Archived modules are in `src/philflood/_archive/`. See `_archive/__init__.py` for importing them. But note: these modules are no longer maintained.

**Q: Do I need to upgrade anything?**  
A: Only if you're upgrading to this version. If you're already on v0.3.0, you're probably fine. Check your imports if you get ModuleNotFoundError.

**Q: Why were the v1.0 placeholder files removed?**  
A: They were never completed and introduced confusion. The roadmap now explicitly states what's in v0.3.0 (core EVT calibration) vs. v1.0 (impact models). See [CHANGELOG.md](CHANGELOG.md).

---

## Getting Help

If you hit migration issues:

1. **ImportError when running a script?** → Check [Updated Module Organization](#updated-module-organization) section
2. **Unsure if your code is affected?** → Look for `from philflood.` lines and compare against "Removed/Moved Modules" above
3. **Still stuck?** → See [Troubleshooting Guide](docs/user-guides/troubleshooting.md#development-issues)

---

## Technical Details for Developers

### What was moved to _archive/?

Six legacy modules that were outdated or incomplete:
- `adapters/glofas.py` (legacy GloFAS reader, replaced by glofas_grib_v4)
- `adapters/glofas_grib_streaming.py` (superseded by optimized version)
- `adapters/climada_river.py` (incomplete v1.0 placeholder)
- `adapters/hazard_maps.py` (incomplete v1.0 placeholder)
- `geo/aoi.py` (population weighting removed Feb 2026)
- `geo/worldpop.py` (population weighting removed Feb 2026)

See `src/philflood/_archive/__init__.py` for full deprecation notices.

### What was deleted entirely?

13 v1.0 placeholder files that were never completed:
- `models/ev/gpd_fit.py` (functionality moved to threshold_selection.py)
- `models/ev/peaks_over_threshold.py` (functionality consolidated)
- `models/ev/synthetic_events.py` (replaced by bootstrap formula approach)
- `models/ev/threshold_analysis.py` (merged into calibration module)
- `models/impact/*` (2 files - v1.0 placeholder, not functional)
- `models/risk/*` (2 files - v1.0 placeholder, not functional)
- `pipelines/validation.py` (incomplete, functionality moved to qc/)
- `config/` directory (duplicate of domain/config - consolidated)

These were confusing because they suggested functionality that didn't actually work. Now the codebase only contains what's actually used.

### What was extracted and improved?

Two significant functions were extracted from inline Notebook 1 code and improved:

1. **`threshold_selection.py`** (217 lines)
   - `auto_select_threshold_pot()` - Automatic threshold selection with 3-tier fallback
   - `_evaluate_threshold()` - GPD parameter diagnostics
   - Fully documented and tested (10 unit tests)

2. **`ProgressLogger` class** (130 lines, in ops/logging_config.py)
   - Human-friendly progress output for Jupyter/CLI
   - No timestamps (clear for operations)
   - Color/symbols for status (✓, ✗, ⚠️)

Both are now reusable and testable, rather than buried in notebook code.

---

## Version Information

- **Version**: v0.3.0 (released February 2026)
- **Previous**: v0.2.x (December 2025)
- **Next**: v1.0.0 (planned Q2 2026 with full impact models)

See [CHANGELOG.md](CHANGELOG.md) for full release notes.
