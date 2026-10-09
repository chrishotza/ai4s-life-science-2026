# External biological validation connections

Status: **connection plan activated**. Date: 2026-10-09.

Goal: turn the current engineering claim (microscopy -> segmentation -> tracking -> phenotype profiles) into a biological validation claim by testing against independent biological labels.

## Route A — ALFI

Official source: https://doi.org/10.6084/m9.figshare.c.6436958.v1

Why it matters:
- ALFI provides 29 label-free time-lapse microscopy sequences from hTERT RPE-1, HeLa, U2OS and U2OS fluorescent cells.
- It includes pixel-wise masks, object-wise boxes, tracking information and phenotype/cell-cycle annotations.
- It is directly aligned with the repository's DIC/label-free image-to-track-to-phenotype system.

Primary test idea:
- Use ALFI annotations as external labels for mitosis/interphase/division-related phenotype classes.
- Compare three conditions:
  1. simple trajectory summary baseline;
  2. repository temporal features;
  3. repository temporal features plus phenotype-discovery outputs.
- Split by sequence/cell line/condition where possible; do not split correlated cells from the same video across train/test.

Competitive role:
- Best route for showing that temporal phenotype features recover cell-cycle or division-related phenotype labels in label-free microscopy.

Risk:
- The dataset is larger and may require format adaptation from figshare/ALFI directory structure.

## Route B — GIDE / BioImage Archive S-BIAD2515

Official source: https://www.ebi.ac.uk/biostudies/bioimages/studies/S-BIAD2515
Project portal: https://www.gide-project.org/portal
Associated processing code: https://github.com/WayScience/live_cell_timelapse_apoptosis

Why it matters:
- High-content live-cell time-lapse imaging of HeLa cells undergoing apoptosis under a 10-point staurosporine dose response.
- Includes raw and illumination-corrected images, segmentation masks, tracking outputs, morphological features and single-cell ground-truth apoptosis readout from AnnexinV.
- Provides a strong external biological endpoint: apoptosis / dose response.

Primary test idea:
- First use existing processed masks, tracks and features where licensing/access allows; avoid heavy full-image recomputation if time is short.
- Map repository phenotype features onto tracks or create an adapter from GIDE tracking outputs to `nodes.csv` / `temporal_edges.csv` / phenotype table.
- Evaluate whether repository phenotype features improve prediction or separation of apoptosis/dose/time outcome over simple speed/displacement baselines.
- Aggregate at well/field/track level carefully; bootstrap over independent wells, not over correlated cells.

Competitive role:
- Best route for a strong biological story: dynamic cell-state trajectories preceding apoptosis.

Risk:
- More complex imaging modality and preprocessing; may be faster to use processed tracking/features rather than raw image ingestion.

## Selection logic

Use both in parallel for scouting, but prioritize by quickest path to a defensible result:

1. If GIDE processed track/feature tables are easy to load, run GIDE first because it has stronger biological ground truth.
2. If GIDE access or format is slow, run ALFI first because its label-free videos and annotations are closer to our current pipeline.
3. Do not claim biological phenotype validity from CTC alone.

## Minimum success criterion

A strong result requires a held-out biological-unit evaluation showing that repository phenotype features add measurable value over simpler baselines.

Acceptable immediate claim if time is short:
- external dataset connection established;
- adapter design specified;
- sample metadata and labels identified;
- one small smoke test loads labels and produces a phenotype table.

Winning-level claim requires:
- held-out evaluation;
- baseline comparison;
- uncertainty estimate over independent wells/sequences;
- leakage audit.

Owner: Bio-Validation Lead, coordinated by GPT-6 / Chris Hotza Research Lab.
