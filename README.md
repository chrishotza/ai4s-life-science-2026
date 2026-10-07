# AI4S Life Science 2026 — Temporal Cellular Phenotype Engine

**Category:** End-to-End System  
**Impact area:** Single-cell Phenotype Analysis

This project turns time-lapse microscopy tracking into an interpretable cellular phenotype analysis pipeline.

## Problem

Cell tracking alone produces trajectories. For life-science analysis, the useful output is the behavior of each cell over time: persistence, movement, divisions, lineage structure, and anomalous temporal behavior.

## MVP pipeline

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
division/event detection
        ↓
temporal phenotype extraction
        ↓
interpretable phenotype report
```

The tracking/lineage engine is being extracted from the private BioHub research repository. This public repository contains only the competition-facing, reproducible layer.

## Current MVP

The first public-facing layer accepts a generic node/edge representation of a tracked cell population and computes:

- trajectory duration
- displacement and path length
- mean speed
- directional persistence
- division events
- lineage depth
- descendant counts
- per-cell phenotype flags

The interface is deliberately independent of Kaggle-specific paths and services.

## Reproducibility

The competition requires a public repository with core code, environment setup, inference/evaluation/demo entry points, I/O descriptions, and reproduction instructions. The final repository will satisfy those requirements without paid services or proprietary hardware.

## Status

Research extraction in progress. BioHub remains the private source project; this repository is the cleaned competition implementation.
