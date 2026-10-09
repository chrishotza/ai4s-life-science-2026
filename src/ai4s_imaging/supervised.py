from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy import ndimage
from sklearn.ensemble import RandomForestClassifier


def _normalize(image: np.ndarray) -> np.ndarray:
    image = np.asarray(image, dtype=np.float32)
    finite = np.isfinite(image)
    if not finite.any():
        return np.zeros_like(image, dtype=np.float32)
    lo, hi = np.percentile(image[finite], (1.0, 99.0))
    if hi <= lo:
        return np.zeros_like(image, dtype=np.float32)
    normalized = np.zeros_like(image, dtype=np.float32)
    normalized[finite] = np.clip((image[finite] - lo) / (hi - lo), 0.0, 1.0)
    return normalized


def _pixel_features(image: np.ndarray) -> np.ndarray:
    """Build deterministic multi-scale intensity, edge, Hessian, and texture features."""
    x = _normalize(image)
    features: list[np.ndarray] = [x]
    for sigma in (1.0, 2.0, 4.0, 8.0):
        smooth = ndimage.gaussian_filter(x, sigma=sigma)
        gx = ndimage.gaussian_filter(x, sigma=sigma, order=(0, 1))
        gy = ndimage.gaussian_filter(x, sigma=sigma, order=(1, 0))
        hxx = ndimage.gaussian_filter(x, sigma=sigma, order=(0, 2))
        hyy = ndimage.gaussian_filter(x, sigma=sigma, order=(2, 0))
        hxy = ndimage.gaussian_filter(x, sigma=sigma, order=(1, 1))
        trace = hxx + hyy
        discriminant = np.sqrt(np.maximum((hxx - hyy) ** 2 + 4.0 * hxy ** 2, 0.0))
        lambda1 = 0.5 * (trace - discriminant)
        lambda2 = 0.5 * (trace + discriminant)

        window = max(3, int(2 * sigma + 1))
        local_mean = ndimage.uniform_filter(x, size=window, mode="nearest")
        local_sq = ndimage.uniform_filter(x**2, size=window, mode="nearest")
        local_variance = np.maximum(local_sq - local_mean**2, 0.0)
        features.extend(
            [
                x - smooth,
                np.hypot(gx, gy),
                lambda1,
                lambda2,
                local_mean,
                local_variance,
            ]
        )
    return np.stack(features, axis=-1).astype(np.float32, copy=False)


def _pixel_classes(instance_mask: np.ndarray) -> np.ndarray:
    """Convert an instance mask into background, interior, and boundary classes."""
    mask = np.asarray(instance_mask)
    if mask.ndim != 2:
        raise ValueError(f"Each instance mask must be 2-D; got {mask.shape}")
    foreground = mask > 0
    maximum = ndimage.maximum_filter(mask, size=3, mode="nearest")
    minimum = ndimage.minimum_filter(mask, size=3, mode="nearest")
    boundary = foreground & (maximum != minimum)
    labels = np.zeros(mask.shape, dtype=np.uint8)
    labels[foreground & ~boundary] = 1
    labels[boundary] = 2
    return labels


