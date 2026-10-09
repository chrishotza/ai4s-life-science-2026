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


### Image-level negative controls

The raw-image experiments are retained as explicit negative controls rather than silently discarded. `docs/ABLATION_AND_FAILURES.md` records generic thresholding, DIC-ridge segmentation, and a lightweight supervised segmentation model, including strict cross-sequence metrics and the resulting decision not to promote these methods into the headline association benchmark.


### Cohort-level experimental comparison

The phenotype layer now exposes an uncertainty-aware cohort comparison API. Given a cohort label and two experimental groups, it reports group means, mean differences, standardized mean differences, and bootstrap 95% confidence intervals for selected temporal phenotype features.

This closes an important analysis gap between unsupervised clustering and a scientific decision. The comparison module does not assign biological meaning to a feature; it quantifies whether two cohorts differ in the measured temporal representation and makes uncertainty visible.

A deterministic synthetic benchmark (scripts/benchmark_cohort_effect.py) verifies recovery of known directionally shifted phenotypes under a strict reproducible protocol. This benchmark is methodological validation only and is not presented as biological validation.


## Appendix A. Data and graph contracts

### A.1 Observation identity

The base object is an observation, not a persistent cell identity. An observation represents one segmented or annotated object at one frame. It carries a stable node identifier, frame index, z/y/x coordinates, and optional numeric attributes produced by the detector.

This separation prevents a common category error in time-lapse workflows: two observations at different times are not known to be the same cell until an association algorithm links them. Likewise, a cell may have one track identity before a division and two daughter track identities afterward. Observation identity, track identity, and biological identity are represented separately.

The core validator checks unique node identifiers, finite coordinates, and consistency of every referenced edge endpoint. These checks are executed before the phenotype layer computes derived quantities. A malformed graph is rejected instead of quietly generating plausible-looking features.

### A.2 Temporal edges

A temporal edge indicates that two observations are inferred to belong to the same track at different times. Its required fields are source observation and target observation. Optional fields record physical distance, link confidence, edge type, and frame gap.

The temporal graph must point forward in time. For the adjacent-frame baseline, accepted edges connect observations at consecutive frames. The separate bounded-gap branch can create an edge across missing observations, but the frame gap is explicit metadata. This is important because a long gap and a one-frame transition have different evidential support even when they share the same source and target schema.

Link confidence is a diagnostic generated by the association layer. It is not a posterior probability that the identity is biologically correct. It supports quality ranking and sensitivity analysis but does not replace validation against reference annotations.

### A.3 Lineage edges

A lineage edge connects a parent track endpoint to a daughter track start. The system uses the same node-level source/target representation while adding an explicit event type so that temporal links and candidate division links cannot be confused.

The candidate event layer is intentionally separated from biological interpretation. Spatial proximity between a parent endpoint and two new track starts can generate a plausible division candidate, but proximity alone is not sufficient to establish a cell division. A true biological division claim requires independent event annotations or a benchmark that compares image-derived candidates with such annotations.

The CTC reference loader preserves the supplied parent identifiers and track intervals. For the principal association benchmark, reference centroids are used as observations and reference lineage edges are independently controlled in the no-oracle sensitivity experiment. The report states which part of the graph was observed, inferred, or held fixed.


## Appendix B. Physical units and tracking

### B.1 Coordinate conversion

Every spatial comparison is made in a common z/y/x coordinate convention. The scale is supplied as a three-element tuple, and the tracking layer converts coordinates to physical distances before applying a gate. For DIC-C2DH-HeLa, the in-plane pixel size is 0.19 micrometers. The real-data benchmark uses the scale (1.0, 0.19, 0.19) with an 8.0 micrometer association gate.

The pixel scale matters directly. A threshold stated only in pixels encodes a dataset-specific resolution assumption and cannot be compared safely across microscopes. A physical gate gives the experiment a stable interpretation and makes it easier to reproduce on a second dataset with a different pixel size.

### B.2 Mutual nearest neighbor

For adjacent frames, the MNN baseline finds nearest candidates between source and target observations under the physical distance metric. A link is retained only when the candidate relationship is reciprocal. The algorithm is deterministic and makes few assumptions about cell dynamics, which makes it an appropriate transparent baseline.

