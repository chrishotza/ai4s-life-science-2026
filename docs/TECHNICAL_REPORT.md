# Technical Report — Temporal Cellular Phenotype Engine

## 1. Project summary

The Temporal Cellular Phenotype Engine is an end-to-end microscopy analysis pipeline designed to turn time-lapse cell observations into interpretable dynamic phenotype profiles.

The core hypothesis is that biological information is often contained not only in a cell's appearance at one frame, but in its trajectory: persistence, motility, temporal stability, division behavior, and lineage context.

The system therefore combines image-to-detection preprocessing, temporal association, 3-D tracking, lineage/event inference, feature extraction, and unsupervised phenotype discovery.

## 1.1 Team information

**Team:** Chris Hotza  
**Team leader:** Chris Hotza  
**Role:** primary researcher, system architect, implementation, benchmarking, and submission lead.

The final team roster and team-lead designation must match the official Kaggle registration exactly at submission time.

## 2. Problem

Many microscopy workflows provide segmentation masks or tracks but stop before producing a compact, interpretable description of cellular state.

The competition target is single-cell phenotype analysis. The system addresses that target by treating tracking as infrastructure for downstream temporal phenotype discovery.

## 3. System architecture

The submission implementation exposes a canonical TemporalPhenotypeEngine that can start from microscopy frames or precomputed detections. Internal data contracts and a centralized physical-coordinate transform are shared by tracking, lineage, and phenotype layers.

### 3.1 Microscopy preprocessing

The submission retains a transparent generic threshold/connected-component baseline, but the DIC-C2DH-HeLa validation also includes a dataset-specific deterministic ridge segmenter. The latter is a faithful implementation of the public KTH-SE DIC ridge methodology: multi-scale Gaussian smoothing at sigma 5–10 px, Hessian eigenvalue ridge response, ridge normalization/thresholding, and local-variance filtering. It is treated as a classical image-processing baseline rather than a pretrained model.

### 3.2 Temporal association

The tracker supports deterministic association strategies including the validated adjacent-frame baseline and experimental variants:

1. mutual-nearest-neighbor;
2. globally optimal Hungarian assignment;
3. constant-velocity prediction followed by Hungarian assignment;
4. mutual nearest neighbor with KD-tree candidate search;
5. bounded-gap Hungarian association for incomplete temporal observations.

Distances can be computed in physical units using sequence-specific voxel sizes.

### 3.3 Lineage and events

Candidate parent-to-daughter events are inferred from terminated tracks and newly appearing nearby tracks. Public Cell Tracking Challenge metadata can also be loaded directly when available.

### 3.4 Temporal phenotype extraction

For each track, the engine computes:

- duration;
- number of observations;
- displacement;
- path length;
- mean speed;
- directional persistence;
- parent count;
- child count;
- descendant count;
- division-event flag;
- observation fraction and temporal-gap diagnostics;
- tracking-link distance and confidence diagnostics.

### 3.5 Phenotype discovery

Standardized temporal features are clustered with K-Means to obtain unsupervised behavioral groups. The clusters are reported together with interpretable feature summaries rather than opaque class IDs alone.

### 3.5.1 Assignment confidence

Each discovered phenotype assignment now records distance to its assigned cluster center and the margin to the second-nearest cluster center. These values are intended for uncertainty visualization and filtering, not as calibrated probabilities.

### 3.6 Auxiliary observation features

When detections contain numeric measurements beyond coordinates and identifiers, the phenotype layer now preserves per-track summaries of those observations. The current microscopy baseline exposes area and mean intensity, so these measurements are retained for future morphology-and-motion analyses.

The published discovery benchmark remains trajectory/lineage-only. Auxiliary features are therefore additive metadata, not a silent change to the validated clustering feature space.


## 4. Data

### 4.1 Synthetic benchmark

The repository contains deterministic microscopy-like image generators and trajectory ground truth for regression testing and controlled perturbation experiments.

### 4.2 Cell Tracking Challenge

The Cell Tracking Challenge publishes freely downloadable 2D+time and 3D+time microscopy datasets, including reference tracking annotations and lineage metadata. The repository includes an adapter for `man_track*.tif` and `man_track.txt` data.

**Data provenance and use conditions:** the DIC-C2DH-HeLa training archive used here is distributed through the official Cell Tracking Challenge dataset repository: https://celltrackingchallenge.net/2d-datasets/ . The repository downloads the training archive transiently for reproduction and does not redistribute the microscopy data or reference annotations. The Cell Tracking Challenge instructs users to review its image-use conditions before download or reuse; the final submission should preserve that provenance and comply with those conditions.

### 4.3 Secondary validation scope

No secondary Organ-on-a-Chip dataset is used in the reported quantitative results. The validated real-data evidence in this submission is based on the DIC-C2DH-HeLa sequences described above.

## 5. Experimental design

