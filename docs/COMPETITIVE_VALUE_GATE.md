# Competitive value gate — AI4S Life Science 2026

Date: 2026-10-09. Status: **research protocol; no new experimental claim**.

## What exists and what it proves

- The 168-frame DIC-C2DH-HeLa Cellpose integration produced an archived artifact in [run 37930909373](https://github.com/chrishotza/ai4s-life-science-2026/actions/runs/37930909373), commit ffc135c. Reported segmentation F1@IoU50 0.9354, detection F1 0.9684, and tracking-edge F1 0.9808.
- These measure segmentation, detection, and temporal linking. They do **not** prove that unsupervised phenotype groups correspond to biological states.
- `scripts/benchmark_ctc_phenotype.py` evaluates preservation of trajectory-derived features from CTC reference centroids. This isolates tracking/feature consistency, not independent phenotype validity.
- `scripts/benchmark_cohort_effect.py` draws two explicitly differentiated **synthetic** groups and compares their feature means with bootstrap intervals. It verifies the comparison implementation; it cannot serve as a real biological discovery or a generalization score.
- `scripts/benchmark_phenotype_stability.py` tests synthetic motility patterns and stability under perturbation, not external biological labels.

## Primary falsifiable question

Given the same masks and tracking outputs, does the phenotype layer reveal or recover a **held-out biological condition or perturbation** better than simpler descriptive features and tracking-only baselines, without fitting on the evaluation cohort?

**Do not state a positive answer unless measured.**

## Minimum experiment

1. Identify an openly licensed time-lapse dataset with biologically defined group/perturbation labels and sufficient independent sequences/wells. Record licensing, provenance, biological label meaning and train/test domains.
2. Fix image segmenter, tracking parameters and splits **before** measuring test performance. Keep all frames/tracks from one well or sequence together to avoid leakage.
3. Compare: (A) simple speed/displacement baseline, (B) trajectory features without phenotype discovery, (C) trajectory features plus the repository's discovered phenotype representations, (D) optional image-only summary if supported.
4. For group discrimination, train simple equal-capacity probes on training wells only; evaluate once on held-out wells. Use a shared input path and the same exclusions.
5. Primary outcome: macro AUROC for binary labels or macro F1 for multiclass labels, aggregated at the **well/sequence** level, not per track. If task labels are continuous, predefine an appropriate regression metric instead.
6. Report cluster stability, fraction of analyzable tracks, time, missingness, feature leakage, and failure modes. Bootstrap over biological experimental units (well/sequence), not over correlated cells.
7. Negative controls: shuffled train labels and random/fixed group assignment. Do not claim phenotype validity on CTC alone.

## Decision thresholds

- **GO for scientific incremental claim:** a predeclared positive improvement over the strongest simpler baseline on fully held-out biological units, with appropriately clustered uncertainty estimate that excludes zero, plus a leakage audit.
- **GO for a modest engineering-system claim:** documented image-to-feature reliability and reproducibility, while explicitly stating phenotype biology is unvalidated.
- **NO-GO for phenotype-discovery superiority:** no independent biological labels or no improvement over simple features.

## Immediate next step

Inspect any phenotype CSVs/provenance in existing real-image artifacts before scheduling compute. If these contain no independently assigned biological treatment labels, request/find an appropriate independent dataset; do not invent labels from clustering.

Owner: Chris Hotza Research Lab; Architecture, Validator, Statistician, Auditor and Engineering. No paid compute authorized.
