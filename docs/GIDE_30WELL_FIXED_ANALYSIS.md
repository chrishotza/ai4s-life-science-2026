# GIDE 30-well expansion — fixed analysis plan (2026-10-09)

This file records the analysis protocol before the first completed 30-well outcome. The actual analysis implementation was already committed as scripts/run_gide_30well_dose_pilot.py at bfb075ed914bb6ab9642b9a8783590a415d525ce; tests at 02cf2e1; run starts at https://github.com/chrishotza/ai4s-life-science-2026/actions/runs/37958169491.

## Source and sample
BioImage Archive S-BIAD2515 CC0. 30 wells: rows C/D/E, columns 02–11; 10 staurosporine doses respectively 0, 0.61, 1.22, 2.44, 4.88, 9.77, 19.53, 39.06, 78.13, 156.25 nM. Three wells/dose. Source design from public WayScience platemap_6hr_4ch.csv. For each well use FOV1, Hoechst C01 at timepoints 1 and 13, terminal Annexin V C05 at timepoint 14: 90 TIFF files. These are distinct source images. Hash all downloads SHA-256. No model fitting on biological labels for feature extraction.

## Prioritized outcomes, set BEFORE viewing results

Primary: two-sided Spearman association between dose and terminal Annexin V image p99 after subtracting the 10th percentile intensity background, treating each well as one independent unit (n=30). Use 9999 well-level label permutations, Monte Carlo plus-one p estimate.

Secondary: two-sided Spearman association between dose and change in Hoechst image corrected p99, T13–T1 (30 wells), same 9999 well permutations. Holm-adjust the p-values for the two declared dose-response hypotheses. These are exploratory biomarker proxy correlations, not mechanistic causal tests.

Predictive ablation (descriptive): leave-one-WELL-out fixed Ridge regression (alpha 10, train-fold-only scaling), predicting terminal AnnexinV p99 from:
- baseline: Hoechst T1 corrected image mean and corrected p99;
- temporal: baseline PLUS T13 minus T1 corrected image mean and corrected p99.
Report held-out MAE, R2, delta MAE and delta R2, even if negative. Dose is NOT a model feature. No tuning of alpha from held-out observations, no post hoc feature choice.

Report high-dose versus control group means (3 wells each) for terminal Annexin V corrected mean/p99 and Hoechst temporal changes.

## Essential limitations

- All three wells for a dose occupy a single COLUMN: plate-position effects and dose are confounded. A positive dose trend alone cannot attribute causality to apoptosis.
- Only FOV1; 2 timepoints for predictor; 30 wells from one plate, not independent plates/biological experiments.
- AnnexinV intensity is measured at whole-image level; not cell-matched terminal AnnexinV ground truth.
- This does not test the AI4S temporal cell-track phenotype module. It is a real-data feasibility bridge and must not be represented as a superior phenotype result, a clinical model, or an official Kaggle score.
- No significance claim from held-out image regression unless independently validated; p adjustments cover only the declared dose-response correlations.

## Decision

Even if the two dose-response tests are statistically strong, advancing to a competitive scientific claim requires cell-level masks/track alignment and an ablation against simpler feature baselines, with externally assigned biological labels and independent held-out units.
