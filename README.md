# Temporal Cellular Phenotype Engine

[![CI](https://github.com/chrishotza/ai4s-life-science-2026/actions/workflows/ci.yml/badge.svg)](https://github.com/chrishotza/ai4s-life-science-2026/actions/workflows/ci.yml) · [MIT license](LICENSE) · [Independent review](docs/INDEPENDENT_REVIEW_PACKET.md)

**AI4S Open Innovation: AI for Life Science (2026)** · **End-to-End System** · **Single-cell Phenotype Analysis**

**From time-lapse microscopy to cell trajectories, interpretable temporal features and testable cell-state hypotheses.**

This publicly auditable research prototype treats tracking as infrastructure for a harder question: **how does an individual cell's behavior change over time?** It ingests microscopy sequences, detects and tracks cells, extracts motion/lineage descriptors and reports trajectory-based phenotype groups. An optional supervised state probe uses present-and-past cell shape/motion features.

> **The strongest image-derived evidence:** CellposeSAM-v2 followed by the actual tracking and phenotype pipeline was run on **168 raw DIC-C2DH-HeLa images** (84 frames in each of two Cell Tracking Challenge sequences). It achieved mean **segmentation F1@IoU≥0.5 = 0.9354**, **detection F1 = 0.9684** and **tracking-edge F1 = 0.9808**. Reference annotations were used for evaluation, **not as input detections**. The historical tracking-edge F1 scores only predicted links whose two endpoints matched a reference marker; predicted links with unmatched endpoints were omitted, so this is **not a full trajectory-identity or strict all-predicted-edge score**. These are internal CTC metrics—not an official leaderboard score, an organ-on-a-chip validation, or proof of biological phenotype discovery. [Completed run](https://github.com/chrishotza/ai4s-life-science-2026/actions/runs/37930909373) · [Audit and protocol](docs/CTC_CELLPOSE_ARTIFACT_AUDIT.md).

**A concrete biological-use scenario:** a researcher studying time-dependent cell migration can use the exported tracks to inspect which cells move faster, reverse direction, or have too little temporal evidence to interpret. This is an **analysis workflow**, not evidence that treatment effects or biological states have been discovered. [See the proposed validation experiment](docs/BIOLOGICAL_IMPACT_CASE.md).

**Observed single-cell example:** [two genuinely image-derived trajectories from the same CTC sequence](docs/CTC_REAL_MOTILITY_CASE_STUDY.md) show why *movement* and *net migration* are different measurements: one traveled 142.10 µm but ended just 4.29 µm from its start. See the [evidence-based comparison figure](docs/figures/ctc_real_motility_example.svg). This is descriptive motion analysis, not a validated biological state.

**Public narrated demo (91 seconds):** [Watch the V10 microscopy-to-tracks explainer on Kaggle](https://www.kaggle.com/datasets/chrishotza/ai4s-2026-temporal-cellular-phenotype-demo). It shows an 8-frame CellposeSAM-v2 real-prediction *visual pilot*, not the full 168-frame benchmark. Published as a public dataset with an in-browser MP4 player and verified signed-out access on October 9, 2026.

**New full-population visualization candidate (V17, not yet public):** 24 consecutive real CTC frames with every detected cell visible, multiple stable model-track colors, and uncertainty-based neutral styling for ambiguous identities. The complete 134-second narrated preview and its pixel-/track-level limitations are documented in [V17 whole-population quality audit](docs/VIDEO_V17_FULL_POPULATION_QA.md). **This does not replace the public V10 Kaggle video**, nor claim that the full 168 evaluated microscope frames appear consecutively in the demonstration.

**Independent reviewer shortcut:** [External AI and scientific review packet](docs/INDEPENDENT_REVIEW_PACKET.md) · [Judge Reader Guide](docs/JUDGE_READER_GUIDE.md) · [Claim–evidence matrix](docs/CLAIM_EVIDENCE_MATRIX.md). The packet distinguishes reproducible experimental results, experimental video previews, and Kaggle submission status. Review the actual code and evidence, not just this README.

**Release status:** [v0.1.0](https://github.com/chrishotza/ai4s-life-science-2026/releases/tag/v0.1.0) is a fixed archival software snapshot. The active `main` branch includes additional experiments and visualization work after that release; do **not** assume the tag represents the newest video or the submitted Kaggle Writeup.

## What it does

Microscopy frames → **instance masks** → centroids and bounding boxes → **temporal tracks** → lineage candidates → **causal motion and morphology** → unsupervised phenotype groups or supervised cell-state scores.

The product exposes three segmentation choices: transparent intensity thresholding; a domain-trained supervised pixel classifier; or pretrained **CellposeSAM-v2** (optional). Tracking uses physical-unit proximity and deterministic matching (mutual nearest-neighbor or Hungarian). The phenotype layer supplies trajectory duration, speed, displacement, directional persistence, lineage candidates and reliability/quality diagnostics. Clusters are *descriptive computational groups*, not externally confirmed biological cell types.

## Results, with protocols kept separate

| Evaluation | Actual input to the evaluated component | Measured outcome | Scientific boundary |
|---|---|---|---|
| **Full image-derived CTC**, DIC-C2DH-HeLa seq01/02, **168 frames** | Raw microscopy → pretrained CellposeSAM-v2 → tracking → phenotype profiles | **Segmentation F1 0.9354; detection F1 0.9684; edge F1 0.9808** | Two CTC sequences; derived phenotype groups do not have independent biological labels |
| **Association isolation**, CTC seq01/02 | **Perfect reference centroids** → temporal linker | Mean edge-association F1 **0.9923** | Isolates the linker; **not** end-to-end detection |
| **Independent ALFI oracle-tracking audit**, eight MI sequences | **Expert bounding boxes and cell IDs** → actual tracker | Hungarian edge F1 **0.9943** across 16,256 gold temporal links | Strong component check; expert detections supplied |
| **ALFI mitosis-stage readout** | Expert-labeled track boxes: train MI01–MI04, evaluate MI05–MI08 | Macro-F1 **0.5138 static → 0.5676** with past motion features | Exploratory; oracle boxes and previously explored cohort; no raw-image phenotype validation |
| **ALFI cross-domain cell segmentation** | Raw ALFI phase microscopy → pretrained instance models | Best of tested pretrained variants: CellposeSAM-v2 instance F1 **0.2282** on four fixed frames | **Poor generalization**. No valid ALFI end-to-end cell-state claim |

The disparity between **CTC 0.9354 instance-segmentation F1** and **ALFI 0.2282 instance F1** is the project's most important limitation: image modality and annotation differences matter. We do not average these scores, call the expert-centroid results image-derived, or infer drug-response phenotypes without labels.

[Complete results](docs/RESULTS.md) · [CTC source artifact audit](docs/CTC_CELLPOSE_ARTIFACT_AUDIT.md) · [ALFI model comparison](docs/ALFI_MODEL_SCOUT_AUDIT.md) · [ALFI state-probe evidence](docs/ALFI_PRODUCT_TEMPORAL_PROBE_RESULTS.md).

### Are the phenotype groups stable?

Clustering uses standardized trajectory and lineage features with K-Means (k=3), as an **unsupervised representation**. Synthetic perturbation benchmarks already exist, but they do not demonstrate real-world biological validity.

The completed [real-CTC cluster stability audit](docs/CTC_REAL_PHENOTYPE_STABILITY.md) evaluated **126 image-derived tracks** using the actual discovery model. **43 tracks contain only one observation**. Across 20 random seeds, full-data cluster ARI was 1.000, but under 80 sequence-stratified trajectory bootstraps the median ARI fell from **0.945 on all 126 tracks** to **0.687 on the 72 tracks with at least three observations**. All 43 singleton tracks landed in one 51-member group in the pooled reference clustering: short observation histories can masquerade as a stable biological behavior. The engine now marks tracks with fewer than three observations as **insufficient_temporal_evidence** while preserving their numerical K-Means cluster for auditing. This quantifies **algorithmic repeatability**, not biological truth.

**Permanent evidence:** [168-frame image-derived CTC summary JSON](docs/evidence/ctc/full_sequence_metrics.json) · [real CTC ARI metrics JSON](docs/evidence/ctc/stability_summary.json) · [126 real derived features CSV](docs/evidence/ctc/derived_phenotype_features.csv) · [reproducible run](https://github.com/chrishotza/ai4s-life-science-2026/actions/runs/37975995897).

## Quick reproduction — no CTC download needed

Python 3.11 is recommended. The lightweight demo synthesizes a deterministic small microscopy-like time series and runs the full baseline to a phenotype report.

```bash
python -m venv .venv
# Activate the virtual environment for your OS:
# Windows CMD: .venv\Scripts\activate.bat
# Linux/macOS: source .venv/bin/activate
pip install -e .
python demo.py
```

For the test suite: `pip install -r requirements-dev.txt && pytest -q`. The CI verifies packaging, contracts, tests and real benchmark scripts. [Workflow map by scientific question](docs/WORKFLOW_MAP.md) explains which jobs actually rerun pretrained models, which are reference-geometry controls, and which create video artifacts. The synthetic demo is a **functionality smoke test**; it is **not** the 168-frame CTC result.

Run on your TIFF stack or directory of per-frame TIFFs:

```bash
python scripts/analyze_microscopy.py ./my_sequence --output ./analysis_output --segmenter threshold --min-area 12 --clusters 3
```

For the pretrained image-derived path, install compatible PyTorch and Cellpose as shown in [the CTC validation workflow](.github/workflows/ctc-image-e2e.yml), then run with `--segmenter cellpose --cellpose-model cpsam_v2`. **Model weights are downloaded from Cellpose at runtime**, require appropriate connectivity and carry upstream training-data/usage conditions; they are not committed here. Coordinate scales (`--voxel-size-um`) must come from your own microscope metadata.

Typical results in the output directory: cell nodes, temporal edges, lineage *candidates*, trajectory phenotype CSVs, discovery outputs, quality diagnostics, JSON summary, Markdown report and figure. The trainable state probe is optional:

```bash
python scripts/predict_cell_states.py --training-boxes train_expert_boxes_with_labels.csv --input-boxes disjoint_test_boxes.csv --output state_predictions.csv --features static_motion
```

This exports per-observation labels/scores with source hashes, prior-history coverage and a strict check that prediction sequences were not used for training. The numerical scores are **uncalibrated**, not clinical probabilities.

## Evaluation, data and scientific limitations

This competition is a **judged Kaggle hackathon**, not a fixed-label Kaggle leaderboard task. There is no universal prediction schema or submission CSV to produce: the official entry is a **Kaggle Writeup** supported by public code, a technical report and a demo. The scoring rubric emphasizes impact (30%), technical innovation (30%), results/validation (20%), reproducibility (10%) and presentation (10%). [Official challenge rules](https://www.kaggle.com/competitions/ai-4-s-open-innovation-artificial-intelligence-for-life-scien/overview/challenge-organization) · [Project Writeup draft](docs/KAGGLE_WRITEUP.md).

**Known limitations:** Organs-on-chip transfer remains untested; CTC biological treatment labels are unavailable for discovery groups; ALFI oracle-track benefits do not survive as a verified full image-to-cell-state score because cross-domain segmentation is currently weak. Causal features mean **past-only computational inputs**, not a causal-effect identification or treatment-response claim. Predicted lineage structures are candidates unless validated against lineage annotations.

**Reproducibility:** [Public 17-page PDF technical report](https://github.com/chrishotza/ai4s-life-science-2026/releases/download/ai4s-2026-technical-report/AI4S_Temporal_Cellular_Phenotype_Technical_Report.pdf) · [Technical report source](docs/TECHNICAL_REPORT.md) · [Architecture](docs/ARCHITECTURE.md) · [Source-provenance audit](docs/CTC_CELLPOSE_ARTIFACT_AUDIT.md) · [GitHub Actions](.github/workflows/) · [Full historical technical README](docs/ARCHIVED_TECHNICAL_README_2026-10-09.md).

## License and third-party rights

Repository code is released under the [MIT License](LICENSE). Experimental datasets, benchmark annotations, generated media, and pretrained model weights have their own upstream terms; this repository does not grant permission to redistribute third-party imagery or external model weights.
