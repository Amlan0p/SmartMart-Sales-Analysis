"""Shared fixtures for the dynamic-platform tests (no Streamlit/Plotly needed)."""
import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def alt_sales():
    """A sales table with NON-SmartMart column names."""
    rng = np.random.default_rng(1)
    n = 200
    return pd.DataFrame({
        "Client_ID": [f"C{i % 40}" for i in range(n)], "Item": rng.choice(list("ABCDEF"), n),
        "Total_Amount": rng.gamma(2, 100, n).round(2),
        "Created_At": pd.date_range("2024-01-01", periods=n, freq="D").astype(str),
        "City": rng.choice(["X", "Y", "Z"], n), "Qty": rng.integers(1, 5, n)})


@pytest.fixture
def generic_df():
    rng = np.random.default_rng(2)
    n = 150
    return pd.DataFrame({"temp": rng.normal(20, 5, n), "humidity": rng.normal(50, 10, n),
                         "sensor": rng.choice(["s1", "s2", "s3"], n)})
