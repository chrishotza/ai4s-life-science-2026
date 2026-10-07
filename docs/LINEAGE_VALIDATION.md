# Lineage and Division Validation

## Scope

The phenotype layer can represent parent/child relationships, division events, and descendant structure when lineage edges are available.

This benchmark validates that the public phenotype engine faithfully transforms Cell Tracking Challenge (CTC) lineage annotations into those temporal phenotype features.

It does not claim that the current baseline tracker infers biological divisions from images. The benchmark input is the CTC reference lineage annotation.

## Protocol

For DIC-C2DH-HeLa sequences 01 and 02:

1. Load the CTC reference marker tracks and lineage metadata.
2. Convert annotated parent-child relations into detection-level lineage edges.
3. Run ai4s_phenotype.analyze on the reference nodes and lineage edges.
4. Compare the resulting child counts, descendant counts, and division_event flags with the annotated lineage graph.

The benchmark reports:
- lineage edges recovered;
- division-parent precision, recall, and F1;
- exact child-count rate;
- exact descendant-count rate.

## Evidence boundary

This is a lineage representation validation, not an end-to-end division detector benchmark. A future biological validation experiment should evaluate inferred divisions directly from image-derived tracks against independent division annotations.

## Reproduction

python scripts/benchmark_ctc_lineage.py

The generated ctc_lineage_results.json is a local benchmark artifact and is not required as a committed dataset.
