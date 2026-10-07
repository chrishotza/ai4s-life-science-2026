# 5-Minute Demo Script

## 0:00–0:30 — Problem

"Microscopy produces huge volumes of cell observations, but segmentation or tracking alone does not answer the biological question. We want to recover how each cell behaves over time."

Show one microscopy sequence and the target phenotype report.

## 0:30–1:15 — End-to-end pipeline

Show:

microscopy → detection → temporal association → tracking → lineage/events → phenotype features → phenotype discovery.

Run:

```bash
python demo.py
```

## 1:15–2:00 — Tracking

Show trajectories and explain that the public baseline is deterministic and reproducible.

Highlight:

- track continuity;
- spatial association;
- candidate division events.

## 2:00–3:00 — Temporal phenotype

Show the phenotype table.

Highlight:

- mean speed;
- displacement;
- directional persistence;
- duration;
- lineage structure.

Explain that the scientific output is the dynamic phenotype, not the track ID.

## 3:00–3:45 — AI phenotype discovery

Show the unsupervised clusters.

Explain that temporal features are standardized and grouped into interpretable behavioral phenotypes without requiring manually assigned phenotype labels.

## 3:45–4:30 — Validation

Show the synthetic benchmark and the real public microscopy benchmark.

Display only measured values:

- link precision;
- link recall;
- F1;
- phenotype stability;
- representative failure cases.

## 4:30–5:00 — Impact

"Instead of stopping at segmentation or tracking, the system converts microscopy into a compact temporal phenotype representation that can be used to compare cellular behaviors and detect abnormal trajectories."

End with GitHub repository, reproducibility instructions, and dataset provenance.
