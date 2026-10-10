# V15 real-cell identity-color demonstration — scientific visualization policy

**Status:** source implementation and tests committed; [true 24-frame color rendering workflow](https://github.com/chrishotza/ai4s-life-science-2026/actions/workflows/ctc-stable-color-24.yml). A workflow execution, even when successful, is **not** a publicly published video or independent biology validation. The [existing CTC redistribution restrictions](FINAL_SUBMISSION_HANDOFF.md) still apply to public hosting.

## What is displayed

- Real **DIC-C2DH-HeLa sequence 02, frames 34–57**, i.e. **24 consecutive microscope images**. This region was selected because CTC reference metadata indicate a division nearby. This selection is **event-enriched**, not a blinded/unbiased sample.
- Raw grayscale panel displays the original microscopy, normalized for visualization. Right panel shows the *same actual frames*, predicted CellposeSAM-v2 cell masks, and the deterministic mutual-nearest-neighbor tracker.
- The bright mask **color is keyed to `track_id`**, not to the frame-local `instance_id`. Frame-to-frame re-numbering of instance masks therefore **cannot arbitrarily recolor an unchanged predicted track**. This is the scientific reason for stable color.
- Each hue represents **model-estimated temporal identity**, **not fluorescence, genetically marked cells or verified biological ID**. The map is deterministic **within a tracking run**, but not an immutable ID across re-training or changes to the tracking algorithm.
- Trajectory trails are calculated from observed centroids. No inferred/future coordinates are drawn. Playback may repeat original frames to achieve normal video framerate, but does not generate synthetic microscope frames or infer intermediate cell positions.

## Division coloring — intentionally conservative

The optional family-hue display uses only the model's `division_parent` candidate edges. A mother-track color may branch into two **related but visually distinct** daughter tones only when:

1. The source track's last detection is in frame `t`;
2. Exactly two distinct child tracks begin in `t+1`;
3. Both have candidate lineage edges from the same source node and no competing candidate parent;
4. Duplicated source node IDs, track/time collisions, and missing detections are treated as errors.

If these conditions fail, all daughter track IDs keep unrelated, independently chosen colors. These **are not true-positive mitosis labels**. CTC lineage ground truth is never substituted into a predicted overlay. The current tracker has **no independently established precision/recall for end-to-end image-derived cell division**.

## Validation and reproducibility

- Renderer: [stable identity and candidate lineage algorithm](../src/ai4s_imaging/track_colors.py)
- Actual model-to-render integration: [predicted 24-frame Cellpose exporter](../scripts/export_cellpose_visual_pilot.py)
- [Six identity/lineage safety tests](../tests/test_track_colors.py), including color continuity when instance IDs change and rejection of continuing/ambiguous parents
- [One-click true-image rendering workflow](../.github/workflows/ctc-stable-color-24.yml); outputs individual PNG frames, manifest JSON, and a silent MP4.
- [Narrated V15 compositor](../scripts/compose_ctc_color_v15.py) rejects clips without matching evidence metadata and preserves the pre-existing V13 scientific narration.
- [Prior 24-frame segmentation QA](CTC_FOCUSED_DIVISION_WINDOW_QA.md): mean frame F1 0.955906, 17 predicted tracks, 272 predicted links. These values are from the earlier unfixed-hue visualization run; confirm independently whether the color-only recomputation reproduces them. They do **not** validate a mother-to-daughter split.

**Publication gate:** A generated/sandbox MP4 must not be presented as the public Kaggle submission until its playback, sourcing rights, and actual Kaggle Writeup link are independently verified. Its contribution is **visual clarity of a validated computational tracking workflow**, not a newly improved model F1 or a confirmed biological discovery.
