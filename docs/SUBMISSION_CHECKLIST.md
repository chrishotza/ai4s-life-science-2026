# Final AI4S Submission Checklist

## Official competition requirements

- [ ] Declare category at the very beginning of the Kaggle Writeup: **End-to-End System**.
- [ ] Include a public demo video (maximum 5 minutes; no login or permission gate).
- [ ] Include the publicly accessible repository URL.
- [ ] Include a concise, self-contained technical report in the Writeup or a public PDF link.
- [ ] Complete the separate mandatory competition registration form.
- [ ] Submit the Kaggle Writeup before the preliminary-round deadline.
- [ ] Verify that every linked asset, dataset, image, model output, and audio track has suitable usage/redistribution rights.

## Evidence already documented in this repository

- [x] Public end-to-end pipeline entry point and reproducible setup instructions.
- [x] Deterministic synthetic benchmark and regression tests.
- [x] Quantitative real-data CTC association benchmark.
- [x] Method/gating ablation.
- [x] Downstream temporal phenotype-preservation benchmark.
- [x] End-to-end tracking-to-phenotype robustness benchmark on controlled synthetic data.
- [x] Explicit architecture/data-contract layer.
- [x] CTC lineage/division representation validation.
- [x] CTC-maintained TRA/LNK external validation on sequences 01 and 02.
- [x] Captured evaluation evidence artifact and documented no-oracle lineage sensitivity control.
- [x] Technical report draft, Kaggle Writeup draft, summary, and five-minute demo script.
- [x] CI and Docker reproduction path.
- [x] Representative real-data visualization and deterministic demo-video renderer.
- [x] Explicit limitations and claim/evidence separation.

## Submission blockers / last-mile actions

- [ ] Make the competition repository public, then verify access in a signed-out/private-browser session.
- [ ] Re-run CI on the final public commit.
- [ ] Re-run the documented benchmark scripts (or attach captured logs/artifacts) and verify published numbers.
- [ ] Render and watch the final narration/video end-to-end; confirm duration <= 5:00 and public playback works.
- [ ] Add the final public video URL and public repository URL to the Kaggle Writeup.
- [ ] Paste the final summary and technical report into the Kaggle Writeup.
- [ ] Complete the mandatory registration form.
- [ ] Perform final rights, dataset provenance, links, and claim-consistency review.
- [ ] Submit the Kaggle Writeup and verify it is visible under the competition's Writeups tab.

## Evidence and claim policy

The current CTC association benchmark uses **reference track centroids as detections**. Its custom edge precision/recall/F1 therefore measures temporal association, not image segmentation and not end-to-end biological phenotype classification.

Keep three evidence levels distinct:
1. **Measured real-data association:** custom edge metrics and separately reported CTC-maintained TRA/LNK association-isolation results.
2. **Controlled synthetic validation:** regression, missing-observation robustness, and phenotype-clustering stability tests.
3. **Scientific hypothesis / future work:** biological phenotype validity and perturbation response, which require independent biological labels or experimental annotations.

The recorded TRA/LNK values preserve reference object geometry and are not official Cell Tracking Challenge leaderboard scores. Do not present them as such.

## Current verified state

The GitHub repository is currently **private** (verified through the connected GitHub repository metadata). It is not submission-ready until public access is enabled and verified. The GitHub integration can edit repository content, but making a private repository public is an external repository-visibility action not performed by this checklist update.
