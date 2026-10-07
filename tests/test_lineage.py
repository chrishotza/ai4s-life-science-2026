import pandas as pd

from ai4s_tracking import infer_divisions


def test_lineage_infers_two_daughters():
    nodes = pd.DataFrame(
        [
            {"node_id": 0, "track_id": 0, "t": 0, "z": 0.0, "y": 10.0, "x": 10.0},
            {"node_id": 1, "track_id": 1, "t": 1, "z": 0.0, "y": 8.5, "x": 10.0},
            {"node_id": 2, "track_id": 2, "t": 1, "z": 0.0, "y": 11.5, "x": 10.0},
        ]
    )
    links = pd.DataFrame(columns=["source_id", "target_id"])

    events = infer_divisions(nodes, links, division_radius_um=3.0)

    assert len(events) == 2
    assert set(events["source_id"]) == {0}
    assert set(events["target_id"]) == {1, 2}
    assert (events["edge_type"] == "division_parent").all()
