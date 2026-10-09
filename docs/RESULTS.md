# Experimental Results

## CTC temporal association benchmark

Dataset: **DIC-C2DH-HeLa**, sequences 01 and 02.

The benchmark uses CTC reference track centroids as the detection input. Therefore these results measure **temporal association**, not image segmentation accuracy or end-to-end segmentation performance.

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

### External CTC TRA/LNK association-isolation validation

The same 8.0 µm mutual-nearest-neighbor association path was exported with the **reference CTC object geometry preserved** and evaluated with the pinned `py-ctcmetrics==1.3.3` implementation. This is a controlled association-isolation result, not an image-segmentation or biological-lineage score.

| Sequence | TRA | LNK | AOGM | AOGM0 | Result validation |
|---|---:|---:|---:|---:|---:|
| 01 | **0.997315** | **0.979091** | 34.5 | 12850.0 | Valid |
| 02 | **0.997207** | **0.978239** | 33.0 | 11816.5 | Valid |

Captured in GitHub Actions run **37662335395**, with evidence artifact **ctc-tra-lnk-evidence (11501247207)**. These values are reported separately from the custom **0.99228 F1** because the metrics are not interchangeable. The exported protocol carries reference lineage only where parent/child frame ranges remain compatible. These are reference-geometry association-isolation results and **not official Cell Tracking Challenge leaderboard scores**; the official submission evaluator was not used.

A lineage-sensitivity control then removed all reference parent edges while keeping the same tracker and reference geometry. The TRA/LNK values for both sequences were exactly unchanged, providing a conservative check against lineage-metadata inflation.

The 3.0 µm point produced mean F1 0.95015. The larger physical gate therefore recovered substantially more true links without collapsing precision.

### Downstream temporal phenotype preservation

## Cross-dataset PhC-C2DL-PSC association and identity

A second public CTC dataset is used to test association under a different microscopy modality: PhC-C2DL-PSC (phase-contrast pancreatic stem cells, 1.6 µm in-plane sampling, 10-minute frame interval). Official data and annotation documentation: https://celltrackingchallenge.net/2d-datasets/ and https://celltrackingchallenge.net/annotations/ .

This is a **reference-centroid association-isolation** benchmark. It does not evaluate detection, image segmentation, automatic lineage discovery, or biological phenotype classification.

The fixed 8.0 µm gate control from the reproducible association sweep yielded mean edge precision 0.99394, recall 0.98864, and edge F1 0.99128 across the two PSC sequences. These are edge-recovery metrics, not track-identity metrics. They must be interpreted with track counts and identity diagnostics: maximizing edge F1 can yield a different gate from preserving the complete track partition.

The updated benchmark computes pairwise trajectory-identity precision/recall/F1, predicted/reference track-count ratio, merged predicted tracks, and fragmented reference tracks. It selects a gate on one sequence by identity F1 (edge F1 and identity precision are tie-breakers), then evaluates that gate on the other sequence in both directions. It also tests the production `gap_hungarian` method with a two-frame observation window. Gap-spanning links are counted separately and excluded from adjacent-frame edge F1; every observation still contributes to trajectory-identity metrics.

**Fixed 8.0 µm gate control across both PSC sequences**

| Method | Adjacent-edge F1 | Identity precision | Identity recall | Identity F1 | Predicted/reference track ratio | Gap links per sequence (mean) |
|---|---:|---:|---:|---:|---:|---:|
| Mutual NN | 0.99128 | 0.72382 | 0.82140 | 0.76910 | 1.2833 | 0 |
| Mutual rescue | 0.99130 | 0.72308 | 0.82178 | 0.76886 | 1.2816 | 0 |
| Hungarian | 0.99045 | 0.73987 | 0.79896 | 0.76783 | 1.3968 | 0 |
| Velocity Hungarian | 0.98702 | 0.82554 | 0.72016 | 0.76879 | 1.7339 | 0 |
| Gap Hungarian (2-frame window) | 0.99111 | 0.73855 | 0.82420 | **0.77858** | **1.3190** | 112 |

**Two-way sequence holdout**

| Method | Selected gate 01→02 | Identity F1 01→02 | Selected gate 02→01 | Identity F1 02→01 | Mean identity F1 |
|---|---:|---:|---:|---:|---:|
| Mutual NN | 6.4 µm | 0.75592 | 8.0 µm | 0.75528 | 0.75560 |
| Mutual rescue | 6.4 µm | 0.75592 | 8.0 µm | 0.75560 | 0.75576 |
| Hungarian | 6.4 µm | 0.74831 | 8.0 µm | 0.75253 | 0.75042 |
| Velocity Hungarian | 8.0 µm | 0.77332 | 8.0 µm | 0.76427 | 0.76879 |
| Gap Hungarian (2-frame window) | 8.0 µm | **0.79346** | 8.0 µm | 0.76371 | **0.77858** |

