# V19 — real whole-population, stable predicted-ID movie (2026-10-10)

**Status:** whole-field Cellpose native artifact verified; **134-second V19 local narrated file finished**. **Not a published Kaggle replacement.** Public distribution rights for CTC images remain unverified.

## Scientific media sources

- Original CTC DIC-C2DH-HeLa **sequence 02, original microscope frames 34–57 inclusive**: 24 consecutive real frames, selected using event-enriched annotations.
- [Completed whole-population original-model run `38028667812`](https://github.com/chrishotza/ai4s-life-science-2026/actions/runs/38028667812), artifact [`11661508906`](https://github.com/chrishotza/ai4s-life-science-2026/actions/runs/38028667812/artifacts/11661508906). Its ZIP contains the original integer `model_predicted_instances.npz`, `model_predicted_track_nodes.csv`, `model_predicted_temporal_edges.csv`, 24 full-frame PNGs, validation metrics and the unvoiced full-field movie.
- 17 predicted track IDs across the 24-frame clip, 289 model-predicted observations, 272 predicted temporal links. Image-segmentation mean frame F1@IoU50 on this selected window: **0.9559062589** (not a new global benchmark).
- The overlay colors 9–12 distinct model-predicted tracks in each actual frame, **up to 14 distinct IDs across the window**, with stable color keyed to `track_id` rather than per-frame mask label. These numbers are counts of rendered *predictions*, not verified cell identities.
- *Per raw frame from 34 to 57 inclusive:* number of highlighted tracks `[10,11,11,11,11,11,11,11,11,11,11,11,12,12,12,11,11,9,10,10,10,10,9,9]`. Ambiguous associations stop receiving color at their first failed overlap/gap/area gate and remain visible as grayscale cell morphology.
- Six tracks (IDs **0,1,6,7,8,9**) have high-continuity prediction masks in **all 24 actual frames**. This is a visualization continuity surrogate, not independent ground-truth tracking or mother/daughter validation.

## Final film verification

| Property | Verified |
|---|---|
| Composition | Replaced seconds **14.0–30.5** of V18's narrated scientific presentation with the original native whole-field rendering |
| Resolution | 1280×720, H.264, 24 fps |
| Narration | Original AAC bitstream copied without change from V18; `SHA256=b80873189860a4d49481f85f6d02a814716951aa2abe2827e7a26ddef76d7f36` for the audio stream |
| Runtime | 134.000 s |
| Complete decode | Successful `ffmpeg -v error -i ... -f null -` |
| MP4 SHA256 | `99d1ad3111642b99dbe574f53e44263f538d21f1238070ec59ad1c6bdc77eb45` |
| Source | Original native 24 chronological photos, each held/repeated for video playback. **No generative frame synthesis**, no attempted re-identification from encoded RGB |
| Source model and identity | CellposeSAM-v2 predicted masks + temporal tracker; source `model_predicted_track_nodes.csv` and per-frame `instance_id` allow exact mask-to-ID auditing |
| Visibility policy | All cells visible in both raw and color-overlay fields, uncertain associations remain uncolored |
| Publishing | **LOCAL ONLY** pending CTC rights permission and authenticated Kaggle submission verification |

Reproduce with [`scripts/compose_ctc_population_narrated.py`](../scripts/compose_ctc_population_narrated.py):

```bash
python scripts/compose_ctc_population_narrated.py \
  --source V18_narrated.mp4 \
  --clip extracted_artifact/ctc-population-real-tracks.mp4 \
  --artifact-dir extracted_artifact \
  --output V19_real_population.mp4
```

The script rejects non-native preview clips and incomplete frame/track evidence, keeps the original audio bitstream and verifies full H.264/AAC decode.

## Boundaries and final review gate

The 24-frame selected visualization is **not** the 168-frame full CTC benchmark, an independently held-out test, whole-trajectory ground-truth ID F1, a validated mitotic-lineage result, or a Kaggle result. It is a technically reliable explanation of how the real model generates temporally continuous cell-identity predictions. For complete identity-switch/fragmentation diagnostics, the **separate 168-frame Cellpose benchmark** must finish and its matching-mode limitations must be disclosed; see [two-reviewer triage](EXTERNAL_AI_REVIEW_TRIAGE_2026-10-10.md).

**Do not upload or promote V19 to a publicly redistributed artifact without independently confirmed permission for CTC images and the applicable pretrained-model constraints.** See [final Kaggle handoff](FINAL_SUBMISSION_HANDOFF.md). The existing public Kaggle dataset video is V10 (91s), not V19.
