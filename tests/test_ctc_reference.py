from pathlib import Path

import numpy as np
import pandas as pd
import tifffile

from ai4s_io.ctc_reference import write_ctc_reference_geometry


def test_write_ctc_reference_geometry_preserves_geometry_and_writes_track_file(tmp_path: Path):
    frame0 = np.array([[1, 0], [0, 2]], dtype=np.uint16)
    frame1 = np.array([[1, 0], [0, 2]], dtype=np.uint16)
    mask0 = tmp_path / "man_track000.tif"
    mask1 = tmp_path / "man_track001.tif"
    tifffile.imwrite(mask0, frame0)
    tifffile.imwrite(mask1, frame1)

    nodes = pd.DataFrame(
        {
            "node_id": [0, 1, 2, 3],
            "track_id": [0, 1, 1, 0],
            "reference_track_id": [1, 2, 1, 2],
            "t": [0, 0, 1, 1],
            "z": [0, 0, 0, 0],
            "y": [0, 1, 0, 1],
            "x": [0, 1, 0, 1],
        }
    )

    output = tmp_path / "result"
    write_ctc_reference_geometry(
        nodes,
        [mask0, mask1],
        output,
    )

    result0 = tifffile.imread(output / "man_track000.tif")
    result1 = tifffile.imread(output / "man_track001.tif")

    np.testing.assert_array_equal(result0, np.array([[1, 0], [0, 2]], dtype=np.uint32))
    np.testing.assert_array_equal(result1, np.array([[2, 0], [0, 1]], dtype=np.uint32))
    assert (output / "res_track.txt").read_text(encoding="utf-8").splitlines() == [
        "1 0 1 0",
        "2 0 1 0",
    ]
