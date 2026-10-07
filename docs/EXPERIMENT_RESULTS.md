# Experiment Results

## Tracking candidate sweep

The competition-oriented A/B harness was run on DIC-C2DH-HeLa sequences 01 and 02.

Frozen baseline:
- mutual nearest neighbor, 8.0 um
- precision 0.99135
- recall 0.99322
- F1 0.99228
- trajectory coverage 0.9451
- directional-persistence MAE 0.0439

Candidate tested:
- **mutual_rescue**: protect mutual nearest-neighbor links, then solve remaining unmatched rows/columns with a global assignment.

Result at 8.0 um:
- precision 0.99135
- recall 0.99322
- F1 0.99228
- trajectory coverage 0.9451
- directional-persistence MAE 0.0439

Decision: **KEEP-UNDER-REVIEW**. The candidate did not improve the frozen baseline, so it is not promoted as the default method.

This is the intended behavior of the experiment protocol: a more complicated method is not accepted merely because it sounds more sophisticated.
