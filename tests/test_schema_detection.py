import pandas as pd

from src.schema_detection import apply_manual_mapping, detect_schema


def test_smartmart_columns_are_detected():
    df = pd.read_csv("data/raw/sales_data.csv")
    s = detect_schema(df)
    assert s.dataset_type == "sales"
    assert s.roles["revenue"] == "Sales" and s.roles["date"] == "Order_Date"
    assert s.roles["customer"] == "Customer_ID" and s.roles["category"] == "Category"
    assert s.roles["location"] == "Region" and s.roles["quantity"] == "Quantity"


def test_different_names_are_detected(alt_sales):
    s = detect_schema(alt_sales)
    assert s.dataset_type == "sales"
    assert (s.roles["revenue"], s.roles["customer"], s.roles["product"], s.roles["location"], s.roles["date"]) == \
        ("Total_Amount", "Client_ID", "Item", "City", "Created_At")


def test_generic_dataset_has_no_sales_roles(generic_df):
    s = detect_schema(generic_df)
    assert s.dataset_type == "generic"
    assert s.roles["revenue"] is None and s.roles["customer"] is None


def test_missing_roles_are_never_invented():
    s = detect_schema(pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]}))
    assert all(v is None for v in s.roles.values())


def test_empty_frame_is_safe():
    assert detect_schema(pd.DataFrame()).dataset_type == "generic"


def test_manual_mapping_overrides(generic_df):
    s = apply_manual_mapping(detect_schema(generic_df), {"revenue": "temp"})
    assert s.roles["revenue"] == "temp" and s.confidence["revenue"] == 1.0
