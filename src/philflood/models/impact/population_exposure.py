"""Population exposure and aggregation utilities.

This module contains helper functions to compute the number of people
affected by flood depths exceeding various thresholds and to
aggregate those counts by administrative units.  It was extracted
from the calibration notebooks to facilitate reuse in both notebook
workflows and automated pipelines.

Functions
---------
aggregate_affected_population(pop, depth, admin_id_raster, thresholds_m, id_to_name)
    Compute affected population per administrative unit at multiple
    depth thresholds.
"""

from __future__ import annotations

from typing import Dict, Iterable, List

import numpy as np
import pandas as pd


def aggregate_affected_population(
    pop: np.ndarray,
    depth: np.ndarray,
    admin_id_raster: np.ndarray,
    thresholds_m: Iterable[float],
    id_to_name: Dict[int, str],
) -> pd.DataFrame:
    """Aggregate affected population by administrative ID for multiple depth thresholds.

    Parameters
    ----------
    pop : numpy.ndarray
        2‑D array of population counts (e.g., WorldPop) aligned to a
        geographic raster.
    depth : numpy.ndarray
        2‑D array of flood depths (in metres) aligned to ``pop``.
    admin_id_raster : numpy.ndarray
        2‑D array of administrative unit identifiers aligned to
        ``pop`` and ``depth``.  Missing values should be NaN.
    thresholds_m : iterable of float
        Sequence of depth thresholds (in metres) for which to count
        affected population.
    id_to_name : dict[int, str]
        Mapping from administrative ID to human‑readable name.  If
        an ID is not found, the integer ID will be used as the name.

    Returns
    -------
    pandas.DataFrame
        DataFrame with columns ``adm_id``, ``adm_name``,
        ``depth_thr_m`` and ``affected_pop``.  Each row corresponds to
        one administrative unit and one depth threshold.
    """
    ids_flat = admin_id_raster.reshape(-1)
    pop_flat = pop.reshape(-1)
    depth_flat = depth.reshape(-1)
    rows: List[Dict[str, object]] = []
    for thr in thresholds_m:
        mask = depth_flat >= thr
        counts: Dict[int, float] = {}
        for id_, p in zip(ids_flat[mask], pop_flat[mask]):
            if isinstance(id_, float) and np.isnan(id_):
                continue
            try:
                key = int(id_)
            except Exception:
                continue
            counts[key] = counts.get(key, 0.0) + float(p)
        for id_, c in counts.items():
            rows.append(
                {
                    "adm_id": id_,
                    "adm_name": id_to_name.get(id_, str(id_)),
                    "depth_thr_m": thr,
                    "affected_pop": c,
                }
            )
    df = pd.DataFrame(rows)
    return df