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
- [ ] Paste and submit the Kaggle Writeup with **the public video URL**, public code URL, category declaration and technical-report content or valid public PDF.
- [ ] Reopen the Writeup and video links in a logged-out/private browsing session to verify external judges can access them.
- [ ] Check that Kaggle reports the submission as actually submitted (not a saved draft).

## Claims to protect in the final paste

- **Main real-data result:** 168 raw DIC-C2DH-HeLa frames, CellposeSAM-v2 and the real image-derived tracker/phenotype path; segmentation F1 **0.9354**, detection F1 **0.9684**, temporal-link F1 **0.9808**.
- **Different control:** reference-centroid association F1 **0.99228** is not an end-to-end raw-image metric.
- **Phenotype boundary:** 126 trajectory profiles, with 54 audit-only, 21 low confidence descriptive and 51 descriptive computational; **no** independent biological-state ground truth.
- **Division boundary:** reference-annotated divisions can locate demo windows; automatic division inference must be validated separately.
- **Limits:** ALFI instance F1 **0.2282** shows a cross-domain generalization gap; actual organ-on-chip data and treated/control biological effects are not validated.
- The code is MIT licensed but upstream datasets, model weights and third-party media retain their own conditions.

**Submission over model tuning:** when time is short, eligibility and public deliverables outrank optional demonstration embellishments.
