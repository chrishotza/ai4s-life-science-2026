# Real CTC phenotype-group stability: seed and trajectory-bootstrap audit

**Date:** 2026-10-09. **Dataset:** CTC DIC-C2DH-HeLa 01 and 02; 84 images per sequence. **Model:** pretrained CellposeSAM-v2 image-to-phenotype pipeline.

## Source and provenance

The same **126 image-derived trajectory profiles** (seq01 79, seq02 47) were recovered from the original full-sequence Cellpose experiment, [GitHub Actions run 37930909373](https://github.com/chrishotza/ai4s-life-science-2026/actions/runs/37930909373), commit ffc135c56fb5adcf2d23bcf4e8461ba284dcc870. The benchmark rejects any SHA256 mismatch against that run's source provenance JSON.

- [Reproducible code](../scripts/benchmark_ctc_real_phenotype_stability.py) runs the **actual package's PhenotypeDiscoveryModel** (KMeans k=3 with StandardScaler, n_init=30), not a replacement implementation.
- [Successful workflow](https://github.com/chrishotza/ai4s-life-science-2026/actions/runs/37975995897).
- [Durable aggregate JSON](evidence/ctc/stability_summary.json) and [derived feature CSV](evidence/ctc/derived_phenotype_features.csv) are **committed to main**, surviving expiring Actions artifacts. No microscopy images or external proprietary weights were copied.
- Seed sensitivity: reference seed 17 versus 20 independently fit seeds, measured by adjusted Rand index (ARI); seed label-number permutations do not affect ARI.
- Stability under **80 sequence-stratified trajectory bootstraps**: resample entire *trajectory profiles* with replacement **within each of the two sequences**; refit KMeans and StandardScaler on the resampled training set, then predict all members of the original cohort; compare with the fixed original fit using ARI. p05/p95 characterize the distribution of the bootstrap outcomes, **not biological confidence intervals**.
- Cohort variants: all observations; at least 3 observations per track; and reliability score >= 0.5. These quality thresholds were examined post hoc and are sensitivity controls, not a selected validation optimum.

## Measured results

| Cohort | Tracks | Single-observation tracks | Seed ARI (min / mean) | Bootstrap ARI median | Bootstrap ARI p05–p95 | Silhouette |
|---|---:|---:|---:|---:|---|---:|
| All tracks | 126 | **43** | 1.000 / 1.000 | **0.9448** | [0.7983, 1.0000] | 0.5110 |
| >=3 observations | 72 | 0 | 0.9230 / 0.9769 | **0.6867** | [0.4906, 0.9150] | 0.3443 |
| Reliability >=0.5 | 56 | 0 | 1.000 / 1.000 | **0.8099** | [0.4647, 1.0000] | 0.4374 |

**Interpretation:** The apparent high stability of all profiles is partly due to numerous trivial short tracks: **43/126 have only one frame**, and **54/126 have fewer than three**. In the reference pooled KMeans fit, the 43 singleton trajectories all fall into one numeric cluster containing 51 observations. Such a cluster can encode **track duration/observation sparsity**, not a confirmed motility phenotype. Restricting the evaluation to tracks with at least 3 observations substantially reduces the bootstrap ARI.

The reported 126 profiles and their cluster assignments originate from the original pipeline and have different semantics from the independently expert-annotated ALFI mitosis-phase classification. **A stable unsupervised group is NOT biological ground truth**. The 2-sequence sample is small and its trajectories are not independent microscopy batches or experimental treatment conditions.

## Corrective action in the product

- Updated [phenotype extraction](../src/ai4s_phenotype/phenotype.py) to label fewer than 3 observations as **insufficient_temporal_evidence** rather than highly_non_directional or high_mobility.
- Updated [discovery model](../src/ai4s_phenotype/discovery.py) to preserve the original numeric cluster ID for reproducibility/ARI but override its **interpretive name** to insufficient_temporal_evidence for tracks with fewer than 3 observations. The output includes phenotype_temporal_evidence_sufficient.
- Added [regression tests](../tests/test_short_track_phenotype_gate.py) for one- and two-observation trajectories.

This does **not** change an old result's numerical clusters or magically create long tracks. It prevents a short track from receiving an overstated behavioral interpretation in future reports.

## Falsifiable next step

If downstream biological impact is claimed, measure phenotype-state agreement against **independent biology labels** or **controlled perturbations** on previously unused imaging batches. The ALFI probe's exploratory improvements on human expert boxes are a promising but separate classification task, and cross-domain raw-image segmentation on ALFI remains a NO-GO. Do not use ARI stability or Cellpose CTC segmentation accuracy as a surrogate for biological label correctness.
