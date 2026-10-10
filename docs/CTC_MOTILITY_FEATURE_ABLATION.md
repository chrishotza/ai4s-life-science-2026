# Real 168-frame Cellpose experiment: motion-only discovery ablation

**Date:** 2026-10-10. **Outcome:** EXPERIMENTAL OPTION SHIPPED; **NO-GO** for replacing the default clusterer. This document reports a real computed experiment on previously archived CTC data, **not** new raw-image inference, independent biological ground truth or a prospective confirmation.

## What changed in the product

`PhenotypeDiscoveryModel.fit(..., feature_set="motion_only")` is a new, optional KMeans(k=3) feature selection mode using only **mean speed** and **directional persistence**. It intentionally excludes observation count, track duration, total path length and lineage counts, which may dominate the standard nine-feature clusters. Crucially, **fitting motion-only groups refuses any trajectory with fewer than three observations**. The existing nine-feature `feature_set="trajectory_lineage"` remains the default, preserving published values and backwards compatibility.

This ablation does not claim that two-feature KMeans creates real named cell types, mitosis stages or drug-response phenotypes.

## Provenance and protocol

- **Actual microscopy input:** pretrained CellposeSAM-v2 outputs from DIC-C2DH-HeLa sequences 01+02, 168 raw images, original [GitHub Actions run 37930909373](https://github.com/chrishotza/ai4s-life-science-2026/actions/runs/37930909373).
- **Frozen feature source:** [126 image-derived trajectory rows](evidence/ctc/derived_phenotype_features.csv), SHA-256 `db29350638077a0a19a30e33e5b0c1aeaf9df4857326008a77ba1f5267e3279c` — 79 seq01 and 47 seq02.
- **Controlled comparison:** Same `PhenotypeDiscoveryModel`, same StandardScaler, KMeans(k=3, n_init=30, random_state=17), two feature specifications only.
- **Cohorts:** tracks with ≥3 observations (72; 39+33) and stricter existing descriptive gate (51; 24+27). Excludes 54 short tracks from the first cohort; for the second excludes an additional 21 low-reliability profiles.
- **Stability:** 20 seed refits, 80 **paired** bootstraps that resample *whole trajectories within each sequence*, refit the model and predict cluster labels on the identical full cohort. ARI is label-permutation invariant. These are computational robustness summaries, **not** biology confidence intervals.
- **Reproduction:** `python scripts/benchmark_ctc_motility_feature_ablation.py --output /tmp/ctc_motility_ablation.json`. [Successful independent real-data workflow](https://github.com/chrishotza/ai4s-life-science-2026/actions/runs/38022564912) and [raw output JSON artifact](https://github.com/chrishotza/ai4s-life-science-2026/actions/runs/38022564912/artifacts/11658948640).

## Measured results

| Cohort | Model | Silhouette ↑ | 80-bootstrap ARI median ↑ | ARI p05 ↑ | Seed ARI minimum ↑ |
|---|---|---:|---:|---:|---:|
| **72 tracks**, ≥3 frames | Legacy nine features | 0.3443 | 0.6867 | **0.4906** | 0.9230 |
| | Motion-only two features | **0.4796** | **0.7868** | 0.3433 | **1.0000** |
| **51 confident tracks** | Legacy nine features | 0.3890 | **0.7746** | **0.5311** | 0.9427 |
| | Motion-only two features | **0.4313** | 0.7442 | 0.3026 | **1.0000** |

**Interpretation:** For the 72-track cohort, the motion-only specification increases internal silhouette by **+0.1353** and median bootstrap ARI by **+0.1001**, but degrades bootstrap ARI p05 by **-0.1473**. In the 51-track higher-quality cohort, silhouette improves **+0.0423** while median bootstrap ARI **declines -0.0305** and the p05 tail declines **-0.2285**. A visually cleaner scatter plot is not stronger evidence that clusters are stable under perturbation. In particular, there is **no uniformly superior method** here.

## Product decision and next hypothesis

1. **Retain legacy nine-feature clustering as the documented default.** Do not re-label original 126 real-image tracks or rewrite archived phenotype evidence.
2. Offer **motility-only** as an explicitly opt-in alternative, usable only with at least three observations per fitting trajectory.
3. Before promoting either clustering scheme to biological-state reporting, obtain **genuinely independent stage/perturbation labels**, better raw-image transfer, sequence/well-level heldout tests and measured uncertainty. No statistical significance or biology validation follows from same-data unsupervised ARI and silhouette.
4. Test an **a priori morphology-aware, uncertainty-aware** representation on new batches rather than searching the same two sequences for a prettier ARI.

The change improves the reproducibility and scientific selectivity of the *research workflow* by making the confound test explicit. It does not show newly validated biological impact or competition ranking improvement.
