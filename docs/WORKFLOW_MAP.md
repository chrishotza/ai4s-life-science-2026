# Workflow map for judges and independent maintainers

The repository contains multiple experiments. **Do not infer that every passing workflow proves end-to-end biology.** These workflows have different input geometry and evaluation questions. Start with the standard [CI](../.github/workflows/ci.yml) and the frozen image-derived CTC result.

## Which workflow to inspect first?

| Question | Workflow | Input and meaning |
|---|---|---|
| Is today's `main` code/test/doc suite healthy? | [CI](../.github/workflows/ci.yml) | Package install, Python compilation, Ruff, pytest, reproducibility audits, claim validation; **no pretrained 168-frame inference** |
| What is the strongest real microscopy image-derived benchmark? | [CTC Cellpose End-to-End](../.github/workflows/ctc-cellpose-validation.yml) | Raw HeLa images → pretrained CellposeSAM-v2 → detections/tracks → phenotype profiles. [Frozen successful complete 168-frame run](https://github.com/chrishotza/ai4s-life-science-2026/actions/runs/37930909373) |
| What did the CTC reference-geometry control establish? | [CTC external evaluation](../.github/workflows/ctc-external.yml), [supervised TRA](../.github/workflows/ctc-supervised-tra-e2e.yml) | **Reference/controlled geometry** is distinct from a full raw-image benchmark; do not copy these TRA/LNK values into an end-to-end claim |
| Are motion phenotype clusters stable? | [Real CTC phenotype stability](../.github/workflows/ctc-real-phenotype-stability.yml), [motility ablation](../.github/workflows/ctc-motility-ablation.yml) | Repeated clustering / feature-set controls on image-derived track feature tables, **not biological phenotype ground truth** |
| Did past motion improve ALFI phase labels? | [ALFI expert-label validation](../.github/workflows/alfi-expert-label-validation.yml) | Expert-annotated boxes and tracks, stage labels and held-out sequence split; **not raw-image end-to-end** |
| What is wrong with transfer to another microscope domain? | [ALFI raw Cellpose](../.github/workflows/alfi-cellpose-raw.yml) and [scale scout](../.github/workflows/alfi-cellpose-scale.yml) | Negative cross-domain results need to stay visible. No successful ALFI raw-image classification claim |
| Can we produce actual, identity-colored consecutive cell images? | [CTC 24-frame colored film](../.github/workflows/ctc-stable-color-24.yml) | Real 24-frame focused video. Examine exact predicted masks and anti-switch filtering before treating colors as trusted identities |
| Can the full population be visualized with native integer masks? | [CTC Full Population Native Identity](../.github/workflows/ctc-population-identity.yml) | Real 24-frame focused mode or **84-frame entire sequence**; outputs integer predicted masks/track CSV, QA and film on successful completion |
| Can the particular 66-observation single-track story be reproduced? | [Continuous Single-Cell Demo](../.github/workflows/ctc-continuous-single-cell.yml) | Re-run the *full 84-frame raw image inference*, then render selected candidate track 21 with no synthetic positions |

## Important distinctions

**Public video today:** [older narrated V10 Kaggle dataset](https://www.kaggle.com/datasets/chrishotza/ai4s-2026-temporal-cellular-phenotype-demo). The V17 whole-population version described in [its QA notes](VIDEO_V17_FULL_POPULATION_QA.md) is a **local preview** until a public replacement is verified.

**Pipeline vs. checks:** `pytest`, lint and the deterministic synthetic demo verify engineering contracts; none alone reproduces the pretrained-model CTC evaluation. The 24-frame video samples are subsets of the original 168 images, not separate independent datasets.

**Evaluation mode:** The reference-centroid/annotation control cannot be relabeled as an image-derived detector. ALFI expert-track experiments cannot be relabeled as an automatic raw-image phenotype prediction.

**Long-running experiments:** Pretrained CPU Cellpose evaluations are computationally expensive and GitHub Actions may still show active runs. Only use their metrics after GitHub marks the run **completed/success**, its published artifact exists, and its manifest matches the source commit and frame counts. Do not infer final video availability from a queued or in-progress run.

**Licensing:** Downloadable benchmark data, pretrained model weights and microscopy-derived videos remain subject to third-party terms. Before copying video to Kaggle or GitHub Releases, see [release/media rights checklist](FINAL_SUBMISSION_HANDOFF.md).

## Browse results without losing provenance

Use the [claim–evidence matrix](CLAIM_EVIDENCE_MATRIX.md) to map each numerical headline to exact evidence, then [source run audit](CTC_CELLPOSE_ARTIFACT_AUDIT.md) to verify dataset/protocol. The [independent review packet](INDEPENDENT_REVIEW_PACKET.md) assigns code, scientific-statistical and reviewer/publishing tasks to separate AI auditors. A stable release [v0.1.0](https://github.com/chrishotza/ai4s-life-science-2026/releases/tag/v0.1.0) exists but predates newer experimental work on `main`; archive version and active code are **not interchangeable**.
