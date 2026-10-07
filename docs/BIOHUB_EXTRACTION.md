# BioHub extraction map

The private BioHub research project contains the strongest existing tracking work used as the source for this competition system.

## Reusable research components identified

- 3D cell detection and coordinate extraction
- learned temporal edge prediction
- graph construction
- ILP association
- motion-based relinking
- one-frame gap closing
- strict gap-2 recovery
- short-track rescue
- lineage/division post-processing
- DeepCenter-based veto/confirmation
- bidirectional association fusion
- official metric validation and post-processing sweeps

## What is not copied into the public MVP

- Kaggle filesystem paths
- Kaggle submission generation
- competition-specific artifact resolution
- private model artifact locations
- private benchmark/test splits
- research-only configuration guards and diagnostic machinery

## Extraction strategy

1. Keep BioHub as the private research/source repository.
2. Extract the generic tracking/lineage components into normal Python modules.
3. Put the competition-facing phenotype layer above those components.
4. Add public data and a reproducible inference path.
5. Validate tracking and phenotype outputs independently before final submission.

The public competition repository should never require access to the private BioHub repository.
