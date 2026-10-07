import pandas as pd

from ai4s_tracking import infer_divisions


def test_lineage_distance_is_measured_in_physical_units():
    nodes = pd.DataFrame(
        [
            {"node_id": 0, "track_id": 0, "t": 0, "z": 0.0, "y": 0.0, "x": 0.0},
            {"node_id": 1, "track_id": 1, "t": 1, "z": 0.0, "y": 10.0, "x": 0.0},
            {"node_id": 2, "track_id": 2, "t": 1, "z": 0.0, "y": 0.0, "x": 10.0},
        ]
    )
    links = pd.DataFrame(columns=["source_id", "target_id"])

    events = infer_divisions(
        nodes,
        links,
        division_radius_um=2.5,
        voxel_size_um=(1.0, 0.1, 0.1),
    )

    assert len(events) == 2
    assert set(events["target_id"]) == {1, 2}
    assert (events["distance_um"] == 1.0).all()
