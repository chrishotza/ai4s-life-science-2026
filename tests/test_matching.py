import pandas as pd

from ai4s_core import greedy_track_overlap


def test_greedy_track_overlap_is_deterministic():
    truth = pd.DataFrame(
        [
            (0, 10, 0),
            (1, 10, 1),
            (2, 20, 0),
            (3, 20, 1),
        ],
        columns=["node_id", "track_id", "t"],
    )
    predicted = pd.DataFrame(
        [
            (0, 200, 0),
            (1, 200, 1),
            (2, 100, 0),
            (3, 100, 1),
        ],
        columns=["node_id", "track_id", "t"],
    )

    matches = greedy_track_overlap(truth, predicted)

    assert matches == [
        (10, 200, 2, 1.0),
        (20, 100, 2, 1.0),
    ]
