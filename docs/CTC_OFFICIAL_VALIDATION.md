# Official CTC Validation Boundary

The current real benchmark in this repository reports custom edge precision, recall, and F1 for temporal association.

These metrics are useful for controlled method comparison, but they are not the official Cell Tracking Challenge TRA score.

The official CTC methodology defines TRA as a normalized Acyclic Oriented Graph Matching (AOGM) measure:

`TRA = 1 - min(AOGM, AOGM0) / AOGM0`

The Cell Tracking Challenge also defines LNK as the linking measure over the temporal graph. Both metrics are distinct from the repository's custom edge F1.

## Architecture decision

Keep both layers:
1. Custom association F1 for transparent A/B method development and rapid regression testing.
2. External CTC-metrics/official evaluator paths for independently comparable validation.

The scores must never be substituted for one another.

## Controlled reference-geometry isolation

The real association benchmark feeds CTC reference centroids into the tracker. A CTC metric bridge therefore needs to preserve the reference object geometry and replace only the track identities. Emitting one-pixel centroid masks is not sufficient for this bridge because the CTC metrics implementation matches reference and result objects by requiring more than 50% reference-object coverage.

The new `scripts/export_ctc_reference.py` path implements the isolation protocol:

```bash
python scripts/export_ctc_reference.py --sequence 01 --distance 8.0
```

It produces CTC-compatible label images with the reference object masks preserved, plus `res_track.txt`. Predicted track IDs are taken from the MNN association layer. Reference lineage is carried as oracle metadata only when the predicted child/parent track ranges remain frame-compatible; incompatible cases are left parentless rather than inventing a graph edge.

This is deliberately an **association-isolation experiment**, not an end-to-end segmentation score and not a full biological lineage claim.

## CTC-maintained Python metrics

The CellTrackingChallenge `py-ctcmetrics` package provides CTC metrics including TRA and LNK and exposes both validation and sequence evaluation APIs.

Install the pinned evaluation dependency:

```bash
pip install -r requirements-ctc.txt
```

Then evaluate an exported sequence:

```bash
python scripts/run_ctcmetrics.py --gt .benchmark_cache/dataset/DIC-C2DH-HeLa/01_GT --res ctc_reference_export/01 --sequence 01 --output-json results/ctc_metrics_01.json
```

The evaluator first validates the CTC result directory and then computes `TRA` and `LNK`. It records the `py-ctcmetrics` version and the repository commit SHA in the JSON artifact.

These values are an externally implemented CTC-metrics validation track. They should be reported separately from the custom 0.99228 F1 headline and from any submission claim that requires the official challenge executable.

## Captured external run

The pull-request workflow executed the pinned evaluator on both real DIC-C2DH-HeLa sequences.

| Sequence | TRA | LNK | AOGM | AOGM0 | Validation |
|---|---:|---:|---:|---:|---:|
| 01 | **0.997315** | **0.979091** | 34.5 | 12850.0 | Valid |
| 02 | **0.997207** | **0.978239** | 33.0 | 11816.5 | Valid |

Run: **GitHub Actions 37662335395**. Evidence artifact: **ctc-tra-lnk-evidence (11501247207)**. Evaluator: `py-ctcmetrics==1.3.3`.

These are **reference-geometry association-isolation results**. The export preserves the CTC reference object masks and uses reference lineage only when frame-compatible; therefore these values are not an end-to-end segmentation result, not a biological lineage result, and not official Cell Tracking Challenge leaderboard scores.

The workflow ran on the pull-request merge ref, so the JSON records checkout commit `a96737195a22d47d3b4f94823a99effbdaff06fe`, which is the merge of PR head `28620d770b30bc728703ddeff5c7c8aaad072b5a` into `main` `892b382ae1692dac9b7fd765b0c6c59ef000ef8c`.

## Official TRA executable boundary

The repository also includes `scripts/run_ctc_tra.py`. It accepts an externally installed official TRA evaluator through the `CTC_TRA_EXECUTABLE` environment variable.

```bash
set CTC_TRA_EXECUTABLE=<path-to-official-TRA-executable>
python scripts/run_ctc_tra.py --directory ctc_reference_export/01 --sequence 01 --digits 3
```

The evaluator binary is deliberately not bundled into the competition repository. The repository records the invocation boundary but does not manufacture an official score before the external evaluator has actually been executed.

## Reproducibility requirements

- CTC dataset and sequence;
- tracker method and physical gate;
- voxel size;
- evaluation-software version;
- command-line arguments;
- generated result directory;
- external evaluator log or JSON result;
- repository commit SHA.

Until an external evaluator is executed, the public quantitative claim remains the custom association F1 already documented in `docs/RESULTS.md`.

## Current status

- Custom real-data association benchmark: validated.
- Reference-geometry CTC export: implemented.
- CTC-maintained TRA/LNK execution path: implemented.
- Official external TRA executable boundary: implemented.
- CTC-maintained `py-ctcmetrics` TRA/LNK execution: **captured for sequences 01 and 02**.
- Official Cell Tracking Challenge TRA/LNK scores: **not claimed; the official challenge submission evaluator has not been executed**.
