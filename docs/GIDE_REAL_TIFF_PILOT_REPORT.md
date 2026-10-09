# GIDE external real-image pilot — 2026-10-09

## Data provenance

Official EMBL-EBI BioImage Archive: https://www.ebi.ac.uk/biostudies/BioImages/studies/S-BIAD2515 (study license CC0). All 6,480 entries returned in seven pages of the official file inventory are TIFF images. The combined CellProfiler/scDINO Parquet files named in the WayScience analysis scripts are **not** listed among these deposited files; their download was not found and they were not used here.

Direct image base URL: https://ftp.ebi.ac.uk/biostudies/fire/S-BIAD/515/S-BIAD2515/Files/

Source channel annotation: https://github.com/WayScience/live_cell_timelapse_apoptosis/blob/main/data/metadata_AnnexinV_2ch.csv (C05 = terminal AnnexinV, C01 = Hoechst); dose map: https://github.com/WayScience/live_cell_timelapse_apoptosis/blob/main/data/platemap_6hr_4ch.csv

## Executed evidence

- Workflow: https://github.com/chrishotza/ai4s-life-science-2026/actions/runs/37956274582
- Completed SUCCESS against commit 4eee0b501b9f862dc8396ed21b6c26f9346b8a81.
- Downloadable evidence artifact: https://github.com/chrishotza/ai4s-life-science-2026/actions/runs/37956274582/artifacts/11627948996
- Artifact content: manifest.json, image_features.csv (SHA-256 checksums of source TIFFs), summary.json.
- Code: scripts/run_gide_tiff_pilot.py.
- 24 real TIFF images, one field of view each: 3 wells at 0 nM (C-02, D-02, E-02) and 3 at 156.25 nM (C-11, D-11, E-11). Per well: 3 Hoechst images (T1, T7, T13) and one terminal Annexin V image (T14).

## Measured image-level descriptives

| Image metric | Control mean (3 wells) | Treated mean (3 wells) | Difference |
|---|---:|---:|---:|
| Terminal AnnexinV corrected image mean | 101.353 | 98.046 | -3.307 |
| Terminal AnnexinV corrected image p99 | 538.333 | 693.333 | +155.000 |
| Hoechst T13-T1 corrected image mean | -1.212 | -2.432 | -1.220 |
| Hoechst T13-T1 corrected p99 | -45.667 | 194.333 | +240.000 |

Exploratory Spearman correlation (well-level, n=6) of Hoechst change to terminal AnnexinV corrected mean:
- Delta corrected mean: rho -0.143, nominal p 0.787.
- Delta corrected p99: rho -0.600, nominal p 0.208.

Exact two-sided permutation over all 20 assignments of three treated versus three control wells, performed on the reported measurements (exploratory):
- Terminal AnnexinV corrected p99 group difference: p = 0.10.
- Hoechst corrected p99 temporal-change group difference: p = 0.10.
- Terminal AnnexinV corrected image mean group difference: p = 0.60.

## Adversarial claim boundary

GO: The repository can fetch, decode and quantitatively measure genuine external live-cell images with real treatment dose provenance, preserving hashes and a reproducible artifact.

NO-GO: Results **do not** demonstrate biological phenotype discovery, significance, prediction of apoptosis, incremental AI4S phenotype value, cell-level independent ground truth, or an official Kaggle score. AnnexinV was summarized over the whole unsegmented FOV, not individual cells. Average and upper-tail measurements disagree in direction. With three wells per group, even perfect two-sided group separation yields a minimum exact permutation p of 0.10. No scientific superiority can be claimed.

Next: if time allows, increase to 30 independent wells spanning ten doses, use multiple FOVs, segment terminal cell objects, preregister early-time prediction and evaluate well-level heldout performance against simple controls. Keep dose and future terminal features OUT of predictors.
