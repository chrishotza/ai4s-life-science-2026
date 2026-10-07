# BioHub provenance and public MVP boundary

The private Biohub-lab repository contains the research implementation and experiment history. This public AI4S repository does not require access to that private repository.

BioHub records the public 0.947 baseline as the Kaggle notebook biohub-lineage-forge-precision-tracking, mirrored in the public naveenlx111-svg/Biohub repository at blob d2967327abf1c4eaf207cc3fde752946c499fe51.

The research tracker uses learned 3-D temporal association, ILP association, bidirectional edge fusion, secondary-model consensus, DeepCenter gating, and post-processing for gaps and divisions. Those research components remain separate from this public MVP until redistribution and model-data provenance are explicitly established.

## Public boundary

1. Deterministic 3-D tracking baseline from frame-wise detections.
2. Temporal phenotype analysis over reconstructed tracks and lineage edges.
3. Reproducible CSV examples and local demo.
4. A clean interface for adding a learned model without coupling reviewers to private Kaggle artifacts.

This separation is intentional: the competition requires a public repository reproducible without non-public datasets or paid services. The final submission should only claim components that can actually be redistributed and executed from the public repository.
