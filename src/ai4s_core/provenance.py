from __future__ import annotations

import os
import platform
import sys


def runtime_metadata() -> dict[str, str]:
    return {
        "commit_sha": os.getenv("GITHUB_SHA", "unknown"),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "implementation": sys.implementation.name,
    }
