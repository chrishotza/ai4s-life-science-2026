import numpy as np

from ai4s_imaging import segment_frames


def test_segmentation_recovers_two_synthetic_bright_objects():
    frames = np.zeros((1, 24, 24), dtype=float)
    frames[0, 5:8, 5:8] = 1.0
    frames[0, 15:18, 16:19] = 1.0

    result = segment_frames(frames, threshold=0.5, min_area=3)

    assert len(result) == 2
    assert sorted(result["area"].astype(int)) == [9, 9]
