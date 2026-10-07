import numpy as np

from ai4s_imaging import segment_frames
from ai4s_imaging.synthetic import moving_blobs


def test_synthetic_microscopy_segmentation_produces_detections():
    frames = moving_blobs(frames=6, height=64, width=64, cells=4, seed=3)
    detections = segment_frames(frames, threshold=0.45, min_area=5)

    assert len(detections) >= 12
    assert detections["t"].nunique() == 6
    assert np.isfinite(detections[["y", "x"]].to_numpy()).all()
    assert (detections["area"] >= 5).all()
