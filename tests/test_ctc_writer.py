import numpy as np
import pandas as pd
import tifffile
import pytest

from ai4s_io import write_ctc_tracking


def test_ctc_writer_emits_positive_deterministic_labels(tmp_path):
    nodes = pd.DataFrame(
        [
            (0, 7, 0, 0.0, 1.0, 2.0),
            (1, 7, 1, 0.0, 2.0, 2.0),
            (2, 11, 1, 0.0, 4.0, 5.0),
        ],
        columns=["node_id", "track_id", "t", "z", "y", "x"],
    )

    mapping = write_ctc_tracking(nodes, tmp_path, (8, 8), digits=3)

    assert mapping == {7: 1, 11: 2}
    first = tifffile.imread(tmp_path / "man_track000.tif")
    second = tifffile.imread(tmp_path / "man_track001.tif")
    assert first.dtype == np.uint32
    assert first[1, 2] == 1
    assert second[2, 2] == 1
    assert second[4, 5] == 2


def test_ctc_writer_rejects_centroid_collisions(tmp_path):
    nodes = pd.DataFrame(
        [
            (0, 7, 0, 0.0, 1.2, 2.2),
            (1, 8, 0, 0.0, 1.4, 2.4),
        ],
        columns=["node_id", "track_id", "t", "z", "y", "x"],
    )

    with pytest.raises(ValueError, match="collision"):
        write_ctc_tracking(nodes, tmp_path, (8, 8), digits=3)
