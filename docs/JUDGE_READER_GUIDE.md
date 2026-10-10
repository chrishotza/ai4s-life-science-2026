# Judge Reader Guide

This page is the shortest route through the submission evidence. It is written for reviewers who need to understand the biological question, the validated computational path, and the evidence boundaries without reading every artifact in `docs/` first.

## Biological question

Time-lapse microscopy can show more than where a cell is. It can show how a cell moves, persists, divides, changes direction, and participates in lineage structure. The project asks:

> Can a reproducible AI pipeline turn microscopy movies into interpretable single-cell temporal phenotype profiles while clearly separating validated computation from unvalidated biological interpretation?

The current answer is a measured computational prototype: it can generate trajectory-derived phenotype profiles and confidence-gated descriptive groups from real microscopy tracks. It does **not** claim validated biological cell states, drug response, clinical probabilities, or organ-on-a-chip transfer.

## Practical single-cell research use case

Imagine comparing cell migration in microscopy time series. A researcher needs to know not just where each cell appears, but how far it moves, whether it persists in one direction, and whether its history is complete enough to trust. This engine provides those **computational descriptors** and explicitly marks insufficient histories. Its image-derived CTC data support that measurement path; **no treated-versus-control experiment or biologically confirmed state labels are included**. See [the concrete research use case and validation proposal](BIOLOGICAL_IMPACT_CASE.md) for the difference between what is measured today and the next falsifiable biology experiment.

