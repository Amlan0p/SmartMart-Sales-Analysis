"""
dashboard_logic.py

Data access, filtering and aggregation for the Streamlit frontend
(``streamlit_app.py``). This module deliberately imports neither Streamlit
nor Plotly, so every number the dashboard shows can be tested with plain
pytest.

Nothing is calculated twice: KPIs, product, category, monthly, regional,
customer, payment and Pareto/ABC figures all come from the existing
functions in ``src/analysis.py``. This module only

* loads the processed CSV files that ``main.py`` writes (it never
  regenerates them),
* applies the sidebar filters,
* adds two small groupings the analysis module does not have (city-wise
  sales and the per-view segment table), and
* formats values (Indian-rupee style) and builds CSV downloads.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import pandas as pd

import config
from src import analysis

REQUIRED_SALES_COLUMNS = [
    "Order_ID", "Order_Date", "Customer_ID", "Product", "Category", "Quantity",
    "Unit_Price", "Sales", "Region", "City", "Payment_Mode", "Customer_Type",
]
NUMERIC_COLUMNS = ["Quantity", "Unit_Price", "Sales"]
TEXT_COLUMNS = ["Order_ID", "Customer_ID", "Product", "Category", "Region", "City",
                "Payment_Mode", "Customer_Type"]

PROCESSED_FILES = {
    "cleaned sales data": config.CLEANED_SALES_DATA_PATH,
    "customer segments": config.CUSTOMER_SEGMENTS_PATH,
    "product classification": config.PRODUCT_CLASSIFICATION_PATH,
}

MISSING_FILES_MESSAGE = (
    "The processed data files were not found. Generate them with the existing pipeline "
    "from the project folder:\n\n    python main.py\n\n"
    "(this writes data/processed/cleaned_sales_data.csv, customer_segments.csv and "
    "product_classification.csv), then reload this page."
)


class DataNotReadyError(FileNotFoundError):
    """Raised when one or more processed CSV files are missing."""


def missing_files() -> list[Path]:
    """Return the processed files that do not exist (paths come from config.py,
    so they are relative to the project folder, not the working directory)."""
    return [path for path in PROCESSED_FILES.values() if not Path(path).is_file()]


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------
def load_sales(path: Path | str | None = None) -> tuple[pd.DataFrame, dict]:
    """Load ``cleaned_sales_data.csv`` with safe types.

    Returns ``(dataframe, info)`` where ``info`` records how many rows were
    dropped because a date, amount or key could not be parsed. The pipeline's
    cleaned file normally has none, so ``dropped`` is normally 0.
    """
    path = Path(path) if path else Path(config.CLEANED_SALES_DATA_PATH)
    if not path.is_file():
        raise DataNotReadyError(f"{path} not found")
    raw = pd.read_csv(path)
    missing = [c for c in REQUIRED_SALES_COLUMNS if c not in raw.columns]
    if missing:
        raise ValueError(f"{path.name} is missing required column(s): {', '.join(missing)}")
    df = raw.copy()
    df["Order_Date"] = pd.to_datetime(df["Order_Date"], errors="coerce")
    for column in NUMERIC_COLUMNS:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    for column in TEXT_COLUMNS:
        df[column] = df[column].astype("string").str.strip()
    before = len(df)
    df = df.dropna(subset=["Order_Date", "Sales", "Quantity", "Customer_ID", "Product"])
    df = df[(df["Sales"] >= 0) & (df["Quantity"] >= 0)]
    df = df.reset_index(drop=True)
    df["Quantity"] = df["Quantity"].astype("int64")
    df["Year"] = df["Order_Date"].dt.year
    df["Month"] = df["Order_Date"].dt.month
    df["Month_Name"] = df["Order_Date"].dt.month_name()
    df["Quarter"] = df["Order_Date"].dt.quarter
    return df, {"rows_in_file": int(len(raw)), "dropped": int(before - len(df))}


def load_segments(path: Path | str | None = None) -> pd.DataFrame:
    path = Path(path) if path else Path(config.CUSTOMER_SEGMENTS_PATH)
    if not path.is_file():
        raise DataNotReadyError(f"{path} not found")
    seg = pd.read_csv(path)
    seg["Customer_ID"] = seg["Customer_ID"].astype("string").str.strip()
    return seg


def load_classification(path: Path | str | None = None) -> pd.DataFrame:
    path = Path(path) if path else Path(config.PRODUCT_CLASSIFICATION_PATH)
    if not path.is_file():
        raise DataNotReadyError(f"{path} not found")
    return pd.read_csv(path)


# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------
@dataclass
class Filters:
    """Sidebar filter state. An empty list means "all" for that field."""
    start: date | None = None
    end: date | None = None
    regions: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    products: list[str] = field(default_factory=list)
    payments: list[str] = field(default_factory=list)


def filter_options(df: pd.DataFrame) -> dict:
    return {
        "min_date": df["Order_Date"].min().date(),
        "max_date": df["Order_Date"].max().date(),
        "regions": sorted(df["Region"].dropna().unique().tolist()),
        "categories": sorted(df["Category"].dropna().unique().tolist()),
        "products": sorted(df["Product"].dropna().unique().tolist()),
        "payments": sorted(df["Payment_Mode"].dropna().unique().tolist()),
    }


def filter_sales(df: pd.DataFrame, f: Filters) -> pd.DataFrame:
    mask = pd.Series(True, index=df.index)
    if f.start is not None:
        mask &= df["Order_Date"] >= pd.Timestamp(f.start)
    if f.end is not None:
        mask &= df["Order_Date"] < pd.Timestamp(f.end) + pd.Timedelta(days=1)
    for column, values in (("Region", f.regions), ("Category", f.categories),
                           ("Product", f.products), ("Payment_Mode", f.payments)):
        if values:
            mask &= df[column].isin(values)
    return df[mask].reset_index(drop=True)


def describe_filters(f: Filters, options: dict) -> str:
    """One-line description of the active filters, for the page header."""
    parts = []
    if f.start and f.end and (f.start != options["min_date"] or f.end != options["max_date"]):
        parts.append(f"{f.start:%d %b %Y} to {f.end:%d %b %Y}")
    for label, values in (("Region", f.regions), ("Category", f.categories),
                          ("Product", f.products), ("Payment", f.payments)):
        if values:
            parts.append(f"{label}: {', '.join(values)}")
    return " | ".join(parts) if parts else "No filters applied (all data)"


# ---------------------------------------------------------------------------
# Aggregations (existing analysis functions + two small additions)
# ---------------------------------------------------------------------------
def city_sales(df: pd.DataFrame) -> pd.DataFrame:
    """City-wise revenue, orders and quantity (the analysis module has no city view)."""
    table = (df.groupby(["Region", "City"], as_index=False)
             .agg(Revenue=("Sales", "sum"), Orders=("Order_ID", "nunique"), Quantity=("Quantity", "sum")))
    table["Average_Order_Value"] = (table["Revenue"] / table["Orders"]).round(2)
    return table.sort_values("Revenue", ascending=False).reset_index(drop=True)


def segment_view(df: pd.DataFrame, segments: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """RFM segments (computed by Python over the whole period, read from
    customer_segments.csv) for the customers present in the filtered view.

    Returns ``(per_customer, summary)``. Revenue is the customer's revenue
    *inside the current filters*; the segment itself is not recomputed.
    """
    spend = df.groupby("Customer_ID", as_index=False).agg(
        Revenue_in_view=("Sales", "sum"), Orders_in_view=("Order_ID", "nunique"))
    per_customer = spend.merge(segments, on="Customer_ID", how="left")
    per_customer["Segment"] = per_customer["Segment"].fillna("Not segmented")
    summary = (per_customer.groupby("Segment", as_index=False)
               .agg(Customers=("Customer_ID", "nunique"), Revenue=("Revenue_in_view", "sum"))
               .sort_values("Customers", ascending=False).reset_index(drop=True))
    return per_customer, summary


def compute_views(df: pd.DataFrame, segments: pd.DataFrame, classification: pd.DataFrame) -> dict | None:
    """Everything the pages show, for the (already filtered) data.

    Returns ``None`` for an empty selection so the UI can show a message.
    """
    if df.empty:
        return None
    products = analysis.product_analysis(df)
    monthly = analysis.monthly_sales_analysis(df)
    customers = analysis.customer_analysis(df)
    pareto = analysis.pareto_analysis(df)
    per_customer, segment_summary = segment_view(df, segments)

    monthly_table = monthly["monthly_table"].sort_values(["Year", "Month"]).reset_index(drop=True)

    pareto_table = pareto["pareto_table"].merge(
        df[["Product", "Category"]].drop_duplicates("Product"), on="Product", how="left")
    static = classification[["Product", "ABC_Class"]].rename(columns={"ABC_Class": "ABC_Class_full_data"})
    pareto_table = pareto_table.merge(static, on="Product", how="left")

    orders_per_customer = (customers["customer_table"]["Number_of_Orders"].value_counts()
                           .sort_index().rename_axis("Orders_per_customer").reset_index(name="Customers"))
    return {
        "summary": analysis.overall_sales_summary(df),
        "products": products,
        "categories": analysis.category_analysis(df),
        "monthly_table": monthly_table,
        "peak_month": monthly["peak_month"],
        "lowest_month": monthly["lowest_month"],
        "regions": analysis.regional_analysis(df),
        "cities": city_sales(df),
        "customers": customers,
        "payments": analysis.payment_analysis(df),
        "pareto": pareto,
        "pareto_table": pareto_table,
        "segment_customers": per_customer,
        "segment_summary": segment_summary,
        "orders_per_customer": orders_per_customer,
    }


def data_overview(df: pd.DataFrame, load_info: dict | None = None) -> dict:
    """Row/column counts and data-quality facts for the *loaded* (unfiltered) data."""
    missing = df.isna().sum()
    return {
        "rows": int(len(df)),
        "columns": int(df.shape[1]),
        "date_min": df["Order_Date"].min().date(),
        "date_max": df["Order_Date"].max().date(),
        "customers": int(df["Customer_ID"].nunique()),
        "products": int(df["Product"].nunique()),
        "duplicate_order_ids": int(df["Order_ID"].duplicated().sum()),
        "missing_values": int(missing.sum()),
        "unknown_city_rows": int((df["City"] == "Unknown").sum()),
        "unknown_payment_rows": int((df["Payment_Mode"] == "Unknown").sum()),
        "rows_dropped_on_load": int((load_info or {}).get("dropped", 0)),
        "column_table": pd.DataFrame({
            "Column": df.columns, "Type": [str(t) for t in df.dtypes],
            "Missing": missing.values, "Distinct values": [int(df[c].nunique()) for c in df.columns]}),
    }


# ---------------------------------------------------------------------------
# Formatting and downloads
# ---------------------------------------------------------------------------
def _indian_grouping(integer_part: str) -> str:
    if len(integer_part) <= 3:
        return integer_part
    head, tail = integer_part[:-3], integer_part[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    return ",".join(groups + [tail])


def inr(value: float, decimals: int = 0) -> str:
    """Indian-rupee formatting with lakh/crore grouping, e.g. ₹18,90,24,946."""
    negative = value < 0
    text = f"{abs(value):.{decimals}f}"
    integer, _, fraction = text.partition(".")
    out = "₹" + _indian_grouping(integer) + (f".{fraction}" if fraction else "")
    return "-" + out if negative else out


def num(value: float) -> str:
    """Whole number with lakh/crore grouping, e.g. 14,970 or 1,23,456."""
    return ("-" if value < 0 else "") + _indian_grouping(f"{abs(round(value)):d}")


def inr_compact(value: float) -> str:
    """Short form for KPI cards: ₹18.90 Cr, ₹39.66 L, ₹12,627."""
    sign = "-" if value < 0 else ""
    v = abs(value)
    if v >= 1e7:
        return f"{sign}₹{v / 1e7:.2f} Cr"
    if v >= 1e5:
        return f"{sign}₹{v / 1e5:.2f} L"
    return f"{sign}{inr(v)}"


def to_csv_bytes(frame: pd.DataFrame) -> bytes:
    return frame.to_csv(index=False).encode("utf-8")


def kpi_frame(views: dict, filter_text: str) -> pd.DataFrame:
    """Headline KPIs as a tidy table for the summary-report download."""
    s = views["summary"]
    c = views["customers"]
    rows = [
        ("Filters applied", filter_text),
        ("Total Revenue", s["Total Revenue"]),
        ("Total Orders", s["Total Orders"]),
        ("Total Customers", s["Total Customers"]),
        ("Total Quantity Sold", s["Total Quantity Sold"]),
        ("Average Order Value", s["Average Order Value"]),
        ("Average Selling Price", s["Average Selling Price"]),
        ("Repeat customers (lifetime flag)", c["repeat_customers"]),
        ("One-time customers (lifetime flag)", c["one_time_customers"]),
        ("Peak revenue month", views["peak_month"]),
        ("Lowest revenue month", views["lowest_month"]),
    ]
    return pd.DataFrame(rows, columns=["Metric", "Value"])


def summary_report_frame(views: dict, filter_text: str) -> pd.DataFrame:
    """One long CSV: KPIs followed by the category, region, payment and product tables."""
    parts = [kpi_frame(views, filter_text).assign(Section="KPIs")]
    for section, table, key in (
        ("Category", views["categories"], "Category"),
        ("Region", views["regions"], "Region"),
        ("Payment mode", views["payments"], "Payment_Mode"),
        ("Product", views["products"]["all_products"], "Product"),
    ):
        long = table.melt(id_vars=[key], var_name="Metric", value_name="Value").rename(columns={key: "Item"})
        long["Section"] = section
        parts.append(long)
    out = pd.concat(parts, ignore_index=True)
    out["Item"] = out.get("Item", pd.Series(dtype="object")).fillna("")
    return out[["Section", "Item", "Metric", "Value"]]
