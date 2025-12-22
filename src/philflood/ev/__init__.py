"""Extreme value modelling utilities.

This subpackage wraps the functionality of external libraries (e.g.
``pyextremes``) and provides project‑specific helper functions for
extracting peaks, fitting GPDs, generating synthetic events and
diagnostic plotting.  By abstracting these operations behind our own
API, we can easily swap or upgrade the underlying library without
changing the rest of the codebase.
"""

__all__ = [
    "peaks_over_threshold",
    "gpd_fit",
    "synthetic_events",
]