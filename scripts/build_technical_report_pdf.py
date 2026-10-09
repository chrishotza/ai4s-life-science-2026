"""Render the checked-in public AI4S technical report into a judge-readable PDF."""
from __future__ import annotations

import re
from pathlib import Path

import markdown
from pypdf import PdfReader
from weasyprint import HTML

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "TECHNICAL_REPORT.md"
DEST = ROOT / "dist" / "AI4S_Temporal_Cellular_Phenotype_Technical_Report.pdf"
GITHUB_DOCS = "https://github.com/chrishotza/ai4s-life-science-2026/blob/main/docs/"

def main() -> None:
    body = markdown.markdown(
        SOURCE.read_text(encoding="utf-8"),
        extensions=["tables", "fenced_code", "sane_lists", "toc"],
        output_format="html5",
    )
    # Markdown source links are repository relative. Make PDF links judge-clickable.
    body = re.sub(
        r'href="(?!https?://|mailto:|#)([^"]+)"',
        lambda m: f'href="{GITHUB_DOCS}{m.group(1)}"',
        body,
    )
    html = """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
    <style>
    @page { size: A4; margin: 17mm 17mm 19mm 17mm;
      @bottom-right { content: "AI4S Technical Report  |  " counter(page); color: #64748b; font-size: 8pt; } }
    html,body { font-family: "DejaVu Sans", sans-serif; color: #1c2938; }
    body { font-size: 9.35pt; line-height: 1.45; }
    h1,h2,h3,h4 { color: #07384d; break-after: avoid; }
    h1 { font-size: 20pt; border-bottom: 2pt solid #0e92a6; padding-bottom: 6pt; }
    h2 { font-size: 14pt; margin-top: 16pt; }
    h3 { font-size: 11pt; margin-top: 10pt; }
    p,li { orphans: 2; widows: 2; }
    a { color: #0b7790; word-wrap: break-word; }
    code,pre { font-family: "DejaVu Sans Mono", monospace; font-size: 8pt; }
    pre { white-space: pre-wrap; word-wrap: break-word; background: #f1f5f9; border-left: 3pt solid #0e92a6; padding: 8pt; }
    table { border-collapse: collapse; width: 100%; margin: 9pt 0; font-size: 8pt; table-layout: fixed; }
    thead { display: table-header-group; }
    tr { break-inside: avoid; }
    td,th { border: .5pt solid #ccdbe3; padding: 5pt; overflow-wrap: break-word; }
    th { background: #e8f3f6; color: #083d53; }
    img { max-width: 100%; height: auto; }
    blockquote { border-left: 3pt solid #0e92a6; padding-left: 12pt; color: #37526a; }
    </style></head><body>""" + body + "</body></html>"
    DEST.parent.mkdir(parents=True, exist_ok=True)
    HTML(string=html, base_url=str(SOURCE.parent)).write_pdf(DEST)
    pages = len(PdfReader(str(DEST)).pages)
    size = DEST.stat().st_size
    assert pages >= 7 and size >= 50000, (pages, size)
    print(f"VALID REPORT: {pages} A4 pages, {size:,} bytes, {DEST}")

if __name__ == "__main__":
    main()
