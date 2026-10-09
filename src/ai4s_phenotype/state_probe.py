"""Optional supervised cell-state probe on leakage-safe temporal features.

Trained from labeled cell tracks; not a replacement for image detection, tracker,
or discovery clustering. Uses only current and past bounding-box geometry.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .causal import (
    STATIC_FEATURES, MOTION_FEATURES, causal_shape_motion_features,
)


@dataclass
class TemporalStateProbe:
    """A trainable readout for phase/state labels, with a heldout-sequence guard.

    Fit on annotated tracks only. On prediction, probabilities are model scores
    and are NOT calibrated biological confidence or disease diagnostics.
    """
    model: Any
    training_sequences: frozenset[str]
    feature_columns: tuple[str, ...]

    @classmethod
    def fit(cls, labeled_boxes: pd.DataFrame, *, c: float = 0.25) -> "TemporalStateProbe":
        if "label" not in labeled_boxes:
            raise ValueError("Fitting a phenotype probe requires a label column")
        if not np.isfinite(c) or c <= 0:
            raise ValueError("C must be finite and positive")
        measured = causal_shape_motion_features(labeled_boxes)
        if measured.empty or measured["label"].isna().any():
            raise ValueError("No valid labeled training cells")
        if measured["label"].nunique() < 2:
            raise ValueError("At least two distinct biological labels are required")
        names = tuple(STATIC_FEATURES + MOTION_FEATURES)
        model = make_pipeline(
            SimpleImputer(strategy="median"),
            StandardScaler(),
            LogisticRegression(
                C=c, max_iter=2000, class_weight="balanced", random_state=0
            ),
        )
        model.fit(measured[list(names)], measured["label"].to_numpy())
        return cls(
            model=model,
            training_sequences=frozenset(measured["sequence"].astype(str).unique()),
            feature_columns=names,
        )

    def predict(
        self, boxes: pd.DataFrame, *, require_heldout_sequences: bool = False
    ) -> pd.DataFrame:
        """Return phase labels and per-class scores aligned to sorted observations.

        When a scientific holdout is intended, setting require_heldout_sequences
        rejects any sequence used during fitting. There is no future lookahead.
        """
        measured = causal_shape_motion_features(boxes)
        seen = set(measured["sequence"].astype(str))
        if require_heldout_sequences and (seen & self.training_sequences):
            raise ValueError("Evaluation includes sequences used for training")
        out = measured[["sequence", "track_id", "frame"]].copy()
        if measured.empty:
            out["predicted_state"] = pd.Series(dtype="object")
            out["score_of_predicted_state"] = pd.Series(dtype=float)
            return out
        scores = self.model.predict_proba(measured[list(self.feature_columns)])
        classes = self.model.named_steps["logisticregression"].classes_
        winners = np.argmax(scores, axis=1)
        out["predicted_state"] = classes[winners]
        out["score_of_predicted_state"] = scores[np.arange(len(out)), winners]
        for index, name in enumerate(classes):
            out[f"score_{name}"] = scores[:, index]
        return out
