"""
SmartMart Sales Performance Analytics - Streamlit frontend (classic six-page view, kept intact).

Run from the project folder:

    python -m pip install -r requirements.txt
    python -m streamlit run streamlit_app.py

This is an additional frontend for the existing pipeline. It reads the processed
CSV files written by ``python main.py`` (it never regenerates data), applies the
sidebar filters, and reuses the functions in ``src/analysis.py`` for every
figure. Data access, filtering and aggregation live in ``src/dashboard_logic.py``
(no Streamlit/Plotly imports, covered by tests/test_dashboard_logic.py); this file
only lays out the pages and draws the charts.
"""

from __future__ import annotations

import inspect
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
if str(PROJECT_DIR) not in sys.path:  # make `config` and `src` importable from any working directory
    sys.path.insert(0, str(PROJECT_DIR))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src import dashboard_logic as L

# ---------------------------------------------------------------------------
# Page setup and look
# ---------------------------------------------------------------------------
st.set_page_config(page_title="SmartMart Sales Analytics", page_icon="📊", layout="wide",
                   initial_sidebar_state="expanded")

BLUE, GREEN, NAVY, GREY, AMBER, RED = "#3669AB", "#69A147", "#1B3A5C", "#8795A8", "#E0A030", "#C0504D"
PALETTE = [BLUE, GREEN, AMBER, "#7F6BB0", "#4BA3A8", "#D2691E", GREY, RED]
PAGES = ["Executive Overview", "Product Performance", "Regional Performance",
         "Customer Analytics", "Payment Analysis", "Data & About"]

