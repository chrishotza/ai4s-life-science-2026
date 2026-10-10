# V17 whole-population time-lapse: delivery status and scientific gates

**2026-10-10 · Scope:** This revision corrects a judge-facing visual communication weakness: previous demos highlighted only one or four cells. The V17 editor uses the *entire fixed microscope field* and retains every observed model-predicted cell, coloring several independent, quality-screened tracks at once.

## Verified existing local deliverables (not a confirmed public release)

- **Full narrated MP4 preview:** `AI4S_V17_Full_Population_Narrated_Preview.mp4`, SHA-256 `2bd8947ff922f1b05b2b5fb6928a0f68851cbfccc00403dfa47bce9c0c587799`, 134.000 seconds, H.264 1280×720/24fps + AAC. Whole-file decode passed. Its decoded audio SHA-256 (`6a17873c9642ce63be64f2821cdc021b562c4118390a26ff874c856c779ee4b5`) is **identical to the V13 original**; do not claim new narration was generated.
- **Standalone 24-frame scene:** `AI4S_V17_All_Cells_Continuous_Visual_QA.mp4`, SHA-256 `00ac1c3fbde911736da31f477547fec4c5ffd0010e2c7dc12cad5d60807b732d`, 16 seconds, frames 34–57 inclusive.
- **Ten-frame QA sheet:** `AI4S_V17_WholeField_Contact_QA.png`, SHA-256 `af5ab115d87b4cbf1307cb28ceea67b038d9d310634d0f608b3cde52d92b8173`.
- Full-scene QC audit is exported separately as `AI4S_V17_Population_Continuity_QA.json` and records frame-by-frame highlighted vs neutral model IDs, plus original grayscale panel byte hashes.

These are **conversation-local deliverables**; they are neither repository-hosted release assets nor confirmed Kaggle Writeup video links. The **CTC publication/redistribution permission gate** in [submission handoff](FINAL_SUBMISSION_HANDOFF.md) remains in force.

## Model evidence and the visual-identity boundary

The actual microscopy is CTC DIC-C2DH-HeLa seq02, frames 34–57; source [successful native model/render run 38025428120](https://github.com/chrishotza/ai4s-life-science-2026/actions/runs/38025428120), [predicted frames and metrics artifact 11661040522](https://github.com/chrishotza/ai4s-life-science-2026/actions/runs/38025428120/artifacts/11661040522). Earlier QA measured 17 predicted tracks, 272 predicted temporal links and selected-window segmentation F1@IoU50 = 0.955906.

- From the complete native PNG panels, V17 recovered **model-colored identity mask approximations** through deterministic alpha-blend inversion, checking the 24 per-frame predicted-object counts. These are **not lossless original integer instance-mask arrays**; small border differences may exist. No new association, tracking model inference, false lineage labels, or synthetic microscope images were introduced in this local composition.
- Across the sequence, 10–14 predicted cells appear in each original frame. V17 visibly colors **8–11 simultaneously**; uncertain predicted masks are still shown in grayscale.
- **Thirteen distinct model track IDs** have an initial visually coherent segment of >=3 frames. A monotonic gate allows color through that first safe segment only: consecutive-mask approximate IoU >=0.50, own-vs-competitor IoU margin >=0.25, and area-size ratio <=1.90. At a gap/merge/suspicious reassignment, the color *ends and never silently restarts* for that ID. This protects the story from artificial identity continuity.
- The color means **model-predicted track identity**, not biochemical fluorescence or a gold biological identity. No confirmed mother-to-daughter split is claimed.

**Critical split:** the 168-frame published numeric evaluation ran on **84 frames × 2 sequences**. The new video visibly shows **24 consecutive frames from only one sequence**. The 24 must not be represented as the full 168-frame movie or added as independent experimental samples.

## Permanent repository improvement: native, not re-extracted masks

The local V17 scene is a checked preview. For truly auditable reproducibility, the repository now implements [`audit_track_color_prefixes`](../src/ai4s_imaging/identity_confidence.py) on **the exact original integer predicted masks and `track_id` ownership table**, not recovered RGB images. The [actual Cellpose exporter](../scripts/export_cellpose_visual_pilot.py) can run in `AI4S_VISUAL_POPULATION_MODE=1`; it exports raw integer predicted-instance NPZ, predicted-track CSV, temporal edges CSV and an explicit per-frame visibility/continuity audit. The [real-image GitHub Actions workflow](../.github/workflows/ctc-population-identity.yml) can run either a 24-frame demonstration or the complete 84-frame sequence.

**Release gate:** compare exact-mask native output against this V17 preview, inspect visually for identity swaps, confirm all QC checks and rights, and only then promote the published demo. Passing internal tests or creating this Markdown documentation alone cannot certify a valid Kaggle submission, biological identity correctness, or winning competition performance.

## V18 update — exact native predicted-track colors, October 10

**A better reproduction is now complete:** [real 24-frame color workflow, success](https://github.com/chrishotza/ai4s-life-science-2026/actions/runs/38028667814), [source artifact `11661553068`](https://github.com/chrishotza/ai4s-life-science-2026/actions/runs/38028667814/artifacts/11661553068). The artifact contains **all 24 frame-level model-native PNG renders** and a metadata JSON, and records model-predicted track IDs, not colors reconstructed from earlier encoded video.

- Sequence 02 / **actual frames 34–57 inclusive**, 24 chronological microscopy frames; CellposeSAM-v2 segmentation + model-predicted `track_id` visualization.
- **Four simultaneously highlighted tracks: 6, 7, 8 and 9.** Every other detected instance remains in the raw/grayscale field to avoid inventing a stable identity where the conservative filter does not support it.
- All four had **24/24 visual detections**. Their *minimum native predicted-mask IoUs* to the following actual frame: track 6 **0.6919**, 7 **0.7318**, 8 **0.7390**, 9 **0.6798**. The corresponding minimum own-versus-best-other overlap margins: **0.6025**, **0.6029**, **0.7213**, **0.5999**. These are visualization-QA checks on model predictions, **not independent ground-truth ID-switch or cell-division accuracy**.
- Manifest reports **zero proposed family-hue division candidates**. No mother-to-daughter identity evidence is claimed.
- A **134.000-second local narrated V18 film** was assembled by replacing seconds 14.0–30.5 of the earlier V13 with this directly predicted native 24-frame scene (video source length 16 sec, slowed modestly without synthesizing microscope images). The original V13 narration was copied rather than regenerated; full H.264/AAC decode passed and a 12-timepoint contact sheet was visually inspected.
- **Local-only film SHA-256:** `004df3d03161b7707ec6db880a13976323cb80307727e185ce4ad5254a19d35a`. Native standalone 24-frame film SHA-256 `eae641e384f98662c78a84f9c5d5863b0156b957ff0447ef9fdf32b35e130483`. These hashes document the local video bytes; **the final V18 movie is not a GitHub Release or Kaggle attachment**.
- **Publication BLOCKED pending verification** of CTC image rights and access to the actual authenticated Kaggle Writeup; neither successful CI nor completion of the MP4 grants upstream distribution permission.

**Why V18 is scientifically preferable to V17:** V17's exploratory local renderer inverted RGB overlays to recover approximate track masks; the V18 replacement uses a successful exact native Cellpose mask/track rendering run and presents fewer simultaneous highlighted IDs rather than assigning unsupported identities to every detected cell. This trades visual density for honest continuity. **Whole-population, full-84-frame native tracking remains a distinct pending workflow**; do not conflate it with the present 24-frame clip.

