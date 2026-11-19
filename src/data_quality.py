"""
data_quality.py

Produces a dedicated data-quality report comparing the raw dataset
("Before") against the cleaned dataset ("After"). Every value is
calculated dynamically from the two DataFrames passed in - nothing is
hard-coded.

Output: outputs/reports/data_quality_report.xlsx
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from config import DATA_QUALITY_REPORT_PATH
from src.utils import ensure_directories, get_logger

logger = get_logger(__name__)

HEADER_FILL = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
HEADER_FONT = Font(color="FFFFFF", bold=True, size=11)
TITLE_FONT = Font(bold=True, size=14, color="1F4E78")


def _count_invalid_numeric(series: pd.Series) -> int:
    """Count values that are missing, non-numeric, or non-positive."""
    numeric = pd.to_numeric(series, errors="coerce")
    return int((numeric.isna() | (numeric <= 0)).sum())


def _count_missing(dataframe: pd.DataFrame, column: str) -> int:
    if column not in dataframe.columns:
        return 0
    return int(dataframe[column].isna().sum())


def _count_invalid_sales(dataframe: pd.DataFrame) -> int:
    """Rows where Sales does not equal Quantity * Unit_Price within a
    small tolerance, considering only rows where both inputs are
    numeric and present."""
    if not {"Quantity", "Unit_Price", "Sales"}.issubset(dataframe.columns):
        return 0
    quantity = pd.to_numeric(dataframe["Quantity"], errors="coerce")
    price = pd.to_numeric(dataframe["Unit_Price"], errors="coerce")
    sales = pd.to_numeric(dataframe["Sales"], errors="coerce")
    valid_inputs = quantity.notna() & price.notna() & sales.notna()
    expected = quantity * price
    mismatch = valid_inputs & ((expected - sales).abs() > 0.01)
    return int(mismatch.sum())


def build_data_quality_checks(raw_df: pd.DataFrame, cleaned_df: pd.DataFrame) -> pd.DataFrame:
    """Build the Before/After data-quality comparison table.

    Every number is computed directly from ``raw_df`` (Before) and
    ``cleaned_df`` (After); nothing is a fixed constant.
    """
    checks = [
        ("Total rows", len(raw_df), len(cleaned_df)),
        ("Missing Unit_Price", _count_missing(raw_df, "Unit_Price"), _count_missing(cleaned_df, "Unit_Price")),
        ("Missing City", _count_missing(raw_df, "City"), _count_missing(cleaned_df, "City")),
        ("Missing Payment_Mode", _count_missing(raw_df, "Payment_Mode"), _count_missing(cleaned_df, "Payment_Mode")),
        ("Duplicate rows", int(raw_df.duplicated().sum()), int(cleaned_df.duplicated().sum())),
        ("Invalid Quantity", _count_invalid_numeric(raw_df.get("Quantity", pd.Series(dtype=float))),
         _count_invalid_numeric(cleaned_df.get("Quantity", pd.Series(dtype=float)))),
        ("Invalid Unit_Price", _count_invalid_numeric(raw_df.get("Unit_Price", pd.Series(dtype=float))),
         _count_invalid_numeric(cleaned_df.get("Unit_Price", pd.Series(dtype=float)))),
        ("Invalid Sales (Sales != Quantity x Unit_Price)", _count_invalid_sales(raw_df), _count_invalid_sales(cleaned_df)),
    ]

    table = pd.DataFrame(checks, columns=["Check", "Before", "After"])
    table["Rows_Fixed_Or_Removed"] = table["Before"] - table["After"]
    return table


def save_data_quality_report(raw_df: pd.DataFrame, cleaned_df: pd.DataFrame,
                              output_path: Path = DATA_QUALITY_REPORT_PATH) -> Path:
    """Build the data-quality checks table and save it as a formatted
    Excel workbook."""
    logger.info("Building data quality report...")
    table = build_data_quality_checks(raw_df, cleaned_df)

    workbook = Workbook()
    ws = workbook.active
    ws.title = "Data Quality"

    ws["A1"] = "SmartMart Sales - Data Quality Report"
    ws["A1"].font = TITLE_FONT
    ws.merge_cells("A1:D1")
    ws["A2"] = "Before (raw dataset) vs After (cleaned dataset) comparison. All values are calculated dynamically."
    ws.merge_cells("A2:D2")
    ws["A2"].font = Font(italic=True, size=9, color="666666")

    start_row = 4
    for col_index, column_name in enumerate(table.columns, start=1):
        cell = ws.cell(row=start_row, column=col_index, value=str(column_name).replace("_", " "))
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center")

    for row_offset, (_, row) in enumerate(table.iterrows(), start=1):
        for col_index, column_name in enumerate(table.columns, start=1):
            ws.cell(row=start_row + row_offset, column=col_index, value=row[column_name])

    for col_index, column_name in enumerate(table.columns, start=1):
        max_length = max([len(str(column_name))] + [len(str(v)) for v in table[column_name].tolist()])
        ws.column_dimensions[get_column_letter(col_index)].width = min(max(max_length + 3, 14), 45)

    ws.freeze_panes = f"A{start_row + 1}"

    ensure_directories(output_path.parent)
    workbook.save(output_path)
    logger.info("Data quality report saved to %s", output_path)
    return output_path
