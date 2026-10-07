from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CRITICAL_VALUES = (
    "0.99135",
    "0.99322",
    "0.99228",
    "0.9451",
    "0.0439",
)

FILES = (
    ROOT / "README.md",
    ROOT / "docs" / "RESULTS.md",
    ROOT / "docs" / "KAGGLE_WRITEUP.md",
    ROOT / "docs" / "TECHNICAL_REPORT.md",
)

REQUIRED_CAVEATS = (
    "reference centroids",
    "not",
)

def main() -> None:
    missing = []
    for path in FILES:
        text = path.read_text(encoding="utf-8")
        for value in CRITICAL_VALUES:
            if value not in text:
                missing.append(f"{path.relative_to(ROOT)} missing {value}")
        lowered = text.lower()
        if "reference centroids" not in lowered:
            missing.append(f"{path.relative_to(ROOT)} missing reference-centroid evidence boundary")

    for path in FILES:
        text = path.read_text(encoding="utf-8").lower()
        if "biological phenotype classification" not in text and "biological phenotype" not in text:
            missing.append(f"{path.relative_to(ROOT)} missing biological-phenotype limitation")

    if missing:
        raise SystemExit("\n".join(missing))

    print("Submission claim audit: PASS")


if __name__ == "__main__":
    main()
