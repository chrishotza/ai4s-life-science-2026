# ALFI assay-stratified external ground-truth benchmark (9 October 2026)

## Evidence and provenance

- Original dataset: ALFI (Antonelli et al.), DOI https://doi.org/10.6084/m9.figshare.23798451.v1, **CC BY**, source https://springernature.figshare.com/articles/dataset/ALFI_dataset_final_/23798451.
- Images total roughly 8.4 GB; **only 29 expert phenotype CSVs** were retrieved via HTTP range and used here, no raw-image segmentation performed.
- [Completed GitHub Actions run](https://github.com/chrishotza/ai4s-life-science-2026/actions/runs/37966261561) — **SUCCESS** on commit d39434ba9a8768157742f88d132f75e9c1d7e945.
- [Full result artifact](https://github.com/chrishotza/ai4s-life-science-2026/actions/runs/37966261561/artifacts/11634325675): 29 expert phenotype CSVs, their sha256s in source_manifest.json, global metrics.json and assay_robustness.json.
- Independent local audit of downloaded artifact found exactly **29/29 matches** between expert CSV bytes and manifest SHA-256 hashes.
- Reproducible code: scripts/evaluate_alfi_expert_labels.py and scripts/evaluate_alfi_assay_robustness.py; workflow .github/workflows/alfi-expert-label-validation.yml; associated [CI success](https://github.com/chrishotza/ai4s-life-science-2026/actions/runs/37966261610).

## Integrity, cohort and model

The 29 sequences contain 7,518 PhenoTruth annotations. One track (38 rows) has ambiguous duplicate sequence/track/frame coordinates; the entire track is dropped, leaving **7,480 expert observations, 356 tracks**.

The whole-dataset, originally run logistic ablation gave **macro-F1 static 0.3565, static+past temporal 0.3219**: negative net change. Do not suppress that result.

After examining this negative outcome, we performed **post-hoc, domain-specific exploration** separating MI (mitosis), CD (cell-death-associated), TP (other phenotypes). Each uses 5-fold GroupKFold holding out WHOLE sequences, never sharing annotation tracks across train/test. Common model is class-balanced logistic regression C=0.25, fold-local median imputation and standardization. All predictor boxes and track IDs are provided by **human expert ground truth**. No phenotype labels, sequence name or track ID are numeric model predictors.

Compared input:
- Static: log width, log height, log area, aspect ratio of expert bounding box.
- Static + motion: adds only **six past-derived** changes (normalized centroid velocity, dlog area, dlog width/height, change in aspect, acceleration). **Excludes age, observation count, cumulative lifetime**.
- Static + full past: adds temporal features including age and cumulative movement.
- Negative control: permutes motion features within each sequence before training and testing, preserving static boxes.
- 10,000 sequence-cluster bootstrap resamples applied to OUT-OF-FOLD predicted labels, preserving sequence clustering. Confidence intervals are **descriptive under post-hoc selection**; they do not correct assay/feature/model search or establish a new independent confirmatory test.

## Assay-stratified findings

| Assay | n seq | rows | Static macro-F1 | + motion-only F1 | Δ motion-only | 95% sequence-bootstrap Δ | Full-past F1 | Shuffled-motion negative F1 |
|---|---:|---:|---:|---:|---:|---|---:|---:|
| MI | 8 | 1,335 | 0.50046 | **0.71886** | **+0.21841** | **[+0.1142, +0.4799]** | 0.74345 | 0.53082 |
| CD | 9 | 1,197 | 0.52587 | 0.55368 | +0.02780 | [-0.0497, +0.1164] | 0.61725 | 0.49054 |
| TP | 12 | 4,948 | 0.32562 | 0.38502 | +0.05940 | [+0.0084, +0.0782] | 0.33633 | 0.31998 |

These assays have **different label sets and imaging conditions**. MI here contains only EarlyMitosis and LateMitosis (1,004 and 331 annotated observations). CD contains EarlyMitosis, LateMitosis and CellDeath, while TP contains all four with strong class imbalance. Do NOT compare macro-F1 levels between these assays as if they have the same classification task.

For MI, the motion-only classifier improves per-sequence F1 in **7/8 sequences**: MI01, MI02, MI03, MI04, MI05, MI06, MI07; MI08 deteriorates. The shuffled-motion negative control drops from 0.71886 to **0.53082**, close to static 0.50046. This is a useful **expert-track geometry signal**, not a proof of learned image phenotypes.

## Scientific/competition decision

**GO for genuine external labels and a reproducible candidate hypothesis:** motion and shape changes supplied by ALFI expert tracking may help distinguish mitosis phases, particularly within the MI assay.

**NO-GO for a validated product superiority claim:** The subgroup and variants were examined after a negative global result; no untouched holdout has tested the selected MI hypothesis; annotations provide idealized expert boxes and IDs (not raw images); this simple logistic baseline is not the user's actual AI4S phenotype model; no official Kaggle score or independent prospective cell-state prediction was obtained. The 10k bootstrap intervals cannot repair post-selection bias.

**Next necessary falsification:** freeze the exact MI task, static baseline and six motion-only variables; evaluate on a truly new expert-labeled sequence / image batch or perform end-to-end image segmentation and tracking with a separate external test set. Report cell-state F1 along with raw-image detection/tracking errors and new heldout-sequence uncertainty. Do not use phenotype ground truth to fit tracking or box extraction.

Data credit: Antonelli et al., ALFI dataset (CC BY), DOI above.
