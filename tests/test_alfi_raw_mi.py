"""Offline contract tests for the ALFI raw-image vs expert-mask benchmark."""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.evaluate_alfi_raw_mi import (
    instance_f1_iou50, instances_from_binary, load_pair, semantic_metrics,
)


def test_semantic_and_instance_metrics_perfect():
    gt = np.zeros((32, 32), dtype=np.uint8)
    gt[3:10, 3:10] = 128
    gt[17:25, 18:25] = 255
    labels = instances_from_binary(gt > 0)
    assert labels.max() == 2
    metrics = semantic_metrics(gt, labels)
    instances = instance_f1_iou50(labels, labels)
    assert metrics["dice"] == metrics["foreground_iou"] == 1
    assert metrics["mitosis_recall"] == metrics["interphase_recall"] == 1
    assert instances["instance_f1_iou50"] == 1


def test_instance_metric_penalizes_missing_object():
    gt = np.zeros((40, 40), dtype=np.uint8)
    gt[3:15, 3:15] = 128
    gt[21:34, 21:34] = 255
    pred = instances_from_binary(gt == 128)
    m = instance_f1_iou50(instances_from_binary(gt > 0), pred)
    assert m["gt_instances"] == 2 and m["matched_iou50"] == 1
    assert abs(m["instance_f1_iou50"] - (2 / 3)) < 1e-9


def test_training_and_test_inputs_must_have_aligned_source_shape(tmp_path):
    Image.fromarray(np.full((40, 40), 100, dtype=np.uint16)).save(
        tmp_path / "MI01_image_0001.png"
    )
    Image.fromarray(np.zeros((20, 40), dtype=np.uint8)).save(
        tmp_path / "MI01_mask_0001.png"
    )
    try:
        load_pair(tmp_path, "MI01", 1)
    except ValueError as error:
        assert "unaligned" in str(error)
    else:
        raise AssertionError("Unaligned expert mask must be rejected")
