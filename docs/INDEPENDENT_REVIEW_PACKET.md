# Independent AI & scientific audit packet

**Purpose:** Invite skeptical, reproducible **read-only** reviews of this public research-software prototype before claiming it is competition-ready. **Do not start by trusting the README or prior AI verdicts.** Verify source code, artifacts, experimental boundaries, and competitor-facing clarity independently.

**Canonical source:** https://github.com/chrishotza/ai4s-life-science-2026 — audit the current `main` commit and record its full SHA. The [v0.1.0 software release](https://github.com/chrishotza/ai4s-life-science-2026/releases/tag/v0.1.0) is a **frozen older snapshot**, not automatically identical to the active branch.

## What is supported; what is not

| Claim or output | Evidence source | Correct boundary |
|---|---|---|
| Full raw-image CTC pipeline processed 168 DIC-C2DH-HeLa frames (84×2) | [Frozen metrics](evidence/ctc/full_sequence_metrics.json), [source run](https://github.com/chrishotza/ai4s-life-science-2026/actions/runs/37930909373), [protocol](CTC_CELLPOSE_ARTIFACT_AUDIT.md) | Segmentation F1@IoU50 0.9354, detection F1 0.9684, *internal* tracking-edge F1 0.9808; **not** an official CTC leaderboard score |
| 126 image-derived track phenotype rows | [Derived CSV](evidence/ctc/derived_phenotype_features.csv), [confidence gate](evidence/ctc/confidence_gated_phenotype_summary.json) | 54 audit-only; 21 low-confidence descriptive; 51 eligible only for **computational descriptive** interpretation; no independent biological phenotype labels |
| ALFI expert-track temporal stage-probe experiment | [ALFI analysis](ALFI_PRODUCT_TEMPORAL_PROBE_RESULTS.md) | Held-out macro F1 0.5138 (static) vs 0.5676 (temporal); **expert/oracle boxes and IDs supplied**, not raw-image end-to-end inference |
| ALFI raw-image generalization | [ALFI failure audit](ALFI_RAW_IMAGE_INSTANCE_AUDIT.md) | Best observed segmentation F1 0.2282 on fixed ALFI frames; **weak transfer**, not biological validation |
| Whole-population V17 narrated movie | [V17 video provenance/QA](VIDEO_V17_FULL_POPULATION_QA.md) | 134-sec **local preview** with 24 consecutive CTC images, not the 168-frame benchmark movie; its visually recovered masks are approximations, **not** the original integer-mask arrays |
| Exact-mask/native full-population rendering | [Source workflow](../.github/workflows/ctc-population-identity.yml), [continuity gate](../src/ai4s_imaging/identity_confidence.py), [tests](../tests/test_identity_confidence.py) | Verify a **completed** workflow, artifact, and per-track anti-switch QA before calling the native output finalized. A test passing does not establish biological identity correctness |
| Official public Kaggle demo | [V10 public dataset](https://www.kaggle.com/datasets/chrishotza/ai4s-2026-temporal-cellular-phenotype-demo), [submission handoff](FINAL_SUBMISSION_HANDOFF.md) | Public V10 is older than local V17 preview. An updated GitHub document **does not** update the actual submitted Kaggle Writeup |

**Scientific claims that must remain blocked:** biological cell-state discovery; independently confirmed mother/daughter splits; treatment/drug response; validated organ-on-a-chip performance; official CTC leaderboard comparisons; a guarantee of zero track identity switches; an independently verified new Kaggle submission receipt.

**Release/publishing boundaries:** the GitHub MIT license covers project **code**, not necessarily CTC microscopy, third-party pretrained weights, or video/annotation redistribution. Review the [media permissions gate](FINAL_SUBMISSION_HANDOFF.md). A Zenodo DOI must not be claimed until independently verified.

## Suggested division of independent AI reviews

### Auditor A — code, data contracts, failure modes

Inspect `src/ai4s_tracking/`, `src/ai4s_pipeline/`, `src/ai4s_imaging/`, `src/ai4s_phenotype/`, and corresponding tests. Independently verify centroid units, frame indexing, label-ID mapping, identity continuity, division-edge logic, malformed input handling, time causality, and actual packaging from a clean environment. Try to build counterexamples. Read the concrete segmentation/association evaluation scripts; check that CTC reference masks/IDs never substitute for image-derived predictions in the **end-to-end** experiment. Include line-level source citations in all findings.

### Auditor B — scientific methodology and statistics

Independently recompute the frozen CTC evidence where practical. Separate image segmentation, association with oracle/reference geometry, py-ctcmetrics bridge, phenotype cluster stability, confidence gates, and ALFI **expert-track** classification. Look for leakage, evaluation-set reuse, optimistic feature/threshold selection, missing uncertainty, misleading averaging, label inconsistencies, data-provenance weaknesses, and a mismatch between descriptive computational groups and biological conclusions. In particular, test cross-domain limitations and whether the provided studies support a meaningful new life-science finding.

### Auditor C — judge-facing clarity and release readiness

Start in [Judge Reader Guide](JUDGE_READER_GUIDE.md), then review [competition Writeup source](KAGGLE_WRITEUP.md), [technical report](TECHNICAL_REPORT.md), [claim matrix](CLAIM_EVIDENCE_MATRIX.md), [latest video QA](VIDEO_V17_FULL_POPULATION_QA.md), and [submission handoff](FINAL_SUBMISSION_HANDOFF.md). Judge whether the innovation is clearly described **without claiming CellposeSAM as an original model**. Check that the public, signed-out video and PDF really open, that Kaggle Writeup status is authenticated rather than inferred, and that all public media have a defensible rights basis. **Do not confuse the local V17 preview with the public V10.**

## Reproduction commands

Use Python 3.11 for the tested path. A smoke test exercises **synthetic data**, not actual CTC performance:

```bash
python -m venv .venv
# activate it on your operating system
python -m pip install -e .
python -m pip install -r requirements-dev.txt
python demo.py
ruff check src scripts demo.py
pytest -q
python scripts/validate_submission_claims.py
python scripts/audit_repo_integrity.py
```

For CTC raw microscopy and pretrained CellposeSAM-v2, follow [the 168-frame workflow](../.github/workflows/ctc-cellpose-validation.yml) and record source model/weight version, original microscope-frame hashes, exact branch/commit, Python packages, hardware/runtime, and model parameters. Re-evaluating the actual Cellpose path requires more resources than this smoke test; **do not claim it was reproduced if it was not run**.

## Required report format for other AI reviewers

1. **Verdict:** `REJECT / REVISE / READY FOR TECHNICAL REVIEW`. Clearly distinguish *code readiness*, *scientific validity*, and *competition/publication readiness*.
2. **Top findings:** P0 (blocking), P1 (material), P2 (polish). Each needs file/line or exact artifact ID, why it matters, and a concrete reproduction/repair procedure. Distinguish verified defects from hypotheses.
3. **Experiments actually executed:** commands, environment, commit SHA, sample/row counts, expected versus actual results; say explicitly if browsing was limited or code could not be executed.
4. **Claims to correct:** exact text plus compliant replacement; prohibit made-up literature, biological labels, official leaderboard scores, licenses, and benchmark outputs.
5. **Presentation and reproducibility:** video continuity, true `track_id` versus frame-local `instance_id`, uncertainty visualization, QA artifacts and sound/source rights, README and report accessibility.
6. **Prioritized fix list:** the three highest-impact repairs that can be verified before the challenge cutoff. **Do not create new marketing features before checking release eligibility.**

### Copy-ready message for a separate AI

> Independently and skeptically audit the public repository https://github.com/chrishotza/ai4s-life-science-2026 for the AI4S Life Science 2026 competition. Read `docs/INDEPENDENT_REVIEW_PACKET.md` first and review the code and cited evidence yourself. This is a research prototype; you must distinguish the 168-frame raw-image CTC evaluation from the separate oracle-reference association tests, the expert-track ALFI stage probe, and the local-only 24-frame V17 video preview. Do not reward persuasive prose unless its measurements can be traced to code and artifacts. Review claim validity, leakage, tracking identity continuity, failure modes, reproducibility, scientific impact, public-demo availability and media licensing. Report P0/P1/P2 findings, exact files/lines, commands/results actually checked, and your three most valuable concrete fixes. Do not assume Kaggle was updated when GitHub changed, or that the release tag matches current `main`. Do not modify the repository; return an evidence-backed review.

## How to consolidate three reviews

Deduplicate identical defects by exact source location. Fix **P0 first**; verify each fix with a regression test and a fresh green `main` CI. If two reviewers disagree on a scientific claim, inspect the source artifacts and actual executed experiment instead of voting. Preserve negative results and unvalidated boundaries. Only after this audit should a public video replacement or competition-readiness assertion be considered.
