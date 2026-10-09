# ALFI oracle detection → tracker benchmark (8 expert-labeled real sequences)

2026-10-09. **Result: tracking algorithm passes its isolated external validation gate. This is NOT an end-to-end video phenotype score.**

## Source and provenance

ALFI, Antonelli et al., expert DTLTruth.csv per-cell bounding boxes, identity and parent-child lineage, **CC BY**, DOI https://doi.org/10.6084/m9.figshare.23798451.v1.

- Successful run: https://github.com/chrishotza/ai4s-life-science-2026/actions/runs/37969784070
- Complete raw source labels + measurement artifact: https://github.com/chrishotza/ai4s-life-science-2026/actions/runs/37969784070/artifacts/11635655792
- Implementation: scripts/benchmark_alfi_oracle_tracking.py (repo actual ai4s_tracking.track_detections, no substitute tracker).
- Regression test tests/test_alfi_oracle_tracking.py.
- Commit 373fb1fd9a9a6990f689927807bf15752837d062; associated CI SUCCESS.
- Independent artifact audit: **8/8 original DTLTruth CSV SHA-256 checksums match both manifest and summary**.

## Data hygiene

ALFI MI01–MI08 have 16,627 source expert detection rows. In MI07, two IDs are repeated in the same frame: ID 14.11 and ID 64; these are ambiguous expert trajectories, so **both complete ID tracks are excluded**, accounting for **39 annotation rows**. Remaining **16,588** expert observations.

Gold temporal edges link consecutive frames **for the same expert ID**; gaps and lineage parent→daughter transitions are expressly excluded. Gold contains **16,256** edges.

The input to the actual tracker uses the center of each expert annotated bounding box. Coordinates treated as 1 pixel = 1 internal tracking length unit, with a **fixed** 45-pixel displacement gate and a maximum gap of exactly one frame. No method tuned on these ALFI annotations; three predeclared existing tracker methods are all reported.

## Measured performance

| Actual tracker method | Temporal edge precision | Recall | F1 | TP | FP | FN |
|---|---:|---:|---:|---:|---:|---:|
| mutual_nn | 0.99593 | 0.99268 | **0.99430** | 16,137 | 66 | 119 |
| hungarian | 0.99587 | 0.99280 | **0.99433** | 16,139 | 67 | 117 |
| velocity_hungarian | 0.99596 | 0.98517 | 0.99054 | 16,015 | 65 | 241 |

Hungarian per-sequence F1: MI01 0.9995; MI02 0.9973; MI03 0.9937; MI04 1.0000; MI05 0.9959; MI06 0.9973; MI07 0.9899; MI08 0.9880. No sequence in this particular oracle benchmark below F1=0.988.

**Strong technical positive:** with perfect expert detections the existing linking component gives an externally auditable ~0.994 F1 on 16,256 real human-annotated identity links. The actual engine was called via its public interface, and mistakes/ambiguous annotations are counted.

**Scientific limitation and submission claim boundary:** This is an **oracle detection** benchmark using external expert boxes. It does not validate the ability to find cells from unseen pixels; it does not measure full trajectory ID association under detection errors, cell divisions, prospective mitosis stage prediction, or clinical claims. The full raw-image ALFI segmentation experiment (docs/ALFI_RAW_IMAGE_INSTANCE_AUDIT.md) demonstrated a severe instance bottleneck (mean instance F1 ~0.05) even while improving pixel Dice. Thus a 99.43% tracker result MUST NOT be quoted as full raw-image-to-phenotype success.

## Execution priority

1. Evaluate pretrained Cellpose-SAM on the same ALFI pixels and expert masks (workflow alfi-cellpose-raw.yml).
2. If pretrained segmentation remains poor, evaluate/recalibrate segmentation explicitly; do not conceal underrepresentation or oversegmentation.
3. Only if independently acceptable instance detection and linking are established, reproduce the real-label mitosis phase baseline with **predicted**, rather than expert, tracks and full-video heldout metrics.
