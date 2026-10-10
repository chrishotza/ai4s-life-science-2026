# AI4S V13 — actual-data scientific video revision

**State:** Local final MP4 generated and quality checked 2026-10-10; **not yet published to Kaggle or verified as the official linked competition video.** Do not confuse this handoff with a Kaggle submission receipt.

## Why this revision exists

V11/V12 already contained genuine CellposeSAM-v2 CTC microscopy footage and valid internal metrics, but their 77–92-second sequence discussed 126 trajectory profiles using a static graphical card. V13 replaces **360 rendered frames (15 seconds)** with a **real-data, time-varying scatterplot** assembled from the original 168-frame CellposeSAM-v2 output: sequence 01+02 trajectory CSVs in [the provenance-verified original Actions artifact](https://github.com/chrishotza/ai4s-life-science-2026/actions/runs/37930909373).

The visual places all **126 actual** track profiles in measured feature space (x: mean speed in µm/frame; y: directional persistence, dimensionless), then reveals the existing conservative confidence/observation evidence tiers:

- **54 audit-only**, insufficient temporal evidence (<3 observations).
- **21 descriptive-low-confidence**, >=3 observations but reliability <0.5.
- **51 descriptive-only**, >=3 observations and reliability >=0.5.

This is **not** an animation of measured cell paths and is not synthetic microscopy: the marks are actual previously computed track-level numerical feature points. The video leaves unchanged its real microscopic footage, 168-frame evaluation claims, labeled ALFI expert-track experiment, and existing English voiceover. The source image pilot remains just an **8-frame visual pilot**, separate from the full 168-frame quantitative results.

## Binary QA

- File: `AI4S_Final_Judges_Demo_V13_Scientific.mp4` (distributed as an external deliverable to the project owner; not checked into GitHub).
- **SHA256:** `c72b537503827e7c35d99939a838218c1227da2296d24650ea35239ced37a4c4`.
- **Duration:** 134.000 seconds, verified with ffprobe.
- **Streams:** H.264 video 1280 × 720, 24 fps; AAC narration. No video/audio duration mismatch identified.
- **Visual audit:** sampled opening, microscopy, internal F1 evidence, real motility case, four times across the new quality-gate panel, ALFI expert labels, limitations, and closing. Revised overcrowded axis label before final render.
- Original audio is **preserved**, not replaced with another experimental voice or soundtrack. The purpose here is enhanced quantitative evidence, not music.

## New source code and research validation

- [Opt-in motion-only discovery implementation](../src/ai4s_phenotype/discovery.py), with ≥3-observation fit gate; default nine-feature model unchanged.
- [Real 80-bootstrap comparison and no-go promotion decision](CTC_MOTILITY_FEATURE_ABLATION.md), including reasons not to claim motility-only uniformly superior.
- [Reproducible benchmark and frozen output artifact](https://github.com/chrishotza/ai4s-life-science-2026/actions/runs/38022564912).
- [Production-gate audit](evidence/ctc/confidence_gated_phenotype_summary.json).

## Public release barrier

The project owner must ensure a public no-login V13 video URL is published and linked in the **actual Kaggle Writeup** (if editing is permitted); the existing linked public V10 remains fallback until that is independently confirmed. Updating files in this repository is not equivalent to updating the already submitted Kaggle Writeup. Third-party CTC data, segmentation-model output, any soundtrack and redistribution permissions should be reviewed before release.

The revision makes the video more accurate and inspectable; it does not create new biological labels, improve the pretrained instance-segmentation F1, or change external competition ranking.
