# AI4S Life Science 2026 — Temporal Cellular Phenotype Engine

**Category:** End-to-End System  
**Impact area:** Single-cell Phenotype Analysis

This project converts time-lapse microscopy into interpretable temporal cellular phenotype analysis.

## Core idea

Most pipelines stop at segmentation or tracking. This system treats tracking as infrastructure and asks the downstream scientific question:

> **What phenotype is a cell expressing over time, and how does that phenotype change across trajectories and lineages?**

The engine combines transparent image preprocessing, temporal association, 3-D trajectory analysis, lineage/event inference, and unsupervised phenotype discovery.

## System

```
microscopy time-lapse
        ↓
cell detection / segmentation
        ↓
temporal association
        ↓
3-D tracking
        ↓
lineage/event structure
        ↓
temporal phenotype features
        ↓
unsupervised phenotype discovery
        ↓
interpretable phenotype report
```

## Public MVP

The public implementation contains explicit reproducible layers:

1. **Microscopy baseline** — threshold + connected-component detection for 2-D+t or 3-D+t time-lapse volumes.
2. **Tracking baseline** — deterministic 3-D association with mutual nearest-neighbor, Hungarian, constant-velocity Hungarian, and an experimental KD-tree MNN variant.
3. **Lineage + temporal phenotype** — duration, displacement, path length, speed, directional persistence, temporal-integrity diagnostics, parent/child structure, divisions and descendants.
4. **Experimental gap branch** — bounded gap-closing Hungarian association for incomplete observations, isolated from the validated baseline.
5. **Phenotype discovery** — standardized trajectory features clustered with K-Means, with a reusable fit/transform model for cross-cohort application.
6. **Canonical orchestration + validation** — TemporalPhenotypeEngine, data contracts, benchmark harnesses, and CI quality gates.

Tracking tables use:

`t,z,y,x`

and produce:

`node_id,track_id,t,z,y,x`

plus:

`source_id,target_id,distance_um,edge_type`

Distances can be evaluated in physical units through `voxel_size_um=(z,y,x)`.

## Reproducible setup

