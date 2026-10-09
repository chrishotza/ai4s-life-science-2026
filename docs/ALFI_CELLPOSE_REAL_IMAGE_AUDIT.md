# ALFI pretrained Cellpose-SAM v2 real-image benchmark (2026-10-09)

Status: **successful reproducible inference; biological end-to-end instance QC NO-GO**.

## Source / provenance

- ALFI (Antonelli et al., CC BY): https://doi.org/10.6084/m9.figshare.23798451.v1
- [Successful GitHub Action](https://github.com/chrishotza/ai4s-life-science-2026/actions/runs/37969271139) at commit 0def630d5031ea97fd9219d664311b1e181d0714.
- [Raw result artifact, including six QC overlays](https://github.com/chrishotza/ai4s-life-science-2026/actions/runs/37969271139/artifacts/11634678094).
- Code: scripts/benchmark_alfi_cellpose.py, using existing project's ai4s_imaging.cellpose_backend.CellposeSegmenter, CPU model cpsam_v2 pretrained upstream; no training or fine-tuning on any ALFI labels.
- Six original ALFI image/mask pairs: MI02/MI03/MI04, image times T0001/T0009. Read from remote Figshare ZIP by HTTP ranges, subsample images by factor two to 512×640. Original masks annotated classes background 0, interphase 128, mitosis 255; both cellular classes counted as foreground.
- Independent artifact audit matched **12 of 12 image/mask SHA256 records** between source extraction manifest and inference summary.

## Exactly matched six-frame comparison

For fairness the supervised model / bright-p92 baseline values below were recomputed from their own earlier original artifact restricted to precisely the same six frames, *not* their 12-frame global averages. Per-frame averages and pooled counts are reported.

| Model | Pixel Dice average | Instance F1@IoU50 frame average | Predicted instances | GT instances | Matched instances |
|---|---:|---:|---:|---:|---:|
| Bright p92 image threshold | 0.24989 | 0.00123 | 1,393 | 58 | 1 |
| Repo supervised MI01→MI02–MI04 | **0.46498** | 0.06533 | 389 | 58 | 12 |
| Repo supervised + MI01 area size gate | **0.46915** | 0.06669 | 386 | 58 | 12 |
| Pretrained Cellpose-SAM v2, no ALFI training | 0.30347 | **0.16889** | **23** | 58 | **7** |

Per Cellpose test sequence:
- MI02: mean Dice 0.31555, mean instance F1 0.19167; 3/22 expert instances matched, 9 predictions.
- MI03: Dice 0.24941, F1 0.14835; 2/20 matched, 7 predictions.
- MI04: Dice 0.34543, F1 0.16667; 2/16 matched, 7 predictions.

Average processing time roughly 60–62 seconds per frame CPU. Visual example MI03 T0001 shows under-segmentation (large predicted green boundaries spanning multiple annotated cells) and missed nuclei.

**Interpretation:** Cellpose reduces the severe overprediction observed with the repository's small supervised segmenter (23 vs 389 instances for 58 expert references), improving *per-frame instance F1* from ~0.067 to ~0.169; nonetheless it correctly matches fewer true cells (7 vs 12). The supervised method retains better *pixel Dice*, but predicts excessive instances. Thus no method meets a credible instance detection threshold. Note that ALFI masks might not annotate every visible structure; report this uncertainty without treating unannotated predictions as verified.

## Crucial validation boundary

**Engineering GO:** genuine external image + expert-mask access; both actual inference methods run with artifact provenance and visual QC; real cross-domain failure exposed.

**Scientific NO-GO:** no credible raw-image cell detection / tracking / phase-of-mitosis phenotype advantage. Neither the pretrained Cellpose nor the supervised model reaches acceptable instance F1. Quoting isolated [oracle-tracker F1 0.9943](ALFI_ORACLE_TRACKING_EXTERNAL_RESULTS.md) as an end-to-end result would be wrong because oracle boxes were used there.

**Promising but distinct:** [ALFI assay-stratified baseline](ALFI_ASSAY_STRATIFIED_REAL_RESULTS.md) shows a post-hoc +0.218 macro-F1 advantage for motion features distinguishing MI mitosis phases, **also on oracle expert boxes/tracks**. It has not been reproduced after real image segmentation errors.

## Next work to close the product gap

1. Focus supervised segmentation on ALFI with stronger cell-domain training across disjoint MI sequences or fine-tune a pretrained detector with MI01–MI04 masks, then evaluate untouched MI05–MI08. Do not tune on a future claimed untouched holdout.
2. Evaluate both instance IoU≥0.5 matching and pixel Dice, not pixel Dice alone, and review QC overlays for false merges and missed cells.
3. Only after adequate segmentation attempt end-to-end tracking and temporal phenotype classification with real inferred objects and held-out expert MI labels.
4. Keep the existing model-independent oracle tracking benchmark as a robust component validation, not a replacement for complete product validation.
