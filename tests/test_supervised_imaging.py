from __future__ import annotations

import numpy as np
import pytest

from ai4s_imaging import Supervised2DSegmenter, instances_to_detections


def annotated_blobs(
    frame_count: int = 8,
    height: int = 64,
    width: int = 64,
) -> tuple[np.ndarray, np.ndarray]:
    """Create a deterministic toy microscopy sequence with instance masks."""
    rng = np.random.default_rng(31)
    frames = np.empty((frame_count, height, width), dtype=np.float32)
    masks = np.zeros((frame_count, height, width), dtype=np.uint16)
    yy, xx = np.mgrid[:height, :width]

    for t in range(frame_count):
        image = rng.normal(0.08, 0.015, size=(height, width)).astype(np.float32)
        centers = (
            (17 + t // 2, 20 + t),
            (43 - t // 3, 42 - t),
        )
        for label_id, (cy, cx) in enumerate(centers, start=1):
            cell = (yy - cy) ** 2 + (xx - cx) ** 2 <= 6**2
            masks[t, cell] = label_id
            image[cell] += 0.65
        frames[t] = image
    return frames, masks


def test_supervised_segmenter_fit_predict_and_make_centroids() -> None:
    frames, masks = annotated_blobs()
    model = Supervised2DSegmenter(
        n_estimators=12,
        max_depth=12,
        samples_per_class_per_frame=300,
        max_training_frames=6,
        random_state=7,
        min_marker_area=4,
        min_instance_area=8,
        max_instance_area=1000,
    )
    model.fit(frames[:6], masks[:6])

    predicted = model.predict_instances(frames[6])
    assert predicted.shape == frames[6].shape
    assert predicted.dtype == np.int32
    assert np.count_nonzero(np.unique(predicted) > 0) >= 1

    detections = instances_to_detections(frames[6:7], predicted[None, ...])
    assert {"t", "z", "y", "x", "area", "mean_intensity"}.issubset(detections.columns)
    assert not detections.empty
    assert (detections["t"] == 0).all()
    assert (detections["area"] > 0).all()


def test_supervised_segmenter_requires_fit_and_matching_shapes() -> None:
    model = Supervised2DSegmenter(n_estimators=2)
    with pytest.raises(RuntimeError, match="Call fit"):
        model.predict_instances(np.zeros((16, 16), dtype=np.float32))

    with pytest.raises(ValueError, match="shapes must match"):
        model.fit(np.zeros((2, 16, 16)), np.zeros((2, 15, 16)))
