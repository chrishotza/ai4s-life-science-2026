# Biological value and falsifiable validation plan

## Researcher question

**Which individual cells in a time-lapse recording display persistent migration, altered motion or insufficiently observed trajectories?**

This question matters in live-cell culture, migration studies and, prospectively, organ-on-chip imaging. It is framed as a *measurement and triage* task. No drug effect, mechanism, clinical marker or biologically verified state is claimed in this submission.

## What exists today (measured, not proposed)

The image-derived CellposeSAM-v2 / tracking / temporal-phenotype path was evaluated on **168 raw DIC-C2DH-HeLa frames**, two complete sequences. The internal CTC protocol produced mean instance F1@IoU 0.5 **0.9354**, detection F1 **0.9684** and temporal-link F1 **0.9808**; reference annotations were **not** fed in as detections. Reproducible evidence: [completed run 37930909373](https://github.com/chrishotza/ai4s-life-science-2026/actions/runs/37930909373) and [committed summary](evidence/ctc/full_sequence_metrics.json).

The analysis emitted **126 per-track profiles** with features including track duration, displacement, speed, directional persistence, trajectory quality and descriptive computational groups. A separate evidence gate classed **54 as audit-only**, **21 as descriptive but low confidence**, and **51 as eligible for *descriptive computational* reporting**. The gate does **not** establish biological truth.

The cell instance segmentation component is **pretrained CellposeSAM-v2, a dependency rather than a new segmentation model**. The project contribution is an auditable pipeline from detections through temporal association to per-cell features, evidence gates and reproducible output.

## An example workflow that can actually be demonstrated

1. Input a real sequence of live-cell microscopy images and record microscope metadata / spatial calibration.
2. Generate predicted cell instance masks with the pretrained image backend; do **not** substitute reference segmentation masks or reference centroids.
3. Link image-derived observations across successive time points and export per-cell trajectories.
4. For tracks with sufficient coverage, inspect speed, displacement, persistence and confidence information; preserve short/incomplete tracks for audit, without meaningful behavior labels.
5. Export the resulting CSV/JSON and use it to **choose candidate cells for closer human review**.

A researcher can examine *descriptive patterns in image-derived behavior*. This is already operationally useful for organizing review, but no downstream savings, decisions, interventions or biology outcomes have been measured.

## Next test: independent perturbation or cell-state validation

**Falsifiable hypothesis (not a demonstrated result):** a real treated-versus-control culture experiment contains condition-associated changes in migration persistence or speed detectable by this pipeline beyond changes caused by image quality or tracking errors.

Minimum experiment design:

1. Acquire time-lapse sequences from treated and matched control wells, spanning **independent biological replicates or batches**, with recorded experimental condition labels and spatial/time calibration.
2. Predeclare a biologically motivated endpoint, e.g. per-cell mean speed or directional persistence, alongside tracking/segmentation quality criteria.
3. Split evaluation by **whole well and independent batch**, not randomly by adjacent frames or daughter tracks, to avoid correlated train/test leakage.
4. Use manual microscopy review and blinded annotations to verify segmentation, temporal identity and candidate divisions on a held-out subset.
5. Quantify condition effects at the appropriate replicate level (e.g. well/batch), with uncertainty and negative controls, and compare against static-frame and non-temporal feature baselines.
6. Report failures and domain shift, including ALFI transfer failures, instead of collapsing different benchmark protocols into one score.

**Pass condition:** on *new* held-out wells/batches, predefined temporal features reliably distinguish the independent known conditions and remain robust after error checks, relative to a non-temporal baseline. **Fail condition:** effects disappear out of distribution or track quality confounds the biological signal. Only after success could biologically grounded state/response claims be considered.

## Division-event clip: strict presentation policy

CTC reference lineage annotations can identify windows in which real mitosis is annotated. Their use for clip selection **is not evidence that the AI inferred the mitosis**. Show a parent-to-daughter prediction or claim end-to-end division recognition only after comparing **image-derived** predicted candidate lineage edges against the independent annotations on the chosen clip. Otherwise label the event explicitly **reference-annotated division, illustrative only**.

## What has not been demonstrated

- Independent biological phenotype or cell-cycle state validation from raw images.
- Drug response or treatment effect from the current CTC data.
- Robust cross-modality ALFI instance segmentation (measured CellposeSAM-v2 F1 was **0.2282** in the reported ALFI pilot).
- Transfer to actual organ-on-chip experiments or reproducible experimental time savings.
- Official Cell Tracking Challenge leaderboard scores.

This distinction is central to the project's claim-evidence policy: [full matrix](CLAIM_EVIDENCE_MATRIX.md).
