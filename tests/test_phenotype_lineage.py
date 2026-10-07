import pandas as pd

from ai4s_phenotype import analyze


def test_division_event_and_descendants_are_extracted_from_lineage_edges():
    nodes = pd.DataFrame(
        [
            (0, 0, 0, 0.0, 10.0, 10.0),
            (1, 0, 1, 0.0, 10.0, 11.0),
            (2, 0, 2, 0.0, 10.0, 12.0),
            (3, 1, 3, 0.0, 9.0, 12.0),
            (4, 1, 4, 0.0, 9.0, 13.0),
            (5, 2, 3, 0.0, 11.0, 12.0),
            (6, 2, 4, 0.0, 11.0, 13.0),
        ],
        columns=["node_id", "track_id", "t", "z", "y", "x"],
    )
    edges = pd.DataFrame(
        [
            (0, 1),
            (1, 2),
            (2, 3),
            (2, 5),
            (3, 4),
            (5, 6),
        ],
        columns=["source_id", "target_id"],
    )

    result = analyze(nodes, edges).set_index("track_id")

    assert bool(result.loc[0, "division_event"])
    assert int(result.loc[0, "child_count"]) == 2
    assert int(result.loc[0, "descendant_count"]) == 2
    assert int(result.loc[1, "parent_count"]) == 1
    assert int(result.loc[2, "parent_count"]) == 1
    assert result.loc[0, "phenotype_flag"] == "division"
