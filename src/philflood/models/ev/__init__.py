"""Extreme value modelling utilities.

This subpackage wraps the functionality of external libraries (e.g.
``pyextremes``) and provides project‑specific helper functions for
threshold selection, peaks extraction, and GPD fitting.  By abstracting
these operations behind our own API, we can easily swap or upgrade the
underlying library without changing the rest of the codebase.
"""

__all__ = [
    "threshold_selection",
    "compute_mrl",
]

from philflood.models.ev.threshold_selection import compute_mrl  # noqa: E402