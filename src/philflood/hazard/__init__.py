"""Hazard generation wrappers.

This subpackage contains functions to convert discharge values and
return periods into spatial flood depth maps using the CLIMADA
framework and open hazard layers.  The code here abstracts away
CLIMADA-specific calls so that the main workflow remains clean.  In
future you could swap CLIMADA for another flood model by rewriting
these wrappers.
"""

__all__ = ["climada_driver"]