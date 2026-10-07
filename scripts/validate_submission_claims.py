from __future__ import annotations

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
    "not official Cell Tracking Challenge leaderboard scores",
)

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

    if missing:
        raise SystemExit("\n".join(missing))

    print("Submission claim audit: PASS")


if __name__ == "__main__":
    main()
