import pandas as pd
import pytest

from ai4s_core import scale_coordinates, validate_edges, validate_nodes


def base_nodes():
    return pd.DataFrame(
        [
            (0, 0, 0, 0.0, 1.0, 2.0),
            (1, 0, 1, 0.0, 2.0, 3.0),
        ],
        columns=["node_id", "track_id", "t", "z", "y", "x"],
    )


def test_node_contract_rejects_duplicate_track_time():
    nodes = pd.concat([base_nodes(), base_nodes().iloc[[0]]], ignore_index=True)
    nodes.loc[2, "node_id"] = 2
    with pytest.raises(ValueError, match="same frame"):
        validate_nodes(nodes)


def test_edge_contract_requires_known_nodes():
    nodes = base_nodes()
    edges = pd.DataFrame({"source_id": [0], "target_id": [99]})
    with pytest.raises(ValueError, match="unknown node"):
        validate_edges(edges, nodes)


def test_edge_contract_can_require_consecutive_time():
    nodes = pd.DataFrame(
        [
            (0, 0, 0, 0.0, 0.0, 0.0),
            (1, 0, 2, 0.0, 1.0, 1.0),
        ],
        columns=["node_id", "track_id", "t", "z", "y", "x"],
    )
    edges = pd.DataFrame({"source_id": [0], "target_id": [1]})
    with pytest.raises(ValueError, match="consecutive"):
        validate_edges(edges, nodes, require_consecutive=True)


def test_scale_coordinates_uses_z_y_x_order():
    scaled = scale_coordinates(base_nodes(), (2.0, 3.0, 4.0))
    assert scaled.loc[1, "z"] == 0.0
    assert scaled.loc[1, "y"] == 6.0
    assert scaled.loc[1, "x"] == 12.0

def test_edge_contract_rejects_self_edges():
    nodes = base_nodes()
    edges = pd.DataFrame({"source_id": [0], "target_id": [0]})
    with pytest.raises(ValueError, match="self"):
        validate_edges(edges, nodes)


def test_edge_contract_can_require_forward_time():
    nodes = base_nodes()
    edges = pd.DataFrame({"source_id": [1], "target_id": [0]})
    with pytest.raises(ValueError, match="forward"):
        validate_edges(edges, nodes, require_forward_time=True)
