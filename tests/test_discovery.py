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

def test_discovery_model_preserves_log_transform_policy_at_fit_time():
    from ai4s_phenotype import fit_phenotype_model
    import pytest

    base = pd.DataFrame(
        [
            {"track_id": 0, "duration": 1, "observations": 2, "displacement": 0.1, "path_length": 0.2, "mean_speed": 0.1, "directional_persistence": 0.9, "parent_count": 0, "child_count": 0, "descendant_count": 0},
            {"track_id": 1, "duration": 2, "observations": 3, "displacement": 0.2, "path_length": 0.4, "mean_speed": 0.2, "directional_persistence": 0.8, "parent_count": 0, "child_count": 0, "descendant_count": 0},
            {"track_id": 2, "duration": 3, "observations": 4, "displacement": 0.3, "path_length": 0.6, "mean_speed": 0.3, "directional_persistence": 0.7, "parent_count": 0, "child_count": 0, "descendant_count": 0},
        ]
    )
    model = fit_phenotype_model(base, n_clusters=3, random_state=17, log_transform=True)
    query = base.copy()
    query.loc[0, "displacement"] = -0.1

    with pytest.raises(ValueError, match="requires log1p"):
        model.transform(query)

def test_discovery_reports_cluster_distance_and_margin():
    from ai4s_phenotype import discover_phenotypes

    result = discover_phenotypes(
        pd.DataFrame(
            [
                {"track_id": 0, "duration": 10, "observations": 11, "displacement": 1.0, "path_length": 1.2, "mean_speed": 0.1, "directional_persistence": 0.9, "parent_count": 0, "child_count": 0, "descendant_count": 0},
                {"track_id": 1, "duration": 10, "observations": 11, "displacement": 8.0, "path_length": 8.5, "mean_speed": 0.8, "directional_persistence": 0.9, "parent_count": 0, "child_count": 0, "descendant_count": 0},
                {"track_id": 2, "duration": 10, "observations": 11, "displacement": 3.0, "path_length": 12.0, "mean_speed": 0.4, "directional_persistence": 0.25, "parent_count": 0, "child_count": 0, "descendant_count": 0},
            ]
        ),
        n_clusters=3,
    )
    assert "phenotype_cluster_distance" in result.columns
    assert "phenotype_cluster_margin" in result.columns
    assert (result["phenotype_cluster_distance"] >= 0).all()
    assert (result["phenotype_cluster_margin"] >= 0).all()
