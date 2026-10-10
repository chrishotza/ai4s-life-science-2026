# Focused 24-frame CellposeSAM-v2 quality check near an annotated division

**This is complementary visual/segmentation QA, not an additional independent benchmark or a validated automatic mitosis detector.**

The previous lineage scout used **CTC reference annotations only to select an interesting window** in DIC-C2DH-HeLa sequence 02, frames **34–57** (24 consecutive images), centered on a reference-annotated division around frame **46**. The actual images and colored segmentation overlays were generated with **pretrained CellposeSAM-v2 model predictions**; CTC ground-truth masks were used only for scoring and never shown in place of predictions.

| Measured property | Result |
|---|---:|
| Consecutive frames | **24** (34–57) |
| Mean frame-level instance segmentation F1 at IoU 0.50 | **0.955906** |
| Minimum frame F1 (frame 51) | **0.800000** |
| Model-derived tracks exported | **17** |
| Model-derived temporal links exported | **272** |
| Segmentation F1 at frames 45 and 46 | **0.952381**, **0.956522** |

**Original provenance:** [successful Actions run 37999545353](https://github.com/chrishotza/ai4s-life-science-2026/actions/runs/37999545353) and its [predicted-mask images, short MP4, and metrics artifact](https://github.com/chrishotza/ai4s-life-science-2026/actions/runs/37999545353/artifacts/11649936578). We preserve the [24 per-frame measurements as JSON](evidence/ctc/segmentation_division_neighborhood_24_frames.json) and unit-test their count, arithmetic average, provenance, and non-claim boundary. The JSON records the SHA-256 of the archived `visual_pilot_metrics.json`.

**Interpretation:** This selected window demonstrates that the pretrained image segmentation model continues producing masks and temporal-link outputs through a visually interesting region, including difficult frames. It **does not** establish that the tracker correctly detected the mother-to-daughter split, nor measure mitosis-event precision, biological phenotype states or independent out-of-domain performance. No biological annotation was fed into the predicted tracks.

The **168-frame, two-sequence image-derived evaluation** remains the primary quantified experiment. These **24 targeted frames are drawn from the same original dataset and must never be added to the 168-frame count as independent test data**. The event-centered selection can favor interesting/easier/harder regions and does not support population inference.
