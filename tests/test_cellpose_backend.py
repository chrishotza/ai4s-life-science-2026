from __future__ import annotations

import numpy as np
import pytest

from ai4s_imaging.cellpose_backend import CellposeSegmenter


class FakeCellposeModel:
    def __init__(self) -> None:
        self.image: np.ndarray | None = None
        self.kwargs: dict[str, object] = {}

    def eval(self, image: np.ndarray, **kwargs: object) -> tuple[np.ndarray, None, None]:
        self.image = np.asarray(image).copy()
        self.kwargs = dict(kwargs)
        labels = np.zeros(image.shape, dtype=np.int32)
        labels[1:3, 1:3] = 9
        labels[4:6, 4:6] = 3
        return labels, None, None


def test_cellpose_adapter_normalizes_labels_and_uses_v4_api() -> None:
    fake = FakeCellposeModel()
    segmenter = CellposeSegmenter(model=fake, min_size=1)

    output = segmenter.predict_instances(np.arange(64, dtype=np.float32).reshape(8, 8))

    assert output.shape == (8, 8)
    assert output.dtype == np.int32
    assert set(np.unique(output)) == {0, 1, 2}
    assert "invert" not in fake.kwargs
    assert fake.kwargs["channel_axis"] is None
    assert fake.kwargs["normalize"] is True
    assert fake.kwargs["min_size"] == 1


def test_cellpose_adapter_inverts_pixels_and_replaces_nonfinite_values() -> None:
    fake = FakeCellposeModel()
    segmenter = CellposeSegmenter(model=fake, invert=True, min_size=1)
    frame = np.arange(64, dtype=np.float32).reshape(8, 8)
    frame[0, 0] = np.nan

    segmenter.predict_instances(frame)

    assert fake.image is not None
    assert np.isfinite(fake.image).all()
    # The missing value is filled with the median before inversion.
    assert fake.image[0, 0] == pytest.approx(float(np.max(np.arange(1, 64, dtype=float))) - 31.5)


def test_cellpose_adapter_rejects_non_2d_inputs() -> None:
    segmenter = CellposeSegmenter(model=FakeCellposeModel())
    with pytest.raises(ValueError, match="2-D"):
        segmenter.predict_instances(np.zeros((2, 8, 8), dtype=np.float32))
