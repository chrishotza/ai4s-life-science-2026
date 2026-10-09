from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CRITICAL_VALUES = (
    "0.99135",
    "0.99322",
    "0.99228",
    "0.9451",
    "0.0439",
    "0.997315",
    "0.979091",
    "0.997207",
    "0.978239",
    "0.87490",
    "0.88810",
    "0.89180",
)

CRITICAL_VALUE_FILES = (
    ROOT / "docs" / "RESULTS.md",
    ROOT / "docs" / "KAGGLE_WRITEUP.md",
    ROOT / "docs" / "TECHNICAL_REPORT.md",
    ROOT / "docs" / "KAGGLE_SUMMARY.md",
)

REQUIRED_CAVEATS = (
    "reference centroids",
    "biological phenotype classification",
    "not official cell tracking challenge leaderboard scores",
)

CAVEAT_FILES = CRITICAL_VALUE_FILES

FORMAL_REQUIREMENTS = (
    (
        ROOT / "docs" / "KAGGLE_WRITEUP.md",
        (
            "## Submission Links",
            "**Category: End-to-End System**",
            "## Project Summary",
            "**Code repository:** https://github.com/chrishotza/ai4s-life-science-2026",
            "**Team (draft):** Chris Hotza",
            "organ-on-a-chip data remains untested",
            "Cellpose-SAM pilot then ran",
        ),
    ),
    (
        ROOT / "docs" / "TECHNICAL_REPORT.md",
        (
            "## 1.1 Team information",
            "**Team leader:** Chris Hotza",
            "## 10.2 Sources and licenses",
            "## 10.3 Exact reproduction recipe",
            "Data provenance and use conditions",
            "Development AI tooling:",
            "1 listed member",
            "organ-on-a-chip data",
            "track_integrity_score",
            "phenotype_assignment_quality",
            "phenotype_reliability_score",
        ),
    ),
    (
        ROOT / "docs" / "SUBMISSION_CHECKLIST.md",
        (
            "[x] Category declaration at start of Writeup",
            "[x] 200–300 word Project Summary in Writeup",
            "[x] Dataset/software provenance and licensing documented",
            "[x] Development AI-tool provenance disclosed",
            "[x] Cross-sequence image-to-tracking validation protocol",
            "[x] CTC GT/SEG image-segmentation validation protocol",
            "[x] Judge reader guide",
            "[x] Top-level MIT code license",
            "Project Summary word-count audit enforced",
            "reviewers can access without login",
            "1–5 members and one leader",
            "publicly viewable without login",
            "+0.5 bonus in Interpretability and Reliability",
            "The bonus is not claimed",
        ),
    ),
    (
        ROOT / "docs" / "RUBRIC_SCORECARD.md",
        (
            "Problem Importance & Potential Impact",
            "Technical Approach & Innovation",
            "Results & Validation",
            "Reproducibility & Implementation Quality",
            "Presentation Quality",
            "Official eligibility and domain boundary",
            "does not show that combination",
            "organ-on-a-chip data",
        ),
    ),
    (
        ROOT / "docs" / "CLAIM_EVIDENCE_MATRIX.md",
        (
            "CTC-CONFIDENCE-GATE",
            "confidence-gated interpretation permissions",
            "Explicitly blocked claims",
            "official CTC leaderboard result",
            "unsupervised phenotype clusters are validated biological cell states",
            "All 126 real CTC tracks are safe for motion-phenotype interpretation",
        ),
    ),
    (
        ROOT / "docs" / "DEMO_SCRIPT.md",
        (
            "association-isolation",
            "reference centroids",
            "biological phenotype score",
            "Synthetic method validation",
            "not a biological treatment result",
        ),
    ),
    (
        ROOT / "docs" / "ABLATION_AND_FAILURES.md",
        (
            "Generic percentile thresholding",
            "Classical DIC ridge segmentation",
            "Lightweight supervised pixel/region model",
            "No image-level method is promoted into the headline benchmark",
        ),
    ),
    (
        ROOT / "docs" / "JUDGE_READER_GUIDE.md",
        (
            "Biological question",
            "Protocol map",
            "Why CellposeSAM-v2 appears in the strongest path",
            "Phenotype claim boundary",
            "organ-on-a-chip transfer remains untested",
            "One-sentence reviewer takeaway",
        ),
    ),
    (
        ROOT / "README.md",
        (
            "Judge Reader Guide",
            "MIT License",
            "third-party imagery or external model weights",
        ),
    ),
    (
        ROOT / "LICENSE",
        (
            "MIT License",
            "Permission is hereby granted",
            "THE SOFTWARE IS PROVIDED \"AS IS\"",
        ),
    ),
    (
        ROOT / "src" / "ai4s_phenotype" / "cohort.py",
        (
            "CohortComparison",
            "bootstrap",
            "standardized_mean_difference",
        ),
    ),
    (
        ROOT / "scripts" / "benchmark_cohort_effect.py",
        (
            "cohort phenotype effect recovery",
            "not biological validation",
        ),
    ),
    (
        ROOT / "requirements-lock-py311.txt",
        (
            "numpy==2.4.6",
            "pandas==3.0.6",
        ),
    ),
    (
        ROOT / "requirements-dev-lock-py311.txt",
        (
            "pytest==9.1.1",
            "ruff==0.16.10",
        ),
    ),
)

