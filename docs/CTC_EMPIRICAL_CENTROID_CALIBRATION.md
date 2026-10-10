# CellposeSAM-v2 cell-center comparison with CTC silver reference masks

**Experimental protocol — numerical results pending completion of the actual inference run.** This note is in the development PR and must not be cited as a completed benchmark until [the run](https://github.com/chrishotza/ai4s-life-science-2026/actions/runs/38016428084) finishes and its exported results are verified.

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

**Result status:** `PENDING_REAL_INFERENCE`. Replace this status with verified measured results and an exact artifact reference before any merge into the submission-ready main branch.
