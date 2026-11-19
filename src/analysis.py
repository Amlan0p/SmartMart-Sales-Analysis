"""
analysis.py

All analytical calculations for the SmartMart sales dataset. Every
number produced here is derived dynamically from the cleaned DataFrame
passed in - nothing is hard-coded.

Each public function returns either a dictionary of scalar metrics or a
pandas DataFrame, so the results can be consumed directly by
``visualization.py``, ``excel_report.py`` and the business-insights
generator in ``main.py``.
"""

from __future__ import annotations

import pandas as pd

from config import (
    ABC_A_THRESHOLD,
    ABC_B_THRESHOLD,
    BOTTOM_N_PRODUCTS,
    REPEAT_CUSTOMER_MIN_ORDERS,
    RFM_BINS,
    TOP_N_CUSTOMERS,
    TOP_N_PRODUCTS,
)
from src.utils import get_logger, safe_divide

logger = get_logger(__name__)


def overall_sales_summary(df: pd.DataFrame) -> dict:
    """Compute headline, order-level KPIs for the whole dataset.

    'Total Orders' counts unique Order_ID values (an order may span
    multiple line-item rows). Average Order Value is based on
    order-level revenue, not row-level revenue.
    """
    order_level = df.groupby("Order_ID")["Sales"].sum()

    total_revenue = float(df["Sales"].sum())
    total_orders = int(df["Order_ID"].nunique())
    total_quantity = int(df["Quantity"].sum())
    total_customers = int(df["Customer_ID"].nunique())

    average_order_value = float(order_level.mean()) if len(order_level) else 0.0
    average_selling_price = safe_divide(total_revenue, total_quantity)

    summary = {
        "Total Revenue": round(total_revenue, 2),
        "Total Orders": total_orders,
        "Total Quantity Sold": total_quantity,
        "Total Customers": total_customers,
        "Average Order Value": round(average_order_value, 2),
        "Average Selling Price": round(average_selling_price, 2),
    }

    logger.info("Overall sales summary computed: %s", summary)
    return summary


