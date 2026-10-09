import numpy as np
import pytest

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from benchmark_phc_psc_supervised_segmentation import score_frame


def test_instance_metrics_do_not_count_one_merged_prediction_as_two_recovered_cells():
    # The single predicted instance overlaps each reference object at IoU=0.5.
    # Best-IoU-per-object metrics would incorrectly report recall=1.0.
    gt = np.array([[1, 1, 2, 2]], dtype=np.int32)
    pred = np.array([[7, 7, 7, 7]], dtype=np.int32)

    result = score_frame(gt, pred)

    assert result["object_tp_iou50"] == 1
    assert result["object_fp_iou50"] == 0
    assert result["object_fn_iou50"] == 1
    assert result["pred_precision_iou50"] == pytest.approx(1.0)
    assert result["gt_recall_iou50"] == pytest.approx(0.5)
    assert result["object_f1_iou50"] == pytest.approx(2 / 3)


def test_instance_metrics_penalize_one_reference_cell_split_into_two_predictions():
    gt = np.array([[1, 1, 1, 1]], dtype=np.int32)
    pred = np.array([[4, 4, 9, 9]], dtype=np.int32)

    result = score_frame(gt, pred)

    assert result["object_tp_iou50"] == 1
    assert result["object_fp_iou50"] == 1
    assert result["object_fn_iou50"] == 0
    assert result["pred_precision_iou50"] == pytest.approx(0.5)
    assert result["gt_recall_iou50"] == pytest.approx(1.0)
    assert result["object_f1_iou50"] == pytest.approx(2 / 3)


def test_instance_metrics_handle_empty_frames_explicitly():
    result = score_frame(np.zeros((3, 3), dtype=np.int32), np.zeros((3, 3), dtype=np.int32))

    assert result["object_tp_iou50"] == 0
    assert result["object_fp_iou50"] == 0
    assert result["object_fn_iou50"] == 0
    assert result["pred_precision_iou50"] == pytest.approx(1.0)
    assert result["gt_recall_iou50"] == pytest.approx(1.0)
    assert result["object_f1_iou50"] == pytest.approx(1.0)
