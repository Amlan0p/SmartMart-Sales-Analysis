import io

import pandas as pd
import pytest

from src import data_entry, data_upload
from src.schema_detection import detect_schema


def test_coerce_values():
    num = data_entry.ColumnSpec("n", "numeric")
    assert data_entry.coerce_value(num, "1,234.5") == 1234.5
    with pytest.raises(ValueError):
        data_entry.coerce_value(num, "abc")
    ints = data_entry.ColumnSpec("i", "numeric", is_integer=True)
    assert data_entry.coerce_value(ints, "7") == 7
    with pytest.raises(ValueError):
        data_entry.coerce_value(ints, "7.5")
    assert pd.isna(data_entry.coerce_value(num, ""))
    with pytest.raises(ValueError):
        data_entry.coerce_value(data_entry.ColumnSpec("d", "datetime"), "not a date")
    assert data_entry.coerce_value(data_entry.ColumnSpec("b", "boolean"), "yes") is True


def test_all_blank_row_rejected():
    specs = [data_entry.ColumnSpec("a", "text")]
    with pytest.raises(data_entry.ValidationError):
        data_entry.validate_row(specs, {"a": ""})


def test_append_row_preserves_rows_and_dtypes():
    df = pd.DataFrame({"a": [1, 2], "b": ["x", "y"], "d": pd.to_datetime(["2024-01-01", "2024-01-02"])})
    out = data_entry.append_row(df, {"a": 3, "b": "z", "d": pd.Timestamp("2024-01-03")})
    assert len(df) == 2 and len(out) == 3          # input untouched
    assert str(out["a"].dtype) == "int64" and pd.api.types.is_datetime64_any_dtype(out["d"])


def test_new_dataset_definition_validation():
    with pytest.raises(ValueError):
        data_entry.new_dataset_from_definition([])
    with pytest.raises(ValueError):
        data_entry.new_dataset_from_definition([("A", "text"), ("a", "text")])


def test_read_csv_variants():
    semi = "a;b\n1;2\n3;4\n".encode()
    assert data_upload.read_upload(semi, "x.csv").shape == (2, 2)
    latin = "name,city\nJosé,Zürich\n".encode("latin-1")
    assert data_upload.read_upload(latin, "x.csv").iloc[0, 0] == "José"
    dup_headers = b"a,a,\n1,2,3\n"
    cols = list(data_upload.read_upload(dup_headers, "x.csv").columns)
    assert len(set(cols)) == 3 and cols[2] == "Column_3"      # unique names, blank header named


def test_read_xlsx_roundtrip():
    buf = io.BytesIO()
    pd.DataFrame({"x": [1, 2, 3], "y": list("abc")}).to_excel(buf, index=False)
    df = data_upload.read_upload(buf.getvalue(), "book.xlsx")
    assert df.shape == (3, 2) and data_upload.excel_sheet_names(buf.getvalue(), "book.xlsx") == ["Sheet1"]


def test_upload_errors_are_readable():
    for payload, name in ((b"", "e.csv"), (b"a,b\n1,2\n", "x.txt"), (b"not an excel file", "bad.xlsx")):
        with pytest.raises(data_upload.UploadError):
            data_upload.read_upload(payload, name)


def test_summary_reports_quality(alt_sales):
    d = alt_sales.copy()
    d.loc[0, "City"] = None
    d = pd.concat([d, d.head(5)], ignore_index=True)
    s = data_upload.summarize(d, "f.csv", 1234, detect_schema(d))
    assert s["rows"] == len(d) and s["duplicate_rows"] >= 5 and s["missing_total"] >= 1
    assert "Total_Amount" in s["kinds"]["numeric"] and s["size"] == "1.2 KB"
