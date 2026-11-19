import hashlib

import pandas as pd
import pytest

import config
from src import dashboard_logic as L
from src import dynamic_analytics as A
from src.data_entry import ValidationError
from src.dataset_manager import DatasetManager

pytestmark = pytest.mark.skipif(L.missing_files(), reason="run `python main.py` first")
FILES = [config.RAW_SALES_DATA_PATH, config.CLEANED_SALES_DATA_PATH, config.CUSTOMER_SEGMENTS_PATH,
         config.PRODUCT_CLASSIFICATION_PATH]


def _hashes():
    return {str(f): hashlib.md5(f.read_bytes()).hexdigest() for f in FILES}


def _kpis(dm):
    return {k["label"]: k["value"] for k in A.compute_kpis(dm.working_df, dm.schema)}


def _row(i):
    return {"Order_ID": f"NEW{i}", "Order_Date": "2024-12-30", "Customer_ID": "CUSTX", "Product": "Laptop",
            "Category": "Electronics", "Quantity": "2", "Unit_Price": "1000", "Sales": "2000", "Region": "East",
            "City": "Patna", "Payment_Mode": "UPI"}


def test_default_matches_existing_pipeline():
    from src import analysis
    dm = DatasetManager()
    dm.load_default()
    ref = analysis.overall_sales_summary(dm.working_df)
    k = _kpis(dm)
    assert k["Total Revenue"] == pytest.approx(ref["Total Revenue"], abs=0.01)
    assert k["Total Orders"] == ref["Total Orders"]
    assert k["Total Units Sold"] == ref["Total Quantity Sold"]
    assert k["Total Customers"] == ref["Total Customers"]
    assert k["Average Order Value"] == pytest.approx(ref["Average Order Value"], abs=0.01)
    assert k["Avg Selling Price"] == pytest.approx(ref["Average Selling Price"], abs=0.01)


def test_A_add_rows_updates_only_active_dataset():
    before = _hashes()
    dm = DatasetManager()
    dm.load_default()
    base_rows, base_rev = len(dm.working_df), _kpis(dm)["Total Revenue"]
    for i in range(3):
        dm.add_row(_row(i))
    assert len(dm.working_df) == base_rows + 3
    assert _kpis(dm)["Total Revenue"] == pytest.approx(base_rev + 6000)
    assert dm.status[0].endswith("modified")
    assert _hashes() == before          # built-in files untouched


def test_A_invalid_row_is_rejected():
    dm = DatasetManager()
    dm.load_default()
    n = len(dm.working_df)
    bad = _row(1)
    bad["Quantity"] = "abc"
    with pytest.raises(ValidationError):
        dm.add_row(bad)
    bad = _row(2)
    bad["Sales"] = "-5"
    with pytest.raises(ValidationError):
        dm.add_row(bad)
    assert len(dm.working_df) == n


def test_B_remove_all_data_and_files_survive():
    before = _hashes()
    dm = DatasetManager()
    dm.load_default()
    dm.clear()
    assert dm.is_empty and dm.status[0] == "Empty" and dm.working_df.shape == (0, 0)
    assert A.compute_kpis(dm.working_df, dm.schema) == []
    assert _hashes() == before


def test_B_clear_can_keep_columns():
    dm = DatasetManager()
    dm.load_default()
    cols = list(dm.working_df.columns)
    dm.clear(keep_columns=True)
    assert dm.is_empty and list(dm.working_df.columns) == cols
    dm.add_row(_row(1))
    assert len(dm.working_df) == 1


def test_manual_dataset_from_scratch():
    dm = DatasetManager()
    dm.create_manual_dataset([("Name", "text"), ("Score", "decimal"), ("When", "date")])
    dm.add_row({"Name": "ann", "Score": "3.5", "When": "2025-01-01"})
    dm.add_row({"Name": "bob", "Score": "4", "When": "2025-01-02"})
    assert len(dm.working_df) == 2 and dm.working_df["Score"].tolist() == [3.5, 4.0]
    assert dm.status[0] == "Manual"


def test_C_upload_replaces_working_dataset_only(alt_sales):
    dm = DatasetManager()
    dm.load_default()
    old_id = dm.dataset_id
    dm.replace_with_upload(alt_sales, "alt.csv")
    assert dm.display_name == "alt.csv" and dm.dataset_id != old_id and dm.extras == {}
    assert len(dm.working_df) == len(alt_sales) and dm.schema.roles["revenue"] == "Total_Amount"
    assert _kpis(dm)["Total Revenue"] == pytest.approx(alt_sales["Total_Amount"].sum())
    dm.add_row({"Client_ID": "Z", "Item": "A", "Total_Amount": "10", "Created_At": "2025-01-01", "City": "X", "Qty": "1"})
    assert len(dm.source_df) == len(alt_sales)      # pristine upload copy not modified
    assert "Created_At" in dm.working_df and pd.api.types.is_datetime64_any_dtype(dm.working_df["Created_At"])


def test_D_load_default_restores_original_after_changes(alt_sales):
    dm = DatasetManager()
    dm.load_default()
    original = _kpis(dm)
    dm.replace_with_upload(alt_sales, "alt.csv")
    dm.add_row({"Client_ID": "Z", "Item": "A", "Total_Amount": "10", "Created_At": "2025-01-01", "City": "X", "Qty": "1"})
    dm.clear()
    dm.load_default()
    assert dm.display_name.startswith("SmartMart") and dm.status[0] == "Default"
    assert _kpis(dm) == original
    assert set(dm.extras) == {"segments", "classification"}


def test_cleaning_can_be_applied_and_undone():
    dm = DatasetManager()
    dm.load_default()
    n = len(dm.working_df)
    dm.apply_cleaned(dm.working_df.head(100))
    assert len(dm.working_df) == 100
    assert dm.undo_cleaning() and len(dm.working_df) == n


def test_default_dataset_is_independent_of_working_copy():
    dm = DatasetManager()
    dm.load_default()
    dm.working_df.loc[0, "Sales"] = -1          # mutate working copy
    dm2 = DatasetManager()
    dm2.load_default()
    assert dm2.working_df.loc[0, "Sales"] != -1
