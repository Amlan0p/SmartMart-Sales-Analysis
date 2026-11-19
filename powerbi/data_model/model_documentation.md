# SmartMart Power BI Data Model

**Type:** star schema, one fact table and three dimensions, all loaded from CSV files written by the Python pipeline. No database is used.

```
Dim_Date (Date)  ──1───*──  Fact_Sales (Order_Date)
Dim_Customer (Customer_ID) ──1───*──  Fact_Sales (Customer_ID)
Dim_Product (Product)      ──1───*──  Fact_Sales (Product)
```

## Tables

| Table | Source | Rows (current run) | Grain | Key |
|---|---|---:|---|---|
| `Fact_Sales` | `data/processed/cleaned_sales_data.csv` | 14,970 | one order (one product line) | `Order_ID` (unique) |
| `Dim_Customer` | `data/processed/customer_segments.csv` | 2,953 | one customer | `Customer_ID` (unique) |
| `Dim_Product` | `data/processed/product_classification.csv` | 35 | one product | `Product` (unique) |
| `Dim_Date` | DAX calculated table (`dax/date_table.dax`) | 731 (2023-01-01 to 2024-12-31) | one calendar day | `Date` (unique, contiguous) |

## Relationships (create exactly these three; see BUILD_GUIDE step 6)

| From (one side) | To (many side) | Cardinality | Cross-filter | Active |
|---|---|---|---|---|
| `Dim_Date[Date]` | `Fact_Sales[Order_Date]` | One-to-many | Single (Dim → Fact) | Yes |
| `Dim_Customer[Customer_ID]` | `Fact_Sales[Customer_ID]` | One-to-many | Single | Yes |
| `Dim_Product[Product]` | `Fact_Sales[Product]` | One-to-many | Single | Yes |

**Why the customer export cannot create duplicates or wrong relationships**
1. `build_customer_dimension()` raises `ValueError` if `Customer_ID` repeats, so the one-side key is unique by construction (unit-tested).
2. Every `Customer_ID` in `Fact_Sales` exists in `Dim_Customer` and vice versa. The reconciliation script checks 0 orphan rows in both directions.
3. The export is built from the same cleaned DataFrame as the sales CSV, so the two files always describe the same customers. **Always re-run `python main.py` before refreshing Power BI** so both files come from the same run.

## Columns kept in `Fact_Sales`

`Order_ID, Order_Date, Customer_ID, Product, Quantity, Unit_Price, Sales, Region, City, Payment_Mode, Customer_Type`

Removed in Power Query to keep one source of truth: `Year, Month, Month_Name, Quarter` (use `Dim_Date`), `Category` (use `Dim_Product[Category]`), `Order_Value` (identical to `Sales`).

`Region`, `City`, `Payment_Mode` and `Customer_Type` stay on the fact table as descriptive attributes. They are not split into dimensions because `City` does not map cleanly to one `Region`: the 60 rows with the placeholder city `Unknown` appear in all five regions.

## Transaction-level vs order-level

In this dataset one row is one order with one product, and `Order_ID` is unique (14,970 rows, 14,970 distinct orders). Revenue is a `SUM` over rows. Order, customer and product counts use `DISTINCTCOUNT`, so nothing is double-counted even if multi-line orders appear in future data.

## Hidden columns and formatting

- Hide in Report view: `Fact_Sales[Order_ID]`, `[Unit_Price]`, `[Sales]`, `[Quantity]` (use measures instead), `Dim_Product[Cumulative_Revenue_Percent]`, `Dim_Customer[Monetary]`.
- `Dim_Date[Month Name]` sorted by `Month Number`; `[Quarter]` by `Quarter Number`; `[Day of Week]` by `Day of Week Number`.
- Mark `Dim_Date` as the date table.

## Static (Python) vs dynamic (DAX) classifications

| Attribute | Where computed | Reacts to slicers? |
|---|---|---|
| `Dim_Customer[Segment]` (RFM) | Python, whole period, exported | No. A customer keeps one segment. Revenue and customer counts per segment do respond to slicers. |
| `Dim_Product[ABC_Class]` | Python, whole period, exported | No (use for stable colouring / donut). |
| `[ABC Class (Dynamic)]` | DAX | Yes (recomputed on the slicer selection). |
| `Fact_Sales[Customer_Type]` | Python, whole period | No. |
| `[Repeat Customers]` | DAX | Yes. |
| `[Repeat Customers (Lifetime Flag)]` | DAX using Python `Frequency` | Partly (counts only customers active in the selection, using their lifetime flag). |

## Segmentation methodology (Python, `src/analysis.py: customer_segmentation`)

Recency (days since last order, relative to the latest order date), Frequency (distinct orders) and Monetary (total revenue) are each scored 1–4 by quantile rank; the three scores are summed (3–12). Rules: Frequency = 1 → **One-time**; repeat customer with RFM ≥ 11 → **High Value**; repeat with RFM > 6 → **Loyal**; otherwise repeat → **Regular**. The code also defines an **Occasional** label, but no customer reaches it in the current data (the Regular rule catches every remaining repeat customer), so only four segments appear.
