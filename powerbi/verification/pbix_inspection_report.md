# PBIX inspection - SmartMart_Sales_Dashboard_Final.pbix

Read-only inspection by `inspect_pbix.py`. The compressed `DataModel` (826,397 bytes) could **not** be read, so measure formulas, relationships and Power Query steps are not covered.

| Page | Canvas | Visuals | Of which slicers (hidden) |
|---|---|---:|---:|
| Executive Overview | 1920 x 1080 | 13 | 5 (0) |
| Product Performance | 1920 x 1080 | 11 | 5 (5) |
| Regional Performance | 1920 x 1080 | 12 | 5 (5) |
| Customer & Payment | 1920 x 1080 | 12 | 5 (5) |

## Executive Overview

| Visual | Fields by role | Sort |
|---|---|---|
| cardVisual | Data: Fact_Sales[Average Order Value] (measure), Fact_Sales[Total Revenue] (measure), Fact_Sales[Total Orders] (measure), Fact_Sales[Total Units Sold] (measure), Fact_Sales[Total Customers] (measure) | Fact_Sales[Average Order Value] (measure) Descending |
| donutChart | Category: Fact_Sales[Payment_Mode]; Y: Fact_Sales[Total Revenue] (measure) | Fact_Sales[Total Revenue] (measure) Descending |
| clusteredBarChart | Category: Fact_Sales[Region]; Y: Fact_Sales[Total Revenue] (measure) | Fact_Sales[Total Revenue] (measure) Descending |
| clusteredColumnChart | Category: dim_product[Category]; Y: Fact_Sales[Total Revenue] (measure) | Fact_Sales[Total Revenue] (measure) Descending |
| clusteredColumnChart | Category: Dim_Date[Year]; Tooltips: Fact_Sales[Revenue Previous Year] (measure); Y: Fact_Sales[Total Revenue] (measure) | Fact_Sales[Total Revenue] (measure) Descending |
| lineChart | Category: Dim_Date[Year-Month]; Y: Fact_Sales[Total Revenue] (measure) | Fact_Sales[Total Revenue] (measure) Descending |
| clusteredBarChart | Category: dim_product[Product]; Y: Fact_Sales[Total Revenue] (measure) | Fact_Sales[Total Revenue] (measure) Descending |
| lineChart | Category: Dim_Date[Year-Month]; Y: Fact_Sales[Total Orders] (measure) | Fact_Sales[Total Orders] (measure) Descending |

## Product Performance

| Visual | Fields by role | Sort |
|---|---|---|
| cardVisual | Data: Fact_Sales[Total Revenue] (measure), Fact_Sales[Total Units Sold] (measure), Fact_Sales[Products Sold] (measure), Fact_Sales[Average Selling Price] (measure) | Fact_Sales[Total Revenue] (measure) Descending |
| clusteredColumnChart | Category: dim_product[Category]; Y: Fact_Sales[Total Revenue] (measure) | Fact_Sales[Total Revenue] (measure) Descending |
| clusteredBarChart | Category: dim_product[Product]; Y: Fact_Sales[Total Revenue] (measure) | Fact_Sales[Total Revenue] (measure) Descending |
| clusteredBarChart | Category: dim_product[Product]; Y: Fact_Sales[Total Revenue] (measure) | Fact_Sales[Total Revenue] (measure) Descending |
| lineClusteredColumnComboChart | Category: dim_product[Product]; Y: Fact_Sales[Total Revenue] (measure); Y2: Fact_Sales[Total Units Sold] (measure) | Fact_Sales[Total Revenue] (measure) Descending |
| tableEx | Values: dim_product[Product], dim_product[Category], Fact_Sales[Total Revenue] (measure), Fact_Sales[Total Units Sold] (measure), Fact_Sales[Average Selling Price] (measure) | - |

## Regional Performance

