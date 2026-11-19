# SmartMart Dashboard Specification

Design contract for the four-page report. The click-by-click build (fields, positions, sizes) is in [`../BUILD_GUIDE.md`](../BUILD_GUIDE.md) section 10. This file explains the design rules and proves every assignment/brief requirement has a home.

**Status:** this is the design *specification*. The delivered `.pbix` implements part of it; the differences are listed in documentation section 21.3.

> **Read this first.** Sections 1-4 are the original *plan*. The delivered `.pbix` implements only part of it; Section 5 states what was and was not built. Items marked "Not implemented" are future scope, not completed requirements. The Python pipeline still produces the Pareto, ABC, segmentation and ranking results (see the report, Chapters 11-16).

## 1. Design rules

| Item | Rule |
|---|---|
| Canvas | 16:9, 1280 × 720 px, page background `#F4F7FB`, visuals white with 6 px rounded `#D9E2EC` border |
| Palette | Cronus blue `#3669AB`, green `#69A147`, navy text `#1B3A5C`, grey `#8795A8`, amber `#E0A030` (highlight only). Theme file: `theme/SmartMart_Theme.json` |
| Type | Segoe UI. Page title 22 pt semibold, visual titles 13 pt, KPI values 24 pt, labels 10 pt |
| Layout grid | 16 px outer margin, 10 px gutter. Header band y 0–56, slicer band y 64–116, content from y 124 |
| Currency | `₹`, 0 decimals on cards and axes (Python reports use the same ₹ symbol) |
| Percentages | 1 decimal |
| Colour meaning | Blue = primary measure, green = positive/growth or highlight series, grey = bottom/neutral, red only for negative variance |
| Data honesty | All data is synthetic. Show a footer note on each page: *"Synthetic data generated for training purposes - not real business data."* (Insert > Text box, y 700, 9 pt, grey.) |

## 2. Interactivity

- **Slicers (synced on all pages):** date range (between), Region, Category, Product, Payment Mode.
- **Cross-filtering:** default on; exceptions listed in guide section 11.
- **Drill-down hierarchies:** Date (Year > Quarter > Month), Category > Product, Region > City.
- **Tooltips:** contribution % on category and customer visuals.

## 3. Requirement traceability

### Page 1 – Executive Overview
| Required | Visual / measure |
|---|---|
| Total Revenue, Orders, Customers, Units, AOV, ASP | Six KPI cards: `[Total Revenue]`, `[Total Orders]`, `[Total Customers]`, `[Total Units Sold]`, `[Average Order Value]`, `[Average Selling Price]` |
| Monthly revenue trend | Line chart on `Dim_Date` hierarchy |
| Revenue by category / region | Bar by `Dim_Product[Category]`, column by `Fact_Sales[Region]` |
| Top 5 products | Bar with Top N = 5 |
| (extra) YoY | `[Latest Year YoY Growth %]`, revenue by year |

### Page 2 – Product Performance
| Required | Visual / measure |
|---|---|
| Top 10 / Bottom 10 by revenue | Two bars with Top N / Bottom N filter |
| Revenue by category | Donut |
| Quantity sold by product | Bar, `[Total Units Sold]` |
| Product revenue contribution | `[Product Contribution %]` (table with data bars) |
| Pareto | Combo chart: `[Total Revenue]` columns + `[Cumulative Revenue %]` line |
| ABC classification | Matrix on `Dim_Product[ABC_Class]` (Python, static) + `[ABC Class (Dynamic)]` in table |
| Product performance comparison | Scatter units vs revenue by category |

### Page 3 – Regional Performance
| Required | Visual / measure |
|---|---|
| Revenue by region / city | Column (Region > City drill) and city bar |
| Orders by region, AOV by region | Two columns |
| Regional comparison | Table with `[Regional Revenue Contribution %]`, `[Regional Revenue Rank]`, `[Revenue vs Regional Average %]` |
| Highest / lowest region | Cards `[Highest Performing Region]`, `[Lowest Performing Region]` (+ revenues) |
| Regional sales trends | Line by month, legend Region |

### Page 4 – Customer and Payment
| Required | Visual / measure |
|---|---|
| Unique customers, repeat, one-time | Cards `[Total Customers]`, `[Repeat Customers]`, `[One-time Customers]` (+ rate) |
| Customer segmentation | Donut and bar on `Dim_Customer[Segment]` (Python RFM) |
| Top 10 customers | Bar with Top N = 10 |
| Revenue by customer type | Donut on `Fact_Sales[Customer_Type]` |
| Payment distribution / revenue | Donut (orders), bar (revenue), summary table |

### Cross-cutting
| Required | Where |
|---|---|
| Date, Region, Category, Product, Payment slicers | Slicer bar (guide section 9) |
| Calendar table + relationships | `dax/date_table.dax`, guide sections 5–6 |
| DISTINCTCOUNT, transaction vs order grain | `data_model/model_documentation.md` |
| Python vs Power BI verification | `verification/` and guide section 12 |

## 4. Accessibility and quality checklist

- Every visual has a title and alt text.
- Contrast: navy text on white; no information carried by colour alone (labels shown).
- No overlaps; nothing outside the canvas.
- Page order matches navigator order.

## 5. Implementation status in the delivered `.pbix`

Sources: the project team's testing of the report in Power BI Desktop (all four pages load and display correctly; functionality and slicer interactions checked), plus the audit's read-only inspection of the report definition (`../verification/pbix_inspection_report.md`) and the four screenshots. The audit could not read the compressed semantic model.

| Specified item | Status in the delivered report |
|---|---|
| Four pages; five synced slicers (Date, Region, Category, Product, Payment_Mode) | Implemented. Slicers visible on page 1, hidden on pages 2-4 |
| Page 1: KPI cards, revenue by category / region / product, monthly trend, yearly column | Implemented as KPI card set (revenue, orders, customers, units, AOV), payment donut, region bar, category column, year column, product bar and two monthly line charts. Top 5 products: not implemented (all products shown) |
| Page 1: monthly trend with date drill-down | Not implemented as specified: flat Year-Month axis, sorted by value (not chronological) |
| Page 2: Top 10 / Bottom 10 products (Top N filter) | Not implemented (two full product bars) |
| Page 2: category donut, quantity ranking, scatter, contribution %, Pareto line, ABC matrix | Not implemented. Present: category column, product bars, units-and-revenue combo chart, product details table |
| Page 3: revenue by region and city, orders, customers, regional table | Implemented. Average order value by region, highest/lowest region cards, regional trend line, Region > City drill: not implemented |
| Page 4: customer KPIs (customers, one-time, repeat, AOV), top customers by revenue, city and payment charts, customer table | Implemented. Top 10 filter: not implemented (customer bar chart not Top-N filtered) |
| Page 4: segmentation visuals, customer-type donut, payment summary table | Not implemented |
| Footer note on every page; drill-down hierarchies; tooltips on contribution %; conditional formatting | Not evidenced in the report definition |
| Custom visual titles and alt text (section 4) | Not implemented: automatic titles, no alt text |
