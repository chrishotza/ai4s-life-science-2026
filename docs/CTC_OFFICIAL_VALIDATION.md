# Official CTC Validation Boundary

The current real benchmark in this repository reports custom edge precision, recall, and F1 for temporal association.

These metrics are useful for controlled method comparison, but they are not the official Cell Tracking Challenge TRA score.

The official CTC methodology defines TRA as a normalized Acyclic Oriented Graph Matching (AOGM) measure:

TRA = 1 - min(AOGM, AOGM0) / AOGM0

The official software is distributed as command-line executables and is the reference implementation used for challenge evaluation.

## Architecture decision

Keep both layers:
1. Custom association F1 for transparent A/B method development and rapid regression testing.
2. Official CTC TRA adapter for an externally comparable validation track.

The two scores should never be substituted for one another.

## Controlled centroid-isolation mode

The current association benchmark feeds CTC reference centroids into the tracker. A future official-TRA bridge should therefore be labeled explicitly as a perfect-segmentation / reference-centroid isolation experiment.

That mode should preserve the reference object geometry while replacing track identities with the predicted association graph. This isolates temporal linking quality without pretending to measure the full image-to-trajectory pipeline.

## Reproducibility requirements

- CTC dataset and sequence;
- tracker method and physical gate;
- voxel size;
- evaluation-software version;
- command-line arguments;
- generated result directory;
- official TRA log;
- repository commit SHA.

Until this bridge is executed, the public quantitative claim remains the custom association F1 already documented in docs/RESULTS.md.