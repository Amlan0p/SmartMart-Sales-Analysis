import numpy as np
import pandas as pd
import pytest

from src import data_cleaning as C
from src.schema_detection import detect_schema


@pytest.fixture
def messy():
    return pd.DataFrame({"Product": [" apple", "APPLE ", "pear", "pear", None, "kiwi", "kiwi", "fig", "fig", "plum"] * 2,
                         "Sales": [10, 10, 20, 20, np.nan, -5, 30, 40, 1000, 12] * 2})


def test_reports(messy):
    s = detect_schema(messy)
    assert C.missing_report(messy).iloc[0]["Missing"] == 2
    assert C.duplicate_report(messy)["duplicate_rows"] > 0
    assert C.invalid_report(messy, s)["Rows"].sum() >= 2      # negative sales
    assert 0 <= C.quality_score(messy, s)["score"] <= 100
    assert C.quality_score(pd.DataFrame(), s)["score"] is None


def test_operations_return_new_frames(messy):
    before = messy.copy()
    out, log = C.remove_duplicates(messy)
    assert len(out) < len(messy) and "Removed" in log
    out, _ = C.handle_missing(messy, "median", ["Sales"])
    assert out["Sales"].isna().sum() == 0
    out, _ = C.handle_missing(messy, "drop_rows", ["Sales"])
    assert len(out) == len(messy) - 2
    out, _ = C.standardize_categories(messy, ["Product"], "lower")
    assert out["Product"].dropna().tolist()[0:2] == ["apple", "apple"]
    out, _ = C.remove_invalid(messy, detect_schema(messy))
    assert (out["Sales"].dropna() >= 0).all()
    out, _ = C.remove_outliers(messy, ["Sales"])
    assert out["Sales"].max() < 1000
    out, _ = C.apply_transform(messy.assign(Sales=messy["Sales"].abs()), "Sales", "log1p")
    assert "Sales_log1p" in out and "Sales_log1p" not in messy
    pd.testing.assert_frame_equal(messy, before)     # inputs never mutated


def test_change_dtype_reports_lost_values():
    df = pd.DataFrame({"v": ["1", "2", "x"]})
    out, log = C.change_dtype(df, "v", "number")
    assert out["v"].isna().sum() == 1 and "could not be converted" in log


def test_invalid_operations_raise():
    with pytest.raises(ValueError):
        C.handle_missing(pd.DataFrame({"a": [1, None]}), "constant", ["a"], "")
    with pytest.raises(ValueError):
        C.apply_transform(pd.DataFrame({"a": [-5.0, 1.0]}), "a", "sqrt")


def test_before_after():
    a = pd.DataFrame({"x": [1, 1, 2]})
    b, _ = C.remove_duplicates(a)
    t = C.before_after(a, b).set_index("Metric")
    assert t.loc["Rows", "Change"] == -1 and t.loc["Duplicate rows", "After"] == 0
