"""Tests for empirical CTC reference mask centroid offsets (no model download)."""
from __future__ import annotations

import math

import numpy as np
import pytest

from scripts.evaluate_ctc_mask_centroid_reference import (
    pair_mask_centroids,
    summarize_errors,
)


def test_hungarian_matches_one_shifted_cell_and_counts_extra_predictions():
    reference = np.zeros((12,12), dtype=np.int32)
    model = np.zeros_like(reference)
    reference[1:5,1:5] = 11
    model[1:5,2:6] = 91
    model[8:10,8:10] = 77
    hits, frame = pair_mask_centroids(reference,model,sequence="01",frame=12)
    assert len(hits)==1
    assert hits[0]["silver_label"]==11
    assert hits[0]["predicted_label"]==91
    assert hits[0]["iou"]==pytest.approx(0.6)
    assert hits[0]["dy_um"]==pytest.approx(0)
    assert hits[0]["dx_um"]==pytest.approx(0.19)
    assert hits[0]["offset_um"]==pytest.approx(0.19)
    assert hits[0]["offset_pixels"]==pytest.approx(1)
    assert hits[0]["reference_area_pixels"]==16
    assert hits[0]["reference_equivalent_radius_um"]==pytest.approx(
        math.sqrt(16*0.19*0.19/math.pi)
    )
    assert frame["matched_instances_iou50"]==1
    assert frame["unmatched_predicted_instances"]==1
    assert frame["unmatched_reference_instances"]==0
    assert frame["frame_f1_iou50"]==pytest.approx(2/3)


def test_inadequate_iou_does_not_get_false_localization_score():
    reference = np.zeros((10,10), dtype=np.int32)
    model = np.zeros_like(reference)
    reference[1:5,1:5]=13
    model[1:5,3:7]=49
    matches, q = pair_mask_centroids(reference, model)
    assert matches==[]
    assert q["frame_f1_iou50"]==0
    assert q["unmatched_reference_instances"]==1
    assert q["unmatched_predicted_instances"]==1


def test_label_renumbering_leaves_centroid_error_unchanged():
    ref=np.zeros((12,12),dtype=np.int32)
    model=np.zeros_like(ref)
    ref[1:5,1:5]=1;ref[7:11,7:11]=2
    model[1:5,2:6]=3;model[7:11,7:11]=5
    orig,_=pair_mask_centroids(ref,model)
    ref2=ref.copy();ref2[ref==1]=92;ref2[ref==2]=34
    pred2=model.copy();pred2[model==3]=70;pred2[model==5]=19
    new,_=pair_mask_centroids(ref2,pred2)
    assert sorted(x["offset_um"] for x in orig)==pytest.approx(
        sorted(x["offset_um"] for x in new)
    )


def test_empty_frames_and_nonzero_without_match():
    z=np.zeros((6,6), dtype=np.int32)
    hits,q=pair_mask_centroids(z,z)
    assert hits==[]
    assert q["frame_f1_iou50"]==1.0
    assert summarize_errors(hits,[q])["centroid_offset_um"]["median"] is None
    ref=z.copy(); ref[1:3,1:3]=1
    matches,frame=pair_mask_centroids(ref,z)
    assert matches==[]
    assert frame["frame_f1_iou50"]==0.0


def test_aggregate_offsets_calculate_median_p95_and_coverage():
    a=np.zeros((10,10),dtype=np.int32)
    b=np.zeros_like(a);a[1:5,1:5]=1;b[1:5,2:6]=1
    hits,q=pair_mask_centroids(a,b)
    summary=summarize_errors(hits,[q])
    assert summary["matched_instances"]==1
    assert summary["centroid_offset_um"]["median"]==pytest.approx(0.19)
    assert summary["centroid_offset_um"]["p95"]==pytest.approx(0.19)
    assert summary["matched_reference_fraction"]==1
    assert summary["matched_prediction_fraction"]==1
    assert summary["fraction_with_offset_le_um"]["0.1"]==0
    assert summary["fraction_with_offset_le_um"]["0.25"]==1


@pytest.mark.parametrize("reference,predicted",[
    (np.zeros((3,3),dtype=float),np.zeros((3,3),dtype=int)),
    (np.zeros((3,3),dtype=int),np.zeros((3,4),dtype=int)),
    (np.full((3,3),-1,dtype=int),np.zeros((3,3),dtype=int)),
])
def test_invalid_masks_rejected(reference,predicted):
    with pytest.raises(ValueError):
        pair_mask_centroids(reference,predicted)
