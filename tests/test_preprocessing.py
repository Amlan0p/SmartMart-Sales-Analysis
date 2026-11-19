"""
tests/test_preprocessing.py

Tests for src.preprocessing using small, controlled DataFrames that
exercise each cleaning rule directly - never the 15,000-row production
dataset.
"""

from __future__ import annotations

import pandas as pd

from src.preprocessing import (
    add_derived_columns,
    clean_dataset,
    drop_duplicate_records,
    fix_data_types,
    handle_missing_values,
    remove_invalid_records,
)


def _raw_dataframe() -> pd.DataFrame:
    """A small, deliberately messy raw dataset covering every cleaning
    rule: a duplicate row, an invalid (negative) Quantity, an invalid
    (negative) Unit_Price, a missing City, and a missing Unit_Price."""
    return pd.DataFrame({
        "Order_ID":     ["ORD1", "ORD1", "ORD2", "ORD3", "ORD4", "ORD5"],
        "Order_Date":   ["2024-01-05", "2024-01-05", "2024-01-10", "2024-02-01", "2024-02-15", "2024-03-01"],
        "Customer_ID":  ["C1", "C1", "C1", "C2", "C3", "C2"],
        "Product":      ["Widget", "Widget", "Widget", "Gadget", "Widget", "Gadget"],
        "Category":     ["Electronics"] * 6,
        "Quantity":     [2, 2, -1, 3, 1, 2],
        "Unit_Price":   [100.0, 100.0, 100.0, -50.0, None, 60.0],
        "Sales":        [200.0, 200.0, -100.0, -150.0, 0.0, 120.0],
        "Region":       ["North"] * 6,
        "City":         ["Delhi", "Delhi", "Delhi", "Chennai", None, "Chennai"],
        "Payment_Mode": ["UPI", "UPI", "UPI", "Cash on Delivery", "UPI", "UPI"],
    })


def test_duplicate_records_are_removed():
    df = _raw_dataframe()
    deduplicated = drop_duplicate_records(df)
    # Rows 0 and 1 are exact duplicates -> exactly one should be removed.
    assert len(deduplicated) == len(df) - 1


def test_invalid_quantity_is_removed():
    df = fix_data_types(_raw_dataframe())
    df = handle_missing_values(df)
    df = drop_duplicate_records(df)
    cleaned = remove_invalid_records(df)
    assert (cleaned["Quantity"] > 0).all()
    assert "ORD2" not in cleaned["Order_ID"].values


def test_invalid_unit_price_is_removed():
    df = fix_data_types(_raw_dataframe())
    df = handle_missing_values(df)
    df = drop_duplicate_records(df)
    cleaned = remove_invalid_records(df)
    assert (cleaned["Unit_Price"] > 0).all()
    assert "ORD3" not in cleaned["Order_ID"].values


def test_missing_values_are_handled():
    df = fix_data_types(_raw_dataframe())
    handled = handle_missing_values(df)

    # Missing City is filled with 'Unknown', never left as NaN.
    assert handled["City"].isna().sum() == 0
    assert "Unknown" in handled["City"].values

    # Missing Unit_Price is imputed (no NaNs remain).
    assert handled["Unit_Price"].isna().sum() == 0


def test_order_date_is_converted_to_datetime():
    df = fix_data_types(_raw_dataframe())
    assert pd.api.types.is_datetime64_any_dtype(df["Order_Date"])


def test_cleaned_dataset_contains_only_valid_values():
    cleaned = clean_dataset(_raw_dataframe())

    assert (cleaned["Quantity"] > 0).all()
    assert (cleaned["Unit_Price"] > 0).all()
    assert (cleaned["Sales"] > 0).all()
    assert cleaned["City"].isna().sum() == 0
    assert cleaned["Order_Date"].isna().sum() == 0
    # Sales must always equal Quantity * Unit_Price after cleaning.
    recalculated = (cleaned["Quantity"] * cleaned["Unit_Price"]).round(2)
    assert (recalculated == cleaned["Sales"]).all()


def test_derived_columns_are_added():
    df = fix_data_types(_raw_dataframe())
    df = handle_missing_values(df)
    df = drop_duplicate_records(df)
    df = remove_invalid_records(df)
    enriched = add_derived_columns(df)

    for column in ["Year", "Month", "Month_Name", "Quarter", "Order_Value", "Customer_Type"]:
        assert column in enriched.columns

    # Customer C2 places 2 distinct orders (ORD3, ORD5) -> repeat customer.
    # (ORD3 is removed as invalid, so C2 has only ORD5 remaining here,
    # which correctly makes them a one-time customer in *this* subset.)
    assert set(enriched["Customer_Type"].unique()).issubset({"Repeat Customer", "One-time Customer"})
