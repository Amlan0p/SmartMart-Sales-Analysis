"""
excel_report.py

Builds a professionally formatted Excel workbook (using OpenPyXL) from
the analysis results dictionary produced by
``analysis.run_full_analysis``. All values are written programmatically
from calculated results - nothing is typed in manually.

Sheets produced:
    - Summary
    - Product Analysis
    - Category Analysis
    - Monthly Analysis
    - Regional Analysis
    - Customer Analysis
    - Payment Analysis
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from config import COMPANY_NAME, EXCEL_REPORT_PATH, PROJECT_NAME
from src.utils import ensure_directories, get_logger

logger = get_logger(__name__)

HEADER_FILL = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
HEADER_FONT = Font(color="FFFFFF", bold=True, size=11)
TITLE_FONT = Font(bold=True, size=14, color="1F4E78")
LABEL_FONT = Font(bold=True, size=11)
THIN_BORDER = Border(
    left=Side(style="thin", color="D9D9D9"),
    right=Side(style="thin", color="D9D9D9"),
    top=Side(style="thin", color="D9D9D9"),
    bottom=Side(style="thin", color="D9D9D9"),
)

CURRENCY_COLUMNS = {"Revenue", "Total_Revenue", "Total Revenue", "Average_Order_Value",
                    "Average Order Value", "Average Selling Price", "Total_Spending",
                    "Average_Spending_Per_Order", "Cumulative_Revenue", "Monetary"}

PERCENT_COLUMNS = {"Revenue_Percentage", "Revenue_Share_Percent", "Order_Share_Percent",
                    "Cumulative_Revenue_Percent", "Revenue_Growth_Percent",
                    "Order_Growth_Percent", "Quantity_Growth_Percent", "Revenue_Percent"}


def _write_dataframe(
    worksheet: Worksheet,
    dataframe: pd.DataFrame,
    start_row: int = 1,
    freeze: bool = True,
    autofilter: bool = True,
) -> int:
    """Write a DataFrame to a worksheet starting at ``start_row`` with
    header styling, currency formatting for money columns, sensible
    column widths, a frozen header row and an autofilter.

    Returns the row number immediately after the written table.
    """
    columns = list(dataframe.columns)

    for col_index, column_name in enumerate(columns, start=1):
        cell = worksheet.cell(row=start_row, column=col_index, value=str(column_name).replace("_", " "))
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = THIN_BORDER

    for row_offset, (_, row) in enumerate(dataframe.iterrows(), start=1):
        for col_index, column_name in enumerate(columns, start=1):
            value = row[column_name]
            if isinstance(value, pd.Timestamp):
                value = value.to_pydatetime()
            cell = worksheet.cell(row=start_row + row_offset, column=col_index, value=value)
            cell.border = THIN_BORDER
            if column_name in CURRENCY_COLUMNS:
                cell.number_format = '"₹"#,##0.00'
            elif column_name in PERCENT_COLUMNS:
                cell.number_format = '0.00"%"'
            elif isinstance(value, float):
                cell.number_format = "#,##0.00"

    for col_index, column_name in enumerate(columns, start=1):
        max_length = max(
            [len(str(column_name))] + [len(str(v)) for v in dataframe[column_name].astype(str).tolist()]
        )
        worksheet.column_dimensions[get_column_letter(col_index)].width = min(max(max_length + 3, 12), 40)

    end_row = start_row + len(dataframe)

    if autofilter and len(dataframe) > 0:
        worksheet.auto_filter.ref = (
            f"A{start_row}:{get_column_letter(len(columns))}{end_row}"
        )

    if freeze:
        worksheet.freeze_panes = worksheet.cell(row=start_row + 1, column=1)

    return end_row + 1


def _write_summary_sheet(workbook: Workbook, summary: dict, findings: list[str] | None = None) -> None:
    """Write the 'Summary' sheet as an executive dashboard: a KPI
    section followed by the key business findings derived from the
    analysis (kept in sync with the plain-text insights report)."""
    ws = workbook.active
    ws.title = "Summary"

    ws["A1"] = PROJECT_NAME
    ws["A1"].font = TITLE_FONT
    ws.merge_cells("A1:C1")

    ws["A2"] = f"{COMPANY_NAME} - Executive Dashboard"
    ws["A2"].font = Font(italic=True, size=10, color="666666")
    ws.merge_cells("A2:C2")

    start_row = 4
    ws.cell(row=start_row, column=1, value="Key Performance Indicator").fill = HEADER_FILL
    ws.cell(row=start_row, column=1).font = HEADER_FONT
    ws.cell(row=start_row, column=2, value="Value").fill = HEADER_FILL
    ws.cell(row=start_row, column=2).font = HEADER_FONT

    for offset, (metric, value) in enumerate(summary.items(), start=1):
        row = start_row + offset
        ws.cell(row=row, column=1, value=metric).font = LABEL_FONT
        cell = ws.cell(row=row, column=2, value=value)
        if "Revenue" in metric or "Value" in metric or "Price" in metric:
            cell.number_format = '"₹"#,##0.00'
        else:
            cell.number_format = "#,##0"
        ws.cell(row=row, column=1).border = THIN_BORDER
        cell.border = THIN_BORDER

    ws.column_dimensions["A"].width = 46
    ws.column_dimensions["B"].width = 22
    ws.freeze_panes = "A5"

    findings_start = start_row + len(summary) + 3
    ws.cell(row=findings_start, column=1, value="Key Business Findings").font = TITLE_FONT
    ws.merge_cells(start_row=findings_start, start_column=1, end_row=findings_start, end_column=3)

    for offset, finding in enumerate(findings or [], start=1):
        row = findings_start + offset
        ws.cell(row=row, column=1, value=f"{offset}. {finding}").alignment = Alignment(
            wrap_text=True, vertical="top"
        )
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=3)
        ws.row_dimensions[row].height = 30


def _write_product_sheet(workbook: Workbook, products: dict) -> None:
    ws = workbook.create_sheet("Product Analysis")
    ws["A1"] = "All Products - Ranked by Revenue"
    ws["A1"].font = LABEL_FONT
    next_row = _write_dataframe(ws, products["all_products"], start_row=3)


def _write_category_sheet(workbook: Workbook, categories: pd.DataFrame) -> None:
    ws = workbook.create_sheet("Category Analysis")
    ws["A1"] = "Category Performance"
    ws["A1"].font = LABEL_FONT
    _write_dataframe(ws, categories, start_row=3)


def _write_monthly_sheet(workbook: Workbook, monthly: dict) -> None:
    ws = workbook.create_sheet("Monthly Analysis")
    ws["A1"] = "Monthly Sales Trend"
    ws["A1"].font = LABEL_FONT
    table = monthly["monthly_table"][["Period", "Orders", "Quantity", "Revenue", "Average_Order_Value"]]
    _write_dataframe(ws, table, start_row=3)

    info_row = 4 + len(table)
    ws.cell(row=info_row, column=1, value="Peak Sales Month:").font = LABEL_FONT
    ws.cell(row=info_row, column=2, value=monthly["peak_month"])
    ws.cell(row=info_row + 1, column=1, value="Lowest Sales Month:").font = LABEL_FONT
    ws.cell(row=info_row + 1, column=2, value=monthly["lowest_month"])


def _write_regional_sheet(workbook: Workbook, regions: pd.DataFrame) -> None:
    ws = workbook.create_sheet("Regional Analysis")
    ws["A1"] = "Regional Performance"
    ws["A1"].font = LABEL_FONT
    _write_dataframe(ws, regions, start_row=3)


def _write_customer_sheet(workbook: Workbook, customers: dict) -> None:
    ws = workbook.create_sheet("Customer Analysis")
    ws["A1"] = "Top Customers by Spending"
    ws["A1"].font = LABEL_FONT
    next_row = _write_dataframe(ws, customers["top_customers"], start_row=3)

    summary_row = next_row + 1
    ws.cell(row=summary_row, column=1, value="Repeat Customers:").font = LABEL_FONT
    ws.cell(row=summary_row, column=2, value=customers["repeat_customers"])
    ws.cell(row=summary_row + 1, column=1, value="One-time Customers:").font = LABEL_FONT
    ws.cell(row=summary_row + 1, column=2, value=customers["one_time_customers"])
    ws.cell(row=summary_row + 2, column=1, value="Repeat Customer Rate (%):").font = LABEL_FONT
    ws.cell(row=summary_row + 2, column=2, value=customers["repeat_customer_rate"])


def _write_payment_sheet(workbook: Workbook, payments: pd.DataFrame) -> None:
    ws = workbook.create_sheet("Payment Analysis")
    ws["A1"] = "Payment Method Breakdown"
    ws["A1"].font = LABEL_FONT
    _write_dataframe(ws, payments, start_row=3)


def _write_segmentation_sheet(workbook: Workbook, segmentation: dict) -> None:
    ws = workbook.create_sheet("Customer Segmentation")
    ws["A1"] = "Customer Segment Summary (RFM-style, rule-based)"
    ws["A1"].font = LABEL_FONT
    next_row = _write_dataframe(ws, segmentation["segment_summary"], start_row=3)

    ws.cell(row=next_row + 1, column=1, value="Segmentation Rules:").font = LABEL_FONT
    ws.cell(row=next_row + 2, column=1, value=segmentation["segmentation_rules"]).alignment = Alignment(
        wrap_text=True, vertical="top"
    )
    ws.merge_cells(start_row=next_row + 2, start_column=1, end_row=next_row + 2, end_column=4)
    ws.row_dimensions[next_row + 2].height = 60


def _write_pareto_sheet(workbook: Workbook, pareto: dict) -> None:
    ws = workbook.create_sheet("Pareto & ABC Analysis")
    ws["A1"] = "Product Revenue Concentration (Pareto Analysis)"
    ws["A1"].font = LABEL_FONT
    ws["A2"] = (
        f"{pareto['products_for_80_percent_revenue']} of {pareto['total_products']} products "
        f"({pareto['percent_of_products_for_80_percent_revenue']:.2f}%) generate approximately 80% of total revenue."
    )
    ws.merge_cells("A2:E2")
    next_row = _write_dataframe(ws, pareto["pareto_table"], start_row=4)

    abc_row = next_row + 2
    ws.cell(row=abc_row, column=1, value="ABC Classification Summary").font = LABEL_FONT
    ws.cell(row=abc_row + 1, column=1, value=pareto["abc_thresholds_note"]).alignment = Alignment(
        wrap_text=True, vertical="top"
    )
    ws.merge_cells(start_row=abc_row + 1, start_column=1, end_row=abc_row + 1, end_column=5)
    ws.row_dimensions[abc_row + 1].height = 45
    _write_dataframe(ws, pareto["abc_summary"], start_row=abc_row + 3, freeze=False, autofilter=False)


def _write_yoy_sheet(workbook: Workbook, yoy: dict) -> None:
    ws = workbook.create_sheet("Year-over-Year Analysis")
    if not yoy.get("has_comparable_periods"):
        ws["A1"] = "Year-over-Year Analysis"
        ws["A1"].font = LABEL_FONT
        ws["A2"] = (
            "Not enough comparable full years are present in the dataset to calculate "
            "meaningful year-over-year growth percentages."
        )
        ws.merge_cells("A2:D2")
        return

    ws["A1"] = "Yearly Totals and Year-over-Year Growth"
    ws["A1"].font = LABEL_FONT
    _write_dataframe(ws, yoy["yearly_table"], start_row=3)


def build_excel_report(analysis_results: dict, output_path: Path = EXCEL_REPORT_PATH,
                        findings: list[str] | None = None) -> Path:
    """Build the full multi-sheet Excel workbook and save it to
    ``output_path``."""
    logger.info("Building Excel report...")

    workbook = Workbook()

    _write_summary_sheet(workbook, analysis_results["summary"], findings)
    _write_product_sheet(workbook, analysis_results["products"])
    _write_category_sheet(workbook, analysis_results["categories"])
    _write_monthly_sheet(workbook, analysis_results["monthly"])
    _write_regional_sheet(workbook, analysis_results["regions"])
    _write_customer_sheet(workbook, analysis_results["customers"])
    _write_payment_sheet(workbook, analysis_results["payments"])
    _write_segmentation_sheet(workbook, analysis_results["segmentation"])
    _write_pareto_sheet(workbook, analysis_results["pareto"])
    _write_yoy_sheet(workbook, analysis_results["yoy"])

    ensure_directories(output_path.parent)
    workbook.save(output_path)

    logger.info("Excel report saved to %s", output_path)
    return output_path
