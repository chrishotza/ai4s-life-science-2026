# Temporal Cellular Phenotype Engine

## Submission Links

**Category: End-to-End System**

**Code repository:** https://github.com/chrishotza/ai4s-life-science-2026

**Demo video:** The final public demo video link is inserted in the Kaggle Writeup at submission time; the reproducible renderer is `scripts/make_demo_video.py`.

**Technical report:** This Writeup contains the submission report sections; the full technical report is also maintained at `docs/TECHNICAL_REPORT.md`.

## Category Declaration

**Category: End-to-End System**

## Project Summary

Time-lapse microscopy contains information about how cells move, persist, divide, and change over time, but many workflows stop at segmentation or tracking. The Temporal Cellular Phenotype Engine turns those trajectories into interpretable temporal phenotype profiles.

The system integrates microscopy preprocessing, cell detection, deterministic 3-D temporal association, lineage/event inference, trajectory feature extraction, and unsupervised phenotype discovery. Tracking is treated as infrastructure; the scientific output is dynamic cellular behavior.

For rigorous real-data measurement, the CTC experiment intentionally uses **reference centroids as detections** to isolate temporal association from segmentation. On DIC-C2DH-HeLa sequences 01 and 02, mutual-nearest-neighbor association with an 8.0 µm gate achieved **0.99135 mean precision, 0.99322 mean recall, and 0.99228 mean F1**. Downstream phenotype preservation on the same reference centroids achieved **0.9451 mean trajectory coverage, 1.0000 median coverage, and 0.0439 directional-persistence MAE**.

The same association path was independently evaluated with pinned **py-ctcmetrics==1.3.3** using preserved reference object geometry: **sequence 01 TRA 0.997315 / LNK 0.979091; sequence 02 TRA 0.997207 / LNK 0.978239**. These are reference-geometry association-isolation results, not end-to-end segmentation or biological phenotype classification and **not official Cell Tracking Challenge leaderboard scores**. A no-oracle sensitivity control produced identical TRA/LNK values on both sequences.

The contribution is a reproducible bridge from **microscopy → trajectories → interpretable temporal phenotype**.

## From cell tracking to dynamic phenotype

### Problem

Time-lapse microscopy captures rich cellular behavior, but conventional pipelines often stop at segmentation or tracking. A track ID tells us where a cell went; it does not directly describe how the cell behaved.

The goal of this project is to turn temporal microscopy into an interpretable **single-cell phenotype representation**.

### Approach

The system is organized as an end-to-end pipeline:

1. microscopy frame preprocessing;
2. cell detection;
3. temporal association;
4. 3-D trajectory reconstruction;
5. lineage and division-event inference;
6. temporal phenotype extraction;
7. unsupervised phenotype discovery.

The submission implementation is deliberately deterministic and reproducible.

### What is novel about the submission

The main contribution is not another isolated tracker. Tracking is treated as infrastructure for a downstream phenotype layer.

For each trajectory, the engine derives:

- duration;
- displacement;
- path geometry;
- mean speed;
- directional persistence;
- parent/child relationships;
- division events;
- descendant structure.

These features form a compact temporal phenotype profile that can be clustered into interpretable behavioral groups.

### End-to-end implementation boundary

The public engine provides a canonical image-to-phenotype path through baseline detection, while the real CTC experiment intentionally bypasses segmentation by using reference centroids. This separation makes the quantitative association result interpretable instead of presenting a centroid benchmark as an image-segmentation score.

### Real benchmark evidence

The system was evaluated on DIC-C2DH-HeLa sequences 01 and 02 from the Cell Tracking Challenge.

The association benchmark uses the reference centroids as detections, intentionally isolating temporal association from segmentation.

A physical-unit sweep compared mutual nearest neighbor, Hungarian assignment, and constant-velocity Hungarian association.

The best measured configuration was mutual nearest neighbor with an 8.0 µm gate:

- mean precision: **0.99135**
- mean recall: **0.99322**
- mean F1: **0.99228**

Per-sequence F1:

