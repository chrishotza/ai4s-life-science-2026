# Architecture

## Pipeline boundary

The public system is organized as explicit scientific layers. The canonical engine can start from raw time-lapse frames or from precomputed detections:

microscopy
→ detection
→ temporal association
→ lineage/event structure
→ temporal phenotype
→ unsupervised phenotype discovery
→ validation/reporting

## Imaging dimensionality

The detection layer accepts either 2-D+t frames or 3-D+t volumes and emits the same `(t,z,y,x)` node schema. In 2-D input, z is a fixed coordinate; in 3-D input, connected components are evaluated volumetrically and z is measured from the component centroid.

This keeps the image-ingestion contract consistent with the downstream 3-D tracker instead of requiring a separate implementation for volumetric inputs.

## End-to-end entry points

TemporalPhenotypeEngine.run_frames performs baseline detection and then enters the same tracking, lineage, phenotype, and discovery path as TemporalPhenotypeEngine.run. This prevents the demo path and the scientific pipeline from silently diverging.

## Contract boundary

All tracking nodes use:

- node_id
- track_id
- t
- z
- y
- x

Temporal and lineage edges use source_id and target_id, with optional distance_um and edge_type metadata.

Core contracts validate uniqueness, finite coordinates, known edge references, and optional consecutive-frame constraints.

## Coordinate boundary

Physical coordinate conversion is centralized as a z/y/x scale.

This prevents a frequent scientific failure mode where tracking is evaluated in micrometers while downstream lineage geometry silently uses raw pixels.

## Orchestration boundary

TemporalPhenotypeEngine is the canonical production path from detections to:

- tracked nodes;
- temporal links;
- candidate lineage edges;
- phenotype table;
- discovered phenotype groups.

Benchmark scripts are intentionally outside this production boundary. PipelineResult also exposes a machine-readable summary so demos and future service/API layers can consume the same execution state without reconstructing metrics from raw tables.

## Evaluation boundary

Validation is separated into:

1. deterministic unit/regression tests;
2. controlled synthetic phenotype stability;
3. end-to-end perturbed-detection tracking-to-phenotype robustness;
4. CTC association benchmarking;
5. CTC trajectory-phenotype preservation;
6. CTC lineage representation validation;
7. automated submission-claim auditing.

## Auxiliary observation features

The canonical pipeline preserves numeric per-detection attributes through tracking and aggregates them into per-track phenotype metadata using mean, standard deviation, minimum, and maximum summaries.

The default phenotype discovery feature space remains trajectory/lineage-only. This separation is deliberate: morphology and intensity information is now available without silently changing the clustering benchmark or its published scores.

For the current microscopy baseline, this preserves fields such as object area and mean intensity for future multimodal phenotype experiments.

## Discovery confidence

Phenotype assignments now expose two diagnostics: distance to the assigned K-Means centroid and the margin to the next-nearest centroid. These are descriptive confidence signals, not calibrated probabilities.

The production discovery feature space remains unchanged. The diagnostics make ambiguous cells visible instead of forcing every cluster assignment to look equally certain.

## Model lifecycle

Phenotype discovery now has an explicit fit/transform boundary. A fitted discovery model stores the scaler, K-Means model, versioned feature schema, transformation policy, and interpretable cluster names.

This makes it possible to fit phenotype states on a reference cohort and transform a new cohort without silently re-fitting the clustering model. It is a prerequisite for scientifically meaningful cross-condition comparisons.

## Temporal-gap branch

The production baseline remains adjacent-frame MNN. A separate gap_hungarian branch can retain unmatched tracks for a bounded number of frames and create forward-time edges with an explicit frame_gap field.

This is intentionally experimental. It exists because real linking tasks can contain incomplete observations, and the Cell Tracking Challenge Cell Linking Benchmark explicitly evaluates establishing tracklets and completing possible temporal gaps.

The gap branch is protected by A/B evaluation rather than being promoted automatically.

## Performance boundary

The production baseline remains exact mutual-nearest-neighbor association for reproducibility. A KD-tree implementation is now available as an explicitly experimental variant and is included in the A/B harness rather than being silently substituted.

Lineage candidate search uses a KD-tree because its spatial query is independent of global assignment. This reduces repeated parent-versus-child scans without changing the physical-unit semantics.

## Known architectural limits

The baseline tracker has no gap closing and only associates adjacent frames.

Division inference is candidate-based and should not be presented as biological division detection without independent labels.

CTC association results use reference centroids as detections and therefore isolate temporal association from image segmentation.

Unsupervised phenotype labels are descriptive and depend on the selected feature space and clustering configuration.
