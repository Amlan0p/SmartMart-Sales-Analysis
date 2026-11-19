# Python vs DAX-equivalent reconciliation report

> **Read this first.** The 'DAX-equivalent value' column was computed in pandas by re-implementing the
> logic of each measure in `powerbi/dax/measures.dax` on the same model tables and relationships.
> It was **not** produced by Power BI. After building the report, compare the real card values in
> Power BI Desktop with the 'Python value' column below.

Total checks: **109** | Matched: **106** | Mismatched: **3**

## Model integrity

| Measure | Python value | DAX-equivalent | Match | Note |
|---|---:|---:|:---:|---|
| Dim_Customer[Customer_ID] unique (1 side) | 1 | 1 | YES |  |
| Dim_Product[Product] unique (1 side) | 1 | 1 | YES |  |
| Dim_Date[Date] unique and contiguous | 1 | 1 | YES |  |
| Orphan Fact_Sales rows (Customer_ID not in Dim_Customer) | 0 | 0 | YES |  |
| Orphan Fact_Sales rows (Product not in Dim_Product) | 0 | 0 | YES |  |
| Orphan Fact_Sales rows (Order_Date not in Dim_Date) | 0 | 0 | YES |  |
| Customers in Dim_Customer with no sales (unused dimension rows) | 0 | 0 | YES |  |
| Fact_Sales[Order_ID] unique (grain = one row per order) | 1 | 1 | YES |  |

## Headline KPIs

| Measure | Python value | DAX-equivalent | Match | Note |
|---|---:|---:|:---:|---|
| Total Revenue | 189,024,945.86 | 189,024,945.86 | YES |  |
| Total Orders | 14,970 | 14,970 | YES |  |
| Total Customers | 2,953 | 2,953 | YES |  |
| Total Units Sold | 30,256 | 30,256 | YES |  |
| Average Order Value | 12,626.92 | 12,626.92 | YES |  |
| Average Selling Price | 6,247.52 | 6,247.52 | YES |  |

## Monthly revenue

| Measure | Python value | DAX-equivalent | Match | Note |
|---|---:|---:|:---:|---|
| Number of months | 24 | 24 | YES |  |
| Largest absolute difference across all 24 months (INR) | 0.00 | 0.00 | YES |  |
| Peak Revenue Month | 2023-11 | 2023-11 | YES |  |
| Lowest Revenue Month | 2023-02 | 2023-02 | YES |  |

## Category revenue

| Measure | Python value | DAX-equivalent | Match | Note |
|---|---:|---:|:---:|---|
| Electronics | 71,223,416.54 | 71,223,416.54 | YES |  |
| Furniture | 66,720,645.27 | 66,720,645.27 | YES |  |
| Home Appliances | 32,390,807.34 | 32,390,807.34 | YES |  |
| Clothing | 11,347,795.67 | 11,347,795.67 | YES |  |
| Accessories | 6,253,898.95 | 6,253,898.95 | YES |  |
| Grocery | 1,088,382.09 | 1,088,382.09 | YES |  |

## Category contribution %

| Measure | Python value | DAX-equivalent | Match | Note |
|---|---:|---:|:---:|---|
| Electronics | 37.68 | 37.68 | YES |  |
| Furniture | 35.30 | 35.30 | YES |  |
| Home Appliances | 17.14 | 17.14 | YES |  |
| Clothing | 6.00 | 6.00 | YES |  |
| Accessories | 3.31 | 3.31 | YES |  |
| Grocery | 0.58 | 0.58 | YES |  |

## Regional revenue

| Measure | Python value | DAX-equivalent | Match | Note |
|---|---:|---:|:---:|---|
| East | 39,657,536.84 | 39,657,536.84 | YES |  |
| South | 39,501,870.25 | 39,501,870.25 | YES |  |
| North | 36,947,750.44 | 36,947,750.44 | YES |  |
| Central | 36,783,935.89 | 36,783,935.89 | YES |  |
| West | 36,133,852.44 | 36,133,852.44 | YES |  |
| Highest Performing Region | East | East | YES |  |
| Lowest Performing Region | West | West | YES |  |

