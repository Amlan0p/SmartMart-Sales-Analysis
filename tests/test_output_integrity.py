"""
tests/test_output_integrity.py

End-to-end integrity checks on the files produced by ``python main.py``.

Unlike the other test modules (which use tiny hand-built DataFrames), these
tests inspect the REAL generated outputs. If the pipeline has not been run yet
the tests are skipped rather than failed - run ``python main.py`` first.
"""

from __future__ import annotations

import pandas as pd
import pytest

import config
from src.utils import format_currency

EXPECTED_CHARTS = [
    "executive_dashboard.png", "monthly_revenue_trend.png", "revenue_by_category.png",
    "top_10_products.png", "regional_sales.png", "payment_method_distribution.png",
    "top_customers.png", "customer_type_distribution.png",
    "avg_order_value_by_region.png", "pareto_analysis.png",
]
ASSIGNMENT_SHEETS = [
    "Summary", "Product Analysis", "Category Analysis", "Monthly Analysis", "Regional Analysis",
]
POWERBI_FILES = [
    "powerbi/BUILD_GUIDE.md", "powerbi/README.md",
    "powerbi/power_query/sales_data.m", "powerbi/power_query/dim_customer.m",
    "powerbi/power_query/dim_product.m", "powerbi/power_query/DataFolderPath.m",
    "powerbi/dax/measures.dax", "powerbi/dax/date_table.dax",
    "powerbi/data_model/model_documentation.md",
    "powerbi/dashboard_design/dashboard_specification.md",
    "powerbi/dashboard_design/theme/SmartMart_Theme.json",
]


def _require(path) -> None:
    if not path.exists():
        pytest.skip(f"{path.name} not found - run `python main.py` first.")


def _cleaned() -> pd.DataFrame:
    _require(config.CLEANED_SALES_DATA_PATH)
    return pd.read_csv(config.CLEANED_SALES_DATA_PATH, parse_dates=["Order_Date"])


def test_cleaned_dataset_integrity():
    df = _cleaned()
    assert not df[config.REQUIRED_COLUMNS].isnull().any().any()
    assert not df.duplicated().any()
    assert df["Order_ID"].is_unique
    assert (df["Quantity"] > 0).all() and (df["Unit_Price"] > 0).all() and (df["Sales"] > 0).all()
    assert ((df["Quantity"] * df["Unit_Price"] - df["Sales"]).abs() < 0.01).all()
    assert df["Order_Date"].min() >= pd.Timestamp(config.DATASET_START_DATE)
    assert df["Order_Date"].max() <= pd.Timestamp(config.DATASET_END_DATE)


def test_charts_exist_and_are_valid_png_files():
    for name in EXPECTED_CHARTS:
        path = config.CHARTS_DIR / name
        _require(path)
        header = path.read_bytes()[:8]
        assert header == b"\x89PNG\r\n\x1a\n", f"{name} is not a valid PNG"
        assert path.stat().st_size > 10_000, f"{name} is suspiciously small"


def test_excel_report_contains_required_sheets_and_matching_totals():
    import openpyxl

    _require(config.EXCEL_REPORT_PATH)
    workbook = openpyxl.load_workbook(config.EXCEL_REPORT_PATH, data_only=True)
    for sheet in ASSIGNMENT_SHEETS:
        assert sheet in workbook.sheetnames, f"Missing sheet: {sheet}"

    values = {row[0]: row[1] for row in workbook["Summary"].iter_rows(values_only=True) if row[0]}
    df = _cleaned()
    assert abs(values["Total Revenue"] - round(df["Sales"].sum(), 2)) < 0.01
    assert values["Total Orders"] == df["Order_ID"].nunique()
    assert values["Total Customers"] == df["Customer_ID"].nunique()
    assert values["Total Quantity Sold"] == int(df["Quantity"].sum())


def test_data_quality_report_row_counts_match_data():
    import openpyxl

    _require(config.DATA_QUALITY_REPORT_PATH)
    _require(config.RAW_SALES_DATA_PATH)
    sheet = openpyxl.load_workbook(config.DATA_QUALITY_REPORT_PATH, data_only=True).worksheets[0]
    rows = {row[0]: row for row in sheet.iter_rows(values_only=True) if row[0]}
    assert rows["Total rows"][1] == len(pd.read_csv(config.RAW_SALES_DATA_PATH))
    assert rows["Total rows"][2] == len(_cleaned())


def test_business_insights_report_quotes_the_real_total_revenue():
    _require(config.BUSINESS_INSIGHTS_PATH)
    text = config.BUSINESS_INSIGHTS_PATH.read_text(encoding="utf-8")
    assert format_currency(round(_cleaned()["Sales"].sum(), 2)) in text
    assert "BUSINESS RECOMMENDATIONS" in text


def test_no_notebook_files_in_project():
    notebooks = [p for p in config.BASE_DIR.rglob("*.ipynb")]
    assert notebooks == [], f"Notebook files are not allowed: {notebooks}"


def test_power_bi_assets_are_present():
    for relative in POWERBI_FILES:
        assert (config.BASE_DIR / relative).exists(), f"Missing Power BI asset: {relative}"


def test_power_bi_dimensions_align_with_sales():
    _require(config.CUSTOMER_SEGMENTS_PATH)
    _require(config.PRODUCT_CLASSIFICATION_PATH)
    sales = _cleaned()
    customers = pd.read_csv(config.CUSTOMER_SEGMENTS_PATH)
    products = pd.read_csv(config.PRODUCT_CLASSIFICATION_PATH)
    assert customers["Customer_ID"].is_unique and products["Product"].is_unique
    assert set(sales["Customer_ID"]) == set(customers["Customer_ID"])
    assert set(sales["Product"]) == set(products["Product"])
    assert products.groupby("Product")["Category"].nunique().max() == 1
