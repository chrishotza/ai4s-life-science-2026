# Final Demo Script

Target duration: 2–3 minutes. Hard maximum: 5 minutes.

## 0:00–0:20 — Problem

**Visual:** real DIC-C2DH-HeLa microscopy.

**Narration:**

"Time-lapse microscopy contains much more than a sequence of images. It contains how individual cells move, persist, divide, and change over time.

The goal of this system is to turn that temporal information into an interpretable single-cell phenotype representation instead of stopping at segmentation or track IDs."

## 0:20–0:45 — Real image input

**Visual:** raw microscopy followed by transparent baseline detections.

**Narration:**

"The public baseline starts directly from microscopy. It uses transparent image preprocessing and connected components to produce reproducible cell observations.

This stage is deliberately simple and inspectable, and it requires no proprietary model or paid service."

## 0:45–1:15 — Tracking

**Visual:** real microscopy sequence with trajectories.

**Narration:**

"Those observations are associated through time using deterministic spatial tracking in physical units.

The selected real-data association configuration is mutual nearest neighbor with an 8 micrometer gate.

Tracking is infrastructure. The scientific output is the behavior represented by the resulting trajectories."

## 1:15–1:45 — Temporal phenotype

**Visual:** phenotype scatter plot and per-cell feature panel.

**Narration:**

"For every trajectory, the engine derives duration, displacement, path length, speed, directional persistence, temporal integrity, and lineage context.

These features can be transformed into reproducible unsupervised behavioral groups with an explicit fit-and-transform lifecycle."

## 1:45–2:15 — Validation

**Visual:** validation summary.

**Narration:**

"On DIC-C2DH-HeLa sequences 01 and 02, the association-isolation benchmark reaches a mean F1 of 0.99228.

Downstream trajectory preservation gives 0.9451 mean coverage and 0.0439 directional-persistence mean absolute error.

The same association path was also checked with pinned py-ctcmetrics, producing TRA and LNK values above 0.97 on both sequences. A no-oracle sensitivity control produced the same values."

## 2:15–2:35 — Cohort decision layer

**Visual:** synthetic cohort-effect validation card.

**Narration:**

"The same phenotype representation can be compared across experimental cohorts. The comparison layer reports effect sizes and bootstrap confidence intervals, so a change can be quantified rather than described only by cluster membership.

This card is a synthetic method validation, not a biological treatment result."

## 2:35–2:55 — Scientific boundary

**Visual:** limitations card.

**Narration:**

"One boundary is important: the strongest CTC association result uses reference centroids as detections to isolate temporal association from segmentation. It is not presented as an end-to-end biological phenotype score.

Image-level validation, association validation, synthetic robustness, and biological interpretation are therefore kept as separate evidence layers."

## 2:55–3:10 — Close

**Visual:** final title and repository.

**Narration:**

"The contribution is a reproducible bridge from microscopy to trajectories to interpretable temporal phenotype.

The next scientific step is independent biological validation against labeled perturbations and conditions."

## Recording rules

- Show the real system and microscopy, not generic stock footage.
- Keep benchmark values visible long enough to read.
- Say "association-isolation" whenever reference centroids are used.
- Do not call TRA/LNK values official CTC leaderboard scores.
- Do not call unsupervised clusters biological diagnoses.
- End on the scientific contribution and evidence boundary.
- Label the cohort card as synthetic methodological validation.