In this reference-centroid benchmark, gap Hungarian raises mean holdout identity F1 by 0.0098 over velocity Hungarian and lowers the mean predicted/reference track-count ratio from 1.7339 to 1.3190. The trade-off is material: mean identity precision falls from 0.8255 to 0.7385 while recall rises from 0.7202 to 0.8242. This candidate reduces fragmentation, but it is **not promoted to the default tracker**: the result is asymmetric across sequence directions and must be re-evaluated when observations come from an image detector rather than the CTC reference centroids.

The benchmark is generated by `scripts/benchmark_ctc_phc_psc_association.py` and `.github/workflows/ctc-cross-domain.yml`. These measurements do **not** validate raw-image segmentation, autonomous lineage detection, biological meaning of unsupervised clusters, or official CTC leaderboard performance.


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

## Cross-sequence PhC-C2DL-PSC raw-image segmentation

This benchmark is deliberately separate from the reference-centroid association results above. A Random Forest was trained on annotated frames from sequence 01 and evaluated on sequence 02, then trained on sequence 02 and evaluated on sequence 01. No masks from the held-out sequence were used for fitting. Each direction used 24 training frames (from 300 annotated silver-mask frames available) and sampled 40 test frames. Training sampled at most 3,000 pixels per class per frame; the model used 60 trees, maximum depth 18, minimum leaf size 2, and random seed 42.

**Instance matching is one-to-one at IoU ≥ 0.5.** The assignment first maximizes the number of valid matches, then uses IoU as a tie-break. Precision, recall, and F1 below are frame-wise object metrics averaged across sampled frames; F1 is averaged per frame, not computed by pooling all pixels.

### Primary evaluation — silver SEG masks

| Train → test | Test frames sampled | Precision @ IoU 0.5 | Recall @ IoU 0.5 | Mean frame F1 @ IoU 0.5 |
|---|---:|---:|---:|---:|
| 01 → 02 | 40 | 0.2090 | 0.3200 | 0.2485 |
| 02 → 01 | 40 | 0.1881 | 0.2371 | 0.2055 |
| **Mean across directions** | — | **0.1986** | **0.2786** | **0.2270** |

This is weak instance-segmentation performance for a general-purpose cell-analysis pipeline: many reference cells are missed and predicted instances frequently fail the IoU matching threshold. The result is retained as a negative/diagnostic baseline, not presented as a competitive segmentation score.

### Sparse gold-mask cross-check

The official gold SEG annotations are available for only two frames in each held-out sequence, so this is a very small cross-check rather than a robust estimate.

| Train → test | Gold frames | Precision @ IoU 0.5 | Recall @ IoU 0.5 | Mean frame F1 @ IoU 0.5 |
|---|---:|---:|---:|---:|
| 01 → 02 | 2 | 0.3548 | 0.6229 | 0.4476 |
| 02 → 01 | 2 | 0.2951 | 0.4211 | 0.3468 |
| **Mean across directions** | — | **0.3250** | **0.5220** | **0.3972** |

