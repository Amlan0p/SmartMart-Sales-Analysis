"""
config.py

Central configuration for the SmartMart Sales Performance Analytics project.

All file paths, directory locations and tunable constants live here so
that no other module needs to hard-code a path or a "magic number".
"""

from pathlib import Path

# --------------------------------------------------------------------------
# Project metadata
# --------------------------------------------------------------------------
PROJECT_NAME = "SmartMart Sales Performance Analytics"
COMPANY_NAME = "SmartMart E-Commerce"

# --------------------------------------------------------------------------
# Base directories
# --------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"

OUTPUTS_DIR = BASE_DIR / "outputs"
CHARTS_DIR = OUTPUTS_DIR / "charts"
REPORTS_DIR = OUTPUTS_DIR / "reports"
RESULTS_DIR = OUTPUTS_DIR / "results"
LOGS_DIR = OUTPUTS_DIR / "logs"

DOCS_DIR = BASE_DIR / "docs"

# --------------------------------------------------------------------------
# File paths
# --------------------------------------------------------------------------
RAW_SALES_DATA_PATH = RAW_DATA_DIR / "sales_data.csv"
CLEANED_SALES_DATA_PATH = PROCESSED_DATA_DIR / "cleaned_sales_data.csv"

EXCEL_REPORT_PATH = REPORTS_DIR / "Sales_Analysis_Report.xlsx"
BUSINESS_INSIGHTS_PATH = REPORTS_DIR / "business_insights.txt"
DATA_QUALITY_REPORT_PATH = REPORTS_DIR / "data_quality_report.xlsx"
EXECUTIVE_DASHBOARD_PATH = CHARTS_DIR / "executive_dashboard.png"
APPLICATION_LOG_PATH = LOGS_DIR / "application.log"

# --------------------------------------------------------------------------
# Dataset generation settings
# --------------------------------------------------------------------------
NUMBER_OF_TRANSACTIONS = 15000
RANDOM_SEED = 42

# Date range for the synthetic dataset (two full years of history)
DATASET_START_DATE = "2023-01-01"
DATASET_END_DATE = "2024-12-31"

# Approximate number of unique customers to simulate repeat-purchase
# behaviour (fewer customers than orders => natural repeat customers).
NUMBER_OF_CUSTOMERS = 3200

# --------------------------------------------------------------------------
# Required columns (used for validation)
# --------------------------------------------------------------------------
REQUIRED_COLUMNS = [
    "Order_ID",
    "Order_Date",
    "Customer_ID",
    "Product",
    "Category",
    "Quantity",
    "Unit_Price",
    "Sales",
    "Region",
    "City",
    "Payment_Mode",
]

# --------------------------------------------------------------------------
# Analysis settings
# --------------------------------------------------------------------------
TOP_N_PRODUCTS = 10
BOTTOM_N_PRODUCTS = 10
TOP_N_CUSTOMERS = 10

# A customer with more than one distinct order is considered a repeat
# customer. This threshold is kept here so the definition is explicit
# and can be changed in a single place if required.
REPEAT_CUSTOMER_MIN_ORDERS = 2

# --------------------------------------------------------------------------
# ABC product classification thresholds (cumulative revenue contribution)
# --------------------------------------------------------------------------
# A product is classified 'A' while cumulative revenue share is <= ABC_A_THRESHOLD,
# 'B' while cumulative revenue share is <= ABC_B_THRESHOLD, and 'C' beyond that.
ABC_A_THRESHOLD = 80.0
ABC_B_THRESHOLD = 95.0

# --------------------------------------------------------------------------
# RFM-style customer segmentation
# --------------------------------------------------------------------------
# Number of quantile bins used to score Recency, Frequency and Monetary
# value (1 = lowest, RFM_BINS = highest). Kept small and explicit so the
# rules stay simple and explainable rather than a "black box" model.
RFM_BINS = 4

# --------------------------------------------------------------------------
# Visualization settings
# --------------------------------------------------------------------------
CHART_DPI = 150
CHART_STYLE = "seaborn-v0_8-whitegrid"
CHART_FIGSIZE_WIDE = (10, 6)
CHART_FIGSIZE_SQUARE = (8, 8)

# --------------------------------------------------------------------------
# Logging
# --------------------------------------------------------------------------
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# --------------------------------------------------------------------------
# Power BI integration (additive - does not affect the core pipeline)
# --------------------------------------------------------------------------
# Python remains the single source of data preparation. These small
# dimension tables are exported next to the cleaned CSV so Power BI can
# relate them to the sales table instead of re-implementing RFM/ABC logic.
CUSTOMER_SEGMENTS_PATH = PROCESSED_DATA_DIR / "customer_segments.csv"
PRODUCT_CLASSIFICATION_PATH = PROCESSED_DATA_DIR / "product_classification.csv"
POWERBI_DIR = BASE_DIR / "powerbi"