## Regional orders

| Measure | Python value | DAX-equivalent | Match | Note |
|---|---:|---:|:---:|---|
| East | 3,038 | 3,038 | YES |  |
| South | 3,023 | 3,023 | YES |  |
| North | 2,909 | 2,909 | YES |  |
| Central | 2,991 | 2,991 | YES |  |
| West | 3,009 | 3,009 | YES |  |

## Regional AOV

| Measure | Python value | DAX-equivalent | Match | Note |
|---|---:|---:|:---:|---|
| East | 13,053.83 | 13,053.83 | YES |  |
| South | 13,067.11 | 13,067.11 | YES |  |
| North | 12,701.19 | 12,701.19 | YES |  |
| Central | 12,298.21 | 12,298.21 | YES |  |
| West | 12,008.59 | 12,008.59 | YES |  |

## Payment revenue

| Measure | Python value | DAX-equivalent | Match | Note |
|---|---:|---:|:---:|---|
| UPI | 71,570,715.96 | 71,570,715.96 | YES |  |
| Cash on Delivery | 34,269,959.25 | 34,269,959.25 | YES |  |
| Credit Card | 32,752,751.80 | 32,752,751.80 | YES |  |
| Debit Card | 31,114,430.49 | 31,114,430.49 | YES |  |
| Net Banking | 18,774,627.72 | 18,774,627.72 | YES |  |
| Unknown | 542,460.64 | 542,460.64 | YES |  |

## Top 5 products

| Measure | Python value | DAX-equivalent | Match | Note |
|---|---:|---:|:---:|---|
| Laptop | 44,345,930.75 | 44,345,930.75 | YES |  |
| Sofa | 30,005,182.30 | 30,005,182.30 | YES |  |
| Dining Table | 18,588,891.86 | 18,588,891.86 | YES |  |
| Smartphone | 15,786,246.34 | 15,786,246.34 | YES |  |
| Microwave Oven | 10,678,166.75 | 10,678,166.75 | YES |  |

## Products

| Measure | Python value | DAX-equivalent | Match | Note |
|---|---:|---:|:---:|---|
| Lowest product by revenue | Biscuits (Pack) | Biscuits (Pack) | YES |  |

## Year-over-year

| Measure | Python value | DAX-equivalent | Match | Note |
|---|---:|---:|:---:|---|
| [Latest Year YoY Growth %] (2024 vs 2023), shown to 1 dp | 5.10 | 5.10 | YES |  |

## Customers

| Measure | Python value | DAX-equivalent | Match | Note |
|---|---:|---:|:---:|---|
| Repeat Customers (context-sensitive measure, no filters) | 2,435 | 2,435 | YES |  |
| Repeat Customers (Lifetime Flag measure, no filters) | 2,435 | 2,435 | YES |  |
| One-time Customers | 518 | 518 | YES |  |
| Repeat Customer Rate % (2 dp) | 82.46 | 82.46 | YES |  |
| Top customer ID | CUST01384 | CUST01384 | YES |  |
| Top customer revenue | 1,257,221.40 | 1,257,221.40 | YES |  |

## Segmentation

| Measure | Python value | DAX-equivalent | Match | Note |
|---|---:|---:|:---:|---|
| High Value - customers | 574 | 574 | YES |  |
| High Value - revenue | 103,683,919.33 | 103,683,919.33 | YES |  |
| Loyal - customers | 1,186 | 1,186 | YES |  |
| Loyal - revenue | 68,897,297.78 | 68,897,297.78 | YES |  |
| Regular - customers | 675 | 675 | YES |  |
| Regular - revenue | 9,584,316.98 | 9,584,316.98 | YES |  |
| One-time - customers | 518 | 518 | YES |  |
| One-time - revenue | 6,859,411.77 | 6,859,411.77 | YES |  |