def product_analysis(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Compute per-product revenue and quantity metrics, including
    top and bottom performers."""
    grouped = (
        df.groupby(["Product", "Category"], as_index=False)
        .agg(Revenue=("Sales", "sum"), Quantity=("Quantity", "sum"), Orders=("Order_ID", "nunique"))
    )
    grouped["Revenue"] = grouped["Revenue"].round(2)
    grouped = grouped.sort_values("Revenue", ascending=False).reset_index(drop=True)
    grouped["Rank"] = grouped.index + 1

    top_by_revenue = grouped.head(TOP_N_PRODUCTS).reset_index(drop=True)
    top_by_quantity = (
        grouped.sort_values("Quantity", ascending=False).head(TOP_N_PRODUCTS).reset_index(drop=True)
    )
    bottom_performers = (
        grouped.sort_values("Revenue", ascending=True).head(BOTTOM_N_PRODUCTS).reset_index(drop=True)
    )

    return {
        "all_products": grouped,
        "top_by_revenue": top_by_revenue,
        "top_by_quantity": top_by_quantity,
        "bottom_performers": bottom_performers,
    }


def category_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """Compute revenue, quantity, orders and average order value by
    category."""
    order_revenue = df.groupby(["Category", "Order_ID"])["Sales"].sum().reset_index()
    aov_by_category = order_revenue.groupby("Category")["Sales"].mean()

    grouped = df.groupby("Category", as_index=False).agg(
        Revenue=("Sales", "sum"),
        Quantity=("Quantity", "sum"),
        Orders=("Order_ID", "nunique"),
    )
    grouped["Revenue"] = grouped["Revenue"].round(2)
    grouped["Average_Order_Value"] = grouped["Category"].map(aov_by_category).round(2)
    grouped = grouped.sort_values("Revenue", ascending=False).reset_index(drop=True)

    total_revenue = grouped["Revenue"].sum()
    grouped["Revenue_Percentage"] = (
        (grouped["Revenue"] / total_revenue * 100).round(2) if total_revenue else 0.0
    )

    return grouped


def monthly_sales_analysis(df: pd.DataFrame) -> dict[str, object]:
    """Compute monthly revenue/orders/quantity trends and identify
    peak/low months. Grouping uses (Year, Month) so multi-year data does
    not conflate the same calendar month across different years.
    """
    monthly = df.groupby(["Year", "Month", "Month_Name"], as_index=False).agg(
        Revenue=("Sales", "sum"),
        Quantity=("Quantity", "sum"),
        Orders=("Order_ID", "nunique"),
    )
    monthly["Revenue"] = monthly["Revenue"].round(2)
    monthly["Average_Order_Value"] = (monthly["Revenue"] / monthly["Orders"]).round(2)
    monthly = monthly.sort_values(["Year", "Month"]).reset_index(drop=True)
    monthly["Period"] = monthly["Month_Name"] + " " + monthly["Year"].astype(str)

    if monthly.empty:
        peak_month = None
        lowest_month = None
    else:
        peak_row = monthly.loc[monthly["Revenue"].idxmax()]
        low_row = monthly.loc[monthly["Revenue"].idxmin()]
        peak_month = f"{peak_row['Month_Name']} {int(peak_row['Year'])}"
        lowest_month = f"{low_row['Month_Name']} {int(low_row['Year'])}"

    return {
        "monthly_table": monthly,
        "peak_month": peak_month,
        "lowest_month": lowest_month,
    }


def year_over_year_analysis(df: pd.DataFrame) -> dict[str, object]:
    """Compute yearly totals and, where at least two comparable years of
    data exist, year-over-year growth percentages for revenue, orders
    and quantity.

    Growth is only calculated between *consecutive* years that are both
    present in the data - no growth figure is invented for a year that
    has no prior-year counterpart to compare against.
    """
    yearly = df.groupby("Year", as_index=False).agg(
        Revenue=("Sales", "sum"),
        Quantity=("Quantity", "sum"),
        Orders=("Order_ID", "nunique"),
    ).sort_values("Year").reset_index(drop=True)
    yearly["Revenue"] = yearly["Revenue"].round(2)

    yearly["Revenue_Growth_Percent"] = yearly["Revenue"].pct_change().mul(100).round(2)
    yearly["Order_Growth_Percent"] = yearly["Orders"].pct_change().mul(100).round(2)
    yearly["Quantity_Growth_Percent"] = yearly["Quantity"].pct_change().mul(100).round(2)

    has_comparable_periods = len(yearly) >= 2

    return {
        "yearly_table": yearly,
        "has_comparable_periods": has_comparable_periods,
    }


def customer_segmentation(df: pd.DataFrame) -> dict[str, object]:
    """RFM-style (Recency, Frequency, Monetary) customer segmentation.

    Method (kept intentionally simple - no machine learning):

    1. For every customer compute:
       - Recency: days between their most recent order and the most
         recent order date in the whole dataset (smaller = more recent).
       - Frequency: number of distinct orders placed.
       - Monetary: total revenue (Sales) generated.
    2. Each of the three metrics is independently split into
       ``RFM_BINS`` quantile-based score bands from 1 (worst) to
       ``RFM_BINS`` (best). Recency is scored in reverse, since a
       *smaller* number of days is better.
    3. The three scores are summed into an RFM_Score, and customers are
       mapped to a business-friendly segment using fixed, documented
       score-range rules:

       - "High Value" : RFM_Score in the top band AND Frequency > 1
       - "Loyal"       : Frequency > 1 (repeat buyer) and RFM_Score above
                         the midpoint, but not already "High Value"
       - "Regular"     : Frequency > 1, RFM_score at or below the
                         midpoint
       - "One-time"    : exactly one distinct order
       - "Occasional"  : everything else (infrequent, lower-value buyers)

    These are explicit, fixed rules over the computed scores - not a
    trained/learned model.
    """
    max_date = df["Order_Date"].max()

    customer_stats = df.groupby("Customer_ID").agg(
        Last_Order_Date=("Order_Date", "max"),
        Frequency=("Order_ID", "nunique"),
        Monetary=("Sales", "sum"),
    ).reset_index()
    customer_stats["Recency_Days"] = (max_date - customer_stats["Last_Order_Date"]).dt.days
    customer_stats["Monetary"] = customer_stats["Monetary"].round(2)

    bins = min(RFM_BINS, customer_stats["Customer_ID"].nunique())
    bins = max(bins, 1)

    def _safe_qcut_scores(series: pd.Series, ascending: bool) -> pd.Series:
        """Quantile-score a series 1..bins (higher = better), tolerating
        columns with too few unique values for ``bins`` quantile cuts."""
        try:
            ranks = series.rank(method="first", ascending=ascending)
            scores = pd.qcut(ranks, q=bins, labels=list(range(1, bins + 1)))
            return scores.astype(int)
        except ValueError:
            return pd.Series([bins] * len(series), index=series.index)

    customer_stats["R_Score"] = _safe_qcut_scores(customer_stats["Recency_Days"], ascending=False)
    customer_stats["F_Score"] = _safe_qcut_scores(customer_stats["Frequency"], ascending=True)
    customer_stats["M_Score"] = _safe_qcut_scores(customer_stats["Monetary"], ascending=True)
    customer_stats["RFM_Score"] = (
        customer_stats["R_Score"] + customer_stats["F_Score"] + customer_stats["M_Score"]
    )

    max_possible_score = bins * 3
    midpoint = max_possible_score / 2

    def _assign_segment(row) -> str:
        if row["Frequency"] <= 1:
            return "One-time"
        if row["RFM_Score"] >= max_possible_score - 1:
            return "High Value"
        if row["RFM_Score"] > midpoint:
            return "Loyal"
        if row["Frequency"] > 1:
            return "Regular"
        return "Occasional"

    customer_stats["Segment"] = customer_stats.apply(_assign_segment, axis=1)

    segment_summary = (
        customer_stats.groupby("Segment", as_index=False)
        .agg(Customers=("Customer_ID", "nunique"), Total_Revenue=("Monetary", "sum"))
        .sort_values("Total_Revenue", ascending=False)
        .reset_index(drop=True)
    )
    segment_summary["Total_Revenue"] = segment_summary["Total_Revenue"].round(2)

    segmentation_rules = (
        "Recency, Frequency and Monetary value are each scored 1 (lowest) to "
        f"{bins} (highest) using quantile bands. Segments are then assigned by "
        "fixed rule: 'One-time' = exactly 1 order; 'High Value' = repeat "
        f"customer with a combined RFM score in the top band (>= {max_possible_score - 1} "
        f"of {max_possible_score}); 'Loyal' = repeat customer with a combined "
        f"score above the midpoint ({midpoint}); 'Regular' = repeat customer at "
        "or below the midpoint; 'Occasional' = remaining infrequent/low-value "
        "customers. No machine learning is used."
    )

    return {
        "customer_rfm_table": customer_stats,
        "segment_summary": segment_summary,
        "segmentation_rules": segmentation_rules,
    }


def pareto_analysis(df: pd.DataFrame) -> dict[str, object]:
    """Product revenue-concentration (Pareto/80-20) analysis and an
    optional ABC classification.

    Products are ranked by revenue (highest first), cumulative revenue
    and cumulative revenue percentage are computed, and the actual
    percentage of products required to reach ~80% of total revenue is
    calculated directly from the data (never assumed to be exactly
    20%).

    ABC thresholds (documented, fixed - not learned):
        A: cumulative revenue share <= ABC_A_THRESHOLD (default 80%)
        B: cumulative revenue share <= ABC_B_THRESHOLD (default 95%)
        C: everything beyond that
    """
    product_revenue = (
        df.groupby("Product", as_index=False)
        .agg(Revenue=("Sales", "sum"))
        .sort_values("Revenue", ascending=False)
        .reset_index(drop=True)
    )
    product_revenue["Revenue"] = product_revenue["Revenue"].round(2)

    total_revenue = product_revenue["Revenue"].sum()
    product_revenue["Rank"] = product_revenue.index + 1
    product_revenue["Cumulative_Revenue"] = product_revenue["Revenue"].cumsum().round(2)
    product_revenue["Cumulative_Revenue_Percent"] = (
        (product_revenue["Cumulative_Revenue"] / total_revenue * 100).round(2) if total_revenue else 0.0
    )

    total_products = len(product_revenue)
    products_for_80_percent = int((product_revenue["Cumulative_Revenue_Percent"] <= 80).sum())
    # Ensure at least the single product that first crosses 80% is counted.
    if products_for_80_percent < total_products and (
        products_for_80_percent == 0
        or product_revenue.loc[products_for_80_percent - 1, "Cumulative_Revenue_Percent"] < 80
    ):
        products_for_80_percent += 1
    products_for_80_percent = min(products_for_80_percent, total_products)
    percent_of_products_for_80_percent_revenue = (
        round(safe_divide(products_for_80_percent, total_products) * 100, 2) if total_products else 0.0
    )

    def _classify(cumulative_percent: float) -> str:
        if cumulative_percent <= ABC_A_THRESHOLD:
            return "A"
        if cumulative_percent <= ABC_B_THRESHOLD:
            return "B"
        return "C"

    product_revenue["ABC_Class"] = product_revenue["Cumulative_Revenue_Percent"].apply(_classify)

    abc_summary = (
        product_revenue.groupby("ABC_Class", as_index=False)
        .agg(Products=("Product", "nunique"), Revenue=("Revenue", "sum"))
        .sort_values("ABC_Class")
        .reset_index(drop=True)
    )
    abc_summary["Revenue"] = abc_summary["Revenue"].round(2)
    abc_summary["Revenue_Percent"] = (
        (abc_summary["Revenue"] / total_revenue * 100).round(2) if total_revenue else 0.0
    )

    abc_thresholds_note = (
        f"ABC thresholds are fixed and documented: Class A = products whose cumulative "
        f"revenue share is <= {ABC_A_THRESHOLD:.0f}%; Class B = <= {ABC_B_THRESHOLD:.0f}%; "
        "Class C = the remainder. Thresholds are configured in config.py."
    )

    return {
        "pareto_table": product_revenue,
        "products_for_80_percent_revenue": products_for_80_percent,
        "percent_of_products_for_80_percent_revenue": percent_of_products_for_80_percent_revenue,
        "total_products": total_products,
        "abc_summary": abc_summary,
        "abc_thresholds_note": abc_thresholds_note,
    }


def run_consistency_checks(df: pd.DataFrame, results: dict) -> list[str]:
    """Reconcile analysis outputs against the cleaned dataset and each
    other, within a small floating-point tolerance.

    Returns a list of human-readable warning messages for any check
    that fails; an empty list means every check passed. Callers decide
    whether to log, print or raise on a non-empty list - this function
    never silently discards a failure.
    """
    tolerance = 0.01
    warnings: list[str] = []

    total_revenue = float(df["Sales"].sum())

    def _check_sum(label: str, value: float) -> None:
        if abs(value - total_revenue) > max(tolerance, abs(total_revenue) * 1e-6):
            warnings.append(
                f"Consistency check failed: {label} ({value:.2f}) does not match "
                f"total revenue ({total_revenue:.2f})."
            )

    _check_sum("sum of monthly revenue", results["monthly"]["monthly_table"]["Revenue"].sum())
    _check_sum("sum of category revenue", results["categories"]["Revenue"].sum())
    _check_sum("sum of regional revenue", results["regions"]["Revenue"].sum())

    expected_sales = (df["Quantity"] * df["Unit_Price"]).round(2)
    mismatched_sales = (expected_sales - df["Sales"]).abs() > tolerance
    if mismatched_sales.any():
        warnings.append(
            f"Consistency check failed: {int(mismatched_sales.sum())} row(s) where "
            "Sales does not equal Quantity * Unit_Price within tolerance."
        )

    expected_orders = df["Order_ID"].nunique()
    if results["summary"]["Total Orders"] != expected_orders:
        warnings.append(
            f"Consistency check failed: Total Orders ({results['summary']['Total Orders']}) "
            f"does not match unique Order_ID count ({expected_orders})."
        )

    expected_customers = df["Customer_ID"].nunique()
    if results["summary"]["Total Customers"] != expected_customers:
        warnings.append(
            f"Consistency check failed: Total Customers ({results['summary']['Total Customers']}) "
            f"does not match unique Customer_ID count ({expected_customers})."
        )

    if warnings:
        for message in warnings:
            logger.warning(message)
    else:
        logger.info("All data consistency/reconciliation checks passed.")

    return warnings


def regional_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """Compute revenue, orders, quantity and average order value by
    region."""
    order_revenue = df.groupby(["Region", "Order_ID"])["Sales"].sum().reset_index()
    aov_by_region = order_revenue.groupby("Region")["Sales"].mean()

    grouped = df.groupby("Region", as_index=False).agg(
        Revenue=("Sales", "sum"),
        Quantity=("Quantity", "sum"),
        Orders=("Order_ID", "nunique"),
    )
    grouped["Revenue"] = grouped["Revenue"].round(2)
    grouped["Average_Order_Value"] = grouped["Region"].map(aov_by_region).round(2)
    grouped = grouped.sort_values("Revenue", ascending=False).reset_index(drop=True)

    return grouped


def customer_analysis(df: pd.DataFrame) -> dict[str, object]:
    """Compute customer-level spending, order frequency and the
    repeat-vs-one-time customer split.

    A customer is classified as a "repeat customer" if they have placed
    at least ``REPEAT_CUSTOMER_MIN_ORDERS`` distinct orders (default: 2).
    """
    customer_orders = df.groupby("Customer_ID").agg(
        Total_Spending=("Sales", "sum"),
        Number_of_Orders=("Order_ID", "nunique"),
    ).reset_index()
    customer_orders["Total_Spending"] = customer_orders["Total_Spending"].round(2)
    customer_orders["Average_Spending_Per_Order"] = (
        customer_orders["Total_Spending"] / customer_orders["Number_of_Orders"]
    ).round(2)

    customer_orders["Customer_Type"] = customer_orders["Number_of_Orders"].apply(
        lambda n: "Repeat Customer" if n >= REPEAT_CUSTOMER_MIN_ORDERS else "One-time Customer"
    )

    top_customers = (
        customer_orders.sort_values("Total_Spending", ascending=False)
        .head(TOP_N_CUSTOMERS)
        .reset_index(drop=True)
    )

    repeat_customers = int((customer_orders["Customer_Type"] == "Repeat Customer").sum())
    one_time_customers = int((customer_orders["Customer_Type"] == "One-time Customer").sum())
    total_customers = len(customer_orders)

    return {
        "customer_table": customer_orders,
        "top_customers": top_customers,
        "repeat_customers": repeat_customers,
        "one_time_customers": one_time_customers,
        "repeat_customer_rate": round(safe_divide(repeat_customers, total_customers) * 100, 2),
    }


def payment_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """Compute usage, revenue and percentage distribution by payment
    method."""
    total_orders = df["Order_ID"].nunique()
    total_revenue = df["Sales"].sum()

    grouped = df.groupby("Payment_Mode", as_index=False).agg(
        Orders=("Order_ID", "nunique"),
        Revenue=("Sales", "sum"),
    )
    grouped["Revenue"] = grouped["Revenue"].round(2)
    grouped["Order_Share_Percent"] = (grouped["Orders"] / total_orders * 100).round(2)
    grouped["Revenue_Share_Percent"] = (grouped["Revenue"] / total_revenue * 100).round(2)
    grouped = grouped.sort_values("Revenue", ascending=False).reset_index(drop=True)

    return grouped


def run_full_analysis(df: pd.DataFrame) -> dict[str, object]:
    """Run every analysis function and return the combined results in a
    single dictionary, used by the reporting and visualization modules.
    """
    logger.info("Running full analysis suite on %d cleaned rows.", len(df))

    results = {
        "summary": overall_sales_summary(df),
        "products": product_analysis(df),
        "categories": category_analysis(df),
        "monthly": monthly_sales_analysis(df),
        "regions": regional_analysis(df),
        "customers": customer_analysis(df),
        "payments": payment_analysis(df),
        "yoy": year_over_year_analysis(df),
        "segmentation": customer_segmentation(df),
        "pareto": pareto_analysis(df),
    }

    results["consistency_warnings"] = run_consistency_checks(df, results)

    logger.info("Full analysis suite complete.")
    return results
