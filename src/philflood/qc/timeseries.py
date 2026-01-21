from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class QCSummary:
    start_date: str
    end_date: str
    n_days_expected: int
    n_days_observed: int
    missing_pct: float
    longest_missing_streak_days: int
    constant_segment_flag: bool
    constant_segment_max_days: int
    spike_flag: bool
    spike_count: int


def qc_daily_series(series: pd.Series, expected_start: Optional[str] = None, expected_end: Optional[str] = None) -> QCSummary:
    """Basic QC for daily discharge time series.

    Flags:
    - missingness
    - long constant segments
    - suspicious spikes (robust on first differences)
    """
    if series is None or len(series) == 0:
        raise ValueError("series is empty")

    s = series.copy().sort_index()
    if not isinstance(s.index, pd.DatetimeIndex):
        raise TypeError("series must have a DatetimeIndex")

    if expected_start is None:
        expected_start = str(s.index.min().date())
    if expected_end is None:
        expected_end = str(s.index.max().date())

    expected = pd.date_range(pd.to_datetime(expected_start), pd.to_datetime(expected_end), freq="D")
    observed = s.reindex(expected)

    n_exp = int(len(expected))
    n_obs = int(observed.notna().sum())
    missing_pct = float((n_exp - n_obs) / n_exp * 100.0) if n_exp else 0.0

    # Longest missing streak
    is_missing = observed.isna().astype(int)
    streak = 0
    max_streak = 0
    for v in is_missing.values:
        if v == 1:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0

    # Constant segments (simple heuristic)
    # We flag if a rolling window has near-zero std for many consecutive days.
    win = 14
    rolling_std = observed.rolling(win, min_periods=win).std()
    const_mask = rolling_std < 1e-6
    const_run = 0
    const_run_max = 0
    for v in const_mask.fillna(False).values:
        if v:
            const_run += 1
            const_run_max = max(const_run_max, const_run)
        else:
            const_run = 0
    constant_flag = const_run_max >= 30  # 30+ days of near-constant discharge is suspicious

    # Spike detection based on robust threshold on first differences
    diffs = observed.diff().dropna()
    spike_count = 0
    spike_flag = False
    if len(diffs) > 30:
        med = np.nanmedian(diffs.values)
        mad = np.nanmedian(np.abs(diffs.values - med))
        if mad > 0:
            z = np.abs((diffs.values - med) / (1.4826 * mad))
            spike_count = int((z > 10).sum())
            spike_flag = spike_count > 0

    return QCSummary(
        start_date=str(expected[0].date()) if n_exp else expected_start,
        end_date=str(expected[-1].date()) if n_exp else expected_end,
        n_days_expected=n_exp,
        n_days_observed=n_obs,
        missing_pct=missing_pct,
        longest_missing_streak_days=int(max_streak),
        constant_segment_flag=bool(constant_flag),
        constant_segment_max_days=int(const_run_max),
        spike_flag=bool(spike_flag),
        spike_count=int(spike_count),
    )


def qc_summary_dict(summary: QCSummary) -> Dict[str, object]:
    return {
        "start_date": summary.start_date,
        "end_date": summary.end_date,
        "n_days_expected": summary.n_days_expected,
        "n_days_observed": summary.n_days_observed,
        "missing_pct": summary.missing_pct,
        "longest_missing_streak_days": summary.longest_missing_streak_days,
        "constant_segment_flag": summary.constant_segment_flag,
        "constant_segment_max_days": summary.constant_segment_max_days,
        "spike_flag": summary.spike_flag,
        "spike_count": summary.spike_count,
    }
