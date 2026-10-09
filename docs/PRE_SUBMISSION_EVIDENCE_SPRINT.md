# Pre-submission evidence sprint

Date: 2026-10-09
Branch: `research/pre-submission-evidence-sprint`

## Purpose

This document turns the current repository state into an explicit pre-submission operating plan. The goal is not to add more speculative claims; the goal is to protect the strongest result, expose the remaining boundary conditions and focus the next engineering work on evidence judges can audit quickly.

## Current verified product state

The project now has a credible image-derived CTC path:

- Dataset: CTC DIC-C2DH-HeLa.
- Input: raw microscopy frames, not reference detections.
- Segmenter: pretrained CellposeSAM-v2.
- Pipeline: CellposeSAM-v2 -> observations -> tracker -> temporal phenotype profiles.
- Coverage: 2 sequences, 84 frames per sequence, 168 total frames.
- Aggregate metrics from the permanent evidence JSON:
  - mean segmentation F1 at IoU >= 0.5: `0.935436011696652`;
  - mean detection F1: `0.9683949158295722`;
  - mean tracking-edge F1: `0.9808198272802555`.
- Claim boundary: internal CTC evaluation only; not official CTC/Kaggle leaderboard scoring; no independently confirmed biological phenotypes.

The stability audit is also honest and useful:

- 126 derived CTC phenotype profiles.
- 43 profiles have only one observation.
- Full-cohort bootstrap median ARI: `0.9448255857946377`.
- Tracks with at least 3 observations bootstrap median ARI: `0.6867139852870741`.
- Reliability >= 0.5 bootstrap median ARI: `0.809909063176141`.
- Interpretation boundary: this is algorithmic repeatability, not biological truth.

The main CI on `main` is green and includes:

- source compilation;
- ruff static analysis;
- pip dependency check;
- pytest;
- phenotype stability benchmark;
- end-to-end phenotype robustness benchmark;
- submission claim audit.

## External scientific signal from the research scouts

The literature supports the direction of this product, but also tells us exactly where the claim must be tightened.