st.markdown(
    """
    <style>
    .block-container {padding-top: 1.6rem; padding-bottom: 2rem; max-width: 1400px;}
    h1, h2, h3 {color: #1B3A5C;}
    div[data-testid="stMetric"] {background: #F4F7FB; border: 1px solid #D9E2EC; border-left: 5px solid #3669AB;
        border-radius: 8px; padding: 12px 16px;}
    div[data-testid="stMetricLabel"] {color: #5B6B7F;}
    div[data-testid="stMetricValue"] {color: #1B3A5C; font-size: 1.7rem;}
    section[data-testid="stSidebar"] {border-right: 1px solid #D9E2EC;}
    .sm-note {color: #5B6B7F; font-size: 0.86rem;}
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
def _stretch(func) -> dict:
    """Full-width keyword that works on old and new Streamlit versions
    (``use_container_width`` was replaced by ``width="stretch"``)."""
    params = inspect.signature(func).parameters
    return {"width": "stretch"} if "width" in params else {"use_container_width": True}


def plain(frame: pd.DataFrame) -> pd.DataFrame:
    """Copy with text columns as plain ``object`` so Plotly handles them on any pandas version."""
    out = frame.copy()
    for column in out.columns:
        if pd.api.types.is_string_dtype(out[column]) and not pd.api.types.is_numeric_dtype(out[column]):
            out[column] = out[column].astype(object)
    return out


def chart(fig: go.Figure, height: int = 380) -> None:
    fig.update_layout(template="plotly_white", height=height, margin=dict(l=10, r=10, t=50, b=10),
                      font=dict(family="Segoe UI, Arial, sans-serif", color=NAVY),
                      title=dict(font=dict(size=16)), legend=dict(title_text=""))
    st.plotly_chart(fig, **_stretch(st.plotly_chart))


def table(frame: pd.DataFrame, money: tuple[str, ...] = (), percent: tuple[str, ...] = (),
          whole: tuple[str, ...] = (), height: int | None = None) -> None:
    """Sortable table (click a column header) with rupee/percent formatting."""
    config_map = {}
    for column in money:
        if column in frame.columns:
            config_map[column] = st.column_config.NumberColumn(column.replace("_", " "), format="₹%.2f")
    for column in percent:
        if column in frame.columns:
            config_map[column] = st.column_config.NumberColumn(column.replace("_", " "), format="%.2f%%")
    for column in whole:
        if column in frame.columns:
            config_map[column] = st.column_config.NumberColumn(column.replace("_", " "), format="%d")
    kwargs = dict(hide_index=True, column_config=config_map, **_stretch(st.dataframe))
    if height:
        kwargs["height"] = height
    st.dataframe(plain(frame), **kwargs)


def download(label: str, frame: pd.DataFrame, file_name: str, key: str) -> None:
    st.download_button(label, data=L.to_csv_bytes(frame), file_name=file_name, mime="text/csv", key=key)


# ---------------------------------------------------------------------------
# Data loading (cached; the CSV files are read, never regenerated)
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner="Loading project data...")
def load_all(signature: tuple) -> tuple:
    """``signature`` (file modification times) is only a cache key: the cache
    refreshes when ``python main.py`` rewrites the files."""
    sales, info = L.load_sales()
    return sales, info, L.load_segments(), L.load_classification()


absent = L.missing_files()
if absent:
    st.title("SmartMart Sales Analytics")
    st.error("Processed data files are missing:\n\n" + "\n".join(f"- `{p.relative_to(PROJECT_DIR)}`" for p in absent))
    st.code(L.MISSING_FILES_MESSAGE, language="text")
    st.stop()

try:
    sales_all, load_info, segments, classification = load_all(
        tuple(int(Path(p).stat().st_mtime) for p in L.PROCESSED_FILES.values()))
except (ValueError, OSError) as error:
    st.title("SmartMart Sales Analytics")
    st.error(f"The processed data could not be read: {error}")
    st.code(L.MISSING_FILES_MESSAGE, language="text")
    st.stop()

options = L.filter_options(sales_all)


# ---------------------------------------------------------------------------
# Sidebar: navigation, global filters, reset, downloads
# ---------------------------------------------------------------------------
def reset_filters() -> None:
    st.session_state["f_date"] = (options["min_date"], options["max_date"])
    for key in ("f_region", "f_category", "f_product", "f_payment"):
        st.session_state[key] = []


st.session_state.setdefault("f_date", (options["min_date"], options["max_date"]))
for _key in ("f_region", "f_category", "f_product", "f_payment"):
    st.session_state.setdefault(_key, [])

with st.sidebar:
    st.markdown("### 📊 SmartMart")
    st.caption("Sales Performance Analytics · Cronus Consultants")
    page = st.radio("Navigate", PAGES, key="page")
    st.divider()
    st.markdown("**Filters** (apply to every page)")
    st.date_input("Date range", min_value=options["min_date"], max_value=options["max_date"], key="f_date")
    st.multiselect("Region", options["regions"], key="f_region", placeholder="All regions")
    st.multiselect("Category", options["categories"], key="f_category", placeholder="All categories")
    st.multiselect("Product", options["products"], key="f_product", placeholder="All products")
    st.multiselect("Payment mode", options["payments"], key="f_payment", placeholder="All payment modes")
    st.button("Reset filters", on_click=reset_filters, key="reset_button")

selected = st.session_state["f_date"]
if isinstance(selected, (tuple, list)) and len(selected) == 2:
    start, end = selected
elif isinstance(selected, (tuple, list)) and len(selected) == 1:
    start, end = selected[0], options["max_date"]  # user is part-way through picking a range
else:
    start, end = selected, selected
filters = L.Filters(start=start, end=end, regions=list(st.session_state["f_region"]),
                    categories=list(st.session_state["f_category"]), products=list(st.session_state["f_product"]),
                    payments=list(st.session_state["f_payment"]))

sales = L.filter_sales(sales_all, filters)
views = L.compute_views(sales, segments, classification)
filter_text = L.describe_filters(filters, options)

with st.sidebar:
    st.divider()
    st.markdown("**Downloads**")
    st.download_button("Filtered sales data (CSV)", data=L.to_csv_bytes(sales), file_name="smartmart_filtered_sales.csv",
                       mime="text/csv", key="dl_sales")
    if views is not None:
        st.download_button("Summary report (CSV)", data=L.to_csv_bytes(L.summary_report_frame(views, filter_text)),
                           file_name="smartmart_summary_report.csv", mime="text/csv", key="dl_summary")
    st.caption(f"{L.num(len(sales))} of {L.num(len(sales_all))} orders selected")

st.title(page)
st.markdown(f"<span class='sm-note'>{filter_text}</span>", unsafe_allow_html=True)

if views is None and page != "Data & About":
    st.warning("No orders match the current filters. Widen the date range or click **Reset filters** in the sidebar.")
    st.stop()


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------
def page_executive() -> None:
    s = views["summary"]
    cols = st.columns(5)
    cols[0].metric("Total Revenue", L.inr_compact(s["Total Revenue"]), help=L.inr(s["Total Revenue"], 2))
    cols[1].metric("Total Orders", L.num(s["Total Orders"]))
    cols[2].metric("Total Customers", L.num(s["Total Customers"]))
    cols[3].metric("Total Quantity Sold", L.num(s["Total Quantity Sold"]))
    cols[4].metric("Average Order Value", L.inr(s["Average Order Value"]))

    monthly = plain(views["monthly_table"])
    fig = px.line(monthly, x="Period", y="Revenue", markers=True, title="Monthly revenue trend",
                  labels={"Period": "Month", "Revenue": "Revenue (₹)"}, color_discrete_sequence=[BLUE])
    fig.update_xaxes(categoryorder="array", categoryarray=monthly["Period"].tolist(), tickangle=-45)
    fig.update_yaxes(tickprefix="₹", tickformat=",.0f")
    chart(fig, 400)
    st.caption(f"Peak month: {views['peak_month']} · Lowest month: {views['lowest_month']} (months with sales in the current selection)")

    left, right = st.columns(2)
    regions = plain(views["regions"]).sort_values("Revenue", ascending=False)
    fig = px.bar(regions, x="Region", y="Revenue", title="Revenue by region", color_discrete_sequence=[BLUE],
                 labels={"Revenue": "Revenue (₹)"})
    fig.update_yaxes(tickprefix="₹", tickformat=",.0f")
    with left:
        chart(fig)
    categories = plain(views["categories"])
    fig = px.pie(categories, names="Category", values="Revenue", hole=0.45, title="Sales by category (share of revenue)",
                 color_discrete_sequence=PALETTE)
    fig.update_traces(textposition="inside", textinfo="percent+label")
    with right:
        chart(fig)


def page_products() -> None:
    products = views["products"]
    all_products = plain(products["all_products"]).sort_values("Revenue", ascending=False)

    fig = px.bar(all_products, x="Revenue", y="Product", color="Category", orientation="h", title="Product-wise revenue",
                 labels={"Revenue": "Revenue (₹)"}, color_discrete_sequence=PALETTE)
    fig.update_yaxes(categoryorder="total ascending")
    fig.update_xaxes(tickprefix="₹", tickformat=",.0f")
    chart(fig, max(380, 22 * len(all_products) + 120))

    top = plain(products["top_by_revenue"]).sort_values("Revenue", ascending=True)
    bottom = plain(products["bottom_performers"]).sort_values("Revenue", ascending=False)
    left, right = st.columns(2)
    fig = px.bar(top, x="Revenue", y="Product", orientation="h", title=f"Top {len(top)} products by revenue",
                 color_discrete_sequence=[BLUE], labels={"Revenue": "Revenue (₹)"})
    fig.update_xaxes(tickprefix="₹", tickformat=",.0f")
    with left:
        chart(fig)
    fig = px.bar(bottom, x="Revenue", y="Product", orientation="h", title=f"Bottom {len(bottom)} products by revenue",
                 color_discrete_sequence=[AMBER], labels={"Revenue": "Revenue (₹)"})
    fig.update_xaxes(tickprefix="₹", tickformat=",.0f")
    with right:
        chart(fig)

    left, right = st.columns(2)
    categories = plain(views["categories"]).sort_values("Revenue", ascending=False)
    fig = px.bar(categories, x="Category", y="Revenue", title="Category-wise sales", color="Category",
                 color_discrete_sequence=PALETTE, labels={"Revenue": "Revenue (₹)"})
    fig.update_layout(showlegend=False)
    fig.update_yaxes(tickprefix="₹", tickformat=",.0f")
    with left:
        chart(fig)
    fig = px.scatter(all_products, x="Quantity", y="Revenue", size="Orders", color="Category", hover_name="Product",
                     title="Product performance comparison (bubble size = orders)", color_discrete_sequence=PALETTE,
                     labels={"Quantity": "Units sold", "Revenue": "Revenue (₹)"})
    fig.update_yaxes(tickprefix="₹", tickformat=",.0f")
    with right:
        chart(fig)

    st.subheader("ABC product classification")
    pareto = views["pareto"]
    ptable = plain(views["pareto_table"])
    fig = go.Figure()
    fig.add_bar(x=ptable["Product"], y=ptable["Revenue"], name="Revenue (₹)", marker_color=BLUE)
    fig.add_scatter(x=ptable["Product"], y=ptable["Cumulative_Revenue_Percent"], name="Cumulative revenue %",
                    yaxis="y2", mode="lines+markers", line=dict(color=AMBER))
    fig.update_layout(title="Pareto analysis of product revenue",
                      yaxis=dict(title="Revenue (₹)", tickprefix="₹", tickformat=",.0f"),
                      yaxis2=dict(title="Cumulative revenue %", overlaying="y", side="right", range=[0, 105]),
                      xaxis=dict(tickangle=-45))
    chart(fig, 430)
    left, right = st.columns([1, 2])
    with left:
        st.markdown("**ABC summary (current selection)**")
        table(pareto["abc_summary"], money=("Revenue",), percent=("Revenue_Percent",), whole=("Products",))
        st.caption(pareto["abc_thresholds_note"])
    with right:
        st.markdown("**Products ranked by revenue**")
        table(ptable[["Rank", "Product", "Category", "Revenue", "Cumulative_Revenue_Percent", "ABC_Class",
                      "ABC_Class_full_data"]], money=("Revenue",), percent=("Cumulative_Revenue_Percent",), height=320)
    st.caption("ABC_Class is recalculated for the current filters by src/analysis.py (pareto_analysis); "
               "ABC_Class_full_data is the whole-dataset class from product_classification.csv.")
    download("Download product table (CSV)", all_products, "smartmart_products.csv", "dl_products")


def page_regions() -> None:
    regions = plain(views["regions"]).sort_values("Revenue", ascending=False).reset_index(drop=True)
    cities = plain(views["cities"])
    if len(regions) >= 1:
        high, low = regions.iloc[0], regions.iloc[-1]
        cols = st.columns(4)
        cols[0].metric("Top-performing region", high["Region"], help="Highest revenue in the current selection")
        cols[1].metric("Its revenue", L.inr_compact(high["Revenue"]), help=L.inr(high["Revenue"], 2))
        cols[2].metric("Lowest-performing region", low["Region"], help="Lowest revenue in the current selection")
        cols[3].metric("Its revenue", L.inr_compact(low["Revenue"]), help=L.inr(low["Revenue"], 2))

    left, right = st.columns(2)
    fig = px.bar(regions, x="Region", y="Revenue", title="Region-wise revenue", color_discrete_sequence=[BLUE],
                 labels={"Revenue": "Revenue (₹)"})
    fig.update_yaxes(tickprefix="₹", tickformat=",.0f")
    with left:
        chart(fig)
    fig = px.bar(cities, x="Revenue", y="City", color="Region", orientation="h", title="City-wise sales",
                 color_discrete_sequence=PALETTE, labels={"Revenue": "Revenue (₹)"})
    fig.update_yaxes(categoryorder="total ascending")
    fig.update_xaxes(tickprefix="₹", tickformat=",.0f")
    with right:
        chart(fig, max(380, 20 * len(cities) + 120))

    st.subheader("Regional sales comparison")
    left, right = st.columns(2)
    fig = px.bar(regions, x="Region", y="Orders", title="Orders by region", color_discrete_sequence=[GREEN])
    with left:
        chart(fig, 320)
    fig = px.bar(regions, x="Region", y="Average_Order_Value", title="Average order value by region",
                 color_discrete_sequence=[AMBER], labels={"Average_Order_Value": "Average order value (₹)"})
    fig.update_yaxes(tickprefix="₹", tickformat=",.0f")
    with right:
        chart(fig, 320)
    table(regions, money=("Revenue", "Average_Order_Value"), whole=("Quantity", "Orders"))
    st.markdown("<span class='sm-note'>No map is shown: the dataset has city and region names but no latitude/longitude "
                "columns, so a geographical chart would need data this project does not contain.</span>", unsafe_allow_html=True)
    st.markdown("**City table**")
    table(cities, money=("Revenue", "Average_Order_Value"), whole=("Quantity", "Orders"), height=300)
    download("Download regional table (CSV)", regions, "smartmart_regions.csv", "dl_regions")


def page_customers() -> None:
    customers = views["customers"]
    summary = views["summary"]
    cols = st.columns(4)
    cols[0].metric("Total unique customers", L.num(summary["Total Customers"]))
    cols[1].metric("Repeat customers", L.num(customers["repeat_customers"]))
    cols[2].metric("One-time customers", L.num(customers["one_time_customers"]))
    cols[3].metric("Repeat customer rate", f"{customers['repeat_customer_rate']:.1f}%")
    st.markdown("<span class='sm-note'>New vs repeat uses the Customer_Type flag from the cleaned data, which is based on each "
                "customer's whole-period order count (not only the selected filters).</span>", unsafe_allow_html=True)

    left, right = st.columns(2)
    split = pd.DataFrame({"Customer type": ["Repeat customers", "One-time customers"],
                          "Customers": [customers["repeat_customers"], customers["one_time_customers"]]})
    fig = px.pie(split, names="Customer type", values="Customers", hole=0.45, title="New (one-time) vs repeat customers",
                 color_discrete_sequence=[BLUE, AMBER])
    fig.update_traces(textinfo="percent+value")
    with left:
        chart(fig)
    seg = plain(views["segment_summary"])
    fig = px.bar(seg, x="Segment", y="Customers", color="Segment", title="RFM customer segment distribution",
                 color_discrete_sequence=PALETTE)
    fig.update_layout(showlegend=False)
    with right:
        chart(fig)

    st.subheader("RFM customer segmentation")
    left, right = st.columns([1, 2])
    with left:
        table(seg, money=("Revenue",), whole=("Customers",))
        st.caption("Segments are computed by Python over the whole period (src/analysis.py: customer_segmentation, read from "
                   "customer_segments.csv) and do not change with the filters; customer counts and revenue are for the "
                   "customers present in the current selection.")
    rfm = plain(views["segment_customers"].dropna(subset=["Monetary"]))
    fig = px.scatter(rfm, x="Recency_Days", y="Monetary", color="Segment", hover_name="Customer_ID",
                     title="RFM view: recency vs monetary value (whole-period values)", color_discrete_sequence=PALETTE,
                     labels={"Recency_Days": "Recency (days since last order)", "Monetary": "Total spend (₹)"})
    fig.update_yaxes(tickprefix="₹", tickformat=",.0f")
    with right:
        chart(fig, 360)

    top = plain(customers["top_customers"])
    left, right = st.columns(2)
    fig = px.bar(top.sort_values("Total_Spending"), x="Total_Spending", y="Customer_ID", orientation="h",
                 title=f"Top {len(top)} customers by revenue", color_discrete_sequence=[BLUE],
                 labels={"Total_Spending": "Revenue (₹)"})
    fig.update_xaxes(tickprefix="₹", tickformat=",.0f")
    with left:
        chart(fig)
    with right:
        table(top, money=("Total_Spending", "Average_Spending_Per_Order"), whole=("Number_of_Orders",))

    st.subheader("Customer purchasing behaviour")
    left, right = st.columns(2)
    frequency = plain(views["orders_per_customer"])
    fig = px.bar(frequency, x="Orders_per_customer", y="Customers", title="Customers by number of orders (current selection)",
                 color_discrete_sequence=[GREEN], labels={"Orders_per_customer": "Orders per customer"})
    with left:
        chart(fig, 340)
    ctable = plain(customers["customer_table"])
    fig = px.scatter(ctable, x="Number_of_Orders", y="Total_Spending", color="Customer_Type", hover_name="Customer_ID",
                     title="Orders vs total spending per customer", color_discrete_sequence=[BLUE, AMBER],
                     labels={"Number_of_Orders": "Orders", "Total_Spending": "Total spending (₹)"})
    fig.update_yaxes(tickprefix="₹", tickformat=",.0f")
    with right:
        chart(fig, 340)
    download("Download customer table (CSV)", ctable, "smartmart_customers.csv", "dl_customers")


def page_payments() -> None:
    pay = plain(views["payments"])
    leader = pay.sort_values("Orders", ascending=False).iloc[0]
    cols = st.columns(3)
    cols[0].metric("Most used payment mode", leader["Payment_Mode"], help="By number of orders")
    cols[1].metric("Its share of orders", f"{leader['Order_Share_Percent']:.1f}%")
    cols[2].metric("Payment modes in selection", L.num(len(pay)))

    left, right = st.columns(2)
    fig = px.pie(pay, names="Payment_Mode", values="Orders", hole=0.45, title="Payment method distribution (orders)",
                 color_discrete_sequence=PALETTE)
    fig.update_traces(textinfo="percent+label")
    with left:
        chart(fig)
    fig = px.bar(pay.sort_values("Revenue", ascending=False), x="Payment_Mode", y="Revenue", title="Revenue by payment method",
                 color_discrete_sequence=[BLUE], labels={"Revenue": "Revenue (₹)", "Payment_Mode": "Payment mode"})
    fig.update_yaxes(tickprefix="₹", tickformat=",.0f")
    with right:
        chart(fig)

    left, right = st.columns(2)
    fig = px.bar(pay.sort_values("Orders", ascending=False), x="Payment_Mode", y="Orders", title="Order count by payment method",
                 color_discrete_sequence=[GREEN], labels={"Payment_Mode": "Payment mode"})
    with left:
        chart(fig, 340)
    share = pay.melt(id_vars="Payment_Mode", value_vars=["Order_Share_Percent", "Revenue_Share_Percent"],
                     var_name="Measure", value_name="Share (%)")
    share["Measure"] = share["Measure"].map({"Order_Share_Percent": "Share of orders",
                                             "Revenue_Share_Percent": "Share of revenue"})
    fig = px.bar(share, x="Payment_Mode", y="Share (%)", color="Measure", barmode="group",
                 title="Payment method comparison: share of orders vs share of revenue",
                 color_discrete_sequence=[BLUE, AMBER], labels={"Payment_Mode": "Payment mode"})
    with right:
        chart(fig, 340)

    comparison = pay.assign(Average_Order_Value=(pay["Revenue"] / pay["Orders"]).round(2))
    table(comparison, money=("Revenue", "Average_Order_Value"), percent=("Order_Share_Percent", "Revenue_Share_Percent"),
          whole=("Orders",))
    download("Download payment table (CSV)", comparison, "smartmart_payments.csv", "dl_payments")


def page_about() -> None:
    st.subheader("About this project")
    st.write(
        "SmartMart is a fictional e-commerce retailer selling electronics, furniture, clothing, grocery, home appliances and "
        "accessories across five regions of India. This project generates a reproducible **synthetic** sales dataset, cleans and "
        "analyses it with a tested Python pipeline, writes charts and Excel/text reports, and exposes the same data to Microsoft "
        "Power BI. This Streamlit app is an additional web frontend on the same processed data. "
        "All figures describe simulated data, not real business results.")
    st.markdown(
        "**Technology stack:** Python · pandas · NumPy · Matplotlib / Seaborn (pipeline charts) · openpyxl (Excel reports) · "
        "pytest · Streamlit + Plotly (this frontend) · Microsoft Power BI (separate `.pbix` dashboard)")
    st.markdown("**Training organisation:** Cronus Consultants · **Mentor:** Subhashish Banerjee · **Course:** Python with Data Analytics")

    st.subheader("Data overview (all loaded data, before filters)")
    info = L.data_overview(sales_all, load_info)
    cols = st.columns(4)
    cols[0].metric("Rows", L.num(info["rows"]))
    cols[1].metric("Columns", L.num(info["columns"]))
    cols[2].metric("Missing values", L.num(info["missing_values"]))
    cols[3].metric("Duplicate Order_IDs", L.num(info["duplicate_order_ids"]))
    st.write(
        f"Orders from **{info['date_min']:%d %b %Y}** to **{info['date_max']:%d %b %Y}** · {L.num(info['customers'])} customers · "
        f"{L.num(info['products'])} products. Rows dropped while loading (unparseable date/amount): {info['rows_dropped_on_load']}. "
        f"Rows with city `Unknown`: {info['unknown_city_rows']}; with payment mode `Unknown`: {info['unknown_payment_rows']}. "
        "The pipeline (`python main.py`) already removed duplicates and invalid rows; see the project documentation for the cleaning rules.")
    table(info["column_table"], whole=("Missing", "Distinct values"))

    st.subheader("Filtered sales data")
    search = st.text_input("Search the table (any text column)", key="table_search")
    shown = sales
    if search.strip():
        needle = search.strip().lower()
        text_columns = [c for c in L.TEXT_COLUMNS if c in shown.columns]
        mask = pd.Series(False, index=shown.index)
        for column in text_columns:
            mask |= shown[column].astype(str).str.lower().str.contains(needle, regex=False)
        shown = shown[mask]
    st.caption(f"{L.num(len(shown))} rows shown. Click a column header to sort.")
    table(shown[["Order_ID", "Order_Date", "Customer_ID", "Product", "Category", "Quantity", "Unit_Price", "Sales",
                 "Region", "City", "Payment_Mode", "Customer_Type"]], money=("Unit_Price", "Sales"), whole=("Quantity",), height=420)
    cols = st.columns(2)
    with cols[0]:
        download("Download filtered sales data (CSV)", sales, "smartmart_filtered_sales.csv", "dl_sales_about")
    with cols[1]:
        if views is not None:
            download("Download summary report (CSV)", L.summary_report_frame(views, filter_text),
                     "smartmart_summary_report.csv", "dl_summary_about")


{
    "Executive Overview": page_executive,
    "Product Performance": page_products,
    "Regional Performance": page_regions,
    "Customer Analytics": page_customers,
    "Payment Analysis": page_payments,
    "Data & About": page_about,
}[page]()
