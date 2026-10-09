# GIDE 30-well real-image study — independently audited outcome

**Run date:** 2026-10-09
**Status:** external image-level dose-response confirmed; **NO-GO for incremental temporal phenotype superiority**.

## Source and reproducibility

- Study: BioImage Archive [S-BIAD2515](https://www.ebi.ac.uk/biostudies/BioImages/studies/S-BIAD2515), CC0.
- [Fixed analysis declared before result](GIDE_30WELL_FIXED_ANALYSIS.md), algorithm [run_gide_30well_dose_pilot.py](../scripts/run_gide_30well_dose_pilot.py), and [workflow](../.github/workflows/gide-30well-dose.yml).
- [Successful 30-well run](https://github.com/chrishotza/ai4s-life-science-2026/actions/runs/37958169491), commit 3bfd0dc8f04abda83a64566228e5c2b2997a2821.
- [Download actual result artifact](https://github.com/chrishotza/ai4s-life-science-2026/actions/runs/37958169491/artifacts/11630767292) — manifest.json, image_features.csv (individual SHA-256 for each TIFF), well_features.csv and summary.json.
- The independent audit used original workflow artifact bytes, confirmed **90 distinct TIFF filenames, 90 SHA-256 hashes, 30 distinct wells, exactly 10 concentrations × 3 wells** and confirmed that the **18 TIFFs overlapping the previous pilot match on their SHA-256 hashes and image-derived features, 18/18**.
- Code and tests at commits bfb075e, 02cf2e1, corrected test import e2fa640; [CI successful](https://github.com/chrishotza/ai4s-life-science-2026/actions/runs/37958293226).

## Predeclared associations: observed values

Thirty wells: staurosporine 0, 0.61, 1.22, 2.44, 4.88, 9.77, 19.53, 39.06, 78.13, 156.25 nM (3 wells/dose, one FOV each). T1/T13 Hoechst and terminal Annexin V C05 TIFF per well.

| Predeclared comparison | Spearman rho | 9,999 permutation two-sided p | Holm adjusted p |
|---|---:|---:|---:|
| Dose vs terminal Annexin V corrected image p99 | +0.595379 | 0.0007 | **0.0007** |
| Dose vs T13-minus-T1 Hoechst corrected image p99 | +0.951259 | 0.0001 | **0.0002** |

**These are associations between dose/plate column and whole-image intensity features**, not confirmed cell-level apoptotic outcomes. All wells for one dose share the same plate column, so positional effects are perfectly confounded with dose. Do not attribute changes causally to apoptosis.

Non-primary sanity checks (exploratory): dose vs terminal Annexin V corrected image mean rho=-0.0154, nominal p=0.9355; dose vs Hoechst corrected mean change rho=-0.3680, nominal p=0.0454. Thus mean brightness does not mirror the upper-tail brightness signal.

## Dose-level aggregates (3 independent wells/dose)

| Dose nM | AnnexinV terminal corrected p99 (mean) | Hoechst corrected p99 change T13-T1 (mean) |
|---:|---:|---:|
| 0 | 538.33 | -45.67 |
| 0.61 | 467.33 | -45.67 |
| 1.22 | 614.33 | -36.67 |
| 2.44 | 571.00 | -30.67 |
| 4.88 | 623.33 | -13.00 |
| 9.77 | 620.00 | -24.67 |
| 19.53 | 611.33 | -12.00 |
| 39.06 | 650.67 | +99.67 |
| 78.13 | 681.33 | +160.33 |
| 156.25 | 693.33 | +194.33 |

Note that corrected Hoechst p99 has a marked increase beginning at the 39.06 nM/column-09 treatment level, an exploratory *image-level pattern*, not a separately validated biological threshold.

## Does temporal information improve independent terminal-image prediction?

Two fixed Ridge(alpha=10) regressors fit solely on Hoechst image intensities. Target: terminal Annexin V corrected image p99. Dose is never supplied as a predictor. Standardization is fit within training folds.

| Out-of-sample scheme and metric | T1 image baseline | T1 plus T13-T1 image change | Increment |
|---|---:|---:|---:|
| **Leave-one-well-out MAE** (lower better) | 63.708 | 65.818 | **-2.110 (temporal WORSE)** |
| Leave-one-well-out R² | 0.0974 | 0.1469 | +0.0495 |
| **Leave-one-dose-out MAE** (exploratory, lower better) | 66.971 | 68.470 | **-1.500 (temporal WORSE)** |
| Leave-one-dose-out R² | 0.0421 | 0.1049 | +0.0628 |

The leave-one-dose-out analysis is a **post-hoc independent audit** (not a predeclared primary test): held-out dose columns were excluded from model training. The paired mean MAE improvement (baseline minus temporal) was -1.500, with exploratory 95% group-bootstrap interval **[-7.952, +5.263]**, which includes zero. A mildly higher R² does **not** justify a superiority claim when MAE is worse.

## Decision and next experiment

**GO** for technical reproducibility and real external microscopic image intensity/dose-association evidence.

**NO-GO** for superior temporal prediction of terminal AnnexinV, independent biological cell-state detection, validating any AI4S discovery clusters, clinical performance or Kaggle ranking. The negative incremental MAE result is valuable: simple image-level Hoechst intensity changes have a dramatic dose-linked signature but are **not sufficient to beat the T1 baseline under the chosen heldout error measure**.

Next experiment must **segment individual nuclei and Annexin V positive cells, join terminal labels to tracked individual objects, and evaluate the repo's phenotype representations against a simpler per-cell baseline on held-out wells, preferably across plates**. Avoid further claims based solely on plate-column dose association. A biological replicate with randomized dose layout is needed to remove plate-position confounding.

Original authors/data credit: WayScience / S-BIAD2515.
