"""Motility-only discovery: scientific QC, isolation from track-age confounding."""
from __future__ import annotations

import pandas as pd
import pytest

from ai4s_phenotype import PhenotypeDiscoveryModel, discover_phenotypes
from ai4s_phenotype.discovery import (
    FEATURE_SCHEMA_VERSION, MOTION_ONLY_FEATURES, MOTION_ONLY_SCHEMA_VERSION,
)


def _profiles() -> pd.DataFrame:
    rows = []
    for i in range(12):
        rows.append({
            "track_id": i,
            "observations": 3 + i * 2,
            "duration": 2 + i * 2,
            "mean_speed": (0.1 if i < 4 else 0.8 if i < 8 else 0.4) + .01 * i,
            "directional_persistence": (
                0.85 if i < 4 else 0.9 if i < 8 else 0.2
            ),
            "path_length": 4.0 + i * 30,
            "displacement": 1.0 + i,
            "parent_count": i % 3,
            "child_count": 0,
            "descendant_count": 0,
        })
    return pd.DataFrame(rows)


def test_motility_only_fit_excludes_observation_and_lineage_columns():
    data = _profiles()
    model = PhenotypeDiscoveryModel.fit(data, feature_set="motion_only")
    assert model.feature_names == MOTION_ONLY_FEATURES
    assert model.feature_schema_version == MOTION_ONLY_SCHEMA_VERSION
    assert model.feature_set == "motion_only"
    first = model.transform(data)
    changed = data.copy()
    for col in ("duration", "observations", "path_length", "displacement",
                "parent_count", "child_count", "descendant_count"):
        changed[col] = changed[col] * 10 + 100
    second = model.transform(changed)
    assert first["phenotype_cluster"].tolist() == second["phenotype_cluster"].tolist()
    assert first["phenotype_feature_set"].eq("motion_only").all()
    assert first["phenotype_temporal_evidence_sufficient"].all()
    assert first["phenotype_cluster_name"].notna().all()


def test_fit_refuses_short_tracks_without_temporal_evidence():
    data = _profiles()
    data.loc[0, "observations"] = 2
    with pytest.raises(ValueError, match=">=3 observations"):
        PhenotypeDiscoveryModel.fit(data, feature_set="motion_only")
    with pytest.raises(ValueError, match=">=3 observations"):
        discover_phenotypes(data, feature_set="motion_only")


def test_default_discovery_remains_backward_compatible():
    data = _profiles()
    original = discover_phenotypes(data)
    explicit = discover_phenotypes(data, feature_set="trajectory_lineage")
    assert original.equals(explicit)
    model = PhenotypeDiscoveryModel.fit(data)
    assert model.feature_schema_version == FEATURE_SCHEMA_VERSION
    assert len(model.feature_names) == 9


def test_motility_only_does_not_claim_biological_states():
    result = discover_phenotypes(_profiles(), feature_set="motion_only")
    assert result["phenotype_cluster"].nunique() == 3
    # Legacy names are descriptive, not ground-truth mitosis/perturbation labels.
    assert set(result["phenotype_cluster_name"]).issubset({
        "high_motility", "exploratory_motion", "persistent_or_stable",
    })


def test_unsupported_discovery_feature_set_rejected():
    with pytest.raises(ValueError, match="feature_set"):
        PhenotypeDiscoveryModel.fit(_profiles(), feature_set="oracle_labels")


def test_motion_only_refuses_missing_observation_counts():
    data = _profiles().drop(columns=["observations"])
    with pytest.raises(ValueError, match="requires observations"):
        PhenotypeDiscoveryModel.fit(data, feature_set="motion_only")
