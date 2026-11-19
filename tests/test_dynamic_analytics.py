import numpy as np
import pandas as pd
import pytest

from src import dynamic_analytics as A
from src.schema_detection import detect_schema


def labels(df):
    return [k["label"] for k in A.compute_kpis(df, detect_schema(df))]


def test_sales_kpis_are_computed_from_data(alt_sales):
    s = detect_schema(alt_sales)
    k = {x["label"]: x["value"] for x in A.compute_kpis(alt_sales, s)}
    assert k["Total Revenue"] == pytest.approx(alt_sales["Total_Amount"].sum())
    assert k["Total Units Sold"] == alt_sales["Qty"].sum()
    assert k["Total Customers"] == alt_sales["Client_ID"].nunique()
    assert k["Products Sold"] == alt_sales["Item"].nunique()
    assert "Total Transactions" in k          # no order-id column -> not called "orders"


def test_no_sales_kpis_for_generic_data(generic_df):
    got = labels(generic_df)
    assert "Total Revenue" not in got and "Records" in got


def test_no_date_dataset_has_no_trend():
    df = pd.DataFrame({"Product": list("ABCABC"), "Revenue": [1, 2, 3, 4, 5, 6.0]})
    assert A.monthly_trend(df, detect_schema(df)) is None
    assert "Total Revenue" in labels(df)


def test_derived_revenue_from_quantity_and_price():
    df = pd.DataFrame({"Item": list("ABAB"), "Quantity": [1, 2, 3, 4], "Unit_Price": [10.0, 20, 30, 40], "Customer": list("wxyz")})
    s = detect_schema(df)
    assert A.revenue(df, s).sum() == 10 + 40 + 90 + 160


def test_hr_and_banking_domains():
    hr = pd.DataFrame({"Department": ["a", "b"] * 5, "Salary": np.arange(10) * 1000.0, "Attrition": ["Yes", "No"] * 5})
    got = {k["label"]: k["value"] for k in A.compute_kpis(hr, detect_schema(hr))}
    assert got["Employee Count"] == 10 and got["Attrition Rate"] == 50.0 and got["Average Salary"] == 4500.0


def test_empty_data_returns_nothing():
    e = pd.DataFrame()
    assert A.compute_kpis(e, detect_schema(e)) == []
    assert A.generate_insights(e, detect_schema(e))["sufficient"] is False


def test_filters_are_applied_and_do_not_mutate(alt_sales):
    from src.schema_detection import coerce_types
    s = detect_schema(alt_sales)
    df = coerce_types(alt_sales, s)
    spec = A.FilterSpec(date_col="Created_At", date_range=(pd.Timestamp("2024-02-01").date(), pd.Timestamp("2024-02-29").date()),
                        categorical={"City": ["X"]}, numeric={"Total_Amount": (0, 150)})
    out = A.apply_filters(df, spec)
    assert len(df) == 200 and 0 < len(out) < len(df)
    assert out["City"].eq("X").all() and out["Total_Amount"].le(150).all()
    assert out["Created_At"].between("2024-02-01", "2024-02-29 23:59").all()
    assert A.apply_filters(df, A.FilterSpec()).shape == df.shape


def test_revenue_breakdown_adds_up(alt_sales):
    s = detect_schema(alt_sales)
    b = A.revenue_breakdown(alt_sales, s, "product")
    assert b["Revenue"].sum() == pytest.approx(alt_sales["Total_Amount"].sum())
    assert b["Share %"].sum() == pytest.approx(100, abs=0.1)
    assert A.revenue_breakdown(alt_sales.drop(columns=["Item"]), detect_schema(alt_sales.drop(columns=["Item"])), "product") is None


def test_insights_are_grounded(alt_sales):
    from src.schema_detection import coerce_types
    s = detect_schema(alt_sales)
    ins = A.generate_insights(coerce_types(alt_sales, s), s)
    assert ins["sufficient"] and len(ins["findings"]) >= 5 and ins["recommendations"]
    assert f"{alt_sales['Total_Amount'].sum():,.2f}" in ins["findings"][0]
    assert A.generate_insights(alt_sales.head(3), s)["sufficient"] is False      # no fake insights for tiny data


def test_missing_and_duplicates_are_reported(alt_sales):
    d = pd.concat([alt_sales, alt_sales.head(10)], ignore_index=True)
    d.loc[0, "Total_Amount"] = np.nan
    ins = A.generate_insights(d, detect_schema(d))
    assert any("duplicated" in q for q in ins["quality"]) and any("missing" in q for q in ins["quality"])