1. [The CellPhe toolkit for cell phenotyping using time-lapse imaging and pattern recognition](https://consensus.app/papers/the-cellphe-toolkit-for-cell-phenotyping-using-timelapse-wiggins-lord/bb84bcf42ddc54d081f1e551a5210d95/?utm_source=chatgpt) — Laura Wiggins, Alice Lord, Killian L. Murphy, Stuart Lacy, Peter J. O'Toole, W. Brackenbury, Julie Wilson; 2023; Nature Communications; 31 citations. This is directly relevant because it frames time-lapse phenotyping as a downstream layer over segmentation/tracking and emphasizes removal or recognition of erroneous boundaries caused by segmentation/tracking mistakes.
2. [CellPhePy: A python implementation of the CellPhe toolkit for automated cell phenotyping from microscopy time-lapse videos](https://consensus.app/papers/cellphepy-a-python-implementation-of-the-cellphe-toolkit-wiggins-lacy/0177501cd7885721ad6c93c24f3a6a18/?utm_source=chatgpt) — Laura Wiggins, Stuart Lacy, Graeme J. Park, J. Marrison, Ben Powell, B. Cimini, Peter J. O'Toole, Julie Wilson, W. Brackenbury; 2025; Journal of Microscopy; 3 citations. This reinforces the value of a Python, Cellpose-compatible, image-to-phenotype workflow.
3. [Cell tracking with accurate error prediction](https://consensus.app/papers/cell-tracking-with-accurate-error-prediction-betjes-kok/2e6ed982e63f56f283cd93e2b4ab78be/?utm_source=chatgpt) — Max A. Betjes, R. Kok, S. Tans, J. V. van Zon; 2024; Nature Methods; 12 citations. This supports a confidence/error-reporting layer for tracks before downstream biological interpretation.

## Strategic diagnosis

The project is no longer weak because it lacks a pipeline. The pipeline exists and the best CTC result is strong.

The remaining vulnerability is claim transfer:

- CTC image-derived segmentation/tracking is strong.
- CTC phenotype groups are computable but not biologically validated.
- ALFI temporal state prediction improves with past motion features, but it uses expert boxes/track IDs.
- ALFI raw-image segmentation is weak.

Therefore, the strongest submission story is:

> We built and validated an auditable temporal phenotype engine. It can run image-to-track-to-phenotype on real CTC microscopy with strong segmentation/tracking metrics, and it includes explicit quality gates that prevent short or unreliable trajectories from becoming biological claims.

The story should not be:

> We solved biological phenotype discovery or mitosis classification end-to-end across datasets.

## Company operating model for the next sprint

### Orchestrator / QA

Own the claim boundary. Every headline number must have:

- source file or workflow run;
- input type;
- scoring metric;
- whether annotations were used as inputs or only as scoring references;
- whether the result is image-derived, oracle-track, synthetic, or exploratory.

### Scientific scouts

Keep only external references that justify the framing:

- time-lapse phenotyping is valuable;
- segmentation/tracking errors must be filtered before phenotype claims;
- confidence/error reporting on tracks is state-of-the-art direction.

Do not add a literature dump. Judges need three sharp references, not twenty.

### Model hunter

Stop random model chasing unless the candidate can beat the verified CTC CellposeSAM-v2 result or specifically address ALFI domain transfer. A new model is only worth testing if it changes one of these:

- end-to-end CTC F1;
- number of usable reliable tracks;
- ALFI raw-image instance F1;
- phenotype stability after filtering short/unreliable tracks.

### Validation/statistics

The next measurable deliverable should be a confidence-gated phenotype evidence table:

- all tracks;
- min observations >= 3;
- reliability >= 0.5;
- reliability >= 0.75 if enough tracks remain;
- per-sequence counts;
- cluster size balance;
- bootstrap ARI;
- silhouette;
- percentage of tracks blocked from phenotype interpretation.

This converts the apparent weakness — singleton tracks — into a scientific safety feature.

### Product/story

The writeup and demo should lead with the bridge:

`raw microscopy -> instance masks -> tracks -> quality-gated temporal phenotype profiles`

Then show that the product refuses to overclaim when tracks are too short.

## Next code PR recommendation

Implement or tighten a single reproducible artifact: `docs/evidence/ctc/confidence_gated_phenotype_summary.json` plus a Markdown section in `docs/CTC_REAL_PHENOTYPE_STABILITY.md` or `docs/RESULTS.md`.

The artifact should be generated by an existing or new script that loads the CTC derived phenotype features and writes a compact table with:

- cohort name;
- number of profiles;
- number and percentage of short tracks;
- cluster counts;
- seed ARI min/median;
- bootstrap ARI min/p05/median/p95;
- interpretation permission: `audit_only`, `descriptive_ok`, or `blocked_biological_claim`.

Acceptance criteria:

1. `pytest -q` passes.
2. `python scripts/benchmark_phenotype_stability.py` passes.
3. `python scripts/benchmark_end_to_end_phenotype.py` passes.
4. `python scripts/validate_submission_claims.py` passes.
5. The new JSON is committed under `docs/evidence/ctc/`.
6. The README/writeup never uses cluster names as biological phenotypes unless the cohort has enough temporal evidence and an explicit biological label source.

## Submission risk register

| Risk | Current status | Mitigation |
|---|---|---|
| ALFI image segmentation weak | Known, documented | Do not claim ALFI end-to-end cell-state prediction |
| CTC phenotype groups not biologically labeled | Known, documented | Present as computational trajectory profiles only |
| Singleton tracks inflate apparent clustering stability | Diagnosed | Use confidence-gated phenotype summary |
| Top-level license absent | Known | Owner must choose and add a license before encouraging reuse |
| Kaggle writeup link to demo not final | Known | Insert final video/demo link at submission time |

## Decision

The next move should not be another broad exploration. It should be a narrow pre-submission hardening PR:

**Confidence-gated phenotype reporting.**

That is the feature that best converts the current evidence into a judge-friendly, scientifically defensible product.
