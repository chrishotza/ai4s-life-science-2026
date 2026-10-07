import pandas as pd
import pytest

from ai4s_core import validate_lineage_graph


def test_lineage_graph_rejects_multiple_parents():
    nodes = pd.DataFrame(
        [
            (0, 0, 0, 0.0, 0.0, 0.0),
            (1, 1, 0, 0.0, 1.0, 0.0),
            (2, 2, 1, 0.0, 0.5, 0.0),
        ],
        columns=["node_id", "track_id", "t", "z", "y", "x"],
    )
    edges = pd.DataFrame(
        [(0, 2), (1, 2)],
        columns=["source_id", "target_id"],
    )
    with pytest.raises(ValueError, match="too many parents"):
        validate_lineage_graph(nodes, edges)


def test_lineage_graph_rejects_intra_track_edges():
    nodes = pd.DataFrame(
        [
            (0, 0, 0, 0.0, 0.0, 0.0),
            (1, 0, 1, 0.0, 1.0, 0.0),
        ],
        columns=["node_id", "track_id", "t", "z", "y", "x"],
    )
    edges = pd.DataFrame([(0, 1)], columns=["source_id", "target_id"])
    with pytest.raises(ValueError, match="intra-track"):
        validate_lineage_graph(nodes, edges)
