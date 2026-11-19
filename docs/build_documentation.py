"""
build_documentation.py

Builds the SmartMart project documentation (DOCX, and PDF when LibreOffice is
available) from the project's real data and source files.

    pip install -r requirements-docs.txt
    python main.py                       # outputs must exist
    python docs/make_diagrams.py         # diagrams and distribution chart
    python docs/build_documentation.py

* Real Power BI screenshots in powerbi/screenshots/ (01_..04_*.png) are inserted automatically.
  Missing ones are replaced by clearly-marked placeholders.
* Output: documentation/SmartMart_Final_Report.docx and .pdf
* The table of contents and list of figures carry page numbers measured from the
  rendered PDF (the build repeats until they are stable). In Word you can still
  right-click the TOC and choose Update Field.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

DOCS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(DOCS_DIR))

import docx_helpers  # noqa: E402
from docx_helpers import add_heading, new_document  # noqa: E402
from doc_context import build_context  # noqa: E402
import chapters_a as a  # noqa: E402
import chapters_b as b  # noqa: E402
import chapters_c as c  # noqa: E402
import chapters_d as d  # noqa: E402

# Compact edition: sections whose content is covered elsewhere (full code is in the repository).
docx_helpers.SKIP_HEADINGS.update({
    "9.3 Code behind the report", "11.4 Implementation", "12.3 Implementation", "13.4 Implementation",
    "14.4 Implementation", "15.2 Implementation", "16.3 Implementation",
    "17.3 Pipeline orchestration (main.py)", "6.2 Reference data in the code", "7.3 Loading the file", "8.5 The orchestrating function",
    "20.3 Growth and contribution measures", "20.5 Pareto and ABC measures", "3.2 Skills developed", "19.2 Why dimension tables are exported", "26.2 Discussion", "4.3 Data flow", "7.2 Custom exceptions and column validation", "10.3 Executive dashboard (Python)", "13.3 City-level revenue", "14.2 Top customers", "18.3 Insight generation", "19.5 Power Query (M)",
    "20.3 Customer measures", "22.4 Slicer scenarios", "25.3 Example tests", "26.3 What each result is based on", "4.4 Project structure", "1.4 Source of requirements", "17.4 Shared utilities", "17.5 Visualisation module",
})

OUTPUT_DIR = DOCS_DIR.parent / "documentation"
OUTPUT_DIR.mkdir(exist_ok=True)
OUTPUT_DOCX = OUTPUT_DIR / "SmartMart_Final_Report.docx"
OUTPUT_PDF = OUTPUT_DIR / "SmartMart_Final_Report.pdf"
LOGO = DOCS_DIR / "assets" / "cronus_logo.png"
MAX_PASSES = 5


def assemble(toc_pages: dict[str, int], figure_pages: dict[int, int]):
    """Build the whole document once. Returns (document, h1_titles, figure registry)."""
    ctx = build_context()
    document = new_document(LOGO, a.PROJECT_TITLE, "Cronus Consultants  |  Python with Data Analytics  |  Team A")

    # Chapters are written first into a scratch list of callables so the figure
    # registry is complete before the list of figures is laid out.
    probe_ctx = build_context()
    probe = new_document(LOGO, a.PROJECT_TITLE, "")
    chapter_steps = [
        a.ch1_introduction, a.ch2_scope, a.ch3_technology, a.ch4_architecture, a.ch5_dataset, a.ch6_generation,
        a.ch7_loading, a.ch8_cleaning, a.ch9_quality, b.ch10_eda_kpi, b.ch11_products, b.ch12_monthly,
        b.ch13_regional, b.ch14_customers, b.ch15_payment, b.ch16_pareto, b.ch17_python, b.ch18_excel,
        c.ch19_powerbi_integration, c.ch20_dax, c.ch21_dashboard, c.ch22_reconciliation, d.ch23_streamlit, c.ch23_insights,
        c.ch24_testing, c.ch25_results, c.ch26_limitations, c.ch27_future_conclusion, c.ch28_references,
        c.appendix_b,
    ]
    for step in chapter_steps:
        step(probe, probe_ctx)
    titles = ["Acknowledgement", "Abstract"] + [p.text for p in probe.paragraphs if p.style.name == "Heading 1"]
    titles = list(dict.fromkeys(titles))

    # ---- real document ----------------------------------------------------
    a.cover_page(document, ctx)
    a.acknowledgement(document, ctx)
    a.abstract(document, ctx)
    entries = [(1, title, toc_pages.get(title, "")) for title in titles]
    a.table_of_contents(document, entries)
    ctx.figures = list(probe_ctx.figures)   # registry from the probe pass
    a.list_of_figures(document, ctx, figure_pages)
    ctx.figures = []                        # numbering restarts for the real chapters
    ctx.figure_count = 0
    ctx.table_count = 0
    for step in chapter_steps:
        step(document, ctx)
    return document, titles, list(probe_ctx.figures)


def find_soffice() -> list[str] | None:
    skill_script = Path("/mnt/skills/public/docx/scripts/office/soffice.py")
    if skill_script.exists():
        return [sys.executable, str(skill_script)]
    for name in ("soffice", "libreoffice"):
        if shutil.which(name):
            return [name]
    return None


def convert_to_pdf(docx_path: Path) -> bool:
    command = find_soffice()
    if command is None:
        print("LibreOffice not found - DOCX built, PDF skipped.")
        return False
    subprocess.run(command + ["--headless", "--convert-to", "pdf", "--outdir", str(docx_path.parent), str(docx_path)],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return docx_path.with_suffix(".pdf").exists()


def pdf_pages(pdf_path: Path) -> list[list[str]]:
    if not shutil.which("pdftotext"):
        return []
    text = subprocess.run(["pdftotext", "-layout", str(pdf_path), "-"], capture_output=True, text=True, check=True).stdout
    return [[line.strip() for line in page.splitlines() if line.strip()] for page in text.split("\f")]


def measure(pages: list[list[str]], titles: list[str], figures: list[tuple[int, str]]):
    leader = re.compile(r"\.{5,}")
    toc, fig = {}, {}
    for title in titles:
        key = title[:34]
        for index, lines in enumerate(pages, start=1):
            if any(line.startswith(key) and not leader.search(line) for line in lines):
                toc[title] = index
                break
    first_chapter = next((page for title, page in toc.items() if title.startswith("1.")), 1)
    for number, _ in figures:
        label = f"Figure {number}:"
        for index, lines in enumerate(pages, start=1):
            if index < first_chapter:
                continue
            if any(line.startswith(label) and not leader.search(line) for line in lines):
                fig[number] = index
                break
    return toc, fig


def main() -> None:
    toc_pages: dict[str, int] = {}
    figure_pages: dict[int, int] = {}
    for attempt in range(1, MAX_PASSES + 1):
        document, titles, figures = assemble(toc_pages, figure_pages)
        document.save(OUTPUT_DOCX)
        if not convert_to_pdf(OUTPUT_DOCX):
            return
        pages = pdf_pages(OUTPUT_PDF)
        if not pages:
            print("pdftotext not found - page numbers in the TOC were not measured.")
            return
        new_toc, new_fig = measure(pages, titles, figures)
        print(f"Pass {attempt}: {len(pages) - 1 if not pages[-1] else len(pages)} pages, "
              f"{len(new_toc)}/{len(titles)} chapters located, {len(new_fig)}/{len(figures)} figures located")
        if new_toc == toc_pages and new_fig == figure_pages:
            break
        toc_pages, figure_pages = new_toc, new_fig
    print(f"Written: {OUTPUT_DOCX.name}, {OUTPUT_PDF.name}")


if __name__ == "__main__":
    main()
