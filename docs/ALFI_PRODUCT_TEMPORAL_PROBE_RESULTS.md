# Actual product temporal-state classifier: real ALFI MI expert labels (2026-10-09)

**Engineering outcome: GO** — causal temporal predictor is a reusable product API, locally 37× faster than former loop implementation on 7,480 expert ALFI rows (0.01s vs 0.37s in a single unoptimized local timing), identical predictors to numerical tolerance 1.5e-14 and identical multi-assay benchmark scores after refactoring.

**Scientific outcome: exploratory positive on oracle cell boxes.** Not verified raw-video E2E phenotype prediction.

## Source and executable evidence

- [Product causal feature API](../src/ai4s_phenotype/causal.py) with no use of future frames or class labels in predictors.
- [Optional trained biological-state probe](../src/ai4s_phenotype/state_probe.py) which exposes static-only vs static-plus-motion feature sets, same logistic classifier, phase score outputs, and a heldout-sequence evaluation guard.
- [Execution and scored script](../scripts/evaluate_alfi_product_probe.py).
- Dataset: ALFI expert PhenoTruth.csv, Antonelli et al., CC BY. https://doi.org/10.6084/m9.figshare.23798451.v1 .
- [Reproducible real-label workflow](https://github.com/chrishotza/ai4s-life-science-2026/actions/runs/37973172342), SUCCESS; [evidence artifact](https://github.com/chrishotza/ai4s-life-science-2026/actions/runs/37973172342/artifacts/11637746931), including the raw 29 expert CSV files, source SHA256, aggregate and per-assay metrics, product_state_probe.json.
- [CI for causal predictor/heldout tests](https://github.com/chrishotza/ai4s-life-science-2026/actions/runs/37973172307), SUCCESS.

The 29-expert-sequence benchmark previously measured MI static macro F1 0.5004573424 and motion-only F1 0.7188630476; after moving the exact numerical features into product code, all global and MI/CD/TP F1 values matched the archived original **exactly**. No claims of new independent discovery from that refactor.

## Fixed product API evaluation: four train/four heldout MI sequences

- **Training:** MI01–MI04, 405 annotated expert observations (21 tracks).
- **Test:** MI05–MI08, 930 annotated expert observations (72 tracks).
- Inputs: raw EXPERT bounding box x,y,width,height and expert track ID. No raw image segmentation is used.
- Class labels: EarlyMitosis and LateMitosis. No future geometry; only six immediate-past derivative motion features.
- Both models use class-balanced LogisticRegression C=0.25, training-only imputation and scaling. Same samples and train/test split.

| Heldout MI05–MI08, 930 expert observations | Static expert-box geometry | Static + six past motion/shape-change features |
|---|---:|---:|
| Macro F1 | 0.51378959 | **0.56761702** |
| Balanced accuracy | 0.54660261 | 0.57859445 |
| EarlyMitosis F1 | 0.85152284 | 0.86098655 |
| LateMitosis F1 | 0.17605634 | **0.27424749** |
| True LateMitosis observations correctly identified | 25 | **41** |
| Incorrect LateMitosis false positives | 3 | 2 |

Global macro-F1 delta temporal minus static = **+0.05382743**. The 10,000-resample **whole-sequence cluster bootstrap** over the four heldout sequences gives descriptive 2.5–97.5% interval **[+0.01341, +0.17538]**. This resamples heldout predictions and does not refit the model.

MI per sequence, F1 baseline → temporal:
- MI05: 0.94889 → 0.94889;
- MI06: 0.43787 → 0.45658;
- MI07: 0.34659 → 0.51564;
- MI08: 0.41944 → 0.60690.

**Critical scientific limits:** Small number of sequence-level units (n=4); trajectories and cells within the same sequence are not independent validation units. Earlier exploratory work has already looked at this ALFI corpus, specific MI task and motion features. So the bootstrap interval does NOT account for subgroup/model/feature selection; this is NOT untouched prospective confirmation. Input boxes/track IDs are provided by EXPERTS. The image-to-instance benchmark fails on ALFI, see [model race](ALFI_MODEL_SCOUT_AUDIT.md). Performance is NOT a Kaggle official score or evidence that raw microscopy identifies mitosis stage automatically.

## Product decision

- **GO**: integrate the causal feature extractor and optional supervised state readout with explicit split guard. Trainable and testable biological state predictions are now first-class package functionality rather than benchmark-only routines.
- **NO-GO**: claiming full image→track→cellular-state validation. The segmentation domain-transfer step remains the bottleneck.
- Next scientific test: obtain genuinely untouched expert-labeled microscopy sequences or independent perturbation/stage labels not previously examined; improve image-level instance detection and evaluate state models from **predicted** trajectories, with a shared comparison against static features.
