# CellposeSAM-v2 cell-center comparison with CTC silver reference masks

**Status: completed empirical silver-reference centroid comparison, internally validated from independently checked per-instance exports.** The [pre-specified 16-frame inference run](https://github.com/chrishotza/ai4s-life-science-2026/actions/runs/38016428084) finished successfully. A separate archive workflow independently validated the per-cell CSV, SHA-256 and percentile calculations before committing results.

## Research question

How far is the geometric center of an image-derived CellposeSAM-v2 instance mask from the geometric center of its corresponding **Cell Tracking Challenge ST/SEG silver annotation mask**, measured in calibrated micrometers?

This is an empirical **matched-instance spatial discrepancy against silver segmentation references**, not a direct measurement of a true biological cell center, displacement accuracy across a full track, drug response, or independent domain generalization.

## Sampling fixed before observing results

- Datasets: the public training sequences **DIC-C2DH-HeLa 01 and 02**, exactly those used for the preceding 168-frame raw-image evaluation.
- Sampling: **8 evenly spaced paired microscopy images / ST/SEG reference masks per sequence**, a total of **16 frames** distributed across each available series. This is a small retrospective validation subset, **not** a new independent holdout.
- Predictor: unchanged pretrained CellposeSAM-v2 `cpsam_v2`, `min_size=200`, `flow_threshold=0.4`, `cellprob_threshold=0.0`, `invert=False`, matching the main Cellpose benchmark. **Reference masks never enter model inference.**
- Image field-of-interest restriction and one-to-one IoU>=0.50 Hungarian assignment follow the existing segmentation protocol.
- Spatial scale is **0.19 µm/pixel** for both in-plane axes, from the existing dataset configuration.

## Prespecified computations

Every matched pair yields: original reference/predicted label IDs, areas, IoU, reference/predicted centroid coordinates (pixels), physical offsets `dx`, `dy` and Euclidean distance in µm, and the centroid offset divided by the silver object's area-equivalent radius. Unmatched silver annotations and unmatched predictions are **counted separately, never omitted silently as successes**.

We report frame-wise matching F1@IoU50, pooled and sequence-stratified match coverage, and matched-pair offset distributions (median, mean, p90, p95, maximum and RMSE). Per-instance and frame-level tabular outputs plus exact CSV SHA-256 accompany the numeric summary. No statistical confidence interval or biological replicate independence is claimed for this two-sequence sampled subset.

## Interpretation constraints

1. **ST/SEG is silver segmentation reference.** Whole-cell mask geometry may differ among human/algorithmic labels. The annotation center is a reproducible spatial target, not the invisible true cell center.
2. **Matched-pair selection is conditional on overlap.** Offsets are not defined for unmatched objects, and their omission can make apparent localization quality optimistic. Every report includes matching counts and F1.
3. **A distribution is not a uniform bound.** Even if the empirical p95 is small, it cannot be substituted for the guaranteed per-position error `epsilon` in our [hypothetical triangle-inequality analysis](CTC_CENTROID_ERROR_SENSITIVITY.md). The two analyses are complementary but not equivalent.
4. **No image-to-track error decomposition.** Wrong tracking links, lineage assignments and fragmentation are not measured here.
5. **Not a new CTC challenge score or out-of-domain test.** The 16 frames are sampled from the same two image sequences as the primary 168-frame evaluation.
6. **No biological states are inferred.** The experiment is an error-audit component for a computational research prototype.

## Provenance and reproduction

Code: [`scripts/evaluate_ctc_mask_centroid_reference.py`](../scripts/evaluate_ctc_mask_centroid_reference.py); tests: [`tests/test_ctc_mask_centroid_reference.py`](../tests/test_ctc_mask_centroid_reference.py).

```bash
python scripts/evaluate_ctc_mask_centroid_reference.py \
  --frames-per-sequence 8 \
  --output ctc_centroid_reference_results.json \
  --matches-csv ctc_centroid_reference_matches.csv
```

GitHub Actions: [real CPU inference and artifact](https://github.com/chrishotza/ai4s-life-science-2026/actions/runs/38016428084).

## Verified measurements (16 selected frames, 193 matched instances)

| Metric | Both sequences | Sequence 01 | Sequence 02 |
|---|---:|---:|---:|
| Sampled frames | **16** | 8 | 8 |
| Silver reference instances | 199 | 104 | 95 |
| Model-predicted instances | 211 | 112 | 99 |
| One-to-one IoU≥0.50 matches | **193** | 99 | 94 |
| Reference-instance match coverage | 97.0% | 95.2% | 98.9% |
| Predicted-instance match coverage | 91.5% | 88.4% | 94.9% |
| Mean frame instance F1@IoU50 | 0.9391 | 0.9139 | 0.9644 |
| **Median matched centroid discrepancy** | **0.909 µm** | 0.906 µm | 0.911 µm |
| **95th-percentile matched discrepancy** | **2.701 µm** | 3.136 µm | 2.563 µm |
| Largest matched discrepancy | **4.289 µm** | 4.289 µm | 3.879 µm |

From the 199 silver-annotated objects, 6 were unmatched; 18 of the 211 model predictions were unmatched. The measured pooled matched-offset mean was **1.103 µm** and RMSE **1.372 µm**. Dividing each offset by the matched silver object's area-equivalent radius yielded a median **0.0814** and 95th percentile **0.2630**, useful for assessing error relative to apparent cell size.

The prespecified frames were **0, 11, 23, 35, 47, 59, 71 and 83 in each sequence**. This was chosen before seeing their results, not cherry-picked after a visual inspection.

**Supplementary overlap-quality check:** Of the 193 IoU≥0.50 matches, 139 also had IoU≥0.75; in that **strictly selected subset** the median discrepancy was **0.773 µm** and its p95 **1.923 µm**. This is a conditional sensitivity diagnostic, not a replacement headline: better-matched cell masks naturally tend to have more similar geometric centroids, and restricting to them discards harder objects.

## What changes in the scientific interpretation

Earlier, [the mathematical sensitivity analysis](CTC_CENTROID_ERROR_SENSITIVITY.md) modeled hypothetical hard upper bounds of 0.05–1.00 µm on individual center errors. These **new empirical silver-reference discrepancies are often larger than those example radii**: just 8.8% of the matched pairs have measured offset ≤0.25 µm and 21.8% ≤0.50 µm. Consequently, it would be **unjustified to describe those small hypothetical bounds as a calibration of the existing tracker**, or to claim our low-directionality findings are empirically secure under such thresholds.

However, reference mask centroid disagreement does **not establish the true biological-center estimation error**, and the per-instance error distribution does **not provide a uniform maximum across every position of any of the 51 exported temporal profiles**. It cannot directly be substituted as epsilon into a whole-track triangle-inequality guarantee. This is a *meaningful numerical limitation* and a clear next validation target, not evidence that a biological phenotype has been discovered or refuted.

## Public proof and provenance

- [Successful 16-frame, two-sequence inference with identical CellposeSAM-v2 settings](https://github.com/chrishotza/ai4s-life-science-2026/actions/runs/38016428084).
- [Original two-file numeric artifact](https://github.com/chrishotza/ai4s-life-science-2026/actions/runs/38016428084/artifacts/11656429049).
- [Versioned aggregate and per-frame JSON](evidence/ctc/cellpose_centroid_reference_16_frames.json).
- [Per-instance audit CSV](evidence/ctc/cellpose_centroid_matches_16_frames.csv).
- [Independent freeze-and-verify action](https://github.com/chrishotza/ai4s-life-science-2026/actions/runs/38017367854) checked unique matches, physical units, median, p95 and exact source CSV SHA-256.

**Verified conclusion:** On these 16 sampled CTC frames, pretrained CellposeSAM-v2 achieved strong matching coverage but **non-negligible reference-mask centroid discrepancies**, with a 0.91 µm median and 2.70 µm p95 among matched objects. We now quantify both the utility and one important spatial limitation of downstream motion estimates, without claiming new biology.