## Pareto / ABC

| Measure | Python value | DAX-equivalent | Match | Note |
|---|---:|---:|:---:|---|
| Products needed for ~80% of revenue | 10 | 10 | YES | Python counts the product that first crosses 80%. |
| ABC class mismatches: Python vs [ABC Class (Dynamic)] (rounded as shipped) | 0 | 0 | YES |  |
| Class A - revenue | 149,793,451.94 | 149,793,451.94 | YES |  |
| Class A - products | 9 | 9 | YES |  |
| Class B - revenue | 29,787,847.51 | 29,787,847.51 | YES |  |
| Class B - products | 11 | 11 | YES |  |
| Class C - revenue | 9,443,646.41 | 9,443,646.41 | YES |  |
| Class C - products | 15 | 15 | YES |  |

## Slicer: Region = East

| Measure | Python value | DAX-equivalent | Match | Note |
|---|---:|---:|:---:|---|
| Total Revenue | 39,657,536.84 | 39,657,536.84 | YES |  |
| Total Orders | 3,038 | 3,038 | YES |  |
| Total Customers | 1,647 | 1,647 | YES |  |
| Total Units Sold | 6,254 | 6,254 | YES |  |
| Average Order Value | 13,053.83 | 13,053.83 | YES |  |
| Average Selling Price | 6,341.15 | 6,341.15 | YES |  |

## Slicer: Year = 2024

| Measure | Python value | DAX-equivalent | Match | Note |
|---|---:|---:|:---:|---|
| Total Revenue | 96,863,375.48 | 96,863,375.48 | YES |  |
| Total Orders | 7,515 | 7,515 | YES |  |
| Total Customers | 2,453 | 2,453 | YES |  |
| Total Units Sold | 15,138 | 15,138 | YES |  |
| Average Order Value | 12,889.34 | 12,889.34 | YES |  |
| Average Selling Price | 6,398.69 | 6,398.69 | YES |  |

## Slicer: Category = Electronics

| Measure | Python value | DAX-equivalent | Match | Note |
|---|---:|---:|:---:|---|
| Total Revenue | 71,223,416.54 | 71,223,416.54 | YES |  |
| Total Orders | 2,592 | 2,592 | YES |  |
| Total Customers | 1,479 | 1,479 | YES |  |
| Total Units Sold | 5,378 | 5,378 | YES |  |
| Average Order Value | 27,478.17 | 27,478.17 | YES |  |
| Average Selling Price | 13,243.48 | 13,243.48 | YES |  |

## Slicer: Payment_Mode = UPI AND Region = South

| Measure | Python value | DAX-equivalent | Match | Note |
|---|---:|---:|:---:|---|
| Total Revenue | 14,771,596.37 | 14,771,596.37 | YES |  |
| Total Orders | 1,141 | 1,141 | YES |  |
| Total Customers | 847 | 847 | YES |  |
| Total Units Sold | 2,344 | 2,344 | YES |  |
| Average Order Value | 12,946.18 | 12,946.18 | YES |  |
| Average Selling Price | 6,301.88 | 6,301.88 | YES |  |

## Expected difference

| Measure | Python value | DAX-equivalent | Match | Note |
|---|---:|---:|:---:|---|
| Repeat Customers, Year=2024: context-sensitive [Repeat Customers] | 2,435 | 1,596 | NO | Different by design: counts customers with >=2 orders INSIDE 2024 only; Python figure is whole-period. |
| Repeat Customers, Year=2024: [Repeat Customers (Lifetime Flag)] | 2,435 | 2,198 | NO | Lifetime flag restricted to customers active in 2024; equals Python's definition for those customers. |
| ABC class mismatches if cumulative % were NOT rounded (0 = none) | 0 | 1 | NO | Boundary case: Jeans (95.004% -> C unrounded vs B in Python) |
