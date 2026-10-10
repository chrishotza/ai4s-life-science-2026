# Geometric persistence bounds under hypothetical centroid-localization error

**Status: retrospective mathematical sensitivity test, NOT a measured cell-center error, independent biological experiment or statistical confidence interval.**

**New empirical companion:** In [16 systematically sampled frames](CTC_EMPIRICAL_CENTROID_CALIBRATION.md), pretrained CellposeSAM-v2 matched **193** CTC silver masks with median **0.909 µm** centroid discrepancy and p95 **2.701 µm**. Those measured **reference-centroid discrepancies are not true-position error bounds**, but caution strongly against treating hypothetical epsilon values of 0.10–0.50 µm as calibrated conditions.

## Why this control matters

A track can accumulate a large traveled path even when endpoint displacement is small. Mask-boundary variation, fluctuating centroids, and poor links may inflate the path length, making *directional persistence* (net displacement divided by accumulated path) appear lower than the underlying physical motion. High instance-segmentation F1 and temporal edge F1 **do not guarantee micrometer-accurate centroid trajectories**.

This control uses the **actual 126 image-derived trajectory summaries** from the [168-frame CellposeSAM-v2 experiment](https://github.com/chrishotza/ai4s-life-science-2026/actions/runs/37930909373). It applies the existing evidence gate: **51 descriptive profiles**, 54 audit-only, and 21 low-reliability. It does **not** rerun segmentation, add ground-truth detections, or estimate localization errors from pixels.

## A conservative conditional guarantee

For a track containing `n` measured centers, let `P` be its accumulated physical path (µm), `D` the distance between its first and last centers (µm), and `epsilon` a **hypothesized maximum Euclidean localization error** per measured center, **assuming track identities are correct**.

The triangle inequality gives:

- Minimum possible true path: `max(0, P - 2 * epsilon * (n - 1))`.
- Maximum possible true path: `P + 2 * epsilon * (n - 1)`.
- Minimum possible true net displacement: `max(0, D - 2 * epsilon)`.
- Maximum possible true net displacement: `D + 2 * epsilon`.

These imply conservative lower and upper bounds on true `D/P`, clipped to the physical range 0–1. When the minimum possible true path is zero, use upper persistence bound 1. Every trajectory is then either **guaranteed below 0.20**, **guaranteed at or above 0.20**, or **indeterminate** under the assumed error radius. The 0.20 threshold is an *exploratory computational distinction*, not a biological phenotype label.

In DIC-C2DH-HeLa the calibrated image pixel size is **0.19 µm/pixel**; the displayed error radii are illustrative scenarios, **not experimentally observed model errors**.

## All 51 production-gated trajectories

| Hypothetical localization-error upper bound | Guaranteed below 0.20 | Indeterminate | Guaranteed at/above 0.20 |
|---|---:|---:|---:|
| **0 µm** | 33 | 0 | 18 |
| **0.05 µm** | 26 | 7 | 18 |
| **0.10 µm** | 25 | 9 | 17 |
| **0.25 µm (≈1.32 pixels)** | 15 | 22 | 14 |
| **0.50 µm (≈2.63 pixels)** | 6 | 34 | 11 |
| **1.00 µm (≈5.26 pixels)** | 0 | 46 | 5 |

The **measured** classification remains 33/51 below the threshold across scenarios; what changes is **how many labels can be guaranteed** despite the hypothetical positional uncertainty. An indeterminate label is *not* a documented misclassification. All counts and sequence-stratified evidence are in the [frozen JSON](evidence/ctc/centroid_localization_bounds.json).

### Example from the real 168-frame export

Sequence 02, track 21 traveled **142.095 µm** with net displacement **4.289 µm** across 66 observations. Its observed persistence is 0.0302, but its conservative upper bound grows as the assumed positional error grows: at 0.25 µm it remains guaranteed below 0.20; at 1.00 µm the conservative interval crosses the threshold and becomes indeterminate.

Sequence 02, track 19 traveled **84.791 µm**, net displacement **16.825 µm**, across 57 observations. Its measured persistence 0.1984 is very close to the 0.20 cutoff, so even a small allowed error makes the threshold assignment indeterminate. **Neither observed trajectory has a verified independent biological-state label.**

## What this does and does not establish

- **It establishes:** rigorous conditional bounds derived from triangle inequalities, using published image-derived measurements and the existing production quality gates. The high-level inference becomes appropriately cautious even when F1 association metrics are strong.
- **It does not measure:** the true centroid-localization error distribution, true cell speed, identity switching, lineage accuracy, or segmentation-induced centroid variability.
- **It does not assume:** random Gaussian noise, independent measurement errors, a cell-state prevalence, or independent biological replicates.
- **Next experiment:** retain predicted instance masks/centers and matched independent reference-center coordinates **per frame**, estimate localization-error magnitudes and systematic bias on a held-out annotated sequence, rerun trajectory aggregation with those measured errors, and separately quantify track fragmentation. This would turn a hypothetical geometric sensitivity bound into an empirically calibrated interpretation.

## Reproduce and verify

```bash
python scripts/audit_ctc_centroid_error_bounds.py --output /tmp/ctc_centroid_error_bounds.json
cmp /tmp/ctc_centroid_error_bounds.json docs/evidence/ctc/centroid_localization_bounds.json
pytest -q tests/test_ctc_centroid_error_bounds.py
```

CI regenerates the JSON byte-for-byte from the committed `docs/evidence/ctc/derived_phenotype_features.csv` and checks the file's SHA-256, monotonic broadening of intervals, physical feasibility and real-cohort gate count. The raw image-derived 168-frame scores are unchanged.