The evaluation contains three levels:

### A. Unit and regression tests

Deterministic tests cover image preprocessing, tracking, lineage inference, phenotype extraction, clustering, and public CTC loading.

### B. Controlled synthetic benchmark

Known 3-D trajectories and exact temporal links are used to test association metrics and regression behavior.

### C. Public microscopy benchmark

The CTC experiment uses DIC-C2DH-HeLa sequences 01 and 02. The association benchmark feeds reference track centroids as detections, isolating the temporal-association problem from segmentation.

### Image-level validation track

To close the boundary between image processing and association-only validation, the repository now includes two additional cross-sequence holdout experiments. The first begins from raw DIC-C2DH-HeLa microscopy, performs transparent object detection, and then measures both object-level detection and temporal-link recovery after tracking. Detector settings are selected on one sequence and evaluated on the other.

The second compares the same transparent segmentation baseline against the available CTC GT/SEG instance annotations using frame-level instance matching. These measurements are reported as an independent image-segmentation validation layer and are not substituted for official CTC SEG leaderboard scores.

### Measured CTC association results

An initial mutual-nearest-neighbor run achieved:

| Sequence | Precision | Recall | F1 |
|---|---:|---:|---:|
| 01 | 1.0000 | 0.8401 | 0.9131 |
| 02 | 0.9977 | 0.8597 | 0.9236 |

A physical-unit method/gating sweep was then run over mutual nearest neighbor, Hungarian assignment, and constant-velocity Hungarian assignment.

The best measured configuration was **mutual-nearest-neighbor at 8.0 µm**:

| Method | Threshold | Mean precision | Mean recall | Mean F1 |
|---|---:|---:|---:|---:|
| Mutual NN | 8.0 µm | 0.99135 | 0.99322 | **0.99228** |
| Hungarian | 8.0 µm | 0.99134 | 0.99230 | 0.99182 |
| Velocity Hungarian | 8.0 µm | 0.99129 | 0.98609 | 0.98868 |

Per-sequence results for the best configuration:

| Sequence | GT tracks | Predicted tracks | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|
| 01 | 38 | 35 | 0.99171 | 0.99446 | 0.99308 |
| 02 | 32 | 31 | 0.99099 | 0.99198 | 0.99149 |

Mean F1 therefore increased from 0.9183 in the initial run to **0.9923** in the calibrated physical-unit configuration, while precision remained approximately 0.991.

At 3.0 µm, mean F1 was 0.95015, showing that the larger physical gate recovered substantially more true links without collapsing precision.

These results identify overly restrictive spatial gating as a major source of track fragmentation on this association benchmark.

### External CTC-maintained TRA/LNK validation

The selected 8.0 µm mutual-nearest-neighbor path was exported with the CTC reference object geometry preserved and evaluated using the pinned `py-ctcmetrics==1.3.3` implementation. Both generated result directories passed CTC validation.

| Sequence | TRA | LNK | AOGM | AOGM0 |
|---|---:|---:|---:|---:|
| 01 | **0.997315** | **0.979091** | 34.5 | 12850.0 |
| 02 | **0.997207** | **0.978239** | 33.0 | 11816.5 |

These measurements are **reference-geometry association-isolation evidence**. They are not segmentation scores, not biological lineage validation, and **not official Cell Tracking Challenge leaderboard scores**. The official challenge submission evaluator remains separate. A separate no-oracle sensitivity control removed all reference parent edges and produced the same TRA/LNK values, strengthening the interpretation that these metrics are not driven by reference lineage metadata in this benchmark.

### Downstream temporal phenotype preservation

The selected 8.0 µm tracker was then evaluated at the phenotype layer on the same two real sequences.

This experiment uses CTC reference centroids as detections. Consequently it measures **preservation of trajectory-derived phenotype features under tracking**, not segmentation quality or biological phenotype classification.

For matched predicted/reference trajectories, the benchmark measured coverage and absolute error for duration, observations, displacement, path length, mean speed, and directional persistence.

Aggregate results:

| Metric | Result |
|---|---:|
| Mean matched tracks per sequence | 27.5 |
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

The median trajectory coverage of 1.0 indicates that at least half of the matched trajectories retain complete frame coverage. Directional persistence is also comparatively stable, with mean absolute error 0.0439 across the two sequences.

This provides downstream evidence that the selected temporal association configuration preserves trajectory-derived phenotype features, while remaining explicit that biological phenotype validity requires independent biological labels or perturbation annotations.

## 6. End-to-end robustness validation

A controlled synthetic benchmark now perturbs detection coordinates and introduces missing observations before re-running the tracker and phenotype pipeline. This produces a stricter end-to-end robustness test than perturbing completed trajectories, because association errors can propagate into the phenotype representation.

The benchmark reports track purity and phenotype-group adjusted Rand index against the known synthetic behavioral groups. It is explicitly treated as controlled computational evidence rather than biological validation.

