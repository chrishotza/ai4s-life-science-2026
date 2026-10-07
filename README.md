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

The public implementation contains four reproducible layers:

1. **Microscopy baseline** — threshold + connected-component detection for time-lapse frames.
2. **Tracking baseline** — deterministic 3-D association with mutual nearest-neighbor, Hungarian, and constant-velocity Hungarian methods.
3. **Temporal phenotype engine** — duration, displacement, path length, speed, directional persistence, parent/child structure, divisions and descendants.
4. **Phenotype discovery** — standardized trajectory features clustered with K-Means into interpretable behavioral groups.

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
- real Cell Tracking Challenge association benchmarking.

See **[docs/RESULTS.md](docs/RESULTS.md)** for the full measured results.

## Real benchmark

The CTC benchmark uses **DIC-C2DH-HeLa sequences 01 and 02**. The evaluation feeds the reference track centroids into the association stage, so it is explicitly a **tracking-association benchmark**, not an end-to-end segmentation score.

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

The benchmark is reproducible through GitHub Actions; the microscopy dataset itself is never committed to the repository.

## Scientific output

The final output is not merely a track ID. For each cell trajectory the engine produces an interpretable temporal phenotype profile, including:

- persistence and motility;
- displacement and path geometry;
- temporal duration;
- lineage relationships;
- division events;
- descendant structure;
- unsupervised phenotype group.

This makes the system directly usable as a phenotype-analysis layer on top of microscopy experiments.

## Research provenance

The private BioHub project contains earlier learned temporal-association research. This public competition repository does not claim private model artifacts as reproducible until their redistribution and dependency conditions are verified.

## Competition positioning

**Category:** End-to-End System  
**Impact:** Single-cell Phenotype Analysis

The intended contribution is a reproducible pipeline that moves from microscopy to **dynamic, interpretable single-cell phenotype**, rather than treating cell tracking as the final objective.

## Next milestones

1. Validate phenotype stability under controlled tracking perturbations.
2. Add representative real-data visualizations.
3. Strengthen lineage/division validation.
4. Produce the final 5-minute demonstration.
5. Finalize the Kaggle Writeup and submission package.
