"""
reconcile_python_vs_dax.py

Reconciles the KPIs produced by the Python pipeline (src/analysis.py) with an
independent pandas EMULATION of the DAX measures in powerbi/dax/measures.dax.

Run from the project root (after `python main.py`):

    python powerbi/verification/reconcile_python_vs_dax.py

HONESTY NOTE
------------
This is NOT a Power BI run. Power BI Desktop is not available in the
environment that produced this file. The "DAX-equivalent" column is computed by
re-implementing each measure's logic from first principles on the model tables
(Fact_Sales + Dim_Date + Dim_Customer + Dim_Product, joined exactly as the Power
BI relationships would join them). It verifies that:

  1. the data model is sound (unique dimension keys, no orphan sales rows,
     contiguous calendar), and
  2. the *definitions* used by the DAX measures reproduce the Python KPIs.

It cannot detect a syntax error or an engine-specific behaviour in DAX. The
person building the report must still compare the real card values in Power BI
Desktop against the 'Python value' column of the generated report.

Outputs: powerbi/verification/reconciliation_report.md and reconciliation_results.csv
Exit code: 0 = no unexplained mismatch, 1 = at least one mismatch.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

import config  # noqa: E402
from src import analysis  # noqa: E402

VERIFICATION_DIR = PROJECT_ROOT / "powerbi" / "verification"
TOLERANCE_MONEY = 0.01      # rupees
TOLERANCE_RATIO = 1e-9

rows: list[dict] = []


def record(group: str, measure: str, python_value, dax_value, note: str = "", tol: float = TOLERANCE_MONEY) -> None:
    if isinstance(python_value, str) or isinstance(dax_value, str):
        match = str(python_value) == str(dax_value)
    else:
        match = abs(float(python_value) - float(dax_value)) <= tol
    rows.append({
        "Group": group, "Measure": measure, "Python value": python_value,
        "DAX-equivalent value": dax_value, "Match": "YES" if match else "NO", "Note": note,
    })


# ---------------------------------------------------------------------------
# Build the model exactly as the Power Query / DAX files describe it
# ---------------------------------------------------------------------------
def load_model():
    sales_raw = pd.read_csv(config.CLEANED_SALES_DATA_PATH, parse_dates=["Order_Date"])
    # sales_data.m removes these columns (single source of truth elsewhere)
    fact = sales_raw.drop(columns=["Year", "Month", "Month_Name", "Quarter", "Category", "Order_Value"])
    dim_customer = pd.read_csv(config.CUSTOMER_SEGMENTS_PATH)
    dim_product = pd.read_csv(config.PRODUCT_CLASSIFICATION_PATH)

    first_year, last_year = fact["Order_Date"].dt.year.min(), fact["Order_Date"].dt.year.max()
    dates = pd.date_range(f"{first_year}-01-01", f"{last_year}-12-31", freq="D")
    dim_date = pd.DataFrame({"Date": dates})
    dim_date["Year"] = dim_date["Date"].dt.year
    dim_date["Month Number"] = dim_date["Date"].dt.month
    dim_date["Year-Month"] = dim_date["Date"].dt.strftime("%Y-%m")
    return sales_raw, fact, dim_customer, dim_product, dim_date


def check_model(fact, dim_customer, dim_product, dim_date) -> None:
    """Relationship integrity: what Power BI needs for 1:many, single-direction."""
    record("Model integrity", "Dim_Customer[Customer_ID] unique (1 side)", 1, int(dim_customer["Customer_ID"].is_unique), tol=0)
    record("Model integrity", "Dim_Product[Product] unique (1 side)", 1, int(dim_product["Product"].is_unique), tol=0)
    record("Model integrity", "Dim_Date[Date] unique and contiguous", 1,
           int(dim_date["Date"].is_unique and (dim_date["Date"].diff().dropna() == pd.Timedelta(days=1)).all()), tol=0)
    record("Model integrity", "Orphan Fact_Sales rows (Customer_ID not in Dim_Customer)", 0,
           int((~fact["Customer_ID"].isin(dim_customer["Customer_ID"])).sum()), tol=0)
    record("Model integrity", "Orphan Fact_Sales rows (Product not in Dim_Product)", 0,
           int((~fact["Product"].isin(dim_product["Product"])).sum()), tol=0)
    record("Model integrity", "Orphan Fact_Sales rows (Order_Date not in Dim_Date)", 0,
           int((~fact["Order_Date"].isin(dim_date["Date"])).sum()), tol=0)
    record("Model integrity", "Customers in Dim_Customer with no sales (unused dimension rows)", 0,
           int((~dim_customer["Customer_ID"].isin(fact["Customer_ID"])).sum()), tol=0)
    record("Model integrity", "Fact_Sales[Order_ID] unique (grain = one row per order)", 1, int(fact["Order_ID"].is_unique), tol=0)


# ---------------------------------------------------------------------------
# DAX emulation helpers (each mirrors one measure in measures.dax)
# ---------------------------------------------------------------------------
def dax_core(f: pd.DataFrame) -> dict:
    revenue = f["Sales"].sum()
    orders = f["Order_ID"].nunique()
    customers = f["Customer_ID"].nunique()
    units = f["Quantity"].sum()
    return {
        "Total Revenue": round(revenue, 2), "Total Orders": orders, "Total Customers": customers,
        "Total Units Sold": units,
        "Average Order Value": round(revenue / orders, 2) if orders else None,
        "Average Selling Price": round(revenue / units, 2) if units else None,
    }


def dax_repeat_customers_in_context(f: pd.DataFrame, min_orders: int = 2) -> int:
    """[Repeat Customers]: SUMX(VALUES(Customer_ID), distinct orders in context >= 2)."""
    return int((f.groupby("Customer_ID")["Order_ID"].nunique() >= min_orders).sum())


def dax_repeat_customers_lifetime(f: pd.DataFrame, dim_customer: pd.DataFrame, min_orders: int = 2) -> int:
    """[Repeat Customers (Lifetime Flag)]: customers in context whose Dim_Customer[Frequency] >= 2."""
    lifetime = dim_customer.set_index("Customer_ID")["Frequency"]
    ids = f["Customer_ID"].unique()
    return int((lifetime.loc[ids] >= min_orders).sum())


def dax_cumulative_abc(f: pd.DataFrame, dim_product: pd.DataFrame, rounded: bool) -> pd.DataFrame:
    """[Cumulative Revenue %] and [ABC Class (Dynamic)] for the products in context."""
    revenue = f.groupby("Product")["Sales"].sum().sort_values(ascending=False)
    cumulative = revenue.cumsum() / revenue.sum() * 100
    if rounded:
        cumulative = cumulative.round(2)
    classes = cumulative.apply(lambda c: "A" if c <= config.ABC_A_THRESHOLD else ("B" if c <= config.ABC_B_THRESHOLD else "C"))
    return pd.DataFrame({"Revenue": revenue, "Cumulative_Percent": cumulative, "ABC": classes})


def main() -> int:
    sales_raw, fact, dim_customer, dim_product, dim_date = load_model()
    results = analysis.run_full_analysis(sales_raw)  # Python side, from the same cleaned CSV
    summary = results["summary"]

    check_model(fact, dim_customer, dim_product, dim_date)

    # ---- 1. Headline KPIs ---------------------------------------------------
    dax = dax_core(fact)
    for name in ["Total Revenue", "Total Orders", "Total Customers", "Total Units Sold",
                 "Average Order Value", "Average Selling Price"]:
        python_key = {"Total Units Sold": "Total Quantity Sold"}.get(name, name)
        record("Headline KPIs", name, summary[python_key], dax[name])

    # ---- 2. Monthly revenue (Dim_Date[Year-Month]) ---------------------------
    merged = fact.merge(dim_date, left_on="Order_Date", right_on="Date", how="left", validate="many_to_one")
    dax_monthly = merged.groupby("Year-Month")["Sales"].sum()
    python_monthly = results["monthly"]["monthly_table"].copy()
    python_monthly["Key"] = python_monthly["Year"].astype(str) + "-" + python_monthly["Month"].astype(str).str.zfill(2)
    python_monthly = python_monthly.set_index("Key")["Revenue"]
    record("Monthly revenue", "Number of months", len(python_monthly), len(dax_monthly), tol=0)
    max_gap = float((python_monthly - dax_monthly.reindex(python_monthly.index)).abs().max())
    record("Monthly revenue", "Largest absolute difference across all 24 months (INR)", 0.0, round(max_gap, 4))
    peak = dax_monthly.idxmax()
    low = dax_monthly.idxmin()
    py_peak = pd.to_datetime(results["monthly"]["peak_month"], format="%B %Y").strftime("%Y-%m")
    py_low = pd.to_datetime(results["monthly"]["lowest_month"], format="%B %Y").strftime("%Y-%m")
    record("Monthly revenue", "Peak Revenue Month", py_peak, peak)
    record("Monthly revenue", "Lowest Revenue Month", py_low, low)

    # ---- 3. Category / Region / Payment / Product ----------------------------
    with_product = fact.merge(dim_product[["Product", "Category", "ABC_Class"]], on="Product", how="left", validate="many_to_one")
    dax_category = with_product.groupby("Category")["Sales"].sum()
    for _, row in results["categories"].iterrows():
        record("Category revenue", row["Category"], row["Revenue"], round(dax_category[row["Category"]], 2))
        share = dax_category[row["Category"]] / dax_category.sum() * 100
        record("Category contribution %", row["Category"], row["Revenue_Percentage"], round(share, 2), tol=0.005)
    dax_region = fact.groupby("Region")["Sales"].sum()
    dax_region_orders = fact.groupby("Region")["Order_ID"].nunique()
    for _, row in results["regions"].iterrows():
        record("Regional revenue", row["Region"], row["Revenue"], round(dax_region[row["Region"]], 2))
        record("Regional orders", row["Region"], row["Orders"], dax_region_orders[row["Region"]], tol=0)
        record("Regional AOV", row["Region"], row["Average_Order_Value"],
               round(dax_region[row["Region"]] / dax_region_orders[row["Region"]], 2))
    record("Regional revenue", "Highest Performing Region", results["regions"].iloc[0]["Region"], dax_region.idxmax())
    record("Regional revenue", "Lowest Performing Region", results["regions"].iloc[-1]["Region"], dax_region.idxmin())
    dax_payment = fact.groupby("Payment_Mode")["Sales"].sum()
    for _, row in results["payments"].iterrows():
        record("Payment revenue", row["Payment_Mode"], row["Revenue"], round(dax_payment[row["Payment_Mode"]], 2))
    dax_product = fact.groupby("Product")["Sales"].sum()
    for _, row in results["products"]["top_by_revenue"].head(5).iterrows():
        record("Top 5 products", row["Product"], row["Revenue"], round(dax_product[row["Product"]], 2))
    record("Products", "Lowest product by revenue", results["products"]["bottom_performers"].iloc[0]["Product"], dax_product.idxmin())

    # ---- 4. Year-over-year ---------------------------------------------------
    yearly = merged.groupby("Year")["Sales"].sum()
    latest = yearly.index.max()
    dax_yoy = round((yearly[latest] / yearly[latest - 1] - 1) * 100, 1)
    python_yoy = results["yoy"]["yearly_table"].set_index("Year").loc[latest, "Revenue_Growth_Percent"]
    record("Year-over-year", f"[Latest Year YoY Growth %] ({latest} vs {latest - 1}), shown to 1 dp", python_yoy, dax_yoy, tol=0.001)

    # ---- 5. Customers --------------------------------------------------------
    py_customers = results["customers"]
    record("Customers", "Repeat Customers (context-sensitive measure, no filters)", py_customers["repeat_customers"],
           dax_repeat_customers_in_context(fact), tol=0)
    record("Customers", "Repeat Customers (Lifetime Flag measure, no filters)", py_customers["repeat_customers"],
           dax_repeat_customers_lifetime(fact, dim_customer), tol=0)
    record("Customers", "One-time Customers", py_customers["one_time_customers"],
           fact["Customer_ID"].nunique() - dax_repeat_customers_in_context(fact), tol=0)
    record("Customers", "Repeat Customer Rate % (2 dp)", py_customers["repeat_customer_rate"],
           round(dax_repeat_customers_in_context(fact) / fact["Customer_ID"].nunique() * 100, 2), tol=0.005)
    top_customer = fact.groupby("Customer_ID")["Sales"].sum().sort_values(ascending=False)
    record("Customers", "Top customer ID", py_customers["top_customers"].iloc[0]["Customer_ID"], top_customer.index[0])
    record("Customers", "Top customer revenue", py_customers["top_customers"].iloc[0]["Total_Spending"], round(top_customer.iloc[0], 2))

    # ---- 6. Segmentation (Dim_Customer joined to Fact_Sales) -----------------
    with_segment = fact.merge(dim_customer[["Customer_ID", "Segment"]], on="Customer_ID", how="left", validate="many_to_one")
    seg_revenue = with_segment.groupby("Segment")["Sales"].sum()
    seg_customers = with_segment.groupby("Segment")["Customer_ID"].nunique()
    for _, row in results["segmentation"]["segment_summary"].iterrows():
        record("Segmentation", f"{row['Segment']} - customers", row["Customers"], seg_customers[row["Segment"]], tol=0)
        record("Segmentation", f"{row['Segment']} - revenue", row["Total_Revenue"], round(seg_revenue[row["Segment"]], 2))

    # ---- 7. Pareto / ABC -----------------------------------------------------
    pareto = results["pareto"]
    exact = dax_cumulative_abc(fact, dim_product, rounded=False)
    rounded = dax_cumulative_abc(fact, dim_product, rounded=True)
    py_classes = pareto["pareto_table"].set_index("Product")["ABC_Class"]
    record("Pareto / ABC", "Products needed for ~80% of revenue", pareto["products_for_80_percent_revenue"],
           int((exact["Cumulative_Percent"] <= 80).sum()) + 1, tol=0,
           note="Python counts the product that first crosses 80%.")
    # The shipped [ABC Class (Dynamic)] measure rounds the cumulative share to
    # 2 dp (as Python does), so the rounded emulation is the one that is compared.
    record("Pareto / ABC", "ABC class mismatches: Python vs [ABC Class (Dynamic)] (rounded as shipped)", 0,
           int((rounded["ABC"] != py_classes.reindex(rounded.index)).sum()), tol=0)
    for _, row in pareto["abc_summary"].iterrows():
        record("Pareto / ABC", f"Class {row['ABC_Class']} - revenue", row["Revenue"],
               round(rounded[rounded["ABC"] == row["ABC_Class"]]["Revenue"].sum(), 2))
        record("Pareto / ABC", f"Class {row['ABC_Class']} - products", row["Products"],
               int((rounded["ABC"] == row["ABC_Class"]).sum()), tol=0)

    # ---- 8. Slicer scenarios: Python on filtered data vs DAX emulation ---------
    scenarios = {
        "Region = East": lambda d: d["Region"] == "East",
        "Year = 2024": lambda d: d["Order_Date"].dt.year == 2024,
        "Category = Electronics": lambda d: d["Category"] == "Electronics",
        "Payment_Mode = UPI AND Region = South": lambda d: (d["Payment_Mode"] == "UPI") & (d["Region"] == "South"),
    }
    for label, predicate in scenarios.items():
        subset_python = sales_raw[predicate(sales_raw)]
        # Build the filtered fact slice through the model so Category comes from Dim_Product
        model = with_product.copy()
        subset_model = model[predicate(model)]
        py = analysis.overall_sales_summary(subset_python)
        dx = dax_core(subset_model)
        for name in ["Total Revenue", "Total Orders", "Total Customers", "Total Units Sold",
                     "Average Order Value", "Average Selling Price"]:
            python_key = {"Total Units Sold": "Total Quantity Sold"}.get(name, name)
            record(f"Slicer: {label}", name, py[python_key], dx[name])

    # ---- 9. Documented, expected differences (not errors) --------------------
    filtered = fact[fact["Order_Date"].dt.year == 2024]
    record("Expected difference", "Repeat Customers, Year=2024: context-sensitive [Repeat Customers]",
           py_customers["repeat_customers"], dax_repeat_customers_in_context(filtered), tol=0,
           note="Different by design: counts customers with >=2 orders INSIDE 2024 only; Python figure is whole-period.")
    record("Expected difference", "Repeat Customers, Year=2024: [Repeat Customers (Lifetime Flag)]",
           py_customers["repeat_customers"], dax_repeat_customers_lifetime(filtered, dim_customer), tol=0,
           note="Lifetime flag restricted to customers active in 2024; equals Python's definition for those customers.")

    unrounded_gap = exact[exact["ABC"] != py_classes.reindex(exact.index)]
    record("Expected difference", "ABC class mismatches if cumulative % were NOT rounded (0 = none)", 0,
           len(unrounded_gap), tol=0,
           note="Boundary case: " + ", ".join(f"{p} ({exact.loc[p, 'Cumulative_Percent']:.3f}% -> {exact.loc[p, 'ABC']} unrounded vs "
                                             f"{py_classes[p]} in Python)" for p in unrounded_gap.index))

    frame = pd.DataFrame(rows)
    frame.to_csv(VERIFICATION_DIR / "reconciliation_results.csv", index=False)
    write_markdown(frame)

    expected_groups = {"Expected difference"}
    unexplained = frame[(frame["Match"] == "NO") & (~frame["Group"].isin(expected_groups))]
    print(f"Checks run: {len(frame)} | matched: {(frame['Match'] == 'YES').sum()} | "
          f"mismatched: {(frame['Match'] == 'NO').sum()} "
          f"({len(unexplained)} unexplained, {(frame['Match'] == 'NO').sum() - len(unexplained)} expected-by-design)")
    if len(unexplained):
        print(unexplained.to_string(index=False))
        return 1
    return 0


def write_markdown(frame: pd.DataFrame) -> None:
    def fmt(value):
        if isinstance(value, float):
            return f"{value:,.2f}"
        if isinstance(value, (int,)) or hasattr(value, "item"):
            try:
                return f"{value:,}"
            except (TypeError, ValueError):
                return str(value)
        return str(value)

    lines = [
        "# Python vs DAX-equivalent reconciliation report",
        "",
        "> **Read this first.** The 'DAX-equivalent value' column was computed in pandas by re-implementing the",
        "> logic of each measure in `powerbi/dax/measures.dax` on the same model tables and relationships.",
        "> It was **not** produced by Power BI. After building the report, compare the real card values in",
        "> Power BI Desktop with the 'Python value' column below.",
        "",
        f"Total checks: **{len(frame)}** | Matched: **{(frame['Match'] == 'YES').sum()}** | "
        f"Mismatched: **{(frame['Match'] == 'NO').sum()}**",
        "",
    ]
    for group, block in frame.groupby("Group", sort=False):
        lines += [f"## {group}", "", "| Measure | Python value | DAX-equivalent | Match | Note |", "|---|---:|---:|:---:|---|"]
        for _, r in block.iterrows():
            lines.append(f"| {r['Measure']} | {fmt(r['Python value'])} | {fmt(r['DAX-equivalent value'])} | {r['Match']} | {r['Note']} |")
        lines.append("")
    (VERIFICATION_DIR / "reconciliation_report.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
