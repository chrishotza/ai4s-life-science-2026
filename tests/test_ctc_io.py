import tifffile

from ai4s_io import load_ctc_tracking


def test_ctc_loader_reads_markers_and_parent_metadata(tmp_path):
    tifffile.imwrite(
        tmp_path / "man_track000.tif",
        [[1, 0, 0], [0, 0, 2], [0, 0, 0]],
    )
    tifffile.imwrite(
        tmp_path / "man_track001.tif",
        [[1, 0, 0], [0, 3, 0], [0, 0, 0]],
    )
    (tmp_path / "man_track.txt").write_text(
        "1 0 1 0\n2 0 0 0\n3 1 1 1\n"
    )

    nodes, edges, metadata = load_ctc_tracking(tmp_path)

    assert len(nodes) == 4
    assert set(nodes["track_id"]) == {1, 2, 3}
    assert len(metadata) == 3
    assert "division_parent" in set(edges["edge_type"])
