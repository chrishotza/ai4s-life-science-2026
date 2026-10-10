"""Repository evidence-link integrity: prevent broken reviewer navigation."""
from __future__ import annotations

from pathlib import Path

from scripts.audit_repo_integrity import (
    ROOT, local_links, remove_fenced_code, scan_tree,
)


def test_real_project_document_links_resolve():
    assert scan_tree(ROOT) == []


def test_markdown_scanner_skips_code_blocks_and_external_urls():
    text = (
        "[valid](real.txt)\n"
        "[web](https://example.com/paper)\n"
        "```bash\n"
        "[fake](never-created.csv)\n"
        "```\n"
    )
    assert "never-created.csv" not in remove_fenced_code(text)
    assert local_links(text) == ["real.txt", "https://example.com/paper"]


def test_report_missing_local_source_and_reject_escape(tmp_path: Path):
    (tmp_path / "README.md").write_text(
        "[missing](other.csv)\n[escape](../outside.txt)\n"
    )
    issues = scan_tree(tmp_path)
    assert len(issues) == 2
    assert {row["error"] for row in issues} == {
        "missing local file", "escapes repository root",
    }


def test_real_local_link_is_accepted(tmp_path: Path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "README.md").write_text("[proof](docs/proof.csv)")
    (tmp_path / "docs" / "proof.csv").write_text("a,b\n1,2\n")
    assert scan_tree(tmp_path) == []