| Visual | Fields by role | Sort |
|---|---|---|
| cardVisual | Data: Fact_Sales[Total Revenue] (measure), Fact_Sales[Total Orders] (measure), Fact_Sales[Total Customers] (measure), Fact_Sales[Average Revenue per Customer] (measure) | Fact_Sales[Total Revenue] (measure) Descending |
| clusteredBarChart | Category: Fact_Sales[Region]; Y: Fact_Sales[Total Revenue] (measure) | Fact_Sales[Total Revenue] (measure) Descending |
| clusteredBarChart | Category: Fact_Sales[City]; Y: Fact_Sales[Total Revenue] (measure) | Fact_Sales[Total Revenue] (measure) Descending |
| donutChart | Category: Fact_Sales[Region]; Y: Fact_Sales[Total Revenue] (measure) | Fact_Sales[Total Revenue] (measure) Descending |
| clusteredColumnChart | Category: Fact_Sales[Region]; Y: Fact_Sales[Total Orders] (measure) | Fact_Sales[Total Orders] (measure) Descending |
| clusteredColumnChart | Category: Fact_Sales[Region]; Y: Fact_Sales[Total Customers] (measure) | Fact_Sales[Total Customers] (measure) Descending |
| tableEx | Values: Fact_Sales[Region], Fact_Sales[Total Revenue] (measure), Fact_Sales[Total Customers] (measure), Fact_Sales[Total Orders] (measure), Fact_Sales[Average Revenue per Customer] (measure) | - |

## Customer & Payment

| Visual | Fields by role | Sort |
|---|---|---|
| cardVisual | Data: Fact_Sales[Total Customers] (measure), Fact_Sales[One-time Customers] (measure), Fact_Sales[Repeat Customers] (measure), Fact_Sales[Average Order Value] (measure) | Fact_Sales[Total Customers] (measure) Descending |
| clusteredBarChart | Category: dim_customer[Customer_ID]; Y: Fact_Sales[Total Revenue] (measure) | Fact_Sales[Total Revenue] (measure) Descending |
| donutChart | Category: Fact_Sales[City]; Y: Fact_Sales[Total Revenue] (measure) | Fact_Sales[Total Revenue] (measure) Descending |
| donutChart | Category: Fact_Sales[Payment_Mode]; Y: Fact_Sales[Total Revenue] (measure) | Fact_Sales[Total Revenue] (measure) Descending |
| clusteredBarChart | Category: Fact_Sales[City]; Y: Fact_Sales[Total Customers] (measure) | Fact_Sales[Total Customers] (measure) Descending |
| clusteredColumnChart | Category: Fact_Sales[Payment_Mode]; Y: Fact_Sales[Total Orders] (measure) | Fact_Sales[Total Orders] (measure) Descending |
| tableEx | Values: Fact_Sales[Customer_ID], Fact_Sales[City], Fact_Sales[Customer_Type], Fact_Sales[Total Orders] (measure), Fact_Sales[Total Revenue] (measure), Fact_Sales[Average Order Value] (measure) | Fact_Sales[City] Descending |

## Checks

| Check | Result | Detail |
|---|---|---|
| Four expected pages in the expected order | PASS | Executive Overview, Product Performance, Regional Performance, Customer & Payment |
| Executive Overview: all five slicers present and synced | PASS | Category, Date, Payment_Mode, Product, Region |
| Product Performance: all five slicers present and synced | PASS | Category, Date, Payment_Mode, Product, Region |
| Regional Performance: all five slicers present and synced | PASS | Category, Date, Payment_Mode, Product, Region |
| Customer & Payment: all five slicers present and synced | PASS | Category, Date, Payment_Mode, Product, Region |
| Top N / Bottom N filter on any visual (specification asks for 5) | FAIL | none found |
| Every non-slicer visual has a custom title | FAIL | titles are Power BI automatic titles |
| Every visual has alt text | FAIL | no alt text set |
| Executive Overview: line chart on Dim_Date[Year-Month] sorted by a measure (axis not chronological) | FAIL | sorted by Fact_Sales[Total Revenue] (measure) Descending |
| Executive Overview: line chart on Dim_Date[Year-Month] sorted by a measure (axis not chronological) | FAIL | sorted by Fact_Sales[Total Orders] (measure) Descending |