## 6.1 Bounded-gap robustness and error diagnostics

The experimental `gap_hungarian` branch retains unmatched tracks for a bounded number of frames and emits an explicit `frame_gap` field. A controlled synthetic stress test evaluates this branch against the production mutual-nearest-neighbor baseline after coordinate noise and detection dropout.

| Dropout | MNN fragmented truth tracks | Gap-Hungarian fragmented truth tracks | MNN phenotype ARI | Gap-Hungarian phenotype ARI |
|---:|---:|---:|---:|---:|
| 5% | 24 | **1** | -0.0184 | **0.4879** |
| 10% | 29 | **7** | -0.0102 | **0.3584** |
| 15% | 30 | **19** | 0.0007 | -0.0114 |

The gap branch preserved reference identity for 42/42, 87/87, and 93/93 gap links in the 5%, 10%, and 15% conditions respectively.

The benchmark also reports a deterministic tracking-error taxonomy covering identity switches, fragmentation, oversegmentation, merges, false and missed links, cross-identity false links, temporally invalid links, and gap-link correctness. This makes failure diagnosis explicit instead of collapsing every error into a single F1 value.

The gap branch remains experimental. It is not used to replace the validated 8.0 µm MNN real-data headline, and promotion requires passing the repository A/B gates plus an appropriate linking-oriented external evaluation.

## 7. Lineage validation

### Lineage and division representation validation

The public lineage layer is now validated separately from the association benchmark using the CTC reference lineage graph for sequences 01 and 02. The benchmark reconstructs parent-child relations from the published lineage metadata, passes the resulting edges through the phenotype engine, and checks division-parent recovery plus exact child-count and descendant-count reconstruction.

This establishes that the phenotype representation faithfully carries annotated lineage structure. It is deliberately not reported as an image-derived division-detection score: the current baseline tracker does not claim biological division inference from microscopy alone.

### Experimental bounded-gap association

In addition to the validated adjacent-frame baseline, the repository now contains an isolated `gap_hungarian` branch that retains unmatched tracks for up to two frames and emits explicit frame-gap metadata.

This branch is evaluated only through the existing A/B protocol and is not part of the published baseline. Its purpose is to test robustness to incomplete observations and align the architecture with linking-oriented benchmark conditions.

## 8. Baselines and ablations

The final experimental table compares:

1. mutual nearest neighbor;
2. Hungarian assignment;
3. constant-velocity Hungarian assignment;
4. physical distance/gating sensitivity;
5. phenotype preservation under the selected tracker;
6. phenotype discovery with and without temporal features.

The measured evidence shows that the simple, calibrated mutual-nearest-neighbor baseline currently outperforms the velocity-aware variant on these two sequences. This is preferable to claiming complexity that is not supported by the data.

## 9. Reliability and limitations

The transparent public baseline has known limitations:

- threshold-based segmentation is not robust to all microscopy modalities;
- temporal association can fail under crowding, crossing trajectories, missing detections, and rapid motion;
- lineage inference is candidate-based and should be validated against reference annotations;
- unsupervised clusters are descriptive rather than biological diagnoses;
- the CTC association and phenotype-preservation experiments use reference centroids and therefore do not measure the full image-to-phenotype pipeline;
- biological phenotype validity is not established by trajectory agreement alone.

These limitations are explicit design constraints rather than hidden assumptions.

## 10. Reproducibility

The repository contains:

- Python package configuration;
- scientific dependencies;
- deterministic synthetic generators;
- automated tests;
- Dockerfile;
- GitHub Actions CI;
- public dataset adapter;
- benchmark scripts;
- demo entry point.

The CI workflow is configured for Python 3.11 and includes syntax, dependency, regression, robustness, and submission-claim gates.

## 10.1 External software and licensing

The public pipeline uses standard scientific Python packages declared in `pyproject.toml` and the requirements files. Core dependencies are specified by minimum versions for the general pipeline; the CTC validation dependency is pinned to **py-ctcmetrics==1.3.3**. `py-ctcmetrics` is released under the BSD 2-Clause License and is maintained by the Cell Tracking Challenge project. The final submission should preserve the corresponding upstream attribution and citation. The technical report should also retain the official CTC dataset provenance and Nature Methods citation described in Section 4.

## 10.2 Sources and licenses

