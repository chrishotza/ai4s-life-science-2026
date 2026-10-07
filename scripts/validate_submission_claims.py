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
)

FILES = (
    ROOT / "README.md",
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

FORMAL_REQUIREMENTS = {
    ROOT / "docs" / "KAGGLE_WRITEUP.md": (
        "## Submission Links",
        "**Category: End-to-End System**",
        "## Project Summary",
        "**Code repository:** https://github.com/chrishotza/ai4s-life-science-2026",
    ),
    ROOT / "docs" / "TECHNICAL_REPORT.md": (
        "## 1.1 Team information",
        "**Team leader:** Chris Hotza",
        "## 10.2 Sources and licenses",
        "## 10.3 Exact reproduction recipe",
        "Data provenance and use conditions",
        "Development AI tooling:",
    ),
    ROOT / "docs" / "SUBMISSION_CHECKLIST.md": (
        "[x] Category declaration at start of Writeup",
        "[x] 200–300 word Project Summary in Writeup",
        "[x] Dataset/software provenance and licensing documented",
        "[x] Development AI-tool provenance disclosed",
        "[x] Cross-sequence image-to-tracking validation protocol",
        "[x] CTC GT/SEG image-segmentation validation protocol",
    ),
    ROOT / "docs" / "RUBRIC_SCORECARD.md": (
        "Problem Importance & Potential Impact",
        "Technical Approach & Innovation",
        "Results & Validation",
        "Reproducibility & Implementation Quality",
        "Presentation Quality",
    ),
    ROOT / "docs" / "DEMO_SCRIPT.md": (
        "association-isolation",
        "reference centroids",
        "biological phenotype score",
    ),
    ROOT / "docs" / "TECHNICAL_REPORT.md": (
        "track_integrity_score",
        "phenotype_assignment_quality",
        "phenotype_reliability_score",
    ),
    ROOT / "docs" / "ABLATION_AND_FAILURES.md": (
        "Generic percentile thresholding",
        "Classical DIC ridge segmentation",
        "Lightweight supervised pixel/region model",
        "No image-level method is promoted into the headline benchmark",
    ),
    ROOT / "docs" / "DEMO_SCRIPT.md": (
        "Synthetic method validation",
        "not a biological treatment result",
    ),
    ROOT / "src" / "ai4s_phenotype" / "cohort.py": (
        "CohortComparison",
        "bootstrap",
        "standardized_mean_difference",
    ),
    ROOT / "scripts" / "benchmark_cohort_effect.py": (
        "cohort phenotype effect recovery",
        "not biological validation",
    ),
    ROOT / "requirements-lock-py311.txt": (
        "numpy==2.4.6",
        "pandas==3.0.6",
    ),
    ROOT / "requirements-dev-lock-py311.txt": (
        "pytest==9.1.1",
        "ruff==0.16.10",
    ),
}


def project_summary_word_count(text: str) -> int:
    match = re.search(
        r"## Project Summary\s+(.+?)(?=\n## |\Z)",
        text,
        flags=re.DOTALL,
    )
    if not match:
        return -1
    words = re.findall(r"\b[\wµ]+(?:[-'][\wµ]+)*\b", match.group(1))
    return len(words)


def main() -> None:
    missing = []

    for path in FILES:
        text = path.read_text(encoding="utf-8")
        for value in CRITICAL_VALUES:
            if value not in text:
                missing.append(f"{path.relative_to(ROOT)} missing {value}")

        lowered = text.lower()
        for required_phrase in REQUIRED_CAVEATS:
            if required_phrase not in lowered:
                missing.append(
                    f"{path.relative_to(ROOT)} missing required evidence boundary: {required_phrase}"
                )

    for path, phrases in FORMAL_REQUIREMENTS.items():
        text = path.read_text(encoding="utf-8")
        for phrase in phrases:
            if phrase.lower() not in text.lower():
                missing.append(
                    f"{path.relative_to(ROOT)} missing formal submission requirement: {phrase}"
                )

    writeup = ROOT / "docs" / "KAGGLE_WRITEUP.md"
    summary_words = project_summary_word_count(writeup.read_text(encoding="utf-8"))
    if not 200 <= summary_words <= 300:
        missing.append(
            f"docs/KAGGLE_WRITEUP.md Project Summary has {summary_words} words; expected 200-300"
        )

    if missing:
        raise SystemExit("\n".join(missing))

    print("Submission claim and formal-requirements audit: PASS")
