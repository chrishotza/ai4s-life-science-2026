# ALFI raw-image, cross-sequence instance segmentation — external pilot audit

Date 2026-10-09. External dataset Antonelli et al., [ALFI](https://doi.org/10.6084/m9.figshare.23798451.v1) licensed CC BY. **This is an image segmentation experiment, NOT yet a successful tracking or phenotype validation.**

## Actual execution

- [Successful run](https://github.com/chrishotza/ai4s-life-science-2026/actions/runs/37968713225) / commit 69570fbacd4268f3153fb66841cfae497796a58f.
- [Evidence artifact](https://github.com/chrishotza/ai4s-life-science-2026/actions/runs/37968713225/artifacts/11633859499) includes 32 PNG (16 original microscopy image frames and 16 original annotation masks), source manifest+SHA-256, quantitative per-frame CSV, summary JSON, and visual overlays.
- An independent audit of downloaded ZIP matched **32/32 source SHA-256 hashes** to its manifest.
- Source image dimensions 1024×1280, 16-bit microscopy, downsampled by factor 2 along x/y to bounded CPU frames 512×640.
- ALFI mask pixel labels: 0 unannotated background; 128 annotated interphase object; 255 annotated mitosis object. Both positive labels are foreground for this segmentation benchmark.
- Repo [Supervised2DSegmenter](../src/ai4s_imaging/supervised.py) trained from **four MI01 image and annotation-mask pairs** (frames 1,5,9,13), no MI02, MI03 or MI04 labels used in the training step.
- Independently evaluated MI02 (previously examined developer sequence), then MI03 and MI04 (new heldout sequences) on frames 1,5,9,13.
- Baseline: foreground from the 92nd percentile of raw-image brightness. Same inputs and masks on all models.
- Post hoc MI01-only area-size QC rule: cutoff = floor(0.35 × 10th percentile of MI01 expert object areas) = **846 half-resolution pixels**. The decision to try size filtering was prompted by MI02 under/over-counts; MI03 and MI04 were not examined while setting this rule.

## Measured heldout outcomes (four frames each)

| Heldout | Model | Mean pixel Dice | Mean pixel IoU | Instance F1 @IoU50 | GT instances | Pred instances | Matched |
|---|---|---:|---:|---:|---:|---:|---:|
| MI02 | p92 brightness | 0.2150 | — | 0.0018 | 48 | 991 | 1 |
| MI02 | Repo supervised | 0.4934 | — | 0.0606 | 48 | 237 | 8 |
| MI02 | + MI01-sized gate | 0.4971 | — | 0.0607 | 48 | 237 | 8 |
| MI03 | p92 brightness | 0.2634 | — | 0.0000 | 41 | 941 | 0 |
| MI03 | Repo supervised | 0.3520 | — | 0.0135 | 41 | 427 | 3 |
| MI03 | + MI01-sized gate | 0.3520 | — | 0.0135 | 41 | 427 | 3 |
| MI04 | p92 brightness | 0.2486 | — | 0.0000 | 32 | 881 | 0 |
| MI04 | Repo supervised | 0.5116 | — | 0.0827 | 32 | 210 | 9 |
| MI04 | + MI01-sized gate | 0.5224 | — | 0.0881 | 32 | 200 | 9 |

Across **12 heldout frames**:
- p92 baseline: mean Dice **0.24233**, IoU **0.13841**, instance F1@IoU50 **0.00061**, GT 121, predicted 2813, matched 1.
- repo supervised: mean Dice **0.45230**, IoU **0.29601**, instance F1 **0.05223**, predicted 874, matched **20/121** GT across 12 frames.
- repo + train-mask size gate: mean Dice **0.45714**, IoU **0.30041**, instance F1 **0.05407**, predicted 864, matched **20/121** GT.

**GO for pixel-level supervised domain-transfer feasibility**, improvement over trivial threshold as evaluated.

**NO-GO for reliable instance separation**: instance F1~0.05 is very poor and ~7× as many objects as annotated are being predicted. Re-examination of overlay images shows numerous textured protrusions/debris segmented as stand-alone objects. Size filtering does not materially correct this failure. Do not use these mask detections for phenotype advantage claims. Because ALFI masks primarily annotate certain cells/classes, unannotated structures may also contribute false positives. Acknowledging that limitation does not convert false positives into verified cells.

## Next recommended experiment

Apply a stronger **pretrained instance segmenter** (Cellpose-SAM v2, already in project) on exactly the same raw MI frames without using MI test masks to train. Compare heldout instance F1 and count calibration. If still poor, use expert masks as an oracle to isolate tracking/phenotype error from segmentation error. A true *raw image → track → mitosis stage* metric remains not demonstrated.
