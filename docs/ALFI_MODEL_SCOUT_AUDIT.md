# Model-scout decision: cross-domain ALFI instance segmentation race (2026-10-09)

**Scientific decision: retain cpsam_v2 for the current validated image backend; do not claim adequate ALFI raw-image instance detection.**

## Evidence and source independence

Study: ALFI (Antonelli et al.), expert image/mask annotations, CC BY. 4 original image/mask pairs MI05, MI06, MI07, MI08 frame 1. Identical raw source PNG bytes were used in all tested methods, with **8/8 SHA256 matches** across:
- [Supervised-model 4-train/4-heldout artifact](https://github.com/chrishotza/ai4s-life-science-2026/actions/runs/37970569505/artifacts/11635512264)
- [Pretrained model race](https://github.com/chrishotza/ai4s-life-science-2026/actions/runs/37972467985) commit 53f02eb (two jobs, both SUCCESS).
- [CellposeSAM-v2 evidence](https://github.com/chrishotza/ai4s-life-science-2026/actions/runs/37972467985/artifacts/11638026369)
- [CellposeDINO-vitb evidence](https://github.com/chrishotza/ai4s-life-science-2026/actions/runs/37972467985/artifacts/11636897162)

Four deliberately fixed heldout frames (MI05–MI08 T0001); same expert mask foreground and IoU≥0.5 instance match. All methods evaluated at 512×640 from original 1024×1280 source microscopy. Model pretrained weights were used without any ALFI fine-tuning. Results are frame averages, not totals aggregated as a single giant image.

| Model | Mean pixel Dice | Mean per-frame instance F1@IoU50 | GT instances | Predictions | Correct matches |
|---|---:|---:|---:|---:|---:|
| Brightness 92nd percentile | 0.36165 | 0.01557 | 71 | 581 | 4 |
| Repo supervised on MI01-MI04 | 0.41178 | 0.04261 | 71 | 190 | 4 |
| Repo supervised with train-derived object-size filter | 0.41694 | 0.04261 | 71 | 185 | 4 |
| CellposeDINO DINOv3 ViT-B (cpdino-vitb) | **0.43747** | 0.18087 | 71 | 32 | 9 |
| CellposeSAM-v2 (cpsam_v2) | 0.40941 | **0.22821** | 71 | 40 | **12** |

Per-sequence matched instance counts:
- cpsam_v2: MI05=2/7, MI06=6/21, MI07=2/25, MI08=2/18.
- cpdino-vitb: MI05=1/7, MI06=5/21, MI07=1/25, MI08=2/18.

DINO has slightly better semantic pixel Dice, yet inferior per-instance F1 and matches fewer expert objects. Both perform poorly on MI07/MI08. CellposeSAM-v2 is the better choice FOR THIS FOUR-FRAME instance metric, but still only matches 12/71 ground-truth objects; **NO-GO for ALFI end-to-end detection**.

## Model research and licensing

- Searches through specialized scientific indexes Consensus and SciSpace identified the value of instance-aware segmentation and domain-specific annotations for label-free microscopy; source and model searches identified the new DINOv3 backbone alternative.
- Official Cellpose supported models: https://cellpose.readthedocs.io/en/latest/models.html
- Upstream model information and training-data rights: https://github.com/MouseLand/cellpose . Upstream states Cellpose models were trained on CC BY-NC data. **Review rights before commercial redistribution or monetization**; do not assume pretrained model weights are unrestricted.

This result shows that simply replacing the pretrained backbone does not solve ALFI detection. The next test must target cell instance separation using domain-specific training or an independently vetted pretrained detector, with untouched evaluation sequences and visual QC.

## Product and biological boundary

The independent [ALFI oracle tracker](ALFI_ORACLE_TRACKING_EXTERNAL_RESULTS.md) achieves F1 ≈0.9943 with expert detections; that result does not transfer to predicted objects here. The [ALFI expert-box phenotype label benchmark](ALFI_ASSAY_STRATIFIED_REAL_RESULTS.md) shows exploratory mitosis-stage signal in motion features. Neither establishes fully automated video-to-verified-biology performance.

Do not average this four-frame external instance result with the much stronger but different CTC DIC-C2DH-HeLa end-to-end experiment: microscopy domain and annotation protocols differ.
