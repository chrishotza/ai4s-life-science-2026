# AI4S Life Science 2026 — Temporal Cellular Phenotype Engine

**Category:** End-to-End System  
**Impact area:** Single-cell Phenotype Analysis

This project converts time-lapse microscopy into interpretable temporal cellular phenotype analysis.

## System

```
3D / time-lapse microscopy
        ↓
cell detection
        ↓
temporal association
        ↓
3D tracking
        ↓
lineage reconstruction
        ↓
division / event detection
        ↓
temporal phenotype extraction
        ↓
interpretable phenotype report
```

Tracking is the infrastructure; the scientific output is the **dynamic phenotype of each cell and lineage**.

## Public MVP

The repository provides a deterministic, reproducible 3-D tracking baseline from frame-wise detections and a phenotype layer over reconstructed trajectories and lineage edges.

Tracking input:

`t,z,y,x`

Tracking output:

`node_id,track_id,t,z,y,x`

and an edge table:

`source_id,target_id,distance_um,edge_type`

The phenotype layer extracts trajectory duration, displacement, path length, mean speed, directional persistence, division events, parent/child counts, descendant counts, and phenotype flags.

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

The test suite includes deterministic pipeline checks, quantitative link precision/recall/F1, and a synthetic 3-D tracking benchmark.

## Synthetic benchmark

The repository contains a deterministic generator for controlled trajectory experiments. It produces known 3-D cell trajectories and exact consecutive-frame ground-truth links, allowing tracking performance to be measured without hidden assumptions.

This benchmark is intended for regression testing and controlled perturbation experiments before evaluation on public microscopy data.

## Research provenance

The private BioHub project contains the research tracker and experiment history. Its documented 0.947 baseline uses a learned 3-D temporal association stack. The public competition repository does not silently redistribute private model artifacts or claim those components as reproducible.

The public repository therefore separates:

1. **Reproducible baseline** — available here.
2. **Research tracker** — private BioHub provenance.
3. **Phenotype interpretation** — competition-facing scientific layer.

## Competition positioning

**Category:** End-to-End System  
**Impact:** Single-cell Phenotype Analysis

The project is intentionally framed around measurable temporal phenotype information rather than presenting cell tracking as the final scientific objective.

## Validation roadmap

- deterministic tracking baseline;
- synthetic perturbation benchmark;
- quantitative tracking metrics;
- public microscopy dataset evaluation;
- lineage/division validation;
- temporal phenotype validation;
- comparison against stronger association methods.

The learned BioHub components will only be promoted into the public pipeline after their model/code redistribution and reproducibility conditions are verified.
