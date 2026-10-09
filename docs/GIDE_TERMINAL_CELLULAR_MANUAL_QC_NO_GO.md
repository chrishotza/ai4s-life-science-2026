# GIDE 30-well terminal nuclear-proxy pilot: independent manual QC — NO-GO

Date: 2026-10-09. Review performed before interpreting the GIDE cellular association.

## Executed evidence

- [Successful real-TIFF workflow](https://github.com/chrishotza/ai4s-life-science-2026/actions/runs/37962992778) with 60 official S-BIAD2515 images; [source artifact with QC mask overlays](https://github.com/chrishotza/ai4s-life-science-2026/actions/runs/37962992778/artifacts/11631833778).
- 30 wells, 10 concentrations with three experimental wells per dose. Terminal Hoechst C01 segmentation into connected components; adjacent pixels of terminal AnnexinV C05 measured as a per-nucleus proxy, not single-cell apoptosis truth.
- Automated QC accepted 28/30 wells and produced 3,708 nucleus-proxy ROI measurements. One C06 official Hoechst TIFF produced an invalid/constant array and was logged as missing experimental input. C03 had only 8 segmented components and failed minimum-count QC.
- Automated well-level Spearman correlation between dose and median nucleus-proximal Annexin V p90 reported rho = 0.5241, permutation p = 0.0051 on the 28 selected wells; NO biological inference should be drawn from this number.

## Adversarial visual audit: FAILED

The automated QC is insufficient to establish acceptable segmentation. At least two reviewed examples (D-04 and C-05) contain visually many nuclei, yet the segmentation overlays show only approximately 26 and 13 accepted components, respectively. These images are in the cited artifact as D-04_segmentation_qc.png and C-05_segmentation_qc.png. This is severe undersegmentation / selective acceptance. Therefore, a 28/30 well auto-passing result is a false sense of coverage. Selection bias can distort both per-cell intensity summaries and any apparent dose association. Prior watershed method (workflow 37961863369) separately showed oversegmentation and halted at invalid C06 input; connected components reduced fragmentation but did not resolve variable undersegmentation.

Verdict: engineering feasibility GO, biological cellular phenotype QC NO-GO. Do not quote the p-value as evidence of independent cell-state discovery, apoptosis prediction, or success of temporal phenotypes.

## Rigorous next step

Validate pixel segmentation against expert masks (e.g. ALFI MI01–MI08 ground-truth images and masks). For GIDE first obtain/verify terminal nuclei plus matched cell-level AnnexinV objects using a pretrained nucleus-specific segmenter and manually audited masks; quantify detection sensitivity/precision and bias by dose. Only after per-object labels and reliable tracks are available compare image-only vs temporal phenotype models on heldout wells, ideally separately randomized treatment plates.

Independent alternative now available: ALFI expert-annotated phenotype tables (PhenoTruth.csv) and detection/lineage annotations (DTLTruth.csv) were recovered without downloading the 8.4GB imagery. These support sequence-heldout classifier baselines, though annotations alone do not validate raw-image inference.