MNN does not solve every data-association case. Crowded fields, closely interacting cells, missing observations, and rapid movement can produce fragmented tracks. The repository therefore tests alternative association methods under the same scoring interface rather than silently replacing the selected baseline.

### B.3 Assignment alternatives

The repository contains Hungarian assignment, a constant-velocity Hungarian variant, a bounded-gap Hungarian branch, and an experimental KD-tree MNN implementation. The global assignment methods can resolve competition between candidate links differently from reciprocal nearest neighbors. The gap branch explicitly addresses missed detections. The KD-tree path changes the computational search strategy and remains under A/B validation until its correctness and performance are independently accepted.

The real DIC headline is tied to the measured MNN configuration. Alternative methods remain experimental comparisons, and their results do not overwrite the reported headline merely because a particular run happens to improve one metric.

## Appendix C. Temporal phenotype feature semantics

### C.1 Duration and observations

Duration is the difference between the last and first observed frame indices. Observation count is the number of detections assigned to the track. These quantities are related but not interchangeable: a long-duration track can contain gaps, and two tracks with equal duration can have different observation counts.

Observation fraction divides the number of observed detections by the number of frame positions in the track's temporal span. It gives a simple measure of temporal coverage and is interpreted alongside the explicit gap count and maximum gap.

### C.2 Displacement, path length, speed, and persistence

Displacement measures the straight-line distance between the first and last observation. Path length sums distances between consecutive observations. Mean speed divides each observed step by its positive frame interval and averages the resulting rates.

Directional persistence is displacement divided by path length where path length is positive. Values near one indicate that the accumulated path aligns with the net displacement; lower values indicate turning or meandering. This is an interpretable geometric descriptor, not a named biological state.

These motion features deliberately use the track's observed points. They inherit uncertainty from the detection and association process; they cannot correct an identity switch or a missing segment by themselves. That is why the report pairs downstream feature errors with link and track diagnostics.

### C.3 Lineage and event features

Parent count, child count, division-event indicator, and descendant count summarize the lineage graph available to the analysis. They are computed from explicit edges rather than inferred from motion features.

Where lineage is derived from reference graph annotations, the report says so. Where lineage is generated from spatial candidates, it is labeled as candidate inference. The implementation does not treat “division detected” as a synonym for “two nearby track starts.”

### C.4 Auxiliary observation attributes

Numeric detection attributes are aggregated per track with mean, standard deviation, minimum, and maximum summaries. Examples include object area and mean intensity where the input adapter provides them. Non-numeric metadata and columns that look like identifiers are excluded.

The default phenotype discovery schema remains the fixed trajectory/lineage feature list. Auxiliary morphology values are preserved for future multimodal experiments but are not allowed to enter the current published clustering benchmark without an explicit schema version update and a new evaluation.


## Appendix D. Reliability diagnostics

The reliability layer exists because temporal phenotype analysis should not treat every trajectory and every cluster assignment as equally trustworthy. It adds bounded, interpretable quality indicators while preserving raw features so a downstream investigator can inspect the components.

The track-integrity score combines observation fraction, mean temporal-link confidence, and the fraction of links classified as low confidence. The combination uses a geometric mean. This choice is conservative: one poor component lowers the total score rather than being fully masked by a high value in another component.

The phenotype-assignment quality uses distance to the assigned K-Means centroid and the margin to the next-nearest centroid. A trajectory far from the assigned center or almost equally close to two centers receives lower assignment quality. The model stores the median assigned training distance as a reference scale, so the distance term is interpreted relative to the geometry of the fitted cohort rather than in an arbitrary raw feature unit.

The phenotype-reliability score combines track integrity and cluster-assignment quality geometrically. It is an evidence-weighting diagnostic, not a calibrated probability of biological correctness. A score near one means the observable track and assignment diagnostics are mutually strong under the chosen method; it does not prove that the phenotype label is biologically true.

The scores are emitted alongside raw motion and lineage features. They are intended to support review queues, quality-filtered cohort sensitivity analyses, and transparent reporting. An analysis should not discard low-score cells silently, because selective exclusion can bias cohort composition. Instead, a report should disclose the threshold, the number of affected tracks, and whether conclusions change under reasonable thresholds.

