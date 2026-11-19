"""Tests for src/dashboard_logic.py (the data layer of the Streamlit frontend).

They use the real processed CSV files and compare every dashboard figure with the
existing analysis functions, so the frontend cannot drift from the pipeline. They do
not need Streamlit or Plotly. The optional last test runs the real app with
streamlit.testing and is skipped when Streamlit is not installed.
"""
import datetime as dt

import pandas as pd
import pytest

import config
from src import analysis
from src import dashboard_logic as L

pytestmark = pytest.mark.skipif(L.missing_files(), reason="run `python main.py` first to create the processed CSV files")


@pytest.fixture(scope="module")
def data():
    sales, info = L.load_sales()
    return sales, info, L.load_segments(), L.load_classification()


def test_loading_matches_cleaned_csv(data):
    sales, info, _, _ = data
    raw = pd.read_csv(config.CLEANED_SALES_DATA_PATH)
    assert len(sales) == len(raw) == info["rows_in_file"]
    assert info["dropped"] == 0
    assert pd.api.types.is_datetime64_any_dtype(sales["Order_Date"])
    assert pd.api.types.is_numeric_dtype(sales["Sales"])
    assert sales["Sales"].sum() == pytest.approx(raw["Sales"].sum())


def test_unfiltered_views_equal_analysis_functions(data):
    sales, _, seg, cls = data
    views = L.compute_views(sales, seg, cls)
    assert views["summary"] == analysis.overall_sales_summary(sales)
    pd.testing.assert_frame_equal(views["regions"], analysis.regional_analysis(sales))
    pd.testing.assert_frame_equal(views["payments"], analysis.payment_analysis(sales))
    pd.testing.assert_frame_equal(views["categories"], analysis.category_analysis(sales))
    assert views["customers"]["repeat_customers"] == analysis.customer_analysis(sales)["repeat_customers"]
    assert views["peak_month"] == analysis.monthly_sales_analysis(sales)["peak_month"]


def test_monthly_table_is_chronological(data):
    sales, _, seg, cls = data
    table = L.compute_views(sales, seg, cls)["monthly_table"]
    keys = list(zip(table["Year"], table["Month"]))
    assert keys == sorted(keys)


def test_filters_change_results_correctly(data):
    sales, _, seg, cls = data
    f = L.Filters(start=dt.date(2024, 1, 1), end=dt.date(2024, 12, 31), regions=["East"], categories=["Electronics"])
    filtered = L.filter_sales(sales, f)
    manual = sales[(sales["Order_Date"].dt.year == 2024) & (sales["Region"] == "East") & (sales["Category"] == "Electronics")]
    assert len(filtered) == len(manual) > 0
    views = L.compute_views(filtered, seg, cls)
    assert views["summary"]["Total Revenue"] == pytest.approx(round(manual["Sales"].sum(), 2))
    assert views["summary"]["Total Orders"] == len(manual)
    assert set(views["regions"]["Region"]) == {"East"}
    assert set(views["categories"]["Category"]) == {"Electronics"}


@pytest.mark.parametrize("column,field,value", [("Product", "products", "Laptop"), ("Payment_Mode", "payments", "UPI"),
                                                ("Region", "regions", "West"), ("Category", "categories", "Grocery")])
def test_each_sidebar_filter_restricts_rows(data, column, field, value):
    sales = data[0]
    out = L.filter_sales(sales, L.Filters(**{field: [value]}))
    assert 0 < len(out) < len(sales)
    assert set(out[column]) == {value}


def test_date_range_is_inclusive_of_end_date(data):
    sales = data[0]
    day = sales["Order_Date"].iloc[0].date()
    out = L.filter_sales(sales, L.Filters(start=day, end=day))
    assert len(out) == (sales["Order_Date"].dt.date == day).sum() > 0


def test_empty_selection_returns_none(data):
    sales, _, seg, cls = data
    empty = L.filter_sales(sales, L.Filters(products=["Laptop"], payments=["Unknown"], regions=["East"], categories=["Grocery"]))
    assert empty.empty
    assert L.compute_views(empty, seg, cls) is None


def test_segments_cover_customers_in_view(data):
    sales, _, seg, cls = data
    f = L.Filters(regions=["North"])
    view = L.compute_views(L.filter_sales(sales, f), seg, cls)
    assert view["segment_summary"]["Customers"].sum() == view["summary"]["Total Customers"]
    assert "Not segmented" not in set(view["segment_summary"]["Segment"])


def test_city_sales_adds_up(data):
    sales = data[0]
    assert L.city_sales(sales)["Revenue"].sum() == pytest.approx(sales["Sales"].sum())


def test_pareto_table_has_static_and_dynamic_abc(data):
    sales, _, seg, cls = data
    table = L.compute_views(sales, seg, cls)["pareto_table"]
    assert {"ABC_Class", "ABC_Class_full_data"} <= set(table.columns)
    assert (table["ABC_Class"] == table["ABC_Class_full_data"]).all()  # unfiltered view equals the exported classification


def test_summary_report_and_overview(data):
    sales, info, seg, cls = data
    views = L.compute_views(sales, seg, cls)
    report = L.summary_report_frame(views, "No filters")
    assert list(report.columns) == ["Section", "Item", "Metric", "Value"]
    assert {"KPIs", "Category", "Region", "Payment mode", "Product"} <= set(report["Section"])
    assert L.to_csv_bytes(report).startswith(b"Section,Item,Metric,Value")
    overview = L.data_overview(sales, info)
    assert overview["rows"] == len(sales) and overview["columns"] == sales.shape[1]
    assert overview["duplicate_order_ids"] == 0 and overview["missing_values"] == 0


def test_rupee_formatting():
    assert L.inr(189024945.86, 2) == "₹18,90,24,945.86"
    assert L.inr(999) == "₹999"
    assert L.inr(-1234567.5, 1) == "-₹12,34,567.5"
    assert L.inr_compact(189024945.86) == "₹18.90 Cr"
    assert L.inr_compact(3965753) == "₹39.66 L"
    assert L.num(1234567) == "12,34,567"


def test_bad_rows_are_dropped_safely(tmp_path):
    good = pd.read_csv(config.CLEANED_SALES_DATA_PATH).head(5)
    bad = good.astype({"Order_Date": object, "Sales": object})
    bad.loc[0, "Order_Date"] = "not a date"
    bad.loc[1, "Sales"] = "abc"
    path = tmp_path / "x.csv"
    bad.to_csv(path, index=False)
    sales, info = L.load_sales(path)
    assert info["dropped"] == 2 and len(sales) == 3


def test_missing_file_is_reported(tmp_path):
    with pytest.raises(L.DataNotReadyError):
        L.load_sales(tmp_path / "nope.csv")
    assert "python main.py" in L.MISSING_FILES_MESSAGE


def test_streamlit_app_runs_if_streamlit_installed():
    """Runs the real app on every page with streamlit's own test harness."""
    pytest.importorskip("streamlit.testing.v1")
    pytest.importorskip("plotly")
    from streamlit.testing.v1 import AppTest
    app = AppTest.from_file(str(config.BASE_DIR / "streamlit_app_classic.py"), default_timeout=90)
    app.run()
    assert not app.exception
    for page in ["Executive Overview", "Product Performance", "Regional Performance",
                 "Customer Analytics", "Payment Analysis", "Data & About"]:
        app.sidebar.radio(key="page").set_value(page).run()
        assert not app.exception, page
