# Kaggle Project Summary (200–300 words)

**Submission category: End-to-End System**  
**Temporal Cellular Phenotype Engine — Interpretable single-cell temporal phenotype analysis**

Time-lapse microscopy captures how cells move and change, but segmentation masks and track IDs alone do not offer an interpretable description of cellular behavior. The Temporal Cellular Phenotype Engine is a reproducible pipeline that transforms microscopy observations into trajectory-level temporal phenotype profiles.

The system combines transparent image preprocessing, cell detection, deterministic temporal association, trajectory reconstruction, lineage/event representation, temporal feature extraction, and unsupervised phenotype discovery. It reports features including duration, displacement, path geometry, mean speed, directional persistence, temporal integrity, and lineage-derived context where available. The scientific aim is to move beyond tracking as an endpoint and make cellular dynamics available for analysis and comparison.

On DIC-C2DH-HeLa sequences 01 and 02 from the Cell Tracking Challenge, a physical-unit sweep selected mutual-nearest-neighbor association with an 8.0 µm gate. With **reference track centroids supplied as detections**, this association-isolation benchmark achieved **0.99135 mean precision, 0.99322 mean recall, and 0.99228 mean edge F1**. A downstream trajectory-feature preservation experiment on the same reference centroids measured **0.9451 mean trajectory coverage, 1.0000 median coverage, and 0.0439 directional-persistence MAE**.

Separate reference-geometry association-isolation checks measured sequence 01 TRA 0.997315 / LNK 0.979091 and sequence 02 TRA 0.997207 / LNK 0.978239; these are not official Cell Tracking Challenge leaderboard scores. These measurements do not establish segmentation performance or biological phenotype validity; controlled synthetic tests probe robustness only. The repository includes setup instructions, tests, benchmark scripts, Docker support, and CI. The next step is independent validation against biologically annotated perturbation data.

**Submission checklist:** a public demo video of no more than five minutes, a publicly accessible repository, a self-contained technical report, and the separate mandatory competition registration form.