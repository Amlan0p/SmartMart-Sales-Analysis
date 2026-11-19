"""
preprocessing.py

Cleans and enriches the raw sales dataset:

- Reports and handles missing values.
- Detects and removes duplicate records.
- Fixes data types (dates, numeric columns).
- Removes/repairs invalid (negative or zero) Quantity/Unit_Price rows.
- Recalculates Sales as Quantity * Unit_Price to guarantee consistency.
- Adds derived columns useful for downstream analysis
  (Year, Month, Month_Name, Quarter, Order_Value, Customer_Type).

The module returns a clean DataFrame and can optionally persist it to
``data/processed/cleaned_sales_data.csv``.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from config import CLEANED_SALES_DATA_PATH, REPEAT_CUSTOMER_MIN_ORDERS
from src.utils import ensure_directories, get_logger

logger = get_logger(__name__)


def report_missing_values(dataframe: pd.DataFrame) -> pd.Series:
    """Return a Series of missing-value counts per column (non-zero only)."""
    missing = dataframe.isna().sum()
    missing = missing[missing > 0]
    if not missing.empty:
        logger.info("Missing values detected:\n%s", missing.to_string())
    else:
        logger.info("No missing values detected.")
    return missing


def drop_duplicate_records(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Remove exact duplicate rows, logging how many were dropped."""
    before = len(dataframe)
    deduplicated = dataframe.drop_duplicates()
    removed = before - len(deduplicated)
    logger.info("Removed %d duplicate record(s).", removed)
    return deduplicated


def fix_data_types(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Coerce columns to their expected data types.

    - ``Order_Date`` -> datetime
    - ``Quantity`` -> numeric (nullable Int)
    - ``Unit_Price`` / ``Sales`` -> numeric float
    """
    df = dataframe.copy()

    df["Order_Date"] = pd.to_datetime(df["Order_Date"], errors="coerce")

    for column in ["Quantity", "Unit_Price", "Sales"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    invalid_dates = df["Order_Date"].isna().sum()
    if invalid_dates:
        logger.info("Found %d row(s) with an invalid/unparseable Order_Date.", invalid_dates)

    return df


def handle_missing_values(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Handle missing values with column-appropriate strategies.

    - Rows missing ``Order_Date``, ``Customer_ID`` or ``Product`` are
      dropped, since these are essential identifiers that cannot be
      safely inferred.
    - Missing ``City`` / ``Payment_Mode`` are filled with "Unknown"
      since they are descriptive attributes, not identifiers.
    - Missing ``Unit_Price`` is imputed using the median price of the
      same ``Product`` (falling back to the overall median), so that
      ``Sales`` can still be recalculated meaningfully.
    """
    df = dataframe.copy()

    essential_columns = ["Order_Date", "Customer_ID", "Product", "Order_ID"]
    before = len(df)
    df = df.dropna(subset=essential_columns)
    dropped_essential = before - len(df)
    if dropped_essential:
        logger.info("Dropped %d row(s) missing essential identifier fields.", dropped_essential)

    for column in ["City", "Payment_Mode"]:
        if column in df.columns:
            missing_count = df[column].isna().sum()
            if missing_count:
                df[column] = df[column].fillna("Unknown")
                logger.info("Filled %d missing value(s) in '%s' with 'Unknown'.", missing_count, column)

    if df["Unit_Price"].isna().any():
        missing_price_count = df["Unit_Price"].isna().sum()
        median_by_product = df.groupby("Product")["Unit_Price"].transform("median")
        df["Unit_Price"] = df["Unit_Price"].fillna(median_by_product)
        # Fallback for products where every price happened to be missing.
        df["Unit_Price"] = df["Unit_Price"].fillna(df["Unit_Price"].median())
        logger.info("Imputed %d missing 'Unit_Price' value(s) using product-level median.", missing_price_count)

    return df


def remove_invalid_records(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Remove rows with non-positive Quantity or Unit_Price, which
    represent data-entry errors rather than valid transactions."""
    df = dataframe.copy()
    before = len(df)

    invalid_mask = (df["Quantity"] <= 0) | (df["Unit_Price"] <= 0)
    invalid_count = int(invalid_mask.sum())

    df = df.loc[~invalid_mask].copy()

    logger.info("Removed %d row(s) with invalid (non-positive) Quantity or Unit_Price.", invalid_count)
    logger.info("Row count after invalid-record removal: %d (was %d).", len(df), before)
    return df


def recalculate_sales(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Recalculate ``Sales`` as ``Quantity * Unit_Price`` for every row,
    guaranteeing internal consistency regardless of what the raw value
    originally contained."""
    df = dataframe.copy()
    df["Sales"] = (df["Quantity"] * df["Unit_Price"]).round(2)
    return df


def add_derived_columns(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Add derived columns used throughout the analysis stage."""
    df = dataframe.copy()

    df["Year"] = df["Order_Date"].dt.year
    df["Month"] = df["Order_Date"].dt.month
    df["Month_Name"] = df["Order_Date"].dt.strftime("%B")
    df["Quarter"] = df["Order_Date"].dt.quarter
    df["Order_Value"] = df["Sales"]

    orders_per_customer = df.groupby("Customer_ID")["Order_ID"].transform("nunique")
    df["Customer_Type"] = pd.Series(
        ["Repeat Customer" if count >= REPEAT_CUSTOMER_MIN_ORDERS else "One-time Customer"
         for count in orders_per_customer],
        index=df.index,
    )

    return df


def clean_dataset(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Run the full cleaning and enrichment pipeline on the raw dataset
    and return the resulting clean DataFrame.
    """
    logger.info("Starting preprocessing pipeline on %d raw rows.", len(dataframe))

    report_missing_values(dataframe)

    df = fix_data_types(dataframe)
    df = handle_missing_values(df)
    df = drop_duplicate_records(df)
    df = remove_invalid_records(df)
    df = recalculate_sales(df)
    df = add_derived_columns(df)

    df = df.sort_values("Order_Date").reset_index(drop=True)

    logger.info("Preprocessing complete. %d clean rows remain.", len(df))
    return df


def save_cleaned_dataset(dataframe: pd.DataFrame, output_path: Path = CLEANED_SALES_DATA_PATH) -> Path:
    """Persist the cleaned dataset to CSV."""
    ensure_directories(output_path.parent)
    dataframe.to_csv(output_path, index=False)
    logger.info("Cleaned dataset saved to %s", output_path)
    return output_path
