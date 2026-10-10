# Cohort-level motility sensitivity audit (image-derived CTC)

**Scope:** An **additional retrospective computational audit of already exported features**, not a new segmentation run or biological validation. Source: the 168-frame pretrained CellposeSAM-v2 experiment from [GitHub Actions run 37930909373](https://github.com/chrishotza/ai4s-life-science-2026/actions/runs/37930909373).

**Reproduction:** `python scripts/audit_ctc_motility_cohort.py --output /tmp/motility.json`. The committed result [JSON](evidence/ctc/motility_cohort_sensitivity.json) is regenerated from the immutable source [CSV](evidence/ctc/derived_phenotype_features.csv); it contains the source SHA-256, exact confidence-gate counts, cohort medians, and sequence-stratified results. The CI job verifies the JSON against the regenerated result.

## Researcher-facing question

Which cell tracks show considerable **motion along a path** without substantial **net migration**? Directional persistence is the ratio **net displacement / accumulated path length**. It is a numerical description of the trajectory, not an independently confirmed cell state.

From the pipeline's **126 predicted trajectories**, the existing production confidence gate limits descriptive reporting to **51 profiles**. The other **54 audit-only** and **21 low-reliability** profiles are retained but are not allowed to support behavioral claims.

We examined five **computational sensitivity cohorts**, each selected *without biological labels*. A persistence value below **0.20** is an **illustrative cutoff**, not a validated biological classification threshold.

| Minimum observations | Minimum reliability | Eligible tracks | Median persistence | With persistence < 0.20 |
|---|---|---:|---:|---:|
| 3 | 0.50 | **51** | 0.183 | **33/51 (64.7%)** |
| 10 | 0.50 | 35 | 0.128 | 31/35 (88.6%) |
| 20 | 0.50 | 24 | 0.126 | 22/24 (91.7%) |
| 3 | 0.65 | 19 | 0.192 | 10/19 (52.6%) |
| 10 | 0.65 | 12 | 0.132 | 10/12 (83.3%) |

**Sequence-stratified check (standard gate):** sequence 01 had **12/24** tracks below 0.20 (50.0%); sequence 02 had **21/27** (77.8%). The two sequences differ appreciably. These data **cannot** establish a population effect or generalization beyond the two imaging sequences.

## Additional measured example

- Sequence 02, track 21: **66 observations**, traveled 142.10 µm, net displacement 4.29 µm, persistence 0.030.
- Sequence 02, track 19: **57 observations**, traveled 84.79 µm, net displacement 16.83 µm, persistence 0.198.

This is a **post-hoc illustration**, not a randomized or statistically significant group comparison. [See existing figure and complete interpretive boundary](CTC_REAL_MOTILITY_CASE_STUDY.md).

## Robustness and failure boundaries

- **Validations added:** exact reproduction of the production 54/21/51 confidence counts; order-invariance tests; rejection of duplicate track identifiers, missing/non-finite fields, negative or geometrically impossible motion, and persistence inconsistent with displacement/path; sensitivity by sequence, track length and reliability.
- **What changes with gating:** the fraction below the example 0.20 cutoff moves from **52.6% to 91.7%** across the shown filters. This variation prevents any blanket claim that a fixed biological fraction is measured.
- **What does not follow:** segmentation score F1 0.9354 and tracking-edge F1 0.9808 do not prove exact trajectory geometry or low-noise per-cell motility. Cell boundary changes, centroid localization jitter and track fragmentation can inflate accumulated path length, thereby decreasing the persistence ratio. This audit uses exported predicted tracks, not independent manually annotated path geometry. An appropriately calibrated noise-control experiment is still needed. A [new empirical 16-frame comparison to CTC silver-mask centroids](CTC_EMPIRICAL_CENTROID_CALIBRATION.md) observed median **0.909 µm** and p95 **2.701 µm** matched-instance discrepancies, but it does not bound complete tracked trajectories or establish true biological-center localization accuracy.
- **Sampling limitations:** only two CTC sequences, without independently replicated experimental batches or condition labels. Trajectories within a movie are correlated; no confidence interval, independence assumption, hypothesis-test p-value, treatment-response claim or biological-state label is offered.
- **Source integrity:** the report includes SHA-256 of its frozen input CSV and links to the original full-image inference workflow. The code does not access future observations for earlier state *prediction*, but this retrospective full-track movement summary necessarily describes the complete observed track.

**Conclusion:** the system can compute, quality-gate and audit per-cell temporal migration descriptors across the **entire measured CTC cohort**. This supports a reproducible *researcher-facing measurement workflow*, not yet an independently validated biological effect.
