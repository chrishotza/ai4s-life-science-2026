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

A reproducible sweep evaluated mutual nearest neighbor, Hungarian assignment, and constant-velocity Hungarian assignment using the CTC DIC pixel scale of 0.19 µm in-plane.

| Method | Threshold | Mean precision | Mean recall | Mean F1 |
|---|---:|---:|---:|---:|
| Mutual NN | **8.0 µm** | 0.99135 | **0.99322** | **0.99228** |
| Hungarian | 8.0 µm | 0.99134 | 0.99230 | 0.99182 |
| Velocity Hungarian | 8.0 µm | 0.99129 | 0.98609 | 0.98868 |

The best measured configuration is therefore **mutual-nearest-neighbor at 8.0 µm**, with mean F1 **0.99228** across the two real sequences.

Per-sequence results:

| Sequence | GT tracks | Predicted tracks | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|
| 01 | 38 | 35 | 0.99171 | 0.99446 | 0.99308 |
| 02 | 32 | 31 | 0.99099 | 0.99198 | 0.99149 |

Compared with the initial mean F1 of 0.9183, the calibrated physical-unit configuration reaches **0.9923 mean F1** while retaining approximately **0.991 precision**.

The 3.0 µm point produced mean F1 0.95015. The larger physical gate therefore recovered substantially more true links without collapsing precision.

### Downstream temporal phenotype preservation

A second real-data experiment pushed the selected tracker into the phenotype layer.

The experiment again used CTC reference centroids as detections, so it measures **phenotype preservation under tracking**, not image segmentation or biological phenotype classification.

For every predicted track matched to a reference track, the benchmark measured trajectory coverage and absolute error in:

- duration;
- observations;
- displacement;
- path length;
- mean speed;
- directional persistence.

Aggregate results across both CTC sequences:

| Metric | Result |
|---|---:|
| Matched tracks | 27.5 mean / sequence |
| Mean trajectory coverage | **0.9451** |
| Median trajectory coverage | **1.0000** |
| Duration MAE | 6.2184 frames |
| Displacement MAE | 2.1605 µm |
| Path-length MAE | 9.9353 µm |
| Mean-speed MAE | 0.1206 µm/frame |
| Directional-persistence MAE | **0.0439** |

Per sequence:

| Sequence | Matched tracks | Mean coverage | Median coverage | Speed MAE | Directional-persistence MAE |
|---|---:|---:|---:|---:|---:|
| 01 | 31 | 0.9557 | 1.0000 | 0.0615 | 0.0307 |
| 02 | 24 | 0.9346 | 1.0000 | 0.1797 | 0.0572 |

The important result is that the downstream temporal phenotype is comparatively stable for matched tracks: the median track coverage is 100%, and directional persistence has a mean absolute error of only 0.0439 across the two sequences.

### End-to-end tracking-to-phenotype robustness

A controlled synthetic benchmark now re-runs the temporal association stage after injecting coordinate noise and detection dropout, then carries those predictions through temporal phenotype extraction and unsupervised phenotype discovery. It reports predicted track count, mean track purity, and phenotype-group ARI against the known synthetic behavioral groups.

This experiment closes an important methodological gap in the earlier phenotype-stability test: the earlier test perturbed already-known tracks, while this benchmark perturbs detections and **reconstructs tracks before phenotype analysis**. It remains a controlled synthetic validation and is not a biological phenotype result.

Reproduce with:

    python scripts/benchmark_end_to_end_phenotype.py

### Lineage and division representation validation

A dedicated benchmark now evaluates the lineage layer against the CTC reference parent/child annotations for sequences 01 and 02. It checks division-parent recovery as well as exact child-count and descendant-count reconstruction.

This result is intentionally classified as **lineage representation validation**. The current baseline tracker creates temporal links but does not claim image-derived biological division detection. The benchmark therefore strengthens the evidence that the phenotype layer correctly consumes and represents lineage structure without inflating the end-to-end tracking claim.

Reproduce with:

    python scripts/benchmark_ctc_lineage.py

The raw benchmark output is generated locally as ctc_lineage_results.json and is not treated as a committed dataset.

### Interpretation

The initial failure mode was track fragmentation caused by an overly restrictive distance gate. Physical calibration corrected most of that association loss.

The phenotype experiment then shows that the selected association layer preserves meaningful trajectory-derived features sufficiently well to support the next stage of the system.

This does **not** establish biological phenotype validity. That requires a dataset with biological phenotype labels or perturbation annotations. The current result establishes reproducible preservation of trajectory-derived phenotype features.

## Evidence policy

Only measured outputs from reproducible benchmark runs are included.

No synthetic score is presented as a real-data result.
No segmentation performance is inferred from centroid-association performance.
No biological phenotype claim is inferred from trajectory agreement alone.
