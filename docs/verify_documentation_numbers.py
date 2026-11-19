"""
verify_documentation_numbers.py

Consistency check: every key figure computed from the project's real outputs
must appear in the text of the rendered PDF. Run after build_documentation.py:

    python docs/verify_documentation_numbers.py
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

DOCS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(DOCS_DIR))

from doc_context import build_context, money, pct, whole  # noqa: E402


def main() -> int:
    pdf = DOCS_DIR.parent / "documentation" / "SmartMart_Final_Report.pdf"
    text = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True, check=True).stdout
    flat = re.sub(r"\s+", " ", text)
    ctx = build_context()
    r, s = ctx.results, ctx.results["summary"]
    expectations = {
        "Total revenue": money(s["Total Revenue"]),
        "Total orders": whole(s["Total Orders"]),
        "Total customers": whole(s["Total Customers"]),
        "Units sold": whole(s["Total Quantity Sold"]),
        "Average order value": money(s["Average Order Value"]),
        "Average selling price": money(s["Average Selling Price"]),
        "Raw rows": whole(len(ctx.raw)),
        "Cleaned rows": whole(len(ctx.df)),
        "Top product revenue": money(r["products"]["top_by_revenue"].iloc[0].Revenue),
        "Top category share": pct(r["categories"].iloc[0].Revenue_Percentage),
        "Top region revenue": money(r["regions"].iloc[0].Revenue),
        "Lowest region revenue": money(r["regions"].iloc[-1].Revenue),
        "Peak month": r["monthly"]["peak_month"],
        "Lowest month": r["monthly"]["lowest_month"],
        "YoY growth": f"{r['yoy']['yearly_table'].iloc[-1].Revenue_Growth_Percent:.1f}%",
        "Repeat customers": whole(r["customers"]["repeat_customers"]),
        "One-time customers": whole(r["customers"]["one_time_customers"]),
        "Top customer spend": money(r["customers"]["top_customers"].iloc[0].Total_Spending),
        "Products for 80%": f"{r['pareto']['products_for_80_percent_revenue']} of {r['pareto']['total_products']} products",
        "Tests passed": f"{sum(1 for l in ctx.test_lines if l.startswith('PASS'))} passed",
    }
    for row in r["segmentation"]["segment_summary"].itertuples():
        expectations[f"Segment {row.Segment} customers"] = whole(row.Customers)
        expectations[f"Segment {row.Segment} revenue"] = money(row.Total_Revenue, 0)
    for row in r["regions"].itertuples():
        expectations[f"Region {row.Region} revenue"] = money(row.Revenue, 0)
    for row in r["categories"].itertuples():
        expectations[f"Category {row.Category} revenue"] = money(row.Revenue, 0)

    missing = {name: value for name, value in expectations.items() if value not in flat}
    print(f"Figures checked: {len(expectations)} | found in PDF: {len(expectations) - len(missing)} | missing: {len(missing)}")
    for name, value in missing.items():
        print(f"  MISSING: {name} -> {value}")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
