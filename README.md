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

The repository currently provides a deterministic, reproducible 3-D tracking baseline from frame-wise detections and a phenotype layer over reconstructed trajectories and lineage edges.

The tracking baseline expects CSV columns:

`t,z,y,x`

and produces node-level tracks plus an edge table with:

`source_id,target_id,distance_um,edge_type`

The phenotype layer extracts trajectory duration, displacement, path length, mean speed, directional persistence, division events, lineage depth, descendant counts, and phenotype flags.

Run the local demo:

```bash
python demo.py
```

## Research provenance

The private BioHub project contains the research tracker and experiment history. Its documented 0.947 baseline uses a learned 3-D temporal association stack. The public competition repository does not silently redistribute private model artifacts or claim those components as reproducible.

The public repository therefore separates:

1. **Reproducible baseline** — available here.
2. **Research tracker** — private BioHub provenance.
3. **Phenotype interpretation** — competition-facing scientific layer.

This is deliberate: the competition requires reviewers to reproduce the public repository without paid services, proprietary hardware, or non-public datasets.

## Competition positioning

**Category:** End-to-End System  
**Impact:** Single-cell Phenotype Analysis

The challenge explicitly accepts cell segmentation, feature extraction and phenotype analysis from microscopy images, and evaluates problem impact, technical innovation, validation, reproducibility and presentation. The final submission will therefore emphasize measurable phenotype information rather than presenting the project as a cell-tracking benchmark alone.

## Next validation target

The next milestone is a public evaluation harness comparing:

- deterministic tracking baseline;
- lineage reconstruction;
- phenotype extraction;
- synthetic perturbation scenarios;
- quantitative tracking and phenotype metrics.

The learned BioHub components will only be promoted into the public pipeline after their model/code redistribution and reproducibility conditions are verified.