## Appendix E. Evaluation protocol and threats to validity

### E.1 Association-isolation versus image-level evaluation

The headline real-data association experiment uses CTC reference centroids as detections. This protocol is deliberate: it isolates temporal association so that the effect of a spatial gate can be measured without conflating it with errors from a baseline image detector.

The protocol also imposes a claim boundary. Association F1 is not segmentation accuracy, and it is not an end-to-end image-to-biological-phenotype score. The separate image-level experiments start from raw microscopy, evaluate object detection or mask overlap, and are recorded as negative controls because their measured performance is insufficient.

### E.2 Independent metric families

The repository keeps three families of metrics separate. The custom edge precision, recall, and F1 scores temporal edge recovery. External TRA/LNK measures evaluate graph quality through the pinned py-ctcmetrics implementation. Phenotype-preservation metrics compare motion-derived features for matched tracks.

These metrics differ in definition and target. They must not be averaged into a single score or substituted for one another. The report presents the value and the protocol together so a reader can determine what the number measures.

### E.3 No-oracle sensitivity

The external graph validation includes a no-oracle lineage sensitivity condition in which reference parent edges are removed while association method and reference geometry remain fixed. The resulting TRA/LNK values are compared directly with the oracle-compatible condition.

The purpose is not to claim that the complete pipeline is independent of all reference annotations. The geometry still comes from reference detections in this experiment. The narrower conclusion is that the metric values on these sequences are invariant to lineage-metadata selection under the tested protocol.

### E.4 Synthetic perturbation

Synthetic robustness experiments have known expected trajectories or phenotype groups and allow controlled changes in coordinate noise, missing detections, and association method. They are useful for identifying fragmentation, merge events, missed links, and the propagation of tracking errors into phenotype clusters.

Synthetic data cannot establish biological validity. It provides a causal diagnostic for the software: when a known perturbation is introduced, one can inspect whether the expected class of computational error increases and whether quality diagnostics expose the degradation.

### E.5 Biological interpretation

The current submission does not claim that unsupervised clusters correspond to validated biological cell states. Cluster names are descriptive labels derived from feature geometry. Interpreting them as proliferation, apoptosis, differentiation, drug response, or disease phenotype requires independent biological labels, experimental perturbations, or orthogonal readouts.

This limit is part of the design rather than an afterthought. The software provides an interpretable temporal representation, while the biological mapping remains a testable hypothesis for future data with appropriate labels.

## Appendix F. Reproducibility and operational controls

The repository provides a Python package, exact runtime snapshots for Python 3.11, development-tool lock files, Docker support, deterministic synthetic tests, CTC benchmark scripts, and GitHub Actions workflows. Benchmark outputs are emitted as machine-readable JSON and CSV artifacts rather than being copied by hand into documentation.

Dataset archives are downloaded at execution time and are not committed or redistributed with the source. This keeps the code repository lightweight and reduces the risk of violating dataset redistribution conditions. The technical report documents source URLs and conditions of use for external datasets used in the reported work.

The final reproducibility procedure should be run on the final submission commit. It includes installation, static validation, unit tests, deterministic synthetic benchmarks, the association benchmark, external metric checks where configured, and the automated claim audit. A successful CI run demonstrates that the declared software environment and verification steps passed; it does not by itself establish a biological hypothesis.

### Threats to validity checklist

- Reference-centroid input improves isolation of association but excludes segmentation error from the headline result.
- Two sequences from one CTC dataset provide limited evidence of cross-domain generalization.
- Gold or silver annotation quality can constrain the interpretation of mask-overlap scores.
- Unsupervised cluster assignments depend on the feature schema, scaling policy, random seed, and fitted reference cohort.
- Reliability scores use observable computational diagnostics and are not probabilistically calibrated.
- Synthetic phenotypes are constructed with known groups and may be easier to separate than real biological populations.
- Cohort bootstrap intervals assume supplied rows are appropriate independent units. Replicate structure should be respected; cells from the same well should not be treated as independent biological replicates without justification.
