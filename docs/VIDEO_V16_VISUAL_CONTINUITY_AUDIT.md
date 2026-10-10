# V16: scientifically conservative visual-continuity correction

**Status 2026-10-10:** V16 corrected local MP4s and a 24-image QA record exist as conversation deliverables, **not as a published Kaggle replacement**. Source code now adds an explicit visual-identity ambiguity gate; its new full Cellpose inference workflow must complete before calling its new produced artifact independently validated.

## The specific error in the earlier V15 preview

The V15 `VisualRecovery` preview attempted to reconstruct **track associations from a finished raster video** using proximity. This can switch apparent cell identities when masks approach, merge, disappear, or divide. The colors appeared consistent but some tracked subjects were not. **Do not show that recovery preview as evidence of original tracker identity continuity.**

The actual CellposeSAM-v2 render produced by [Actions run 38025428120](https://github.com/chrishotza/ai4s-life-science-2026/actions/runs/38025428120) **finished successfully**; it provides 24 real chronological frame PNGs, the originally model-predicted `track_id` palette, and a bounded F1 JSON. [Source artifact](https://github.com/chrishotza/ai4s-life-science-2026/actions/runs/38025428120/artifacts/11661040522).

- Original raw microscopy sequence 02, frame numbers **34–57 inclusive**, 24 images.
- Original run: 17 model-predicted tracks, 272 temporal associations, mean frame segmentation F1@IoU50 **0.9559062589**.
- The run recorded **no unambiguous predicted mother→two-daughter color-family candidates**. Do not imply that a green cell genuinely divided.
- This selected window is event-enriched by reference annotation and is not independent evaluation.

## Actual continuity QA (V16)

The V16 editor compares the **original paired raw/colored PNG panels pixel-wise** to recover high-confidence already-rendered `track_id` regions. It does **not** rerun association; it assigns no new ID and does not interpolate missing cell pixels. Each of its 24 recovered per-frame track counts equals the source run's expected predicted instance count (24/24 checks). Four full-window model-native IDs survived a stringent descriptive visual screen:

| Predicted track | Coverage | Minimum consecutive-mask IoU | Minimum self-vs-other consecutive IoU margin | Maximum frame-to-frame area ratio |
|---|---:|---:|---:|---:|
| 06 | 24/24 | 0.677 | 0.586 | 1.191 |
| 07 | 24/24 | **0.719** | **0.597** | 1.275 |
| 08 | 24/24 | 0.727 | 0.712 | 1.179 |
| 09 | 24/24 | 0.664 | 0.589 | 1.416 |

**These overlap scores are approximate, computed from losslessly saved model-native RGB-rendered masks, not original per-instance TIFF/NPY labels.** They support the limited *visual continuity* decision, not biological-ID precision or recall. The full `24/24` numerator establishes appearance in every visible time point but does not prove laboratory-validated cell identity. The strongest single-track presentation uses **track 07 only**, and keeps the field of view **fixed** (no tracking camera motion, no subject replacement). Other cells are still visible in uncolored raw microscopy to prevent spurious cross-cell hue impressions.

The 16-second single-track standalone MP4 and 134-second fully narrated demo **were generated and decoded successfully**. All 24 raw-source panel interiors matched their original microscopy crops pixel-for-pixel before H.264 compression; QA samples include the opening, boundary transitions and closing. This local V16 is deliberately a **preview until a full native exact-mask evidence run**.

## Code-level permanent prevention

- [`identity_confidence.py`](../src/ai4s_imaging/identity_confidence.py): independently scores *true predicted instance masks* and tracked `instance_id → track_id` per frame, including gaps, abrupt area jumps, self-to-self IoU versus competing-track overlap, and ambiguous ownership. **Fails closed** rather than visualizing an uncertain identity as proven.
- [Regression tests](../tests/test_identity_confidence.py): stable movement, swapped identities, missing temporal observation, sudden cell merger, inconsistent instance coverage and duplicate instance ownership.
- [Actual exporter](../scripts/export_cellpose_visual_pilot.py) uses these masks directly, colors eligible IDs only, and records all filtered identities/reasons in its metrics JSON.
- [Rendering workflow](../.github/workflows/ctc-stable-color-24.yml) requests strict rendering for IDs 6,7,8,9, validates exported eligibility, and publishes a new source artifact only when that genuine image-inference run completes.

There is a **non-negotiable rights gate** for redistributing CTC microscopy on a third-party public Kaggle page; see [release handoff](FINAL_SUBMISSION_HANDOFF.md). No repo commit equals editing an already-submitted Kaggle Writeup.

## Why this still is not biological validation

Temporal IoU and stable model IDs are a useful **visual QA surrogate**, not annotated track identity truth. Physical mixing and close contacts can cause even a plausible mask-history sequence to switch biological identity. A future true-ID evaluation must compare whole trajectories with independent CTC ground truth and report ID switches, target visibility, gaps and division reconstruction. Until then the video must say **model-predicted track**, not independently confirmed same living cell.
