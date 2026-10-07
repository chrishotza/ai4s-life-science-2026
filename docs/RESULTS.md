# Experimental Results

## CTC temporal association benchmark

Dataset: **DIC-C2DH-HeLa**, sequences 01 and 02.

The current benchmark uses the CTC reference track centroids as the detection input. Therefore these results measure **temporal association**, not image segmentation accuracy.

### Initial measured baseline

The first reproducible run used mutual-nearest-neighbor association with a 12-coordinate-unit distance threshold.

| Sequence | Detections | GT tracks | Predicted tracks | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| 01 | 1120 | 38 | 211 | 1.0000 | 0.8401 | 0.9131 |
| 02 | 1030 | 32 | 170 | 0.9977 | 0.8597 | 0.9236 |

These values were produced by GitHub Actions from the public benchmark archive and stored as a JSON artifact. They must not be interpreted as end-to-end microscopy performance.

### Active ablation

The repository now evaluates:

- mutual nearest neighbor;
- global Hungarian assignment;
- constant-velocity Hungarian assignment;

across a physical distance grid of 0.8–3.0 µm using the CTC DIC pixel scale.

The sweep is designed to answer whether global assignment and motion prediction improve recall without materially reducing precision.

**The final ablation table will be populated only from the completed GitHub Actions run.**

## Interpretation

The initial baseline is already highly precise but loses links primarily through missed associations, as reflected by substantially higher recall loss than precision loss.

That makes the next technical target clear: recover difficult links rather than simply increasing the number of accepted matches.

The velocity-aware and globally optimal association variants are specifically intended to address that failure mode.

## Evidence policy

Only measured outputs from the public repository and reproducible benchmark runs will be included in the final submission.

No synthetic score is presented as a real-data result.
No segmentation performance is inferred from centroid-association performance.
