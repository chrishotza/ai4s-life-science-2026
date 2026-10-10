# Kaggle submission handoff — final actions

**Deadline:** AI4S preliminary round ends **October 10, 2026**; check the Kaggle platform's exact local cutoff time before the final submit action.

## Official links

- [Competition and submission rules](https://www.kaggle.com/competitions/ai-4-s-open-innovation-artificial-intelligence-for-life-scien/overview/challenge-organization)
- [Required organizer registration form](https://docs.google.com/forms/d/e/1FAIpQLSdRAat5jIunRaFNh_NntsVeJUnekEJDrbuokLZ32LFgCwPtiA/viewform?usp=publish-editor)
- [Competition Writeups](https://www.kaggle.com/competitions/ai-4-s-open-innovation-artificial-intelligence-for-life-scien/writeups)
- [Public GitHub repository](https://github.com/chrishotza/ai4s-life-science-2026) — GitHub API verified `visibility: public`, October 9, 2026
- [Copy-ready Writeup source](KAGGLE_WRITEUP.md), starting with **Category: End-to-End System**
- [Full technical report — 17-page public PDF](https://github.com/chrishotza/ai4s-life-science-2026/releases/download/ai4s-2026-technical-report/AI4S_Temporal_Cellular_Phenotype_Technical_Report.pdf) (verified public GitHub Release). [Markdown source](TECHNICAL_REPORT.md).
- [Evidence and biological-use-case guide](BIOLOGICAL_IMPACT_CASE.md).

## Human / authenticated actions that must be verified

- [x] **Submit organizer registration form.** Team leader confirmed this completed on October 9, 2026; this is self-reported and the form's confirmation receipt was not independently inspected.
- [ ] Verify registered team roster **and one leader** match the report; report currently contains **Chris Hotza as the single draft member**, not verified registration.
- [x] **Publish the V10 narrated demo publicly:** https://www.kaggle.com/datasets/chrishotza/ai4s-2026-temporal-cellular-phenotype-demo; public dataset with MP4 in-browser player, verified from signed-out Kaggle session on October 9, 2026. **Upstream dataset and model-weight usage rights still require review** before final competition submission.
- [x] **Team leader reports that the Kaggle Writeup was submitted** (recorded in the judge guide; this is a human attestation, **not** an independently authenticated platform receipt). Reported entry: https://www.kaggle.com/competitions/ai-4-s-open-innovation-artificial-intelligence-for-life-scien/writeups/new-writeup-1791588412439.
- [ ] **Critical authenticated check before the platform deadline:** log in to the registered Kaggle account, open that exact Writeup, confirm it shows **Submitted** (not merely a draft), its competition/team/category are correct, and that the video, repository and technical PDF appear in the **actual Kaggle content**.
- [ ] **Synchronize the submitted Kaggle page with the latest GitHub Writeup source:** https://github.com/chrishotza/ai4s-life-science-2026/blob/main/docs/KAGGLE_WRITEUP.md. GitHub commits do **not** edit a Kaggle Writeup automatically. The current source includes the real ALFI expert-track mitosis-stage comparison, 193-cell silver-centroid discrepancy audit and absolute public evidence links. If editing the submitted Kaggle page is permitted before cutoff, update and resubmit/save it, then confirm status again.
- [ ] **Verify third-party media and pretrained-model/dataset redistribution rights** for the published video and supporting files before submission cutoff.
- [ ] Check external access to the published video in a fresh signed-out browser. Our independent machine-fetch retrieved the Kaggle dataset title but its frontend crashed while loading a CSS asset, so current in-browser playback is **not independently reconfirmed**.
- [ ] If the Kaggle Writeup URL returns a signed-out 404, do **not** infer that the project was never submitted: private/draft/access restrictions can cause ambiguous errors. Verify in the competition account and record the confirmed submission page/status.

## Claims to protect in the final paste

- **Main real-data result:** 168 raw DIC-C2DH-HeLa frames, CellposeSAM-v2 and the real image-derived tracker/phenotype path; segmentation F1 **0.9354**, detection F1 **0.9684**, temporal-link F1 **0.9808**.
- **Different control:** reference-centroid association F1 **0.99228** is not an end-to-end raw-image metric.
- **Phenotype boundary:** 126 trajectory profiles, with 54 audit-only, 21 low confidence descriptive and 51 descriptive computational; **no** independent biological-state ground truth.
- **Division boundary:** reference-annotated divisions can locate demo windows; automatic division inference must be validated separately.
- **Limits:** ALFI instance F1 **0.2282** shows a cross-domain generalization gap; actual organ-on-chip data and treated/control biological effects are not validated.
- The code is MIT licensed but upstream datasets, model weights and third-party media retain their own conditions.

**Submission over model tuning:** when time is short, eligibility and public deliverables outrank optional demonstration embellishments.
