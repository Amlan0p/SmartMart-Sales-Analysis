"""
tests/test_data_loader.py

Tests for src.data_loader using small, controlled data - never the
15,000-row production dataset.
"""

from __future__ import annotations

import pandas as pd
import pytest

from src.data_loader import (
    DatasetNotFoundError,
    EmptyDatasetError,
    MissingColumnsError,
    load_sales_data,
    validate_columns,
)

REQUIRED_COLUMNS = [
    "Order_ID", "Order_Date", "Customer_ID", "Product", "Category",
    "Quantity", "Unit_Price", "Sales", "Region", "City", "Payment_Mode",
]


def _valid_dataframe() -> pd.DataFrame:
    return pd.DataFrame({
        "Order_ID": ["ORD1", "ORD2"],
        "Order_Date": ["2024-01-01", "2024-01-02"],
        "Customer_ID": ["C1", "C2"],
        "Product": ["Widget", "Gadget"],
        "Category": ["Electronics", "Electronics"],
        "Quantity": [1, 2],
        "Unit_Price": [100.0, 50.0],
        "Sales": [100.0, 100.0],
        "Region": ["North", "South"],
        "City": ["Delhi", "Chennai"],
        "Payment_Mode": ["UPI", "Cash on Delivery"],
    })


def test_missing_file_raises_dataset_not_found_error(tmp_path):
    missing_path = tmp_path / "does_not_exist.csv"
    with pytest.raises(DatasetNotFoundError):
        load_sales_data(missing_path)


def test_required_columns_are_validated_when_missing():
    df = _valid_dataframe().drop(columns=["Unit_Price"])
    with pytest.raises(MissingColumnsError):
        validate_columns(df, REQUIRED_COLUMNS)


def test_required_columns_pass_when_all_present():
    df = _valid_dataframe()
    # Should not raise.
    validate_columns(df, REQUIRED_COLUMNS)


def test_valid_dataset_loads_successfully(tmp_path):
    csv_path = tmp_path / "sales_data.csv"
    _valid_dataframe().to_csv(csv_path, index=False)

    loaded = load_sales_data(csv_path)

    assert len(loaded) == 2
    assert list(loaded.columns) == list(_valid_dataframe().columns)
    assert set(REQUIRED_COLUMNS).issubset(set(loaded.columns))


def test_empty_file_raises_empty_dataset_error(tmp_path):
    csv_path = tmp_path / "empty.csv"
    _valid_dataframe().iloc[0:0].to_csv(csv_path, index=False)

    with pytest.raises(EmptyDatasetError):
        load_sales_data(csv_path)
