# GIDE terminal cellular measurement — pre-result audit gate (2026-10-09)

## Question

Can real, independently sourced terminal GIDE Hoechst C01 TIFFs provide **plausible per-nucleus segmentation**, and can matching Annexin V C05 TIFFs produce reproducible nucleus-proximal fluorescence measurements?

This is a bridge from image-level intensities to **per-object proxies**, NOT cell-death labels or temporal phenotype validation.

## Study / data

CC0 S-BIAD2515: https://www.ebi.ac.uk/biostudies/BioImages/studies/S-BIAD2515
30 wells: 10 doses × 3 wells; rows C–E, columns 02–11. Same field of view (F0001), same terminal time (T0014), same Z0001, C01 Hoechst and C05 AnnexinV. Total **60 original TIFF images**.

## Frozen pipeline

- Segment nuclei ONLY from terminal Hoechst: smoothed, low-frequency-background-subtracted image, fixed Otsu/percentile threshold, morphological cleanup, distance-transform watershed with fixed parameters, area filtering.
- Measure AnnexinV signal in a fixed-radius (~12px) ring outside each nucleus, excluding all nucleus-mask pixels; fixed p10 background subtraction within the AnnexinV image. This is a **nuclear-proximal proxy** and NOT a label of a tracked or apoptotic individual cell.
- Export raw cellular ROI table, per-well aggregates and per-file SHA-256 (do not store cell count as count of biological replicates).
- Emit 6 example mask-overlay QC images from control/high-dose wells for **manual visual review**.
- Automated plausibility QC per well: 10–3,000 segmented nuclei, mask foreground fraction 0.0003–0.55, >0 ROI summaries. This is a smoke gate, not annotation accuracy.
- Primary exploratory association: dose vs **per-well median nucleus-proximal AnnexinV p90**, two-sided Spearman permutation test shuffling wells, 9,999 permutations.
- Secondary association: dose vs per-well valid nucleus count, same procedure (segmentation bias/density check).
- Report the complete full dose table including weak/negative outcomes. No parameter optimization to maximize association.

## Decisions

*Engineering GO*: all 60 images downloaded, checksums saved, script and tests passing; at least 24 of 30 automated QC wells pass; segmentation overlays reviewed and plausible.

*Scientific no-go unless independently validated*: per-object ROI signals are not apoptosis ground truth. Because dose is perfectly confounded with plate column, a dose association alone cannot validate biology. Cells in the same well are pseudoreplicates, so tests must use 30 wells, not thousands of nuclei.

*Real phenotype value gate*: only after independent cell tracks, matched terminal Annexin V labels, heldout wells or independent plates, and incremental comparison against simple per-cell imaging features can one assert evidence for temporal phenotyping.

Workflow: https://github.com/chrishotza/ai4s-life-science-2026/actions/workflows/gide-terminal-cells.yml
