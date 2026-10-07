from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the externally supplied CTC TRA evaluator."
    )
    parser.add_argument("--directory", required=True)
    parser.add_argument("--sequence", required=True)
    parser.add_argument("--digits", type=int, default=3)
    args = parser.parse_args()

    executable = os.getenv("CTC_TRA_EXECUTABLE")
    if not executable:
        raise SystemExit(
            "Set CTC_TRA_EXECUTABLE to the official TRA evaluator executable. "
            "The repository intentionally does not redistribute the evaluator binary."
        )

    command = [
        executable,
        str(Path(args.directory).resolve()),
        args.sequence,
        str(args.digits),
    ]
    print("Running:", " ".join(command))
    subprocess.run(command, check=True)


if __name__ == "__main__":
    main()