SUMMARY_START = "## Project Summary"
SUMMARY_END = "## From cell tracking to dynamic phenotype"
SUMMARY_WORD_MIN = 200
SUMMARY_WORD_MAX = 300


def section_between(text: str, start_heading: str, end_heading: str) -> str:
    start = text.find(start_heading)
    if start == -1:
        raise ValueError(f"missing section start: {start_heading}")

    content_start = start + len(start_heading)
    end = text.find(end_heading, content_start)
    if end == -1:
        raise ValueError(f"missing section end: {end_heading}")

    return text[content_start:end].strip()


def word_count(text: str) -> int:
    return len(re.findall(r"\b[\wµ]+(?:[-'][\wµ]+)*\b", text))


def main() -> None:
    missing = []

    for path in CRITICAL_VALUE_FILES:
        text = path.read_text(encoding="utf-8")
        for value in CRITICAL_VALUES:
            if value not in text:
                missing.append(f"{path.relative_to(ROOT)} missing {value}")

    for path in CAVEAT_FILES:
        lowered = path.read_text(encoding="utf-8").lower()
        for required_phrase in REQUIRED_CAVEATS:
            if required_phrase not in lowered:
                missing.append(
                    f"{path.relative_to(ROOT)} missing required evidence boundary: {required_phrase}"
                )

    for path, phrases in FORMAL_REQUIREMENTS:
        text = path.read_text(encoding="utf-8")
        for phrase in phrases:
            if phrase.lower() not in text.lower():
                missing.append(
                    f"{path.relative_to(ROOT)} missing formal submission requirement: {phrase}"
                )

    writeup_text = (ROOT / "docs" / "KAGGLE_WRITEUP.md").read_text(encoding="utf-8")
    project_summary = section_between(writeup_text, SUMMARY_START, SUMMARY_END)
    project_summary_words = word_count(project_summary)
    if not SUMMARY_WORD_MIN <= project_summary_words <= SUMMARY_WORD_MAX:
        missing.append(
            "docs/KAGGLE_WRITEUP.md Project Summary has "
            f"{project_summary_words} words; expected "
            f"{SUMMARY_WORD_MIN}-{SUMMARY_WORD_MAX}"
        )

    if missing:
        raise SystemExit("\n".join(missing))

    print(
        "Submission claim and formal-requirements audit: PASS "
        f"(Project Summary: {project_summary_words} words)"
    )


if __name__ == "__main__":
    main()
