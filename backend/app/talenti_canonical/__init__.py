"""
talenti_canonical — shared canonical schema constants for the Talenti platform.

This package is the single source of truth for canonical dimension names, default
weights, and the signal taxonomy used by the backend. It is intentionally kept
free of any model-service-specific logic so it can be imported by the backend
without creating a dependency on the model services.

The model services (model-service-1, model-service-2) maintain their own copies
of talenti_dimensions.py. Those copies MUST be kept in sync with the constants
exported here. When making changes:

  1. Update this package first.
  2. Update model-service-1/talenti_dimensions.py to match.
  3. Update model-service-2/talenti_dimensions.py to match.

Exports
-------
  CANONICAL_DIMENSIONS       – ordered list of the 5 dimension names
  DEFAULT_DIMENSION_WEIGHTS  – default scoring weights (sum to 1.0)
  CANONICAL_TAXONOMY_V2      – the production signal taxonomy (talenti_canonical_v2)
  ENV_VARIABLE_NAMES         – the 6 operating environment variable names
  ENV_VARIABLE_VALUES        – valid values per environment variable
"""

from app.talenti_canonical.dimensions import (
    CANONICAL_DIMENSIONS,
    DEFAULT_DIMENSION_WEIGHTS,
    ENV_VARIABLE_NAMES,
    ENV_VARIABLE_VALUES,
)
from app.talenti_canonical.taxonomy import CANONICAL_TAXONOMY_V2

__all__ = [
    "CANONICAL_DIMENSIONS",
    "DEFAULT_DIMENSION_WEIGHTS",
    "ENV_VARIABLE_NAMES",
    "ENV_VARIABLE_VALUES",
    "CANONICAL_TAXONOMY_V2",
]
