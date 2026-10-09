# Competition Rubric Evidence Map

This document maps each AI4S Open Innovation judging criterion to concrete evidence in the submission.

## 1. Problem Importance & Potential Impact — 30%

**Judge-facing claim:** The system turns time-lapse microscopy into an interpretable temporal representation of single-cell behavior, rather than stopping at segmentation or track IDs.

**Evidence**
- README.md: competition positioning and scientific output.
- docs/KAGGLE_WRITEUP.md: Problem, Why this matters, Limitations.
- docs/TECHNICAL_REPORT.md: Sections 2 and 11.
- Real CTC evidence: trajectory preservation and temporal phenotype extraction.
- Cross-sequence image-to-tracking validation: raw microscopy is evaluated before tracking.

**What must be visible in the final demo:** real microscopy → cell observations → trajectories → temporal features → phenotype groups → quantitative validation.

## 2. Technical Approach & Innovation — 30%

**Judge-facing claim:** The innovation is the explicit bridge from temporal association to a reusable phenotype representation with physical-unit semantics, lineage context, and a reproducible fit/transform discovery boundary.

**Evidence**
- src/ai4s_pipeline/engine.py: canonical orchestration boundary.
- src/ai4s_tracking/: deterministic association variants and physical-unit gating.
- src/ai4s_phenotype/: temporal features and phenotype discovery lifecycle.
- docs/ARCHITECTURE.md: data contracts, coordinate boundary, model lifecycle, validation boundary.
- Method/gating ablation and no-oracle CTC sensitivity control.
- Observable trajectory-integrity and phenotype-reliability scores, validated under controlled tracking perturbations.
- Uncertainty-aware cohort comparison with standardized effect sizes and bootstrap confidence intervals.

**What must be visible in the final report:** why this is more than a tracker, why the architecture is interpretable, and which components are validated versus experimental.

## 3. Results & Validation — 20%

**Measured real-data evidence**
- CTC reference-centroid association: mean F1 0.99228.
- External py-ctcmetrics 1.3.3: TRA/LNK captured for sequences 01 and 02.
- No-oracle sensitivity control: unchanged TRA/LNK.
- Downstream trajectory-feature preservation: coverage and persistence error.
- Cross-sequence image-to-tracking benchmark: raw microscopy is segmented before evaluation, with sequence-level holdout.
- Cross-sequence PhC-C2DL-PSC raw-image-to-instance-mask validation with one-to-one object matching at IoU ≥ 0.5; silver-mask primary evaluation and sparse gold-mask cross-check are kept distinct.

**Controlled validation**
- Synthetic tracking regression.
- Detection perturbation → tracking → phenotype robustness, including reliability diagnostics.
- Gap-closing stress test.
- Lineage representation validation.
- Phenotype-discovery robustness.

**Claims boundary**
- No biological phenotype classification claim is made without independent biological labels or perturbation annotations.
- CTC TRA/LNK values are not presented as official CTC leaderboard scores.
- Reference-centroid benchmarks are labeled as association-isolation evidence.

## 4. Reproducibility & Implementation Quality — 10%

**Evidence**
- Installable Python package.
- Dockerfile.
- GitHub Actions CI and benchmark workflows.
- Deterministic tests and benchmark scripts.
- Exact reproduction commands in docs/TECHNICAL_REPORT.md.
- External dependency provenance and AI-development-tool disclosure.

**Final gate:** run the full benchmark suite on the final public commit and verify the reported numbers.

## 5. Presentation Quality — 10%

**Required final narrative**
1. The biological/computational problem.
2. Real microscopy input.
3. Transparent detection and tracking.
4. Temporal phenotype representation.
5. Quantitative validation.
6. Limitations and scientific use boundary.

**Demo requirements**
- ≤5 minutes.
- Publicly viewable without login or payment.
- Show actual system execution and real microscopy.
- Show quantitative output instead of generic slides alone.
- End with the single-sentence contribution and the evidence boundary.

**Primary presentation assets**
- scripts/make_demo_video.py
- .github/workflows/demo-video.yml
- docs/KAGGLE_WRITEUP.md

## Final zero-surprises gate

Before submission, the repository, technical report, Kaggle Writeup, demo, benchmark outputs, and claims auditor must all agree on:
- dataset name and provenance;
- physical scale;
- selected tracking method and gate;
- headline F1;
- TRA/LNK values;
- phenotype-preservation numbers;
- the distinction between reference-centroid evidence and image-derived end-to-end evidence.


## Reliability evidence

The engine now exposes a bounded track_integrity_score and phenotype_reliability_score. These scores are deliberately descriptive: they combine observables already present in the trajectory and association output and are not presented as calibrated probabilities.

The synthetic robustness benchmark records reliability scores alongside phenotype-group ARI and tracking-error profiles. The intended use is operational: down-weight ambiguous trajectories, surface low-integrity cells for review, and avoid treating every unsupervised phenotype assignment as equally trustworthy.


## Scientific decision layer

The cohort comparison API is the final analysis layer between phenotype extraction and experimental interpretation. It reports effect sizes and bootstrap intervals for selected trajectory features across two cohorts while keeping biological labeling outside the software unless independent evidence is supplied.
