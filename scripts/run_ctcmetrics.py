from __future__ import annotations

import argparse
import json
import subprocess
from importlib.metadata import version
from pathlib import Path


def git_sha(root: Path) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return completed.stdout.strip() or None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate a CTC result with the CTC-maintained py-ctcmetrics implementation."
    )
    parser.add_argument("--gt", required=True, help="CTC sequence GT directory.")
    parser.add_argument("--res", required=True, help="CTC sequence result directory.")
    parser.add_argument("--sequence", required=True, choices=["01", "02"])
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args()

    try:
        from ctc_metrics import evaluate_sequence, validate_sequence
    except ImportError as exc:
        raise SystemExit(
            "py-ctcmetrics is not installed; run `pip install -r requirements-ctc.txt`."
        ) from exc

    gt = str(Path(args.gt).resolve())
    res = str(Path(args.res).resolve())
    validation = validate_sequence(res, threads=args.threads)
    if not validation.get("Valid", False):
        raise SystemExit(f"CTC result validation failed: {validation}")

    metrics = evaluate_sequence(
        res,
        gt,
        metrics=["TRA", "LNK"],
        threads=args.threads,
    )

    root = Path(args.repository_root).resolve()
    payload = {
        "sequence": args.sequence,
        "gt": gt,
        "res": res,
        "metrics": {
            "TRA": metrics.get("TRA"),
            "LNK": metrics.get("LNK"),
            "AOGM": metrics.get("AOGM"),
            "AOGM_0": metrics.get("AOGM_0"),
        },
        "validation": validation,
        "evaluator": {
            "package": "py-ctcmetrics",
            "version": version("py-ctcmetrics"),
        },
        "repository_commit": git_sha(root),
        "protocol": "reference-geometry association isolation; oracle lineage when frame-compatible",
    }

    output = Path(args.output_json)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
