"""
doc_context.py

Single access point for everything the documentation quotes:

* real analytical results (src.analysis.run_full_analysis on the cleaned CSV),
* verbatim source-code snippets (extracted from the project's own files),
* figure / table numbering and the registry used for the list of figures.

Nothing is typed in by hand: every number in the report is read from the
project's data or output files, so the document cannot drift from the code.
"""

from __future__ import annotations

import ast
import csv
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import config  # noqa: E402
from src import analysis  # noqa: E402

logging.disable(logging.CRITICAL)  # keep the build output quiet


def money(value: float, decimals: int = 2) -> str:
    return f"\u20B9{value:,.{decimals}f}"


def whole(value: float) -> str:
    return f"{int(round(value)):,}"


def pct(value: float, decimals: int = 1) -> str:
    return f"{value:.{decimals}f}%"


@dataclass
class DocContext:
    raw: pd.DataFrame
    df: pd.DataFrame
    results: dict
    customers_dim: pd.DataFrame
    products_dim: pd.DataFrame
    reconciliation: pd.DataFrame
    test_lines: list[str]
    figure_count: int = 0
    table_count: int = 0
    figures: list[tuple[int, str]] = field(default_factory=list)
    screenshot_dir: Path = PROJECT_ROOT / "powerbi" / "screenshots"

    # ----- numbering ------------------------------------------------------
    def next_figure(self, title: str) -> str:
        import docx_helpers
        if docx_helpers._SKIPPING[0]:          # section dropped from the compact edition: do not consume a number
            return f"Figure 0: {title}"
        self.figure_count += 1
        self.figures.append((self.figure_count, title))
        return f"Figure {self.figure_count}: {title}"

    def next_table(self, title: str) -> str:
        import docx_helpers
        if docx_helpers._SKIPPING[0]:
            return f"Table 0: {title}"
        self.table_count += 1
        return f"Table {self.table_count}: {title}"

    # ----- chart / asset paths --------------------------------------------
    @staticmethod
    def chart(name: str) -> Path:
        return config.CHARTS_DIR / name

    @staticmethod
    def diagram(name: str) -> Path:
        return PROJECT_ROOT / "docs" / "assets" / "diagrams" / name

    def screenshot(self, name: str) -> Path | None:
        path = self.screenshot_dir / name
        return path if path.exists() else None

    # ----- verbatim code ----------------------------------------------------
    @staticmethod
    def function_source(relative_file: str, name: str, with_docstring: bool = True) -> str:
        """Return the exact source of a top-level function or class."""
        path = PROJECT_ROOT / relative_file
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        tree = ast.parse(text)
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name == name:
                start = node.lineno - 1
                if node.decorator_list:
                    start = node.decorator_list[0].lineno - 1
                block = lines[start:node.end_lineno]
                if not with_docstring and ast.get_docstring(node):
                    doc_end = node.body[0].end_lineno - start
                    doc_start = node.body[0].lineno - start
                    block = block[:doc_start] + block[doc_end:]
                return "\n".join(block)
        raise KeyError(f"{name} not found in {relative_file}")

    @staticmethod
    def lines_between(relative_file: str, start_marker: str, end_marker: str, include_end: bool = True) -> str:
        """Exact lines from the first line containing ``start_marker`` to the
        next line containing ``end_marker`` (used for excerpts)."""
        lines = (PROJECT_ROOT / relative_file).read_text(encoding="utf-8").splitlines()
        start = next(i for i, line in enumerate(lines) if start_marker in line)
        end = next(i for i in range(start, len(lines)) if end_marker in lines[i])
        return "\n".join(lines[start:end + (1 if include_end else 0)])

    @staticmethod
    def text_file(relative_file: str) -> str:
        return (PROJECT_ROOT / relative_file).read_text(encoding="utf-8")

    def dax_measure(self, name: str) -> str:
        """Exact text of one measure block from powerbi/dax/measures.dax."""
        lines = self.text_file("powerbi/dax/measures.dax").splitlines()
        start = next(i for i, line in enumerate(lines) if line.startswith(name + " ="))
        end = start + 1
        while end < len(lines) and (lines[end].startswith(" ") or lines[end].startswith("\t")):
            end += 1
        return "\n".join(lines[start:end])


def build_context() -> DocContext:
    raw = pd.read_csv(config.RAW_SALES_DATA_PATH)
    df = pd.read_csv(config.CLEANED_SALES_DATA_PATH, parse_dates=["Order_Date"])
    results = analysis.run_full_analysis(df)
    customers_dim = pd.read_csv(config.CUSTOMER_SEGMENTS_PATH)
    products_dim = pd.read_csv(config.PRODUCT_CLASSIFICATION_PATH)
    reconciliation = pd.read_csv(PROJECT_ROOT / "powerbi" / "verification" / "reconciliation_results.csv")
    test_file = config.OUTPUTS_DIR / "results" / "test_run_summary.txt"
    test_lines = test_file.read_text(encoding="utf-8").splitlines() if test_file.exists() else []
    return DocContext(raw, df, results, customers_dim, products_dim, reconciliation, test_lines)


def read_data_quality_rows() -> list[list]:
    """Rows of the generated data-quality workbook (header row excluded)."""
    import openpyxl

    sheet = openpyxl.load_workbook(config.DATA_QUALITY_REPORT_PATH, data_only=True).worksheets[0]
    rows = [list(row) for row in sheet.iter_rows(values_only=True)]
    start = next(i for i, row in enumerate(rows) if row and row[0] == "Check") + 1
    return [row for row in rows[start:] if row and row[0]]


def read_excel_sheet_shapes() -> list[tuple[str, int, int]]:
    import openpyxl

    workbook = openpyxl.load_workbook(config.EXCEL_REPORT_PATH)
    return [(sheet.title, sheet.max_row, sheet.max_column) for sheet in workbook]
