"""Legacy and archived modules (v0.xxx < 0.3.0 or experimental features).

⚠️ **DEPRECATION WARNING**

This directory contains archived code that is no longer part of the
active codebase:

- **glofas.py**: Legacy non-v4 GloFAS interface. Use
  `philflood.adapters.glofas_grib_v4` instead.
  
- **glofas_grib_streaming.py**: Legacy streaming implementation.
  Functionality integrated into `glofas_grib_v4.py`.
  
- **climada_river.py**: CLIMADA integration placeholder (v1.0 feature).
  Placeholder, not yet functional.
  
- **hazard_maps.py**: Hazard map generation (v1.0 feature).
  Not yet implemented for v0.3.0.
  
- **aoi.py**: Area-of-interest utilities for population weighting.
  Removed February 2026; functionality deprecated.
  
- **worldpop.py**: WorldPop raster integration.
  Removed February 2026; population weighting deprecated.

**Note**: `pipelines/monitoring.py` is now a v1.0 placeholder stub that raises
NotImplementedError. It remains in the main codebase to prevent import errors,
but is not functional until v1.0 (Q2 2026).

**How to migrate:**

If you have code importing from archived modules:

```python
# ❌ OLD (archive usage - don't do this)
from philflood.adapters.glofas import legacy_function

# ✅ NEW (production module)
from philflood.adapters.glofas_grib_v4 import open_grib_dataset
```

**Questions?**

- Check ARCHITECTURE.md for overview of current structure
- See MIGRATION.md for migration guide (v0.2 → v0.3)
- Review ops/configs/ for example basin configurations

These files are kept for reference only. Do not import from _archive/
in production code.
"""

__all__ = []  # Intentionally empty - archive is not part of public API
