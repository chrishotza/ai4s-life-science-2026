import numpy as np
import tifffile

from ai4s_io import load_ctc_tracking


def test_ctc_loader_builds_temporal_edges_and_metadata(tmp_path):
    seq = tmp_path / "TRA"
    seq.mkdir()

    frame0 = np.zeros((8, 8), dtype=np.uint16)
    frame0[2:4, 2:4] = 1
    frame1 = np.zeros((8, 8), dtype=np.uint16)
    frame1[2:4, 3:5] = 1

    tifffile.imwrite(seq / "man_track000.tif", frame0)
    tifffile.imwrite(seq / "man_track001.tif", frame1)
    (seq / "man_track.txt").write_text("1 0 1 0\n")

    nodes, edges, metadata = load_ctc_tracking(seq)

    assert len(nodes) == 2
    assert set(nodes["track_id"]) == {1}
    assert len(edges) == 1
    assert edges.iloc[0]["edge_type"] == "link"
    assert len(metadata) == 1
    assert int(metadata.iloc[0]["parent_id"]) == 0