The silver annotations are the primary higher-coverage evaluation. Neither silver-mask agreement nor this sparse gold sample is an independent biological validation or an official CTC leaderboard score. The two-way holdout was rerun successfully against current `main` at commit [`6d7bbc4`](https://github.com/chrishotza/ai4s-life-science-2026/commit/6d7bbc4ad4fece809b0752166230aeafc732a698) in [GitHub Actions run 37924623262](https://github.com/chrishotza/ai4s-life-science-2026/actions/runs/37924623262), with machine-readable results and code/data provenance in [artifact 11613811430](https://github.com/chrishotza/ai4s-life-science-2026/actions/runs/37924623262/artifacts/11613811430). The repeated metrics matched the values above (silver F1 0.22698; sparse gold F1 0.39723). This confirms reproducibility of this specific benchmark on that source snapshot; it does not improve the weak segmentation result.

Reproduce with:

    python scripts/benchmark_phc_psc_supervised_segmentation.py

## Raw-image validation status

These image-derived measurements are separate from the reference-centroid association scores above.

### Supervised DIC-C2DH-HeLa holdout

The completed two-way sequence holdout trained on one sequence and tested on the other. Across the held-out images, mean frame-wise instance F1 at IoU ≥ 0.5 was **0.09155**; the image-derived detection F1 was **0.37728**, and temporal-link F1 after image-derived detection was **0.09716**. This run completed successfully and uploaded [artifact 11605411442 from Actions run 37907638057](https://github.com/chrishotza/ai4s-life-science-2026/actions/runs/37907638057/artifacts/11605411442).

These are weak end-to-end image-derived results. They show that the current supervised baseline does not yet reliably connect raw DIC images to tracks. The success status of the workflow means the benchmark completed, not that its accuracy is adequate.

### Strict non-overlapping temporal holdout

A completed temporal holdout trained on earlier frames and evaluated on later, non-overlapping frames of the same CTC sequences. Its mean image-derived segmentation F1 at IoU ≥ 0.5 was **0.14942**, detection F1 was **0.43454**, tracking-edge F1 was **0.30197**, and sparse-gold object recall at IoU ≥ 0.5 was **0.1132**. The predefined quality gate required segmentation F1 ≥ 0.25, detection F1 ≥ 0.50, and sparse-gold recall ≥ 0.20, so the gate correctly **failed**. The benchmark completed and uploaded [artifact 11605019590 from Actions run 37907133446](https://github.com/chrishotza/ai4s-life-science-2026/actions/runs/37907133446/artifacts/11605019590).

This is a distinct temporal-split protocol from the sequence-held-out supervised result above; their numbers are not directly comparable. Both show that current image-derived baselines do not yet meet the desired end-to-end performance.

### Pretrained Cellpose-SAM partial run

A separate run evaluated `cpsam_v2` on raw DIC-C2DH-HeLa frames with one-to-one instance matching at IoU ≥ 0.5. Before cancellation, it completed 40/40 sampled frames from sequence 01 (mean frame F1 **0.92903**) and 14/40 from sequence 02 (mean frame F1 **0.94621**). The [Actions log](https://github.com/chrishotza/ai4s-life-science-2026/actions/runs/37899689242) contains these per-frame outputs.

This is promising partial segmentation evidence only. The run was cancelled before the second sequence, the aggregate JSON and artifact were not produced, and no complete image-derived tracking-to-phenotype score is available from it. Do not treat these partial frame means as a completed benchmark or combine them with the supervised holdout metrics.

### Bounded Cellpose image-to-tracking pilot

A subsequent bounded pilot evaluated the first **4 frames from each sequence** (8 total) using the same pretrained cpsam_v2 model and one-to-one IoU ≥ 0.5 segmentation match. It reported:

- Mean instance segmentation F1: **0.87490**
- Image-derived detection F1: **0.88810**
- Tracking-edge F1: **0.89180**

The [Actions run](https://github.com/chrishotza/ai4s-life-science-2026/actions/runs/37912623248) and [captured JSON artifact](https://github.com/chrishotza/ai4s-life-science-2026/actions/runs/37912623248/artifacts/11608135086) preserve the evidence. The sample covers only the opening four frames of each sequence, so the result is exploratory; it does not establish robust cross-time generalization or biological phenotype validity. These pilot metrics are separate from both the earlier cancelled partial run and the supervised holdout.



### End-to-end tracking-to-phenotype robustness

A controlled synthetic benchmark now re-runs the temporal association stage after injecting coordinate noise and detection dropout, then carries those predictions through temporal phenotype extraction and unsupervised phenotype discovery. It reports predicted track count, mean track purity, and phenotype-group ARI against the known synthetic behavioral groups.

This experiment closes an important methodological gap in the earlier phenotype-stability test: the earlier test perturbed already-known tracks, while this benchmark perturbs detections and **reconstructs tracks before phenotype analysis**. It remains a controlled synthetic validation and is not a biological phenotype result.

Reproduce with:

    python scripts/benchmark_end_to_end_phenotype.py

### Bounded-gap association robustness

A separate controlled synthetic stress test evaluates the experimental `gap_hungarian` branch under coordinate noise and detection dropout. The production baseline remains adjacent-frame mutual nearest neighbor; the gap branch is not used to revise the real-data 0.99228 F1 headline.

| Dropout | MNN fragmented truth tracks | Gap-Hungarian fragmented truth tracks | MNN phenotype ARI | Gap-Hungarian phenotype ARI |
|---:|---:|---:|---:|---:|
| 5% | 24 | **1** | -0.0184 | **0.4879** |
| 10% | 29 | **7** | -0.0102 | **0.3584** |
| 15% | 30 | **19** | 0.0007 | -0.0114 |

The bounded-gap branch produced 42/42, 87/87, and 93/93 correct-identity gap links at 5%, 10%, and 15% dropout respectively in this synthetic benchmark.

The result is important because the dominant MNN failure mode under missing observations is fragmentation rather than false cross-identity linking. `gap_hungarian` substantially reduces fragmentation in the mild and moderate dropout regimes while exposing explicit `frame_gap` and link-confidence metadata.

This is controlled computational evidence, not real-data biological validation. The branch remains experimental until it demonstrates a benefit under a public linking-oriented evaluation and the frozen A/B acceptance gates.

### Tracking error taxonomy

The robustness benchmark now records a deterministic error profile for each condition, including:

- identity switches;
- fragmented reference tracks and oversegmentation events;
- merged predicted tracks and merge events;
- true-positive, false-positive, and missed links;
- cross-identity false links;
- temporally invalid false links;
- bounded-gap link counts and correct-identity gap links.

This taxonomy is used diagnostically and does not replace the headline association metrics.

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
