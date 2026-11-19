"""
tests/test_powerbi_export.py

Tests for src.powerbi_export using a small controlled DataFrame. They check
the properties Power BI relies on: one row per key (so relationships are
one-to-many), full key coverage (no orphan sales rows) and file output.
"""

from __future__ import annotations

import pandas as pd
import pytest

from src.analysis import customer_segmentation, pareto_analysis, product_analysis
from src.powerbi_export import (
    CUSTOMER_DIMENSION_COLUMNS,
    PRODUCT_DIMENSION_COLUMNS,
    build_customer_dimension,
    build_product_dimension,
    export_powerbi_tables,
)


def _sales_dataframe() -> pd.DataFrame:
    """Six single-line orders: C1 buys 3 times, C2 twice, C3 once."""
    return pd.DataFrame({
        "Order_ID":    ["O1", "O2", "O3", "O4", "O5", "O6"],
        "Order_Date":  pd.to_datetime(["2024-01-05", "2024-02-10", "2024-03-15",
                                       "2024-01-20", "2024-03-01", "2024-02-25"]),
        "Customer_ID": ["C1", "C1", "C1", "C2", "C2", "C3"],
        "Product":     ["Laptop", "Mouse", "Laptop", "Mouse", "Desk", "Desk"],
        "Category":    ["Electronics", "Accessories", "Electronics",
                        "Accessories", "Furniture", "Furniture"],
        "Quantity":    [1, 2, 1, 3, 1, 1],
        "Unit_Price":  [1000.0, 50.0, 1000.0, 50.0, 400.0, 400.0],
        "Sales":       [1000.0, 100.0, 1000.0, 150.0, 400.0, 400.0],
    })


def _results() -> dict:
    df = _sales_dataframe()
    return {
        "products": product_analysis(df),
        "pareto": pareto_analysis(df),
        "segmentation": customer_segmentation(df),
    }


def test_customer_dimension_has_one_row_per_customer():
    dim = build_customer_dimension(_results()["segmentation"])
    assert list(dim.columns) == CUSTOMER_DIMENSION_COLUMNS
    assert dim["Customer_ID"].is_unique
    assert set(dim["Customer_ID"]) == set(_sales_dataframe()["Customer_ID"])


def test_customer_dimension_rejects_duplicate_keys():
    segmentation = _results()["segmentation"]
    table = segmentation["customer_rfm_table"]
    broken = {"customer_rfm_table": pd.concat([table, table.head(1)], ignore_index=True)}
    with pytest.raises(ValueError):
        build_customer_dimension(broken)


def test_one_time_customer_is_labelled_one_time():
    dim = build_customer_dimension(_results()["segmentation"]).set_index("Customer_ID")
    assert dim.loc["C3", "Segment"] == "One-time"
    assert dim.loc["C3", "Frequency"] == 1


def test_product_dimension_has_one_row_per_product_with_abc_class():
    results = _results()
    dim = build_product_dimension(results["products"], results["pareto"])
    assert list(dim.columns) == PRODUCT_DIMENSION_COLUMNS
    assert dim["Product"].is_unique
    assert set(dim["Product"]) == {"Laptop", "Mouse", "Desk"}
    assert set(dim["ABC_Class"]).issubset({"A", "B", "C"})
    assert dim.iloc[0]["Product"] == "Laptop"  # highest revenue ranks first


def test_every_sales_key_exists_in_dimensions():
    """No orphan rows: each sales Customer_ID / Product has a dimension row."""
    results = _results()
    sales = _sales_dataframe()
    customers = build_customer_dimension(results["segmentation"])
    products = build_product_dimension(results["products"], results["pareto"])
    assert sales["Customer_ID"].isin(customers["Customer_ID"]).all()
    assert sales["Product"].isin(products["Product"]).all()


def test_export_writes_both_csv_files(tmp_path):
    customer_path = tmp_path / "customer_segments.csv"
    product_path = tmp_path / "product_classification.csv"
    export_powerbi_tables(_results(), customer_path, product_path)
    assert len(pd.read_csv(customer_path)) == 3
    assert len(pd.read_csv(product_path)) == 3
