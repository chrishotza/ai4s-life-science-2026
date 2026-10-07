# Experimental Results

## CTC temporal association benchmark

Dataset: **DIC-C2DH-HeLa**, sequences 01 and 02.

The benchmark uses the CTC reference track centroids as the detection input. Therefore these results measure **temporal association**, not image segmentation accuracy.

### Initial measured baseline

The first reproducible run used mutual-nearest-neighbor association with a 12-coordinate-unit distance threshold.

| Sequence | Detections | GT tracks | Predicted tracks | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| 01 | 1120 | 38 | 211 | 1.0000 | 0.8401 | 0.9131 |
| 02 | 1030 | 32 | 170 | 0.9977 | 0.8597 | 0.9236 |

### Physical-unit ablation

A second reproducible run evaluated mutual nearest neighbor, Hungarian assignment, and constant-velocity Hungarian assignment using the CTC DIC pixel scale of 0.19 µm in-plane and a physical distance threshold.

At **3.0 µm**, the best mean-F1 configuration in that sweep was Hungarian assignment:

| Method | Threshold | Mean precision | Mean recall | Mean F1 |
|---|---:|---:|---:|---:|
| Hungarian | 3.0 µm | 0.99734 | 0.90736 | **0.95015** |
| Mutual NN | 3.0 µm | 0.99734 | 0.90736 | **0.95015** |
| Velocity Hungarian | 3.0 µm | 0.99730 | 0.89283 | 0.94212 |

Per-sequence results for the best 3.0 µm configuration:

| Sequence | Predicted tracks | Precision | Recall | F1 |
|---|---:|---:|---:|---:|
| 01 | 153 | 0.99793 | 0.89187 | 0.94192 |
| 02 | 106 | 0.99675 | 0.92285 | 0.95838 |

This raises mean F1 from the initial 0.9183 average to 0.9501 while maintaining approximately 0.997 precision.

A wider 3.0–8.0 µm sweep has been launched to test whether additional difficult links can be recovered without excessive false associations.

### Interpretation

The central failure mode is track fragmentation: precision is already very high, while recall remains the limiting metric.

The next technical target is therefore **continuity recovery** rather than simply accepting more links. Candidate directions are longer-range motion-aware association, gap closing, and lineage-aware relinking.

## Evidence policy

Only measured outputs from reproducible benchmark runs are included.

No synthetic score is presented as a real-data result.
No segmentation performance is inferred from centroid-association performance.
