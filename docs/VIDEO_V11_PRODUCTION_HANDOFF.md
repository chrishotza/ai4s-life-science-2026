# AI4S V11 narrated judges demo — production handoff

**Status (October 10, 2026):** An improved **134-second MP4** has been rendered and locally verified for the project owner. It is **not yet verified publicly published** and must **not** replace the official V10 Kaggle link in the submission until a public playable V11 URL is confirmed.

## Measured media integrity

- Container: MP4; H.264 video 1280 × 720 at 24 fps; AAC mono narration at 44.1 kHz.
- Runtime: 134 seconds (within the official competition's maximum five-minute video requirement).
- Final file SHA-256: `f7c98e4dba74e1a779c7aebd336d11562be65a0e0fc81522ef30ba7d6033dda2`.
- Input public V10 video SHA-256: `390a632fde2818b03482ed0b938f827b1fc782e962e55d03e1f97fc702afb711`.
- New ElevenLabs narration SHA-256: `a222b4df124bbf85046ee5da862fe14c5ab6c53c4286de25b84115f12e35f654`.
- The prior video audio was discarded; this V11 cut has its own British-English scientific narration.
- A contact sheet was inspected at nine timestamps. Source-panel cropping was tightened after QA to prevent previous V10 interface fragments from entering V11 scenes.
- Provenance: actual public Kaggle V10 microscopy material derived from a separate **8-frame CellposeSAM-v2 visual pilot**; **no claims that this footage itself depicts the entire 168-frame scored run**.

## Storyboard (visual timestamps)

| Video time | Claim | Scientific boundary |
| --- | --- | --- |
| 00:00–00:14 | Why time-lapse behavior matters | Descriptive scientific motivation |
| 00:14–00:29 | Real microscopy and predicted masks | Source footage is an 8-frame visual pilot |
| 00:29–00:45 | Linking predicted cells across time | Not a reference-centroid oracle performance claim |
| 00:45–01:01 | 168-frame CTC evaluation: segmentation F1 0.9354, detection F1 0.9684, link F1 0.9808 | Results come from distinct completed evaluation, not the short footage |
| 01:01–01:17 | Example: 142.10 µm traveled; 4.29 µm net movement | Descriptive measured track, no drug or phenotype biological label |
| 01:17–01:32 | 126 trajectories: 54 audit-only, 21 low-confidence, 51 descriptive | No independent biological state validation |
| 01:32–01:51 | Separate ALFI supervised mitosis experiment: macro F1 0.5138 vs 0.5676 | Expert geometry supplied; CTC footage is illustrative only |
| 01:51–02:04 | ALFI transfer limitation and lack of organ-on-chip validation | Do not imply cross-domain success |
| 02:04–02:14 | Open-source research contribution | Explicit limited scientific interpretation |

## Official handoff before cutoff

1. Upload the verified V11 MP4 to a **publicly viewable** media URL (Kaggle dataset attachment or public video host); confirm playback without login. Verify licensing/rights for the original microscope images, pretrained masks and model outputs before redistribution.
2. Update the **actual Kaggle Writeup**, not just the GitHub source, with the new public V11 URL, if edits are permitted. Confirm the platform's **Submitted** state. GitHub commits do not automatically modify Kaggle's submitted text.
3. Keep the currently public [V10 demo](https://www.kaggle.com/datasets/chrishotza/ai4s-2026-temporal-cellular-phenotype-demo) as the official linked fallback until V11 is publicly hosted and independently checked.
4. Judge-facing scientific evidence and exact source claims remain in [the updated Kaggle Writeup source](KAGGLE_WRITEUP.md), [ALFI experiment](ALFI_PRODUCT_TEMPORAL_PROBE_RESULTS.md), and [CTC Cellpose audit](CTC_CELLPOSE_ARTIFACT_AUDIT.md).

## Notes

The V11 presenter does **not** introduce invented cell imagery or claim a novel segmentation foundation model. It presents actual CTC CellposeSAM-v2 prediction footage from the earlier Kaggle video alongside separate validated result cards. Public availability and submission state remain independent requirements.
