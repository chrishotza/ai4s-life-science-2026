from __future__ import annotations

import numpy as np


class CellposeSegmenter:
    """Optional pretrained Cellpose-SAM adapter for 2-D grayscale microscopy.

    Cellpose is kept optional so the lightweight threshold and supervised
    pipelines do not acquire a PyTorch dependency. The model is loaded lazily.
    Model weights are fetched by Cellpose at runtime; users are responsible for
    observing the upstream model and weight licenses.
    """

    def __init__(
        self,
        model_name: str = "cpsam_v2",
        *,
        min_size: int = 200,
        flow_threshold: float = 0.4,
        cellprob_threshold: float = 0.0,
        invert: bool = False,
        model: object | None = None,
    ) -> None:
        if not model_name.strip():
            raise ValueError("model_name must not be empty")
        if min_size < 1:
            raise ValueError("min_size must be >= 1")
        if flow_threshold < 0:
            raise ValueError("flow_threshold must be >= 0")
        self.model_name = model_name
        self.min_size = int(min_size)
        self.flow_threshold = float(flow_threshold)
        self.cellprob_threshold = float(cellprob_threshold)
        self.invert = bool(invert)
        if model is None:
            try:
                from cellpose import models
            except ImportError as exc:
                raise RuntimeError(
                    "Cellpose support requires the optional dependency: "
                    "pip install 'cellpose>=4.2.0'"
                ) from exc
            model = models.CellposeModel(
                gpu=False,
                pretrained_model=self.model_name,
                use_bfloat16=False,
            )
        self.model = model

    def predict_instances(self, frame: np.ndarray) -> np.ndarray:
        """Return a 2-D integer label mask, with zero reserved for background."""
        image = np.asarray(frame)
        if image.ndim != 2:
            raise ValueError(f"frame must be 2-D; got {image.shape}")
        if image.size == 0:
            raise ValueError("frame must not be empty")
        if not np.isfinite(image).any():
            return np.zeros(image.shape, dtype=np.int32)

        # Keep Cellpose normalization enabled: DIC frames can vary in raw scale.
        result = self.model.eval(
            np.asarray(image, dtype=np.float32),
            channel_axis=None,
            normalize=True,
            invert=self.invert,
            flow_threshold=self.flow_threshold,
            cellprob_threshold=self.cellprob_threshold,
            min_size=self.min_size,
            augment=False,
        )
        if not isinstance(result, (tuple, list)) or len(result) < 1:
            raise RuntimeError("Cellpose eval returned an unexpected result")
        labels = np.asarray(result[0])
        if labels.shape != image.shape:
            raise RuntimeError(
                f"Cellpose mask shape {labels.shape} does not match image {image.shape}"
            )
        if labels.ndim != 2:
            raise RuntimeError(f"Cellpose returned a non-2-D mask: {labels.shape}")

        # Canonicalize IDs so downstream exports and metrics are independent of
        # the particular label integers emitted by the model.
        output = np.zeros(labels.shape, dtype=np.int32)
        next_id = 1
        for label_id in np.unique(labels):
            if label_id <= 0:
                continue
            output[labels == label_id] = next_id
            next_id += 1
        return output
