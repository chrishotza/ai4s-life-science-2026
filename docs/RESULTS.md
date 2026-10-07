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

The second reproducible run evaluated mutual nearest neighbor, Hungarian assignment, and constant-velocity Hungarian assignment using the CTC DIC pixel scale of 0.19 µm in-plane and a physical distance threshold.

| Method | Threshold | Mean precision | Mean recall | Mean F1 |
|---|---:|---:|---:|---:|
| Mutual NN | **8.0 µm** | 0.99135 | **0.99322** | **0.99228** |
| Hungarian | 8.0 µm | 0.99134 | 0.99230 | 0.99182 |
| Velocity Hungarian | 8.0 µm | 0.99129 | 0.98609 | 0.98868 |

The best measured configuration is therefore **mutual-nearest-neighbor at 8.0 µm**, with mean F1 **0.99228** across the two real sequences.

Per-sequence results for that configuration:

| Sequence | GT tracks | Predicted tracks | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|
| 01 | 38 | 35 | 0.99171 | 0.99446 | 0.99308 |
| 02 | 32 | 31 | 0.99099 | 0.99198 | 0.99149 |

Compared with the initial mean F1 of 0.9183, the calibrated physical-unit configuration reaches **0.9923 mean F1** while retaining approximately **0.991 precision**.

The 3.0 µm point is also informative: mean F1 was 0.95015. Increasing the physical gate to 8.0 µm recovers substantially more true links without collapsing precision.

### Interpretation

The initial failure mode was track fragmentation caused by an overly restrictive distance gate. On this CTC association benchmark, the strongest simple baseline is not the velocity model: it is a physically calibrated mutual-nearest-neighbor association with a permissive 8.0 µm gate.

This is a useful result because it gives us a measured, reproducible reference configuration before introducing additional learned or lineage-aware machinery.

## Evidence policy

Only measured outputs from reproducible benchmark runs are included.

No synthetic score is presented as a real-data result.
No segmentation performance is inferred from centroid-association performance.
