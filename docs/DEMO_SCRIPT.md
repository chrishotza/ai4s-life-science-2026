# Five-Minute Demo Script — Competition Version

**Category: End-to-End System**  
**Target runtime: 4:40–4:55.** Keep the final rendered video at or below 5:00.

This script is designed around the AI4S evaluation dimensions: impact (30%), technical approach and innovation (30%), results and validation (20%), reproducibility (10%), and presentation (10%). Show real operation and results rather than relying on slides alone.

## 0:00–0:25 — The scientific problem

**Visual:** Real DIC-C2DH-HeLa microscopy frames; show the raw input before overlays.

**Narration:**  
“Time-lapse microscopy captures how cells move and change, but a segmentation mask or track ID is not yet a useful description of cellular behavior. Our goal is to turn temporal observations into an interpretable phenotype profile for each cell trajectory.”

## 0:25–1:05 — Run the system

**Visual:** Terminal running `python demo.py`, followed by the actual output artefacts.

**Narration:**  
“The Temporal Cellular Phenotype Engine connects image preprocessing, detection, temporal association, trajectory reconstruction, lineage representation, feature extraction, and unsupervised phenotype discovery in one reproducible workflow.”

**On-screen pipeline:**  
Microscopy → detection → temporal association → trajectories → lineage/events → temporal features → phenotype groups.

## 1:05–1:45 — Show the core output

**Visual:** Real image sequence with overlays and a phenotype table/trajectory view.

**Narration:**  
“For each trajectory, the engine describes duration, displacement, path length, speed, directional persistence, temporal integrity, and available lineage context. The central output is not the track ID itself; it is a transparent, time-dependent behavioral representation.”

## 1:45–2:25 — What is technically distinctive

**Visual:** Brief comparison of MNN, Hungarian, and constant-velocity Hungarian methods, then show the physical-unit gate.

**Narration:**  
“We compared simple and more complex association methods rather than assuming that complexity would improve performance. The best measured configuration on our two evaluated CTC sequences was mutual-nearest-neighbor association with an 8-micrometre gate. The selected configuration is explicit, deterministic, and physically calibrated.”

## 2:25–3:10 — Measured validation

**Visual:** Results card with the exact metric names and a small per-sequence breakdown.

**On-screen values:**
- Mean association precision: **0.99135**
- Mean association recall: **0.99322**
- Mean association F1: **0.99228**
- Mean trajectory coverage: **0.9451**
- Median trajectory coverage: **1.0000**
- Directional-persistence MAE: **0.0439**

**Narration:**  
“These association numbers come from DIC-C2DH-HeLa sequences 01 and 02, with reference centroids supplied as detections. This isolates temporal association; it is not a segmentation score. The phenotype-preservation measurements likewise describe trajectory-derived features, not biological phenotype classification.”

## 3:10–3:45 — Reliability and limitations

**Visual:** Show the controlled missing-observation stress test and label it synthetic.

**Narration:**  
“We also tested controlled detection dropout. A bounded-gap association branch reduced track fragmentation under mild and moderate synthetic dropout, but we keep it experimental because those tests do not establish improved performance on real biological data. Unsupervised clusters are descriptive groups, not validated biological labels.”

## 3:45–4:25 — Reproducibility

**Visual:** GitHub tree with README, requirements, tests, benchmark scripts, CI, and technical report.

**Narration:**  
“The repository provides installation instructions, a direct demo entry point, tests, benchmark scripts, Docker support, and continuous integration. Dataset sources and evidence boundaries are documented, and microscopy data are downloaded transiently rather than redistributed.”

## 4:25–4:50 — Practical value and next validation

**Visual:** End on a clear trajectory/phenotype view and repository title.

**Narration:**  
“This system provides a reproducible bridge from microscopy to interpretable dynamic cellular behavior. The next scientific step is validation against independently annotated biological perturbations, so behavioral clusters can be tested against biological outcomes rather than inferred from trajectories alone.”

**End card:**  
Temporal Cellular Phenotype Engine  
End-to-End System · Single-cell Phenotype Analysis  
Public repository: [insert final public URL]  
Technical report and reproduction instructions: [repository/docs]
