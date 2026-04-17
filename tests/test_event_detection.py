"""Unit tests for event detection utilities."""

import unittest

import numpy as np
import pandas as pd

from philflood.utils.event_detection import auto_select_threshold


class TestAutoSelectThreshold(unittest.TestCase):
    """Tests for auto_select_threshold edge-case handling."""

    @classmethod
    def setUpClass(cls):
        dates = pd.date_range("2020-01-01", periods=365, freq="D")
        np.random.seed(123)
        values = 100 + np.random.normal(0, 10, len(dates))
        cls.series = pd.Series(values, index=dates)

    def test_empty_candidates_raises(self):
        with self.assertRaisesRegex(
            ValueError, r"q_candidates must contain at least one quantile in \[0, 1\]\."
        ):
            auto_select_threshold(self.series, [], decluster_days=3, min_events=2, max_events=20)

    def test_out_of_range_candidates_raise(self):
        with self.assertRaises(ValueError):
            auto_select_threshold(
                self.series, [-0.1, 0.95], decluster_days=3, min_events=2, max_events=20
            )
        with self.assertRaises(ValueError):
            auto_select_threshold(
                self.series, [0.90, 1.1], decluster_days=3, min_events=2, max_events=20
            )

    def test_nan_candidates_raise(self):
        with self.assertRaisesRegex(ValueError, r"must be finite quantiles in \[0, 1\]"):
            auto_select_threshold(
                self.series, [0.90, float("nan")], decluster_days=3, min_events=2, max_events=20
            )

    def test_non_numeric_candidates_raise(self):
        with self.assertRaisesRegex(ValueError, r"must contain only numeric quantiles"):
            auto_select_threshold(
                self.series, ["0.90", "not-a-number"], decluster_days=3, min_events=2, max_events=20
            )

    def test_valid_candidates_still_work(self):
        threshold = auto_select_threshold(
            self.series, [0.90, 0.95, 0.99], decluster_days=3, min_events=2, max_events=20
        )
        self.assertTrue(np.isfinite(threshold))
        self.assertGreaterEqual(threshold, float(self.series.min()))
        self.assertLessEqual(threshold, float(self.series.max()))


if __name__ == "__main__":
    unittest.main()
