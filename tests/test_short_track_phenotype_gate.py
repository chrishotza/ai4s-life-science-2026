"""Scientific interpretation gate: tracks with <3 observations are not phenotypes."""
from __future__ import annotations

import pandas as pd

from ai4s_phenotype import discover_phenotypes, analyze


def test_single_point_trajectory_is_not_called_non_directional():
    nodes = pd.DataFrame(
        [(0, 7, 1, 0.0, 0.0, 0.0)],
        columns=["node_id", "track_id", "t", "z", "y", "x"],
    )
    edges = pd.DataFrame(columns=["source_id", "target_id"])
    phenotype = analyze(nodes, edges)
    assert phenotype.iloc[0]["observations"] == 1
    assert phenotype.iloc[0]["phenotype_flag"] == "insufficient_temporal_evidence"


def test_short_observations_retain_numeric_cluster_for_audit_not_semantic_name():
    rows = []
    for i in range(9):
        rows.append({
            "track_id": i, "duration": i,
            "observations": (1 if i < 3 else (2 if i < 5 else 10)),
            "displacement": float(i), "path_length": 1.0+i,
            "mean_speed": 0.1*i, "directional_persistence": i/10,
            "parent_count": 0, "child_count": 0, "descendant_count": 0,
        })
    result = discover_phenotypes(pd.DataFrame(rows), n_clusters=3)
    short = result[result["observations"] < 3]
    longer = result[result["observations"] >= 3]
    assert len(short) == 5
    assert short["phenotype_cluster"].notna().all()
    assert (short["phenotype_cluster_name"] ==
            "insufficient_temporal_evidence").all()
    assert (~short["phenotype_temporal_evidence_sufficient"]).all()
    assert longer["phenotype_temporal_evidence_sufficient"].all()
    assert (~longer["phenotype_cluster_name"].eq(
        "insufficient_temporal_evidence")).all()
