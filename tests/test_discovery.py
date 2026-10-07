import pandas as pd

from ai4s_phenotype import discover_phenotypes


def test_discovery_assigns_three_behavioral_groups():
    rows = []
    for i in range(3):
        rows.append(
            {
                "track_id": i,
                "duration": 10,
                "observations": 11,
                "displacement": 1.0,
                "path_length": 1.2,
                "mean_speed": 0.1,
                "directional_persistence": 0.85,
                "parent_count": 0,
                "child_count": 0,
                "descendant_count": 0,
            }
        )
    for i in range(3, 6):
        rows.append(
            {
                "track_id": i,
                "duration": 10,
                "observations": 11,
                "displacement": 8.0,
                "path_length": 8.5,
                "mean_speed": 0.8,
                "directional_persistence": 0.9,
                "parent_count": 0,
                "child_count": 0,
                "descendant_count": 0,
            }
        )
    for i in range(6, 9):
        rows.append(
            {
                "track_id": i,
                "duration": 10,
                "observations": 11,
                "displacement": 3.0,
                "path_length": 12.0,
                "mean_speed": 0.4,
                "directional_persistence": 0.25,
                "parent_count": 0,
                "child_count": 0,
                "descendant_count": 0,
            }
        )

    result = discover_phenotypes(pd.DataFrame(rows), n_clusters=3)

    assert result["phenotype_cluster"].nunique() == 3
    assert result["phenotype_cluster_name"].notna().all()
