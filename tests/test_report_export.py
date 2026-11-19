import io

import pandas as pd
import pytest

from src import dashboard_logic as L
from src import dynamic_analytics as A
from src import report_export as R
from src.schema_detection import coerce_types, detect_schema


def sheets(b):
    return pd.ExcelFile(io.BytesIO(b)).sheet_names


def test_generic_reports_for_non_smartmart_data(alt_sales):
    s = detect_schema(alt_sales)
    df = coerce_types(alt_sales, s)
    assert "Summary" in sheets(R.generic_excel_report_bytes(df, s, "alt", "none"))
    q = pd.read_excel(io.BytesIO(R.quality_report_bytes(df, s, "alt")), sheet_name="Summary")
    assert "Quality score (0-100)" in q["Item"].tolist()
    assert not R.can_use_smartmart_report(df)
    assert R.csv_bytes(df).startswith(b"\xef\xbb\xbf")
    ins = A.generate_insights(df, s)
    assert "KEY FINDINGS" in R.insights_text(ins, "alt")


@pytest.mark.skipif(L.missing_files(), reason="run `python main.py` first")
def test_original_excel_report_is_reused_for_smartmart_data():
    sales, _ = L.load_sales()
    assert R.can_use_smartmart_report(sales)
    names = sheets(R.smartmart_excel_report_bytes(sales))
    assert "Product Analysis" in names and len(names) == 10
    assert any(label.startswith("Power BI dashboard") for label, _ in R.powerbi_assets())


def test_tiny_and_empty_exports_do_not_crash():
    df = pd.DataFrame({"a": [1]})
    s = detect_schema(df)
    assert R.generic_excel_report_bytes(df, s, "t", "")
    assert R.quality_report_bytes(df, s, "t")
    assert "Not enough" in R.insights_text(A.generate_insights(df, s), "t") or "too few" in R.insights_text(A.generate_insights(df, s), "t")
