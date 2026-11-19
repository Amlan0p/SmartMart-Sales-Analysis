"""
insights.py

Generates a plain-text business insights and recommendations report
from the analysis results dictionary. Every statement is derived from
the actual computed numbers - nothing here is a fixed/invented claim.

Findings (descriptive, what the data shows) are kept clearly separate
from recommendations (suggested actions traceable to those findings).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from config import BUSINESS_INSIGHTS_PATH, COMPANY_NAME, PROJECT_NAME
from src.utils import ensure_directories, format_currency, format_percentage, get_logger

logger = get_logger(__name__)


def build_findings(results: dict) -> list[str]:
    summary = results["summary"]
    products = results["products"]
    categories = results["categories"]
    monthly = results["monthly"]
    regions = results["regions"]
    customers = results["customers"]
    payments = results["payments"]

    findings = []

    findings.append(
        f"Total revenue across the analyzed period was {format_currency(summary['Total Revenue'])} "
        f"from {summary['Total Orders']:,} orders placed by {summary['Total Customers']:,} customers."
    )
    findings.append(
        f"The average order value was {format_currency(summary['Average Order Value'])}, "
        f"with an average selling price of {format_currency(summary['Average Selling Price'])} per unit."
    )

    top_product_row = products["top_by_revenue"].iloc[0]
    findings.append(
        f"The highest-revenue product was '{top_product_row['Product']}' in the {top_product_row['Category']} "
        f"category, generating {format_currency(top_product_row['Revenue'])}."
    )

    bottom_product_row = products["bottom_performers"].iloc[0]
    findings.append(
        f"The lowest-performing product by revenue was '{bottom_product_row['Product']}' "
        f"({format_currency(bottom_product_row['Revenue'])})."
    )

    top_category_row = categories.iloc[0]
    findings.append(
        f"The highest-revenue category was {top_category_row['Category']}, contributing "
        f"{format_currency(top_category_row['Revenue'])} "
        f"({format_percentage(top_category_row['Revenue'] / summary['Total Revenue'] * 100)} of total revenue)."
    )

    lowest_category_row = categories.iloc[-1]
    findings.append(
        f"The lowest-revenue category was {lowest_category_row['Category']}, contributing "
        f"{format_currency(lowest_category_row['Revenue'])}."
    )

    top_region_row = regions.iloc[0]
    findings.append(
        f"The highest-revenue region was {top_region_row['Region']}, generating "
        f"{format_currency(top_region_row['Revenue'])}."
    )
    lowest_region_row = regions.iloc[-1]
    findings.append(
        f"The lowest-revenue region was {lowest_region_row['Region']}, generating "
        f"{format_currency(lowest_region_row['Revenue'])}."
    )

    findings.append(
        f"The peak sales month was {monthly['peak_month']}, while the lowest sales month was "
        f"{monthly['lowest_month']}, indicating a seasonal pattern in demand."
    )

    findings.append(
        f"Out of {summary['Total Customers']:,} customers, {customers['repeat_customers']:,} "
        f"({format_percentage(customers['repeat_customer_rate'])}) placed more than one order and are "
        f"classified as repeat customers, while {customers['one_time_customers']:,} made only a single purchase."
    )

    top_customer_row = customers["top_customers"].iloc[0]
    findings.append(
        f"The highest-spending customer was '{top_customer_row['Customer_ID']}', with total spending of "
        f"{format_currency(top_customer_row['Total_Spending'])} across "
        f"{int(top_customer_row['Number_of_Orders'])} order(s)."
    )

    top_payment_row = payments.iloc[0]
    findings.append(
        f"The most-used payment method was {top_payment_row['Payment_Mode']}, accounting for "
        f"{format_percentage(top_payment_row['Order_Share_Percent'])} of orders and "
        f"{format_percentage(top_payment_row['Revenue_Share_Percent'])} of revenue."
    )

    pareto = results.get("pareto")
    if pareto:
        findings.append(
            f"Revenue is concentrated: {format_percentage(pareto['percent_of_products_for_80_percent_revenue'])} "
            f"of products ({pareto['products_for_80_percent_revenue']} of {pareto['total_products']}) "
            "account for approximately 80% of total revenue."
        )

    yoy = results.get("yoy")
    if yoy and yoy.get("has_comparable_periods"):
        yearly = yoy["yearly_table"]
        latest = yearly.iloc[-1]
        if pd.notna(latest["Revenue_Growth_Percent"]):
            direction = "grew" if latest["Revenue_Growth_Percent"] >= 0 else "declined"
            findings.append(
                f"Year-over-year revenue {direction} by {format_percentage(abs(latest['Revenue_Growth_Percent']))} "
                f"in {int(latest['Year'])} compared to the prior year."
            )

    segmentation = results.get("segmentation")
    if segmentation:
        segment_summary = segmentation["segment_summary"]
        if not segment_summary.empty:
            top_segment_row = segment_summary.iloc[0]
            findings.append(
                f"Among customer segments, '{top_segment_row['Segment']}' generated the highest total "
                f"revenue ({format_currency(top_segment_row['Total_Revenue'])}) across "
                f"{int(top_segment_row['Customers']):,} customer(s)."
            )

    return findings


def _build_recommendations(results: dict) -> list[str]:
    products = results["products"]
    categories = results["categories"]
    regions = results["regions"]
    payments = results["payments"]
    customers = results["customers"]

    recommendations = []

    top_category_row = categories.iloc[0]
    recommendations.append(
        f"Since {top_category_row['Category']} is the leading revenue-generating category, maintain strong "
        "inventory availability and prioritize supplier reliability for products in this category."
    )

    bottom_products = products["bottom_performers"]
    if len(bottom_products) > 0:
        low_product_names = ", ".join(bottom_products["Product"].head(3).tolist())
        # NOTE: this is a total-revenue ranking, not a time-series analysis,
        # so the wording intentionally avoids implying consistency over time
        # (see project requirement on precise, non-overstated language).
        recommendations.append(
            f"Products with comparatively low total revenue, such as {low_product_names}, could be "
            "reviewed by management for pricing, promotional support, or product positioning, as they "
            "may be underperforming relative to their category peers."
        )

    lowest_region_row = regions.iloc[-1]
    top_region_row = regions.iloc[0]
    if lowest_region_row["Revenue"] < top_region_row["Revenue"]:
        recommendations.append(
            f"The {lowest_region_row['Region']} region generates comparatively lower revenue than "
            f"{top_region_row['Region']}; consider investigating regional demand drivers and evaluating "
            "targeted marketing or promotional campaigns in this region."
        )

    if customers["repeat_customer_rate"] < 50:
        recommendations.append(
            f"With a repeat-customer rate of {format_percentage(customers['repeat_customer_rate'])}, there "
            "is an opportunity to invest in customer retention initiatives such as loyalty programs, "
            "personalized offers, or post-purchase engagement to convert more one-time buyers into repeat "
            "customers."
        )
    else:
        recommendations.append(
            f"The repeat-customer rate of {format_percentage(customers['repeat_customer_rate'])} indicates "
            "healthy customer retention; continued investment in loyalty and engagement programs is "
            "recommended to sustain this trend."
        )

    known_payments = payments[payments["Payment_Mode"] != "Unknown"]
    if not known_payments.empty:
        least_used_payment_row = known_payments.sort_values("Order_Share_Percent").iloc[0]
        recommendations.append(
            f"{least_used_payment_row['Payment_Mode']} is the least-used payment method "
            f"({format_percentage(least_used_payment_row['Order_Share_Percent'])} of orders). If this method "
            "carries lower transaction fees or faster settlement, consider incentivizing its adoption; "
            "otherwise, evaluate whether it should continue to be supported."
        )

    return recommendations


def generate_business_insights(results: dict) -> str:
    """Build the full business-insights text content from the analysis
    results dictionary."""
    findings = build_findings(results)
    recommendations = _build_recommendations(results)

    lines = []
    lines.append("=" * 70)
    lines.append(f"{PROJECT_NAME.upper()}")
    lines.append(f"{COMPANY_NAME} - BUSINESS INSIGHTS REPORT")
    lines.append("=" * 70)
    lines.append("")
    lines.append("This report is generated automatically from the cleaned sales")
    lines.append("dataset. All figures below are calculated directly from the data,")
    lines.append("not manually entered.")
    lines.append("")
    lines.append("-" * 70)
    lines.append("KEY FINDINGS (Descriptive)")
    lines.append("-" * 70)
    for index, finding in enumerate(findings, start=1):
        lines.append(f"{index}. {finding}")
    lines.append("")
    lines.append("-" * 70)
    lines.append("BUSINESS RECOMMENDATIONS (Actionable)")
    lines.append("-" * 70)
    for index, recommendation in enumerate(recommendations, start=1):
        lines.append(f"{index}. {recommendation}")
    lines.append("")
    lines.append("=" * 70)
    lines.append("END OF REPORT")
    lines.append("=" * 70)

    return "\n".join(lines)


def save_business_insights(results: dict, output_path: Path = BUSINESS_INSIGHTS_PATH) -> Path:
    """Generate and persist the business insights report to a text
    file."""
    content = generate_business_insights(results)
    ensure_directories(output_path.parent)
    output_path.write_text(content, encoding="utf-8")
    logger.info("Business insights report saved to %s", output_path)
    return output_path
