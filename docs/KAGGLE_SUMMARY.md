# Kaggle Project Summary (200–300 words)

**Temporal Cellular Phenotype Engine — End-to-End System for Single-cell Phenotype Analysis**

Time-lapse microscopy contains information about how cells move, persist, divide, and change over time, but many workflows stop at segmentation or tracking. The Temporal Cellular Phenotype Engine turns those trajectories into interpretable temporal phenotype profiles.

The system integrates microscopy preprocessing, cell detection, deterministic 3-D temporal association, lineage/event inference, trajectory feature extraction, and unsupervised phenotype discovery. Tracking is treated as infrastructure; the scientific output is dynamic cellular behavior.

The canonical engine can start from microscopy frames and execute the public detection-to-phenotype path. For rigorous real-data measurement, the CTC experiment intentionally uses **reference centroids as detections** to isolate temporal association from segmentation.

On DIC-C2DH-HeLa sequences 01 and 02, mutual-nearest-neighbor association with an 8.0 µm gate achieved **0.99135 mean precision, 0.99322 mean recall, and 0.99228 mean F1**. Downstream phenotype preservation on the same reference centroids achieved **0.9451 mean trajectory coverage, 1.0000 median coverage, and 0.0439 directional-persistence MAE**.

The same association path was independently evaluated with pinned **py-ctcmetrics==1.3.3** using preserved reference object geometry: **sequence 01 TRA 0.997315 / LNK 0.979091; sequence 02 TRA 0.997207 / LNK 0.978239**.

These are reference-geometry association-isolation results, not end-to-end segmentation or biological phenotype classification and **not official Cell Tracking Challenge leaderboard scores**. Biological phenotype validity still requires independent biological labels or perturbation annotations.

The contribution is a reproducible bridge from **microscopy → trajectories → interpretable temporal phenotype**.