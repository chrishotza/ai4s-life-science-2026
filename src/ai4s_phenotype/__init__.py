"""AI4S temporal cellular phenotype analysis."""

from .discovery import (
    FEATURE_SCHEMA_VERSION,
    PhenotypeDiscoveryModel,
    discover_phenotypes,
    fit_phenotype_model,
)
from .phenotype import analyze
from .cohort import CohortComparison, compare_cohorts
from .state_probe import TemporalStateProbe
from .causal import (causal_shape_motion_features, STATIC_FEATURES,
                     MOTION_FEATURES, HISTORY_FEATURES)
from .confidence import gate_phenotype_profiles, artifact_summary

__all__ = [
    "analyze",
    "discover_phenotypes",
    "fit_phenotype_model",
    "PhenotypeDiscoveryModel",
    "FEATURE_SCHEMA_VERSION",
    "CohortComparison",
    "compare_cohorts",
    "causal_shape_motion_features",
    "TemporalStateProbe",
    "STATIC_FEATURES",
    "MOTION_FEATURES",
    "HISTORY_FEATURES",
    "gate_phenotype_profiles",
    "artifact_summary",
]