**Public 91-second video:** [V10 narrated microscopy demo on Kaggle](https://www.kaggle.com/datasets/chrishotza/ai4s-2026-temporal-cellular-phenotype-demo). The video uses real image-derived masks/tracks from the 8-frame visual pilot; it does not portray the full 168-frame benchmark footage.

**Concrete observed example:** [Why total cell motion differs from net migration](CTC_REAL_MOTILITY_CASE_STUDY.md). An image-derived predicted track traveled 142.10 µm but moved only 4.29 µm net; the [figure](figures/ctc_real_motility_example.svg) compares two real tracks. This is an exploratory computational example and **not** a biological phenotype or treatment result.

**Beyond the two selected cells:** [audited full-cohort motility sensitivity](CTC_COHORT_MOTILITY_AUDIT.md) analyzes all **126 image-derived tracks** using the production confidence gate (51 accepted as descriptive). Low directional persistence under one *exploratory* cutoff occurs in **33/51**, but its rate shifts with observation and reliability requirements, and differs between sequences. The [machine-readable frozen result](evidence/ctc/motility_cohort_sensitivity.json) is checked in CI. Detector centroid jitter and track fragmentation remain possible confounds; this is not a validated biological state frequency.

**New measured localization audit:** [Pretrained CellposeSAM-v2 centroid discrepancy versus CTC silver masks](CTC_EMPIRICAL_CENTROID_CALIBRATION.md). Across **16 systematically sampled raw frames** and **193 correctly overlapped predicted/reference cell pairs**, median geometric-center offset is **0.91 µm**, p95 **2.70 µm**; **6 reference cells and 18 model instances were unmatched**. This is a *matched-object discrepancy to silver masks*, not an absolute true biological-center error or a guaranteed error bound for all trajectory nodes. [Machine-readable per-instance evidence](evidence/ctc/cellpose_centroid_matches_16_frames.csv) and its [verified summary](evidence/ctc/cellpose_centroid_reference_16_frames.json) are preserved.

**Biological-label sensitivity signal:** In a separate **ALFI expert-box and expert-track** mitosis-stage experiment, a matched-capacity static-only classifier scored macro F1 **0.5138**, while adding past motion/shape-change features scored **0.5676** on four held-out MI sequences (930 observations). The absolute improvement **+0.0538** supports incremental information from temporal features *conditional on oracle geometry*. It does **not** validate raw-image mitosis prediction or transfer to organ-on-a-chip microscopy: ALFI raw-image instance segmentation remains weak (F1 **0.2282**), and just four held-out sequences plus prior exploration limit the inference. [Protocol and underlying evidence](ALFI_PRODUCT_TEMPORAL_PROBE_RESULTS.md).

**Additional robustness check:** [Hypothetical centroid-localization error bounds](CTC_CENTROID_ERROR_SENSITIVITY.md) quantify when low directional persistence remains mathematically guaranteed despite bounded positional error. **These are conditional bounds, not measured accuracy or validated biological effects.** The [frozen numerical audit](evidence/ctc/centroid_localization_bounds.json) is reproduced by CI.

## What to read first

1. `README.md` for the public-facing summary and quick reproduction path.
2. `docs/KAGGLE_WRITEUP.md` for the competition submission narrative.
3. `docs/CLAIM_EVIDENCE_MATRIX.md` for claim-by-claim evidence boundaries.
4. `docs/CTC_CELLPOSE_ARTIFACT_AUDIT.md` and `docs/evidence/ctc/full_sequence_metrics.json` for the strongest image-derived CTC evidence.
5. `docs/SUBMISSION_CHECKLIST.md` for final submission blockers.

## Protocol map

| Protocol | What enters the evaluated component | Main result | What it supports | What it does **not** support |
|---|---|---:|---|---|
| Full image-derived CTC path | Raw DIC-C2DH-HeLa frames -> CellposeSAM-v2 -> tracker -> phenotype profiles | Segmentation F1 0.9354; detection F1 0.9684; tracking-edge F1 0.9808 | The public pipeline can run from raw microscopy to tracks and phenotype profiles on two CTC sequences | Official CTC leaderboard status, biological phenotype discovery, or organ-on-a-chip transfer |
| Association isolation | Reference CTC centroids -> temporal association | Edge-association F1 0.99228 | The linker is strong when object detections are trusted | Image segmentation quality or end-to-end biological interpretation |
| CTC TRA/LNK bridge | Reference geometry preserved -> py-ctcmetrics | TRA about 0.997; LNK about 0.979 | External metric sanity check for association-isolation outputs | Official challenge submission score |
| Real CTC phenotype stability | 126 image-derived tracks -> clustering/stability audit | 54 audit-only, 21 descriptive low confidence, 51 descriptive computational groups | Confidence gates prevent over-reading short tracks | Validated biological cell states |
| ALFI expert-track mitosis-stage probe | Expert bounding boxes and tracked IDs -> static vs past-motion supervised probes on MI05–MI08 | Macro F1 0.5138 -> 0.5676 (+0.0538) | Past motion features provide exploratory incremental signal on labeled cells given expert geometry | Automatic raw-image mitosis detection, prospective biology validation or generalization |
| ALFI cross-domain segmentation | Raw ALFI phase microscopy -> pretrained instance models | CellposeSAM-v2 instance F1 0.2282 on fixed frames | Cross-domain transfer is weak and honestly bounded | A valid ALFI end-to-end cell-state claim |

## Why CellposeSAM-v2 appears in the strongest path

The transparent threshold segmenter is useful for a no-download smoke test and for inspecting data contracts, but it is not the strongest image segmenter. The strongest current raw-image CTC result uses pretrained CellposeSAM-v2 for instance segmentation, then evaluates the repository's detection, association, and phenotype layers downstream.

That is the intended boundary: segmentation can be a replaceable dependency, while the project contribution is the reproducible route from detections/tracks to temporal phenotype profiles, confidence gates, and claim discipline.

## Phenotype claim boundary

The term phenotype is used operationally: trajectory-derived behavioral descriptors such as duration, speed, displacement, directionality, lineage candidates, and reliability diagnostics. Unsupervised clusters are descriptive computational groups unless an independent biological label or perturbation assay validates them.

The current confidence policy blocks or downgrades weak cases instead of presenting every cluster as biology:

- single-observation or insufficient-history tracks remain auditable but are not safe for motion-phenotype interpretation;
- low-confidence groups are descriptive only;
- biological state, treatment-response, clinical, and organ-on-a-chip claims require evidence not yet present in the repository.

## Submission and scientific boundaries

The team leader confirmed the [Kaggle Writeup was submitted](https://www.kaggle.com/competitions/ai-4-s-open-innovation-artificial-intelligence-for-life-scien/writeups/new-writeup-1791588412439). The [public narrated demo](https://www.kaggle.com/datasets/chrishotza/ai4s-2026-temporal-cellular-phenotype-demo) and [technical-report PDF](https://github.com/chrishotza/ai4s-life-science-2026/releases/tag/ai4s-2026-technical-report) are linked. The Kaggle submission is controlled independently from GitHub edits: a changed repository Writeup source **does not automatically update** an already submitted Kaggle article.

The remaining limitations are scientific: two microscopy sequences are not independent experimental batches, cross-domain ALFI transfer is weak, biological phenotypes have not been independently validated, and **organ-on-a-chip transfer remains untested**.

## One-sentence reviewer takeaway

This is not a black-box claim that AI discovered biology. It is a reproducible image-to-trajectory-to-phenotype engine with strong CTC tracking evidence, explicit segmentation dependence, confidence-gated interpretation, and clear boundaries on what remains unvalidated.