- sequence 01: **0.99308**
- sequence 02: **0.99149**

The improvement over the initial restrictive-gate baseline was substantial: mean F1 increased from approximately 0.9183 to 0.9923.

### External CTC TRA/LNK validation

The selected 8.0 µm MNN association path was also exported with the **reference CTC object geometry preserved** and evaluated with the pinned `py-ctcmetrics==1.3.3` implementation. The captured association-isolation results were:

- sequence 01: **TRA 0.997315**, **LNK 0.979091**;
- sequence 02: **TRA 0.997207**, **LNK 0.978239**.

These values are reported separately from the custom F1 because TRA/LNK and the repository's edge F1 are different metrics. They are not end-to-end segmentation results, not biological lineage validation, and **not official Cell Tracking Challenge leaderboard scores**. The official submission evaluator was not used. A no-oracle sensitivity control removed all reference parent edges and produced identical TRA/LNK values on both sequences.

### Downstream phenotype preservation

The selected tracker was then evaluated through the phenotype layer on the same real sequences.

For matched trajectories:

- mean trajectory coverage: **0.9451**
- median trajectory coverage: **1.0000**
- directional-persistence MAE: **0.0439**
- mean-speed MAE: **0.1206 µm/frame**

This experiment demonstrates reproducible preservation of trajectory-derived phenotype features.

It does **not** claim biological phenotype classification. That requires independent biological labels or perturbation annotations.

### Lineage and division evidence

The public phenotype layer also represents parent/child structure, division events, and descendant counts. A dedicated CTC validation benchmark now checks that these features reproduce the reference lineage annotations for sequences 01 and 02. This is a representation-level validation using the CTC reference lineage graph; it is not presented as an end-to-end biological division detector result.

The benchmark is executed in CI through scripts/benchmark_ctc_lineage.py, with exact child-count and descendant-count checks alongside division-parent precision, recall, and F1.

### Missing-observation robustness

We also stress-tested the temporal association layer under controlled synthetic detection dropout.

At 5% dropout, mutual-nearest-neighbor tracking fragmented 24 reference tracks, while the experimental bounded-gap Hungarian branch fragmented only 1. At 10% dropout the counts were 29 versus 7, and at 15% dropout 30 versus 19.

The corresponding phenotype-group ARI was also substantially better for the bounded-gap branch at 5% and 10% dropout (0.4879 vs -0.0184 and 0.3584 vs -0.0102). In the same runs, every measured gap link preserved reference identity.

This branch remains experimental and is reported separately from the validated real-data CTC association result.

### Phenotype-discovery robustness

The phenotype layer was also stress-tested under controlled synthetic trajectory perturbations. Standard scaling + K-Means had the strongest measured stability among the tested configurations, with mean ARI 0.7839 and minimum ARI 0.5312 across the perturbation sweep. More complex robust-scaling variants were tested and rejected because they performed worse in this controlled experiment.

This is computational robustness evidence, not biological phenotype validation.

### Why this matters

The practical value of the system is the transition from:

**microscopy → track IDs**

to:

**microscopy → temporal cellular behavior → interpretable phenotype**

That representation can support motility analysis, state characterization, abnormal-behavior screening, lineage-aware studies, and downstream biological investigation.

### Reproducibility

The repository contains:

- complete source code;
- public benchmark loader;
- deterministic synthetic tests;
- quantitative evaluation;
- Docker support;
- GitHub Actions CI;
- reproducible benchmark workflows;
- technical report;
- five-minute demo script.

The microscopy datasets are downloaded transiently for evaluation and are not redistributed in the repository.

### Limitations

The current public baseline has transparent limitations:

- threshold-based image segmentation is not universal;
- association can fail under severe crowding or missing detections;
- lineage events remain candidate inferences;
- unsupervised phenotype clusters are descriptive;
- CTC association results use reference centroids and are not a full image-to-phenotype score.

These limitations are explicitly reported rather than hidden.

### Future direction

The strongest next step is to validate the phenotype layer on an independently labeled biological perturbation dataset and compare temporal phenotype distributions between conditions.
