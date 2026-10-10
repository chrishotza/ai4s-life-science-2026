# A real microscopy example: moving versus migrating

**What a biologist can ask:** Which individual cells move repeatedly yet remain close to their starting position? A speed-only measurement cannot distinguish movement along a wandering path from sustained net displacement.

## Measurements from a completed image-derived run

The dataset is **CTC DIC-C2DH-HeLa**, sequence 02, and the image backend is pretrained **CellposeSAM-v2**, followed by deterministic tracking and feature extraction. The numeric values below are taken from the [committed derived feature table](evidence/ctc/derived_phenotype_features.csv) produced by the verified [168-frame end-to-end run](https://github.com/chrishotza/ai4s-life-science-2026/actions/runs/37930909373).

| Predicted trajectory | Observations | Total path (µm) | Net displacement (µm) | Speed (µm/frame) | Directional persistence | Reliability |
|---|---:|---:|---:|---:|---:|---:|
| Sequence 02, track 21 | 66 | 142.10 | 4.29 | 2.19 | 0.030 | 0.607 |
| Sequence 02, track 19 | 57 | 84.79 | 16.83 | 1.51 | 0.198 | 0.625 |

![Path versus net displacement for two measured trajectories](figures/ctc_real_motility_example.svg)

**Explanation:** The first trajectory covers more total ground while ending closer to its start. Directional persistence is simply **net displacement divided by total traveled distance**; values near zero indicate little progress relative to the path length. The second measured trajectory is less active by mean speed but has greater net displacement and directional persistence.

This is the output of the pipeline's **temporal measurement layer**—a concrete answer to a useful *computational* question beyond cell detection. Both selected tracks exceed the minimum observation count (3) and reliability score (0.5) thresholds, and are therefore eligible only for **descriptive** interpretation under the existing [confidence gate](evidence/ctc/confidence_gated_phenotype_summary.json).

## What it does not establish

- These tracks were selected **post hoc to illustrate** existing output; no inferential group test or effect size was estimated from two examples.
- Track IDs are computed associations, not independently validated biological cell identities.
- The project **does not** claim that these cells belong to different biological states, had specific treatments, or displayed a verified migration mechanism.
- The CTC generalization and ALFI domain-shift limitations remain as reported; the example does not supersede those benchmarks.

## Why the research-software contribution matters

The novelty is **not** a new image foundation model. It is the reproducible combination of pretrained cell segmentation, calibrated temporal association, interpretable motion features, quality gating, and an audit trail so an investigator can identify candidate cells for further biological review.

For an actual validated life-science claim, an independent experiment would need treatment/control labels, held-out batches or wells, verified masks/tracks, predefined motility endpoints, and replicate-level statistics.
