"""
Tracked canonical scoring primitives used by the backend.

The backend package is the authoritative in-repo source for canonical
dimensions, default weights, environment enums, and deterministic requirement
helpers. Model services may carry local copies for runtime isolation, but the
backend imports should point here.
"""

from app.talenti_canonical.dimensions import (
    ARCHETYPE_FATAL_RISKS,
    CANONICAL_DIMENSIONS,
    DEFAULT_DIMENSION_WEIGHTS,
    DimensionRequirement,
    ENV_VARIABLE_NAMES,
    ENV_VARIABLE_VALUES,
    compute_dimension_requirements,
    get_archetype_fatal_risks,
)
from app.talenti_canonical.taxonomy import CANONICAL_TAXONOMY_V2

__all__ = [
    "ARCHETYPE_FATAL_RISKS",
    "CANONICAL_DIMENSIONS",
    "CANONICAL_TAXONOMY_V2",
    "DEFAULT_DIMENSION_WEIGHTS",
    "DimensionRequirement",
    "ENV_VARIABLE_NAMES",
    "ENV_VARIABLE_VALUES",
    "compute_dimension_requirements",
    "get_archetype_fatal_risks",
]
