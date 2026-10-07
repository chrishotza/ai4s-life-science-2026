# CTC Linking Alignment

The Cell Tracking Challenge has a dedicated Cell Linking Benchmark in addition to the broader Cell Tracking Benchmark.

The linking task is particularly relevant to this architecture because it evaluates object linking from incomplete segmentation inputs and explicitly includes completing possible temporal gaps between established tracklets.

Official methodology:
https://celltrackingchallenge.net/evaluation-methodology/

Cell Linking Benchmark protocol:
https://public.celltrackingchallenge.net/documents/Cell%20Linking%20Benchmark.pdf

## Architectural consequence

The repository keeps two tracking modes:

- mutual_nn: validated adjacent-frame production baseline;
- gap_hungarian: experimental bounded-gap branch.

The gap branch exposes frame_gap, physical distance, and normalized link confidence.

It is not part of the published baseline until it demonstrates an improvement under the repository A/B protocol.

## Why this matters

A detection dropout should not automatically force a cell identity reset. A bounded temporal-gap layer gives the architecture a place to test that hypothesis without contaminating the current MNN baseline.

The benchmark protocol also gives us a principled future route to compare this branch against a recognized linking-oriented evaluation instead of relying only on custom F1.

## Output boundary

The repository now includes a deterministic CTC result writer at `ai4s_io.write_ctc_tracking`. It maps internal track IDs to positive contiguous labels and rejects centroid collisions instead of silently overwriting them.

This creates a reproducible artifact boundary for future CTC TRA/LNK evaluation without changing the current benchmark semantics.
