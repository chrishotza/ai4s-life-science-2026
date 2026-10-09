# Confidence-Gated Phenotypes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reproducible confidence-gated CTC phenotype summary that separates audit-only tracks from descriptive phenotype evidence and blocks biological claims when track evidence is insufficient.

**Architecture:** Add a small pure-Python phenotype evidence gate in `ai4s_phenotype`, a repository script that reads the persisted CTC feature snapshot and stability summary, and a CI assertion that regenerates the stable JSON artifact. The gate is deterministic and policy-based: it does not refit clusters or create new biological labels.

**Tech Stack:** Python 3.11, pandas, JSON, pytest, existing GitHub Actions CI.

**Spec:** `docs/PRE_SUBMISSION_EVIDENCE_SPRINT.md`

## Global Constraints

- Use only persisted CTC evidence already committed under `docs/evidence/ctc/`; do not download new datasets.
- Do not call phenotype clusters biological cell types.
- Preserve auditable raw cluster IDs while adding interpretation permissions.
- Tracks with fewer than 3 observations must not receive a motion-phenotype interpretation.
- The output artifact must be deterministic and committed under `docs/evidence/ctc/confidence_gated_phenotype_summary.json`.

## Review Focus

- Singleton and two-observation tracks must be marked `audit_only` with `blocked_biological_claim`.
- Tracks with at least 3 observations but low reliability must remain descriptive only, not biological claims.
- Summary counts must add up to the number of input profiles.
- The artifact must retain provenance from the existing stability summary.
- The CI command must regenerate the committed artifact exactly.

---

### Task 1: Confidence gate model

**Files:**
- Create: `src/ai4s_phenotype/confidence.py`
- Test: `tests/test_confidence_gated_phenotypes.py`

**Interfaces:**
- Produces: `gate_phenotype_profiles(features: pandas.DataFrame, stability_summary: dict, *, min_motion_observations: int = 3, reliable_threshold: float = 0.5) -> dict`

- [ ] **Step 1: Write failing tests** for singleton audit blocking, low-reliability descriptive gating, high-quality descriptive gating, and count conservation.
- [ ] **Step 2: Verify RED** with `pytest tests/test_confidence_gated_phenotypes.py -q`; expected failure because `ai4s_phenotype.confidence` does not exist.
- [ ] **Step 3: Implement `gate_phenotype_profiles`** in `src/ai4s_phenotype/confidence.py`.
- [ ] **Step 4: Verify GREEN** with `pytest tests/test_confidence_gated_phenotypes.py -q`.
- [ ] **Step 5: Run suite subset** with `pytest tests/test_confidence_gated_phenotypes.py tests/test_ctc_real_phenotype_stability.py -q`.

### Task 2: Reproducible artifact writer

**Files:**
- Create: `scripts/generate_confidence_gated_ctc_summary.py`
- Create: `docs/evidence/ctc/confidence_gated_phenotype_summary.json`
- Modify: `.github/workflows/ci.yml`
- Test: `tests/test_confidence_gated_phenotypes.py`

**Interfaces:**
- Consumes: `gate_phenotype_profiles(...) -> dict` from Task 1.
- Produces: CLI `python scripts/generate_confidence_gated_ctc_summary.py --features docs/evidence/ctc/derived_phenotype_features.csv --stability docs/evidence/ctc/stability_summary.json --output docs/evidence/ctc/confidence_gated_phenotype_summary.json`.

- [ ] **Step 1: Write failing CLI test** that builds temporary CSV/JSON inputs, runs the script, and checks the output schema.
- [ ] **Step 2: Verify RED** with `pytest tests/test_confidence_gated_phenotypes.py -q`; expected failure because the script does not exist.
- [ ] **Step 3: Implement script** with deterministic JSON output and no data download.
- [ ] **Step 4: Generate committed artifact** from existing evidence files.
- [ ] **Step 5: Add CI step** to regenerate the artifact and compare it with the committed JSON.
- [ ] **Step 6: Verify GREEN** via GitHub Actions CI.
