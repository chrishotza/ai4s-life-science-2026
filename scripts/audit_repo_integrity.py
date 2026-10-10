#!/usr/bin/env python3
"""Fail on broken local Markdown evidence/document links in the public AI4S repo.

All assets are resolved relative to their source Markdown file. External links
are deliberately out of scope: network access is neither needed nor implied.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
# Match standard Markdown inline links and linked images, not fenced code.
INLINE = re.compile(r"!?(?:\[[^\]]*\])\((<[^>]+>|[^)\s]+)(?:\s+['\"][^)]*['\"])?\)")
DEFINITION = re.compile(r"^\s{0,3}\[[^\]]+\]:\s*(<[^>]+>|\S+)", re.MULTILINE)
FENCES = re.compile(r"^\s*(?:\x60{3}|~{3})")


def remove_fenced_code(body: str) -> str:
    output = []
    inside = False
    for line in body.splitlines():
        if FENCES.match(line):
            inside = not inside
            output.append("")
        else:
            output.append("" if inside else line)
    return "\n".join(output)


def local_links(text: str) -> list[str]:
    prose = remove_fenced_code(text)
    links = [m.group(1) for m in INLINE.finditer(prose)]
    links += [m.group(1) for m in DEFINITION.finditer(prose)]
    return links


def scan_tree(root: Path) -> list[dict[str, str]]:
    """Broken relative links; reject references that escape checkout root."""
    base = root.resolve()
    problems = []
    documents = [base / "README.md", *sorted((base / "docs").rglob("*.md"))]
    for source in documents:
        if not source.is_file():
            continue
        for literal in local_links(source.read_text(encoding="utf-8")):
            url = literal.strip("<>").strip()
            parts = urlsplit(url)
            if parts.scheme or parts.netloc or not parts.path:
                continue
            # POSIX Markdown paths are portable even on Windows.
            path_text = unquote(parts.path)
            if path_text.startswith("/"):
                dest = (base / path_text.lstrip("/")).resolve()
            else:
                dest = (source.parent / path_text).resolve()
            if not dest.is_relative_to(base):
                problems.append({"source": str(source.relative_to(base)),
                                 "target": url, "error": "escapes repository root"})
            elif not dest.exists():
                problems.append({"source": str(source.relative_to(base)),
                                 "target": url, "error": "missing local file"})
    return problems


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    problems = scan_tree(args.root)
    if problems:
        for issue in problems:
            print(f"{issue['source']}: {issue['target']} -> {issue['error']}")
        raise SystemExit(f"{len(problems)} broken local Markdown references")
    print("All local README + docs Markdown references resolve to repository files")


if __name__ == "__main__":
    main()