Requires Python 3.10+.

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -e .
pip install -r requirements-dev.txt
pytest -q
python demo.py
```

The demo runs end-to-end from a deterministic microscopy-like image stack to detections, tracks, lineage candidates, temporal phenotypes, and discovered phenotype groups.

## Quantitative validation

The repository includes:

- deterministic tracking regression tests;
- link precision, recall and F1;
- exact synthetic trajectory ground truth;
- microscopy-to-detection tests;
- phenotype discovery tests;
- controlled synthetic perturbations;
- end-to-end tracking-to-phenotype robustness under perturbed detections;
- deterministic tracking-error taxonomy (identity switches, fragmentation, merges, missed/false links and temporal-gap diagnostics);
- real Cell Tracking Challenge association benchmarking;
- downstream temporal phenotype preservation benchmarking.

See **[docs/RESULTS.md](docs/RESULTS.md)** for the measured results.

## Real benchmark

The CTC benchmark uses **DIC-C2DH-HeLa sequences 01 and 02**. The association experiment feeds the reference track centroids into the tracking stage, so it is explicitly a **tracking-association benchmark**, not an end-to-end segmentation score.

The completed physical-unit sweep compared:

- mutual nearest neighbor;
- Hungarian assignment;
- constant-velocity Hungarian assignment;
- distance thresholds from 0.8 to 8.0 µm.

The best measured configuration is **mutual nearest neighbor at 8.0 µm**, reaching:

**mean precision 0.99135 · mean recall 0.99322 · mean F1 0.99228**

Per sequence:

- sequence 01: F1 0.99308;
- sequence 02: F1 0.99149.

The downstream phenotype-preservation experiment on the same reference centroids reports:

**mean trajectory coverage 0.9451 · median coverage 1.0000 · directional-persistence MAE 0.0439**

These phenotype values measure trajectory-feature preservation under tracking; they are not biological phenotype classification scores.

### External CTC validation track

The same 8.0 µm MNN association path was exported with CTC reference object geometry preserved and evaluated with the pinned `py-ctcmetrics==1.3.3` implementation. The captured reference-geometry association-isolation results were:

- sequence 01: **TRA 0.997315 · LNK 0.979091**
- sequence 02: **TRA 0.997207 · LNK 0.978239**

These values are independently reproduced CTC-metrics evidence, not end-to-end segmentation or biological phenotype results, and **not official Cell Tracking Challenge leaderboard scores**. The official challenge submission evaluator remains a separate boundary. See [docs/CTC_OFFICIAL_VALIDATION.md](docs/CTC_OFFICIAL_VALIDATION.md). A no-oracle lineage sensitivity control produced exactly the same TRA/LNK values on both sequences, removing lineage-metadata dependence for this benchmark.

### Missing-observation stress test

The experimental bounded-gap Hungarian branch was evaluated separately under controlled synthetic dropout. At 5%, 10%, and 15% dropout it reduced fragmented reference tracks from 24/29/30 with the MNN baseline to 1/7/19 respectively, while preserving reference identity for every measured gap link in those runs. The corresponding phenotype-group ARI was 0.4879, 0.3584, and -0.0114 for the gap branch versus -0.0184, -0.0102, and 0.0007 for MNN.

This is computational stress-test evidence only; the bounded-gap branch remains experimental and does not replace the validated 8.0 µm MNN real-data result.

The repository also validates the lineage representation layer against the CTC reference parent/child annotations. That validation is explicitly separate from end-to-end biological division detection.

The benchmark suite is reproducible through GitHub Actions; the microscopy dataset itself is never committed to the repository.

The current association F1 is a custom transparent benchmark metric. The official CTC TRA/LNK scores are intentionally tracked as a separate validation boundary and is not substituted into the published F1 claim. See [docs/CTC_OFFICIAL_VALIDATION.md](docs/CTC_OFFICIAL_VALIDATION.md).

## Demo video

A reproducible demo-video renderer is included in `scripts/make_demo_video.py`. It downloads the public DIC-C2DH-HeLa sequence, overlays the deterministic tracking trajectories on real microscopy frames, and appends a measured validation summary card.

The GitHub Actions workflow `.github/workflows/demo-video.yml` produces the MP4 as a workflow artifact. The rendered sequence now shows real microscopy with tracks, an unsupervised temporal-phenotype view, and the measured validation summary.

## Scientific output

The final output is not merely a track ID. For each cell trajectory the engine produces an interpretable temporal phenotype profile, including:

- persistence and motility;
- displacement and path geometry;
- temporal duration;
- lineage relationships;
- division events;
- descendant structure;
- temporal integrity and tracking-link confidence diagnostics;
- unsupervised phenotype group.

This makes the system directly usable as a phenotype-analysis layer on top of microscopy experiments.

## Research provenance

The private BioHub project contains earlier learned temporal-association research. This public competition repository does not claim private model artifacts as reproducible until their redistribution and dependency conditions are verified.

## Architecture hardening

See **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** for the full contract, model-lifecycle, validation, and performance architecture.

The public system now has explicit boundaries between:

1. **Data contracts** — node/edge schema validation and a single physical coordinate transform.
2. **Detection** — microscopy-to-centroid preprocessing.
3. **Tracking** — deterministic temporal association with physical-unit gating.
4. **Lineage** — candidate division inference using the same physical coordinate system.
5. **Phenotype** — trajectory and lineage-derived feature extraction.
6. **Discovery** — reproducible unsupervised phenotype clustering.
7. **Orchestration** — TemporalPhenotypeEngine exposes one canonical path from detections to the complete phenotype result.
8. **Evaluation** — regression tests and benchmark protocols remain separate from the production pipeline.

This separation prevents benchmark-specific scaling, duplicate scoring logic, and demo-specific orchestration from silently becoming part of the scientific method.

## Competition positioning

**Category:** End-to-End System  
**Impact:** Single-cell Phenotype Analysis

The intended contribution is a reproducible pipeline that moves from microscopy to **dynamic, interpretable single-cell phenotype**, rather than treating cell tracking as the final objective.

## Finalization status

1. Phenotype stability stress test: completed.
2. Real-data phenotype visualization: integrated into the demo renderer.
3. Lineage/division representation validation: added as a dedicated GitHub Actions benchmark.
4. Final demo renderer: implemented with real microscopy, tracking, phenotype discovery, and validation summary.
5. Remaining submission blockers: public repository visibility, final public-URL check, Kaggle upload, and final claim consistency review.
