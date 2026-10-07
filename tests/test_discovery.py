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


def test_discovery_model_can_transform_a_new_dataset_without_refitting():
    from ai4s_phenotype import fit_phenotype_model

    base = pd.DataFrame(
        [
            {"track_id": 0, "duration": 10, "observations": 11, "displacement": 1.0, "path_length": 1.2, "mean_speed": 0.1, "directional_persistence": 0.9, "parent_count": 0, "child_count": 0, "descendant_count": 0},
            {"track_id": 1, "duration": 10, "observations": 11, "displacement": 8.0, "path_length": 8.5, "mean_speed": 0.8, "directional_persistence": 0.9, "parent_count": 0, "child_count": 0, "descendant_count": 0},
            {"track_id": 2, "duration": 10, "observations": 11, "displacement": 3.0, "path_length": 12.0, "mean_speed": 0.4, "directional_persistence": 0.25, "parent_count": 0, "child_count": 0, "descendant_count": 0},
        ]
    )
    model = fit_phenotype_model(base, n_clusters=3, random_state=17)

    query = base.copy()
    query["track_id"] += 10
    transformed = model.transform(query)

    assert list(transformed["track_id"]) == [10, 11, 12]
    assert transformed["phenotype_cluster_name"].notna().all()
