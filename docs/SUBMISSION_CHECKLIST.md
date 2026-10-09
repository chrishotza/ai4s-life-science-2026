# Final AI4S Submission Checklist

## Evidence

- [x] Reproducible end-to-end pipeline (prepared for public release)
- [x] Deterministic synthetic benchmark
- [x] Quantitative tracking metrics
- [x] Real CTC association benchmark
- [x] Method/gating ablation
- [x] Downstream phenotype preservation benchmark
- [x] Cross-sequence image-to-tracking validation protocol
- [x] CTC GT/SEG image-segmentation validation protocol
- [x] End-to-end tracking-to-phenotype robustness benchmark
- [x] Explicit architecture/data-contract layer
- [x] CTC lineage/division representation validation
- [x] CTC-maintained TRA/LNK external validation on sequences 01 and 02
- [x] Reproducible CTC TRA/LNK evidence artifact captured
- [x] No-oracle lineage sensitivity control completed with unchanged TRA/LNK
- [x] Submission claim audit synchronized with CTC TRA/LNK values
- [x] Project Summary word-count audit enforced in `scripts/validate_submission_claims.py`
- [x] Technical report draft
- [x] Kaggle Writeup draft
- [x] Category declaration at start of Writeup
- [x] 200–300 word Project Summary in Writeup
- [x] Dataset/software provenance and licensing documented
- [x] Development AI-tool provenance disclosed
- [x] Five-minute demo script
- [x] CI tests
- [x] Docker reproduction path
- [x] Judge-facing rubric evidence map
- [x] Judge reader guide
- [x] Top-level MIT code license

## Official competition submission constraints

Verified against the [official Kaggle competition overview](https://www.kaggle.com/competitions/ai-4-s-open-innovation-artificial-intelligence-for-life-scien/overview) on October 9, 2026. The required submission is a Kaggle Writeup with a category declaration, public demo video, public code repository, and technical report. The required registration form must also be completed before submission. The preliminary-round window ends **October 10, 2026**.

Official detail reflected in this checklist:
- The demo video must be no longer than 5 minutes and publicly viewable without login, permission approval, or payment; all media/data/model-output rights must be clear.
- The technical report must be self-contained in the Writeup or linked as a public PDF; the organizers recommend 15–20 pages excluding references and appendices.
- Teams must have 1–5 members and one leader. The draft report currently lists Chris Hotza as the sole member; synchronize it with the Kaggle registration.
- The organizers offer a +0.5 bonus in Interpretability and Reliability for a team covering both AI/CS and biology, bioengineering, or clinical expertise. The current draft does not evidence that mix, so the bonus is not claimed.

## Before submission

- [ ] Complete the required competition registration form
- [x] Make competition repository public
- [x] Verify final public repository URL (public GitHub repository confirmed)
- [ ] Confirm the registered team has 1–5 members, one leader, and a roster matching the technical report
- [ ] Synchronize technical-report team roster with the official Kaggle registration
- [ ] Check whether the registered roster qualifies for the +0.5 cross-disciplinary bonus; do not claim it unless both expertise areas are represented
- [x] CI has passed on recent submission-document PRs; rerun on the final merge commit before official Kaggle submission
- [ ] Reproduce the remaining published benchmark suite on the final submission commit; the PhC-C2DL-PSC supervised segmentation holdout and bounded Cellpose image-to-phenotype integration have been re-run on current source snapshots (runs 37924623262 and 37925893949)
- [x] Re-run the bounded Cellpose product path through per-track phenotype outputs; captured CSVs, JSON, and provenance (run 37925893949; artifact 11613698759)
- [x] Capture bounded pretrained Cellpose pilot metrics (4 frames per sequence; exploratory)
- [x] Add a public real-data validation figure reviewers can access without login (`docs/figures/validation-evidence.svg`); it separates three protocols and states their evidence limits
- [x] Produce reproducible demo video renderer
- [ ] Paste Kaggle Writeup
- [ ] Submit final technical report
- [ ] Add independent biological phenotype validation if time permits
- [ ] Produce final demo video (max 5 minutes), publish it without login/approval/payment, and verify media usage rights
- [x] Final consistency check: no claim exceeds measured evidence

## Current verified state

- `main` contains the merged external CTC validation bridge, confidence-gated phenotype interpretation, claim-evidence matrix, and compact 200–300 word Kaggle Project Summary.
- `docs/JUDGE_READER_GUIDE.md` is the judge-facing entry point for the biological question, protocol map, CellposeSAM-v2 boundary, phenotype-claim policy, and remaining submission blockers.
- Captured `py-ctcmetrics==1.3.3` results are documented for sequences 01 and 02.
- Official Cell Tracking Challenge leaderboard scores remain explicitly unclaimed.
- Repository visibility and root URL were verified on the final public `main` branch; repeat only if ownership or visibility changes.

## Claims policy

The final submission should distinguish three evidence levels:

1. **Measured real benchmark:** CTC association and trajectory-feature preservation.
2. **Controlled synthetic validation:** deterministic regression tests.
3. **Scientific hypothesis / future work:** biological phenotype interpretation not yet independently labeled.

No benchmark score should be presented as an end-to-end image-to-biological-phenotype score unless that experiment has actually been run.
