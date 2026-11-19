"""
generate_dataset.py

Generates a realistic synthetic retail transaction dataset for
SmartMart E-Commerce.

The generator intentionally builds in real-world structure rather than
drawing every column independently at random:

- Products belong to a fixed category, with a realistic price band.
- Cities are drawn from the region they belong to.
- A small pool of customers accounts for most orders (repeat buyers),
  while many customers appear only once (one-time buyers), producing a
  realistic mix of high- and low-value customers.
- Sales volume varies by month to create a genuine seasonal pattern
  (e.g. a festive/holiday uplift), rather than being flat.
- ``Sales`` is always ``Quantity * Unit_Price`` - never independently
  randomized.
- A small, controlled number of data-quality issues (missing values,
  duplicate rows, a few invalid numeric values) are injected so the
  preprocessing stage has real work to do.

Running this module directly writes the raw dataset to
``data/raw/sales_data.csv``.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from config import (
    DATASET_END_DATE,
    DATASET_START_DATE,
    NUMBER_OF_CUSTOMERS,
    NUMBER_OF_TRANSACTIONS,
    RANDOM_SEED,
    RAW_SALES_DATA_PATH,
)
from src.utils import ensure_directories, get_logger

logger = get_logger(__name__)

# --------------------------------------------------------------------------
# Reference data: regions, cities, categories, products, payment modes
# --------------------------------------------------------------------------

REGION_CITY_MAP = {
    "North": ["Delhi", "Lucknow", "Chandigarh", "Jaipur"],
    "South": ["Bengaluru", "Chennai", "Hyderabad", "Kochi"],
    "East": ["Kolkata", "Patna", "Bhubaneswar", "Guwahati"],
    "West": ["Mumbai", "Pune", "Ahmedabad", "Surat"],
    "Central": ["Bhopal", "Nagpur", "Raipur", "Indore"],
}

# category -> list of (product_name, min_price, max_price)
PRODUCT_CATALOG = {
    "Electronics": [
        ("Wireless Headphones", 1200, 3500),
        ("Smartphone", 9000, 45000),
        ("Laptop", 32000, 85000),
        ("Bluetooth Speaker", 900, 4500),
        ("Smartwatch", 1800, 12000),
        ("Keyboard", 500, 2500),
        ("Mouse", 300, 1500),
        ("Power Bank", 700, 2800),
    ],
    "Furniture": [
        ("Office Chair", 3500, 12000),
        ("Study Table", 2800, 9000),
        ("Bookshelf", 2200, 7000),
        ("Sofa", 12000, 45000),
        ("Dining Table", 9000, 32000),
    ],
    "Clothing": [
        ("T-Shirt", 300, 1200),
        ("Jeans", 800, 2800),
        ("Jacket", 1500, 5500),
        ("Saree", 900, 6000),
        ("Kurta", 500, 2200),
        ("Shoes", 900, 4500),
    ],
    "Grocery": [
        ("Rice (5kg)", 250, 600),
        ("Cooking Oil (1L)", 120, 260),
        ("Tea (250g)", 80, 220),
        ("Coffee (200g)", 150, 400),
        ("Biscuits (Pack)", 30, 90),
        ("Spices Combo", 100, 350),
    ],
    "Home Appliances": [
        ("Mixer Grinder", 1800, 5500),
        ("Electric Kettle", 700, 2200),
        ("Microwave Oven", 5500, 15000),
        ("Air Cooler", 4500, 13000),
        ("Vacuum Cleaner", 3500, 11000),
    ],
    "Accessories": [
        ("Wallet", 300, 1500),
        ("Backpack", 700, 3200),
        ("Belt", 250, 1200),
        ("Sunglasses", 500, 3500),
        ("Mobile Cover", 150, 800),
    ],
}

PAYMENT_MODES = ["UPI", "Credit Card", "Debit Card", "Net Banking", "Cash on Delivery"]
PAYMENT_WEIGHTS = [0.38, 0.18, 0.16, 0.10, 0.18]

# Relative monthly demand multipliers to create a seasonal pattern
# (index 1 = January ... 12 = December). Festive months (Oct/Nov) and
# the new-year sale period (Jan) see an uplift; mid-year is quieter.
MONTHLY_SEASONALITY = {
    1: 1.05, 2: 0.90, 3: 0.95, 4: 0.90, 5: 0.95, 6: 0.90,
    7: 0.95, 8: 1.00, 9: 1.05, 10: 1.25, 11: 1.35, 12: 1.15,
}


def _build_customer_pool(rng: random.Random) -> list[str]:
    """Build a pool of customer IDs where a minority of customers are
    responsible for a disproportionate share of future orders.

    Returns a list of customer IDs of length ``NUMBER_OF_CUSTOMERS`` with
    an associated "weight" so that sampling with these weights produces
    realistic repeat-purchase behaviour.
    """
    customer_ids = [f"CUST{str(i).zfill(5)}" for i in range(1, NUMBER_OF_CUSTOMERS + 1)]
    return customer_ids


def _customer_weights(rng: random.Random, customer_ids: list[str]) -> list[float]:
    """Assign purchase-frequency weights: ~15% of customers are
    "high frequency" (weight drawn from a higher band), the rest are
    "normal" buyers. This produces a realistic long-tail distribution
    of orders per customer.
    """
    weights = []
    for _ in customer_ids:
        if rng.random() < 0.15:
            weights.append(rng.uniform(4.0, 9.0))
        else:
            weights.append(rng.uniform(0.5, 2.0))
    return weights


def _random_date_with_seasonality(rng: random.Random, start: datetime, end: datetime) -> datetime:
    """Pick a random date between start and end, biased by
    ``MONTHLY_SEASONALITY`` so some months naturally receive more
    transactions than others.
    """
    total_days = (end - start).days
    while True:
        offset = rng.randint(0, total_days)
        candidate = start + timedelta(days=offset)
        month_weight = MONTHLY_SEASONALITY.get(candidate.month, 1.0)
        # Accept/reject sampling to bias toward higher-weight months.
        if rng.random() <= (month_weight / 1.35):
            return candidate


def _pick_customer_spend_tier(rng: random.Random) -> str:
    """Return a spend tier label used to bias quantity/price choices,
    creating a mix of high-value and low-value customers.
    """
    roll = rng.random()
    if roll < 0.12:
        return "high"
    if roll < 0.55:
        return "medium"
    return "low"


def generate_raw_dataset(
    number_of_transactions: int = NUMBER_OF_TRANSACTIONS,
    seed: int = RANDOM_SEED,
) -> pd.DataFrame:
    """Generate the full synthetic transaction dataset as a DataFrame.

    The returned DataFrame intentionally contains a small number of
    realistic data-quality issues (see module docstring) so that the
    preprocessing module has genuine cleaning work to perform.
    """
    rng = random.Random(seed)
    np.random.seed(seed)

    start_date = datetime.strptime(DATASET_START_DATE, "%Y-%m-%d")
    end_date = datetime.strptime(DATASET_END_DATE, "%Y-%m-%d")

    customer_ids = _build_customer_pool(rng)
    customer_weights = _customer_weights(rng, customer_ids)
    customer_spend_tier = {cid: _pick_customer_spend_tier(rng) for cid in customer_ids}

    categories = list(PRODUCT_CATALOG.keys())
    regions = list(REGION_CITY_MAP.keys())

    records = []

    for order_index in range(1, number_of_transactions + 1):
        order_id = f"ORD{str(order_index).zfill(6)}"

        customer_id = rng.choices(customer_ids, weights=customer_weights, k=1)[0]
        spend_tier = customer_spend_tier[customer_id]

        region = rng.choice(regions)
        city = rng.choice(REGION_CITY_MAP[region])

        category = rng.choice(categories)
        product_name, min_price, max_price = rng.choice(PRODUCT_CATALOG[category])

        # Spend tier nudges the price point chosen within the product's
        # realistic price band (a "high" tier customer more often buys
        # near the top of the band).
        if spend_tier == "high":
            price_fraction = rng.uniform(0.6, 1.0)
        elif spend_tier == "medium":
            price_fraction = rng.uniform(0.35, 0.75)
        else:
            price_fraction = rng.uniform(0.0, 0.5)

        unit_price = round(min_price + price_fraction * (max_price - min_price), 2)

        if spend_tier == "high":
            quantity = rng.randint(2, 6)
        elif spend_tier == "medium":
            quantity = rng.randint(1, 3)
        else:
            quantity = rng.randint(1, 2)

        sales = round(unit_price * quantity, 2)

        order_date = _random_date_with_seasonality(rng, start_date, end_date)

        payment_mode = rng.choices(PAYMENT_MODES, weights=PAYMENT_WEIGHTS, k=1)[0]

        records.append(
            {
                "Order_ID": order_id,
                "Order_Date": order_date.strftime("%Y-%m-%d"),
                "Customer_ID": customer_id,
                "Product": product_name,
                "Category": category,
                "Quantity": quantity,
                "Unit_Price": unit_price,
                "Sales": sales,
                "Region": region,
                "City": city,
                "Payment_Mode": payment_mode,
            }
        )

    dataframe = pd.DataFrame(records)
    dataframe = _inject_data_quality_issues(dataframe, rng)

    logger.info("Generated synthetic dataset with %d records.", len(dataframe))
    return dataframe


def _inject_data_quality_issues(dataframe: pd.DataFrame, rng: random.Random) -> pd.DataFrame:
    """Inject a small, controlled set of realistic data-quality issues:

    - ~0.6% missing values in a few non-key columns
    - ~0.5% duplicate rows
    - a handful of invalid (negative) Quantity/Unit_Price values

    These proportions are deliberately small so the dataset stays usable
    while still giving the preprocessing module real issues to detect
    and handle.
    """
    df = dataframe.copy()
    n = len(df)

    # Missing values in a few columns that are plausible to go unrecorded.
    for column in ["City", "Payment_Mode", "Unit_Price"]:
        missing_count = max(1, int(n * 0.004))
        missing_indices = rng.sample(range(n), missing_count)
        df.loc[missing_indices, column] = np.nan

    # A few invalid (negative) numeric values, simulating data-entry errors.
    invalid_count = max(1, int(n * 0.002))
    invalid_indices = rng.sample(range(n), invalid_count)
    for idx in invalid_indices:
        if rng.random() < 0.5:
            df.loc[idx, "Quantity"] = -abs(df.loc[idx, "Quantity"])
        else:
            df.loc[idx, "Unit_Price"] = -abs(df.loc[idx, "Unit_Price"]) if pd.notna(df.loc[idx, "Unit_Price"]) else -1

    # Duplicate rows: pick a few existing rows and append exact copies.
    duplicate_count = max(1, int(n * 0.005))
    duplicate_indices = rng.sample(range(n), duplicate_count)
    duplicate_rows = df.loc[duplicate_indices]
    df = pd.concat([df, duplicate_rows], ignore_index=True)

    # Shuffle so injected duplicates aren't all trailing in original order.
    df = df.sample(frac=1, random_state=RANDOM_SEED).reset_index(drop=True)

    return df


def save_raw_dataset(dataframe: pd.DataFrame, output_path: Path = RAW_SALES_DATA_PATH) -> Path:
    """Write the generated dataset to CSV, creating parent directories
    if necessary."""
    ensure_directories(output_path.parent)
    dataframe.to_csv(output_path, index=False)
    logger.info("Raw dataset saved to %s", output_path)
    return output_path


def main() -> None:
    """Generate and persist the raw synthetic dataset."""
    dataframe = generate_raw_dataset()
    save_raw_dataset(dataframe)


if __name__ == "__main__":
    main()