- **Cell Tracking Challenge dataset:** DIC-C2DH-HeLa training data and reference annotations are obtained from the official CTC dataset repository. CTC permits use for challenge preparation, participation, and reporting without additional consent, while prohibiting cloning/redistribution of the datasets or annotations. Any publication resulting from CTC data use should acknowledge the CTC and cite its Nature Methods paper.
- **CTC methodology reference:** Maška et al., *The Cell Tracking Challenge: 10 years of objective benchmarking*, Nature Methods 20, 1010–1020 (2023), DOI 10.1038/s41592-023-01879-y.
- **DIC segmentation method reference:** KTH-SE, public Cell Tracking Challenge participant description of the DIC-C2DH-HeLa multi-scale Hessian-ridge segmentation method (sigma 5–10 px, gamma=1, beta=10, threshold 0.75 and local-variance filtering).
- **CTC metrics:** `py-ctcmetrics==1.3.3`, CellTrackingChallenge, BSD 2-Clause License.
- **Core scientific software:** NumPy, pandas, SciPy, scikit-learn, tifffile, imagecodecs, and matplotlib are declared through the repository dependency files and should retain their upstream license/attribution notices. Development dependencies include pytest and ruff.
- **Development AI tooling:** OpenAI ChatGPT was used as an AI-assisted development and reasoning tool during implementation and documentation. No external AI service is required at runtime, and no third-party model weights are required or redistributed by the submitted system.
- **External AI services at runtime:** none are required to run the submitted baseline, benchmarks, or demo renderer.

## 10.3 Exact reproduction recipe

The following commands reproduce the principal public evidence from a clean Python 3.11 environment. For an exact environment snapshot, the repository provides `requirements-lock-py311.txt` and `requirements-dev-lock-py311.txt`, generated from the verified CI environment used for submission validation:

```bash
pip install -r requirements-lock-py311.txt
pip install -e .
pip install -r requirements-dev-lock-py311.txt
python scripts/benchmark_ctc_association.py
python scripts/benchmark_ctc_phenotype.py
python scripts/benchmark_ctc_lineage.py
python scripts/benchmark_phenotype_stability.py
python scripts/benchmark_end_to_end_phenotype.py
```

The headline 0.99228 mean-F1 result is produced by `scripts/benchmark_ctc_association.py`, which evaluates DIC-C2DH-HeLa sequences 01 and 02 across the physical gates 0.8, 1.0, 1.2, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, and 8.0 µm for mutual-nearest-neighbor, Hungarian, and constant-velocity Hungarian association.

The captured CTC-maintained TRA/LNK validation can be reproduced after installing `requirements-ctc.txt`:

```bash
pip install -r requirements-ctc.txt
python scripts/export_ctc_reference.py --sequence 01 --distance 8.0
python scripts/run_ctcmetrics.py --gt .benchmark_cache/dataset/DIC-C2DH-HeLa/01_GT --res ctc_reference_export/01 --sequence 01 --output-json results/ctc_metrics_01.json --lineage-mode oracle-compatible
python scripts/export_ctc_reference.py --sequence 02 --distance 8.0
python scripts/run_ctcmetrics.py --gt .benchmark_cache/dataset/DIC-C2DH-HeLa/02_GT --res ctc_reference_export/02 --sequence 02 --output-json results/ctc_metrics_02.json --lineage-mode oracle-compatible
```

The no-oracle lineage sensitivity protocol uses the same commands with `--lineage-mode none`.

The exact-lock path is also used by the `Final Reproducibility` workflow and the Docker image. The demo-video renderer additionally requires `ffmpeg`; its GitHub Actions workflow installs it on a standard Ubuntu runner. No paid API, proprietary hardware, pretrained model download, or private dataset is required for the submitted baseline or its reported benchmarks.

## 11. Scientific impact

The intended output is a dynamic phenotype representation that can support:

- cell-state characterization;
- motility analysis;
- abnormal-behavior screening;
- lineage-aware phenotype analysis;
- downstream perturbation studies.

## 12. Final submission evidence

The final Kaggle submission should only claim quantitative performance that is directly reproduced by the submitted repository.

Required evidence before submission:

- at least one real microscopy benchmark;
- quantitative baseline comparison;
- downstream phenotype preservation evidence;
- representative visual results;
- limitations/failure cases;
- public code;
- 5-minute demo video;
- final technical report.


### Reliability as a first-class output

A key failure mode in temporal phenotype analysis is treating every inferred trajectory as equally trustworthy. The engine therefore exposes a reproducible quality layer alongside the phenotype label.

The track-integrity score uses only quantities already measured by the tracker: observation fraction, mean link confidence, and the fraction of low-confidence links. The assignment-quality score uses the fitted K-Means geometry: distance to the assigned centroid and the margin to the next-nearest cluster. The combined reliability score is bounded to [0,1].

This design deliberately avoids a statistical calibration claim. It is a transparent operational score for triage and cohort analysis. The end-to-end synthetic robustness benchmark now records reliability together with phenotype-group ARI and the tracking-error taxonomy, allowing degradation to be inspected rather than hidden.

In a biological workflow, the intended behavior is conservative: high-integrity/high-separation trajectories contribute normally to downstream analysis, while low-integrity or ambiguous trajectories can be flagged for manual review or sensitivity analysis.
