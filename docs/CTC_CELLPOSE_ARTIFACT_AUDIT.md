# CTC Cellpose 168-frame artifact audit
Status: **measured artifact audit**, not a new benchmark run. Source: GitHub Actions run `37930909373`, artifact `11622434978`, commit `ffc135c56fb5adcf2d23bcf4e8461ba284dcc870`.
## Integrity
- results: verified
- sequence_01_phenotypes: verified
- sequence_02_phenotypes: verified

## What the completed run shows
- Frames evaluated: **168** raw DIC-C2DH-HeLa frames (84 from sequence 01 and 84 from sequence 02).
- Sequence 01: segmentation F1@IoU50 **0.9198**, detection F1 **0.9532**, tracking-edge F1 **0.9804**, phenotype profiles **79**.
- Sequence 02: segmentation F1@IoU50 **0.9511**, detection F1 **0.9835**, tracking-edge F1 **0.9813**, phenotype profiles **47**.

## Phenotype output actually produced
- Total phenotype profiles: **126** (seq01: 79, seq02: 47).
- Overall mean track-integrity score: **0.596**.
- Overall mean phenotype-reliability score: **0.372**.
- Fraction of tracks with integrity >= 0.8: **61.1%**.
- Fraction of tracks with phenotype reliability >= 0.5: **44.4%**.

### Descriptive cluster counts

| sequence | exploratory_motion | high_motility | persistent_or_stable |
|---:|---:|---:|---:|
| 01 | 33 | 33 | 13 |
| 02 | 18 | 18 | 11 |

### Largest descriptive sequence differences

| feature | mean01 | mean02 | Cohen d, seq01 - seq02 |
|:--|--:|--:|--:|
| mean_area | 7305.213 | 10828.651 | -0.694 |
| phenotype_assignment_quality | 0.601 | 0.459 | 0.495 |
| phenotype_reliability_score | 0.327 | 0.448 | -0.429 |
| track_integrity_score | 0.538 | 0.694 | -0.363 |
| duration | 14.063 | 21.043 | -0.287 |
| observations | 15.063 | 22.043 | -0.287 |
| displacement | 3.606 | 4.957 | -0.267 |
| mean_speed | 1.113 | 1.419 | -0.260 |

## Competitive meaning
- **Strong engineering result:** the product path generated high segmentation/detection/tracking metrics and exported per-track phenotype tables for a complete 168-frame raw-image run.
- **Not yet a winning biological claim:** the artifact contains no independent perturbation, treatment, or biological-state labels. The observed sequence differences are descriptive domain differences, not validated phenotype discovery.
- **Most important next experiment:** evaluate the phenotype layer on an independent time-lapse dataset with biological condition labels, using held-out wells/sequences and baselines that omit the phenotype-discovery layer.
