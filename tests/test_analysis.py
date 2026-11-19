"""
tests/test_analysis.py

Tests for src.analysis using a small, controlled, already-clean
DataFrame with hand-computed expected values - never the 15,000-row
production dataset.
"""

from __future__ import annotations

import pandas as pd

from src.analysis import (
    category_analysis,
    monthly_sales_analysis,
    overall_sales_summary,
    product_analysis,
    regional_analysis,
)


def _clean_dataframe() -> pd.DataFrame:
    """A small, already-clean dataset with easy-to-verify totals:

    - 5 rows, 2 orders each contributing to totals below.
    - Order_ID ORD1 has two line items (rows 0 and 1); ORD2..ORD4 are
      single-item orders.
    - Total Sales = 200 + 100 + 150 + 300 + 90 = 840
    - Total Quantity = 2 + 1 + 3 + 2 + 3 = 11
    - Unique customers = C1, C2, C3 -> 3
    - Unique orders = ORD1, ORD2, ORD3, ORD4 -> 4
    """
    dates = pd.to_datetime([
        "2024-01-10", "2024-01-10", "2024-01-20", "2024-02-05", "2024-02-15",
    ])
    return pd.DataFrame({
        "Order_ID":     ["ORD1", "ORD1", "ORD2", "ORD3", "ORD4"],
        "Order_Date":   dates,
        "Customer_ID":  ["C1", "C1", "C1", "C2", "C3"],
        "Product":      ["Widget", "Gadget", "Widget", "Widget", "Gizmo"],
        "Category":     ["Electronics", "Electronics", "Electronics", "Electronics", "Accessories"],
        "Quantity":     [2, 1, 3, 2, 3],
        "Unit_Price":   [100.0, 100.0, 50.0, 150.0, 30.0],
        "Sales":        [200.0, 100.0, 150.0, 300.0, 90.0],
        "Region":       ["North", "North", "North", "South", "South"],
        "City":         ["Delhi", "Delhi", "Delhi", "Chennai", "Chennai"],
        "Payment_Mode": ["UPI", "UPI", "UPI", "Cash on Delivery", "UPI"],
        "Year":         [2024, 2024, 2024, 2024, 2024],
        "Month":        [1, 1, 1, 2, 2],
        "Month_Name":   ["January", "January", "January", "February", "February"],
    })


def test_revenue_calculation():
    summary = overall_sales_summary(_clean_dataframe())
    assert summary["Total Revenue"] == 840.0


def test_order_count():
    summary = overall_sales_summary(_clean_dataframe())
    assert summary["Total Orders"] == 4


def test_customer_count():
    summary = overall_sales_summary(_clean_dataframe())
    assert summary["Total Customers"] == 3


def test_quantity_total():
    summary = overall_sales_summary(_clean_dataframe())
    assert summary["Total Quantity Sold"] == 11


def test_average_order_value():
    # Order-level revenue: ORD1=300, ORD2=150, ORD3=300, ORD4=90
    # Average = (300 + 150 + 300 + 90) / 4 = 210.0
    summary = overall_sales_summary(_clean_dataframe())
    assert summary["Average Order Value"] == 210.0


def test_product_aggregation():
    result = product_analysis(_clean_dataframe())
    all_products = result["all_products"].set_index("Product")

    # Widget appears in ORD1 (200) + ORD2 (150) + ORD3 (300) = 650
    assert all_products.loc["Widget", "Revenue"] == 650.0
    # Gadget appears only in ORD1 = 100
    assert all_products.loc["Gadget", "Revenue"] == 100.0
    # Gizmo appears only in ORD4 = 90
    assert all_products.loc["Gizmo", "Revenue"] == 90.0

    # Top product by revenue must be Widget.
    assert result["top_by_revenue"].iloc[0]["Product"] == "Widget"


def test_category_aggregation():
    categories = category_analysis(_clean_dataframe()).set_index("Category")

    # Electronics: 200 + 100 + 150 + 300 = 750
    assert categories.loc["Electronics", "Revenue"] == 750.0
    # Accessories: 90
    assert categories.loc["Accessories", "Revenue"] == 90.0

    # Revenue percentage should sum to (approximately) 100%.
    total_percent = categories["Revenue_Percentage"].sum()
    assert round(total_percent, 1) == 100.0


def test_monthly_aggregation():
    monthly_results = monthly_sales_analysis(_clean_dataframe())
    monthly_table = monthly_results["monthly_table"].set_index("Month_Name")

    # January: 200 + 100 + 150 = 450
    assert monthly_table.loc["January", "Revenue"] == 450.0
    # February: 300 + 90 = 390
    assert monthly_table.loc["February", "Revenue"] == 390.0

    assert monthly_results["peak_month"] == "January 2024"
    assert monthly_results["lowest_month"] == "February 2024"


def test_regional_aggregation():
    regions = regional_analysis(_clean_dataframe()).set_index("Region")

    # North: 200 + 100 + 150 = 450
    assert regions.loc["North", "Revenue"] == 450.0
    # South: 300 + 90 = 390
    assert regions.loc["South", "Revenue"] == 390.0
