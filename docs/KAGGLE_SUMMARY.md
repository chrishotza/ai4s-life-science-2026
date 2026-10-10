# Kaggle Project Summary (200–300 words)

**Temporal Cellular Phenotype Engine — End-to-End System**

Time-lapse microscopy can show a cell moving without making much net progress. A static mask cannot answer whether individual cells travel persistently, change direction, or have too little evidence to interpret. Our Temporal Cellular Phenotype Engine transforms microscopy sequences into auditable cell tracks, motion measurements, and confidence-gated descriptive profiles.

**Innovation:** We do not claim a new foundation segmentation model. We combine pretrained CellposeSAM-v2 masks with physically calibrated deterministic temporal linking, trajectory features, candidate lineage relationships, reproducible outputs, and explicit quality gates. Tracking is infrastructure; the useful research output is a transparent description of temporal cellular behavior.

On two DIC-C2DH-HeLa sequences comprising **168 raw frames**, the image-derived pipeline achieved **segmentation F1 0.9354**, **detection F1 0.9684**, and **temporal-link F1 0.9808** under documented internal evaluation. Reference annotations were used for scoring, not supplied as input cell detections.

The system exported **126 image-derived trajectories**: 54 remained audit-only, 21 were low-confidence descriptive, and 51 qualified for descriptive computational interpretation. In a new complete-cohort sensitivity audit, **33 of those 51** had directional persistence below an exploratory threshold of 0.20. This fraction changed when minimum track duration and reliability thresholds were tightened, and differed between the two sequences. The thresholds are not biological cell-state labels.

A concrete trajectory traveled **142.10 µm** yet displaced only **4.29 µm** net. Such measurements can guide closer review, not prove drug response, independent biological states or organ-on-chip transfer. A separate association control used **reference centroids**; it is not **biological phenotype classification**, and these metrics are **not official Cell Tracking Challenge leaderboard scores**.

**Reproducibility:** [Source and audited workflows](https://github.com/chrishotza/ai4s-life-science-2026) · [Complete-cohort evidence](CTC_COHORT_MOTILITY_AUDIT.md) · [91-second narrated demo](https://www.kaggle.com/datasets/chrishotza/ai4s-2026-temporal-cellular-phenotype-demo).
