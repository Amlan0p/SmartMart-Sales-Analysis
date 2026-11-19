"""
powerbi_export.py

Exports the small dimension tables that Power BI needs in addition to the
cleaned sales CSV. This module is purely additive: it only *reads* the
results already produced by ``analysis.run_full_analysis`` and writes two
CSV files next to ``cleaned_sales_data.csv``.

Why it exists
-------------
* RFM customer segments are computed in Python (quantile scoring is not
  trivial to reproduce faithfully in DAX), so the per-customer result is
  exported as a *customer dimension* with exactly ONE row per Customer_ID.
  Power BI relates it to the sales table 1:many on Customer_ID.
* The Python ABC class (fixed 80/95 % cumulative-revenue thresholds) is
  exported as a *product dimension* with exactly ONE row per Product, so
  Power BI can reconcile its own dynamic ABC measure against Python.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from config import CUSTOMER_SEGMENTS_PATH, PRODUCT_CLASSIFICATION_PATH
from src.utils import ensure_directories, get_logger

logger = get_logger(__name__)

CUSTOMER_DIMENSION_COLUMNS = [
    "Customer_ID", "Segment", "R_Score", "F_Score", "M_Score", "RFM_Score",
    "Recency_Days", "Frequency", "Monetary", "Last_Order_Date",
]
PRODUCT_DIMENSION_COLUMNS = [
    "Product", "Category", "Revenue_Rank", "ABC_Class",
    "Cumulative_Revenue_Percent",
]


def build_customer_dimension(segmentation: dict) -> pd.DataFrame:
    """Return one row per customer with RFM scores and the Python segment.

    Raises ``ValueError`` if Customer_ID is not unique, because a duplicate
    key would make the Power BI relationship many-to-many.
    """
    table = segmentation["customer_rfm_table"][CUSTOMER_DIMENSION_COLUMNS].copy()
    if table["Customer_ID"].duplicated().any():
        raise ValueError("Customer dimension contains duplicate Customer_ID values.")
    table["Last_Order_Date"] = pd.to_datetime(table["Last_Order_Date"]).dt.strftime("%Y-%m-%d")
    return table.sort_values("Customer_ID").reset_index(drop=True)


def build_product_dimension(product_results: dict, pareto: dict) -> pd.DataFrame:
    """Return one row per product with Category, revenue rank and ABC class."""
    categories = product_results["all_products"][["Product", "Category"]]
    pareto_table = pareto["pareto_table"][["Product", "Rank", "ABC_Class", "Cumulative_Revenue_Percent"]]
    table = categories.merge(pareto_table, on="Product", how="inner", validate="one_to_one")
    table = table.rename(columns={"Rank": "Revenue_Rank"})[PRODUCT_DIMENSION_COLUMNS]
    return table.sort_values("Revenue_Rank").reset_index(drop=True)


def export_powerbi_tables(
    results: dict,
    customer_path: Path = CUSTOMER_SEGMENTS_PATH,
    product_path: Path = PRODUCT_CLASSIFICATION_PATH,
) -> tuple[Path, Path]:
    """Write the customer and product dimension CSVs and return their paths."""
    customers = build_customer_dimension(results["segmentation"])
    products = build_product_dimension(results["products"], results["pareto"])

    ensure_directories(customer_path.parent, product_path.parent)
    customers.to_csv(customer_path, index=False)
    products.to_csv(product_path, index=False)
    logger.info("Power BI customer dimension saved: %s (%d rows)", customer_path, len(customers))
    logger.info("Power BI product dimension saved: %s (%d rows)", product_path, len(products))
    return customer_path, product_path
