import numpy as np

from ai4s_imaging import segment_frames


def test_segmentation_recovers_two_synthetic_bright_objects():
    frames = np.zeros((1, 24, 24), dtype=float)
    frames[0, 5:8, 5:8] = 1.0
    frames[0, 15:18, 16:19] = 1.0

    result = segment_frames(frames, threshold=0.5, min_area=3)

    assert len(result) == 2
    assert sorted(result["area"].astype(int)) == [9, 9]

import pytest

from ai4s_imaging.synthetic import moving_blobs


def test_moving_blobs_supports_small_frames():
    stack = moving_blobs(frames=2, height=8, width=9, cells=2, seed=3)
    assert stack.shape == (2, 8, 9)


def test_moving_blobs_rejects_nonpositive_radius():
    with pytest.raises(ValueError, match="radius"):
        moving_blobs(radius=0)

def test_segmentation_rejects_nonfinite_threshold():
    import pytest

    frames = np.zeros((1, 8, 8), dtype=float)
    with pytest.raises(ValueError, match="finite"):
        segment_frames(frames, threshold=float("nan"))

def test_segmentation_supports_3d_time_lapse_volumes():
    frames = np.zeros((2, 6, 10, 10), dtype=float)
    frames[0, 2:4, 2:4, 2:4] = 1.0
    frames[1, 2:4, 3:5, 2:4] = 1.0

    result = segment_frames(frames, threshold=0.5, min_area=3)

    assert len(result) == 2
    assert sorted(result["z"].round(3).tolist()) == [2.5, 2.5]
