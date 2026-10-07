# AI4S Life Science 2026 — Temporal Cellular Phenotype Engine

**Category:** End-to-End System  
**Impact area:** Single-cell Phenotype Analysis

This project converts time-lapse microscopy into interpretable temporal cellular phenotype analysis.

## Core idea

Most pipelines stop at segmentation or tracking. This system treats tracking as infrastructure and asks the downstream scientific question:

> **What phenotype is a cell expressing over time, and how does that phenotype change across trajectories and lineages?**

The engine combines transparent image preprocessing, temporal association, 3-D trajectory analysis, and unsupervised phenotype discovery.

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
2. **Tracking baseline** — deterministic mutual-nearest-neighbor 3-D temporal association.
3. **Temporal phenotype engine** — duration, displacement, path length, speed, directional persistence, parent/child structure, divisions and descendants.
4. **Phenotype discovery** — standardized trajectory features clustered with K-Means into interpretable behavioral groups.

Tracking tables use:

`t,z,y,x`

and produce:

`node_id,track_id,t,z,y,x`

plus:

`source_id,target_id,distance_um,edge_type`

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

The demo runs end-to-end from a deterministic microscopy-like image stack to detections, tracks, temporal phenotypes, and discovered phenotype groups.

## Quantitative validation

The repository includes:

- deterministic tracking regression tests;
- link precision, recall and F1;
- exact synthetic trajectory ground truth;
- microscopy-to-detection tests;
- phenotype discovery tests;
- controlled synthetic perturbations for stress testing.

The next evaluation target is a public microscopy benchmark with reference annotations.

## Public benchmark target

The Cell Tracking Challenge provides freely downloadable 2D+time and 3D+time microscopy datasets with reference annotations. The repository is designed so the same detection/tracking/phenotype pipeline can be evaluated against those public references. Real benchmark results will be reported only after an actual run, not inferred from synthetic tests.

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

## Validation roadmap

1. Public microscopy benchmark evaluation.
2. Baseline comparison against stronger association methods.
3. Division/lineage validation.
4. Phenotype-discovery stability analysis.
5. Real experimental perturbation case study.
6. 5-minute demonstration and 15–20 page technical report.

