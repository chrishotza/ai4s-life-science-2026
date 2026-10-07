# Final AI4S Submission Checklist

## Evidence

- [x] Reproducible end-to-end pipeline (prepared for public release)
- [x] Deterministic synthetic benchmark
- [x] Quantitative tracking metrics
- [x] Real CTC association benchmark
- [x] Method/gating ablation
- [x] Downstream phenotype preservation benchmark
- [x] End-to-end tracking-to-phenotype robustness benchmark
- [x] Explicit architecture/data-contract layer
- [x] CTC lineage/division representation validation
- [x] CTC-maintained TRA/LNK external validation on sequences 01 and 02
- [x] Reproducible CTC TRA/LNK evidence artifact captured
- [x] No-oracle lineage sensitivity control completed with unchanged TRA/LNK
- [x] Submission claim audit synchronized with CTC TRA/LNK values
- [x] Technical report draft
- [x] Kaggle Writeup draft
- [x] Category declaration at start of Writeup
- [x] 200–300 word Project Summary in Writeup
- [x] Dataset/software provenance and licensing documented
- [x] Five-minute demo script
- [x] CI tests
- [x] Docker reproduction path

## Official competition submission constraints

Verified against the current Kaggle competition overview: the official submission is a Kaggle Writeup containing a public demo video, a publicly accessible code repository, and a technical report. Teams must also complete the required registration form before submission. The current preliminary-round window ends **October 10, 2026**. See: https://www.kaggle.com/competitions/ai-4-s-open-innovation-artificial-intelligence-for-life-scien/overview

## Before submission

- [ ] Complete the required competition registration form
- [ ] Make competition repository public
- [ ] Verify final public repository URL
- [ ] Synchronize technical-report team roster with the official Kaggle registration
- [ ] Re-run CI on the final public commit
- [ ] Confirm all benchmark scripts reproduce their published numbers
- [x] Add representative real-data visualization artifact
- [x] Produce reproducible demo video renderer
- [ ] Paste Kaggle Writeup
- [ ] Submit final technical report
- [ ] Add independent biological phenotype validation if time permits
- [ ] Produce final narrated demo video (max 5 minutes)
- [x] Final consistency check: no claim exceeds measured evidence

## Current verified state

- `main` contains the merged external CTC validation bridge.
- Captured `py-ctcmetrics==1.3.3` results are documented for sequences 01 and 02.
- Official Cell Tracking Challenge leaderboard scores remain explicitly unclaimed.
- Final repository visibility and URL must be verified immediately before submission.

## Claims policy

The final submission should distinguish three evidence levels:

1. **Measured real benchmark:** CTC association and trajectory-feature preservation.
2. **Controlled synthetic validation:** deterministic regression tests.
3. **Scientific hypothesis / future work:** biological phenotype interpretation not yet independently labeled.

No benchmark score should be presented as an end-to-end image-to-biological-phenotype score unless that experiment has actually been run.