@dataclass
class Supervised2DSegmenter:
    """Small supervised microscopy segmenter trained from instance-labeled frames.

    The model predicts background/interior/boundary pixels, then uses interior
    components as seeds to restore separate instance IDs. It is a practical
    baseline for one imaging domain, not a universal pretrained cell model.
    """

    n_estimators: int = 60
    max_depth: int = 18
    min_samples_leaf: int = 2
    samples_per_class_per_frame: int = 2500
    max_training_frames: int = 24
    random_state: int = 42
    min_marker_area: int | None = None
    effective_min_marker_area: int = field(default=8, init=False)
    min_instance_area: int = 12
    max_instance_area: int = 30000
    model: RandomForestClassifier | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.n_estimators < 1:
            raise ValueError("n_estimators must be >= 1")
        if self.samples_per_class_per_frame < 1:
            raise ValueError("samples_per_class_per_frame must be >= 1")
        if self.max_training_frames < 1:
            raise ValueError("max_training_frames must be >= 1")
        if (self.min_marker_area is not None and self.min_marker_area < 1) or self.min_instance_area < 1:
            raise ValueError("minimum areas must be >= 1")
        if self.max_instance_area < self.min_instance_area:
            raise ValueError("max_instance_area must be >= min_instance_area")

    def fit(self, frames: np.ndarray, instance_masks: np.ndarray) -> "Supervised2DSegmenter":
        frames = np.asarray(frames)
        masks = np.asarray(instance_masks)
        if frames.ndim != 3 or masks.ndim != 3:
            raise ValueError("frames and instance_masks must both have shape (t, y, x)")
        if frames.shape != masks.shape:
            raise ValueError(
                f"Image/mask stack shapes must match; got {frames.shape} and {masks.shape}"
            )
        if frames.shape[0] == 0:
            raise ValueError("At least one annotated frame is required")

        if frames.shape[0] > self.max_training_frames:
            selected = np.unique(
                np.linspace(
                    0, frames.shape[0] - 1, num=self.max_training_frames, dtype=int
                )
            )
        else:
            selected = np.arange(frames.shape[0], dtype=int)

        training_instance_areas: list[int] = []
        for frame_index in selected:
            values, counts = np.unique(masks[int(frame_index)], return_counts=True)
            training_instance_areas.extend(
                int(count) for value, count in zip(values, counts) if value > 0
            )
        if self.min_marker_area is None:
            median_area = float(np.median(training_instance_areas)) if training_instance_areas else 200.0
            self.effective_min_marker_area = int(np.clip(round(0.10 * median_area), 16, 256))
        else:
            self.effective_min_marker_area = int(self.min_marker_area)

        rng = np.random.default_rng(self.random_state)
        feature_rows: list[np.ndarray] = []
        label_rows: list[np.ndarray] = []
        for frame_index in selected:
            image = np.asarray(frames[int(frame_index)])
            mask = np.asarray(masks[int(frame_index)])
            if not np.isfinite(image).any():
                continue
            pixel_features = _pixel_features(image).reshape(-1, 25)
            pixel_labels = _pixel_classes(mask).reshape(-1)
            finite = np.isfinite(image).reshape(-1)

            chosen: list[np.ndarray] = []
            for class_id in (0, 1, 2):
                indices = np.flatnonzero((pixel_labels == class_id) & finite)
                if len(indices) > self.samples_per_class_per_frame:
                    indices = rng.choice(
                        indices,
                        size=self.samples_per_class_per_frame,
                        replace=False,
                    )
                if len(indices):
                    chosen.append(indices)
            if not chosen:
                continue
            keep = np.concatenate(chosen)
            rng.shuffle(keep)
            feature_rows.append(pixel_features[keep])
            label_rows.append(pixel_labels[keep])

        if not feature_rows:
            raise ValueError("No finite labeled pixels were available for training")
        x = np.vstack(feature_rows)
        y = np.concatenate(label_rows)
        classes = np.unique(y)
        if len(classes) < 2 or not np.any(y > 0):
            raise ValueError("Training masks must contain both background and cell pixels")

        self.model = RandomForestClassifier(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            min_samples_leaf=self.min_samples_leaf,
            class_weight="balanced_subsample",
            n_jobs=-1,
            random_state=self.random_state,
        )
        self.model.fit(x, y)
        return self

    def predict_instances(self, frame: np.ndarray) -> np.ndarray:
        if self.model is None:
            raise RuntimeError("Call fit(frames, instance_masks) before prediction")
        image = np.asarray(frame)
        if image.ndim != 2:
            raise ValueError(f"frame must be 2-D; got {image.shape}")
        features = _pixel_features(image)
        classes = self.model.predict(features.reshape(-1, features.shape[-1])).reshape(image.shape)

        interior = classes == 1
        boundary = classes == 2
        markers, marker_count = ndimage.label(interior)

        # Suppress fragments using a threshold estimated from labeled training cells.
        if marker_count:
            sizes = np.bincount(markers.reshape(-1), minlength=marker_count + 1)
            remap = np.zeros(marker_count + 1, dtype=np.int32)
            next_id = 1
            for old_id in range(1, marker_count + 1):
                if (
                    self.effective_min_marker_area <= int(sizes[old_id])
                    <= self.max_instance_area
                ):
                    remap[old_id] = next_id
                    next_id += 1
            markers = remap[markers]

        kept_interior = markers > 0
        if not kept_interior.any():
            # Boundary-only predictions are not cells; do not promote them to objects.
            return np.zeros(image.shape, dtype=np.int32)

        # Reconstruct complete instances from both predicted interiors and boundaries.
        # Restricting boundary growth to a 2-pixel band truncates cells when the pixel
        # classifier predicts thick boundary regions, collapsing instance IoU even when
        # the cell contour was recognized. Assign predicted foreground to the nearest
        # surviving interior marker; the learned background remains excluded.
        foreground = (classes == 1) | boundary
        _, nearest_indices = ndimage.distance_transform_edt(
            ~kept_interior, return_indices=True
        )
        nearest_markers = markers[tuple(nearest_indices)]
        instances = np.where(foreground, nearest_markers, 0).astype(np.int32)

        # Re-number after filtering and remove very small output objects.
        output = np.zeros_like(instances, dtype=np.int32)
        next_id = 1
        for label_id in np.unique(instances):
            if label_id <= 0:
                continue
            region = instances == label_id
            area = int(region.sum())
            if self.min_instance_area <= area <= self.max_instance_area:
                output[region] = next_id
                next_id += 1
        return output


def instances_to_detections(
    frames: np.ndarray,
    instance_masks: np.ndarray,
) -> pd.DataFrame:
    """Convert a (t,y,x) grayscale stack plus predicted instance labels to centroids."""
    frames = np.asarray(frames)
    masks = np.asarray(instance_masks)
    if frames.ndim != 3 or masks.shape != frames.shape:
        raise ValueError("frames and instance_masks must have the same (t, y, x) shape")

    rows: list[dict[str, float | int]] = []
    for t, (frame, mask) in enumerate(zip(frames, masks)):
        for label_id in np.unique(mask):
            if label_id <= 0:
                continue
            yy, xx = np.nonzero(mask == label_id)
            if len(yy) == 0:
                continue
            rows.append(
                {
                    "t": int(t),
                    "z": 0.0,
                    "y": float(yy.mean()),
                    "x": float(xx.mean()),
                    "area": int(len(yy)),
                    "mean_intensity": float(np.asarray(frame)[yy, xx].mean()),
                    "instance_id": int(label_id),
                }
            )
    return pd.DataFrame(
        rows,
        columns=["t", "z", "y", "x", "area", "mean_intensity", "instance_id"],
    )
