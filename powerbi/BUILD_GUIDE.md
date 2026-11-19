# SmartMart Power BI Build Guide (step by step)

> **Status.** This guide is the *original* build recipe, written before the report existed. A four-page report has since been built by the team, who opened and tested it in Power BI Desktop, and is delivered as `SmartMart_Sales_Dashboard_Final.pbix` (see `verification/pbix_inspection_report.md`). The delivered report implements only part of this recipe; use this guide to rebuild or extend it. Sections that say "not done" describe the state before the report was built. Visuals described here that are absent from the delivered report (Top N filters, Pareto, ABC matrix, segmentation, regional trend, highest/lowest cards, custom titles, alt text) are **future scope**, not completed work; see `dashboard_design/dashboard_specification.md` section 5.

**You need:** Power BI Desktop for Windows (free), Python 3.10+ with the project installed, and this project folder.

Files you will paste from:

| File | Used in step |
|---|---|
| `powerbi/power_query/DataFolderPath.m` | 3 |
| `powerbi/power_query/sales_data.m`, `dim_customer.m`, `dim_product.m` | 4 |
| `powerbi/dax/date_table.dax` | 5 |
| `powerbi/dax/measures.dax` | 7 |
| `powerbi/dashboard_design/theme/SmartMart_Theme.json` | 8 |

---

## 1. Generate the data with Python

```bash
pip install -r requirements.txt
python main.py
```

Confirm that `data/processed/` now holds **three** CSV files:

| File | Expected rows (excluding header) |
|---|---:|
| `cleaned_sales_data.csv` | 14,970 |
| `customer_segments.csv` | 2,953 |
| `product_classification.csv` | 35 |

Optional but recommended: `python powerbi/verification/validate_powerbi_assets.py` (expect "All static checks passed").

## 2. Create the report and switch off hidden date tables

1. Open Power BI Desktop → **Blank report** → **File > Save as** → `SmartMart_Sales_Dashboard.pbix` inside the `powerbi/` folder.
2. **File > Options and settings > Options > Current File > Data Load** → under *Time intelligence* **untick "Auto date/time for new files"** → OK. (Otherwise Power BI creates hidden date tables that conflict with `Dim_Date`.)

## 3. Create the folder parameter

1. **Home > Transform data > Transform data** (opens Power Query Editor).
2. **Home > Manage Parameters > New Parameter**.
3. Name `DataFolderPath` · Type **Text** · Suggested values **Any value** · Current value = full path of `data\processed\` **ending with a backslash**, e.g. `C:\Projects\SmartMart-Sales-Analytics\data\processed\` → OK.

## 4. Load the three CSV tables

Repeat for each row of the table (Power Query Editor still open):

| Query to create | Paste code from | Rename the query to |
|---|---|---|
| 1 | `power_query/sales_data.m` | `Fact_Sales` |
| 2 | `power_query/dim_customer.m` | `Dim_Customer` |
| 3 | `power_query/dim_product.m` | `Dim_Product` |

For each: **Home > New Source > Blank Query** → **Home > Advanced Editor** → delete everything → paste the whole file → **Done** → right-click the query in the left list → **Rename**.

Checks in the editor: no yellow error bar; `Fact_Sales` has **11** columns; `Dim_Customer` 10; `Dim_Product` 5. In *View > Column profile* on `Order_ID` of `Fact_Sales`, *Distinct* = *Unique* = 14,970.

Click **Home > Close & Apply**. If asked about privacy levels choose *Ignore* for local files.

## 5. Create the calendar table

1. **Table view** (left icon) → **Table tools/Modeling > New table**.
2. Paste the block from `dax/date_table.dax` (from `Dim_Date =` down to the closing parenthesis; the trailing comments are optional) → ✔.
3. Select the `Dim_Date` table → **Table tools > Mark as date table** → Date column `Date` → OK.
4. Sort-by-column (select the column, then **Column tools > Sort by column**):
   `Month Name` → `Month Number`; `Month Short` → `Month Number`; `Quarter` → `Quarter Number`; `Day of Week` → `Day of Week Number`.
5. Hierarchy: in the Data pane right-click `Dim_Date[Year]` → **Add to hierarchy → New hierarchy**, rename it `Date Hierarchy`, then add `Quarter` and `Month Name` (in that order) via right-click → **Add to hierarchy**.
6. Hierarchies on other tables, same method:
   `Dim_Product` → `Category Hierarchy` = `Category` > `Product`;
   `Fact_Sales` → `Geography` = `Region` > `City`.

Expected: `Dim_Date` has **731** rows, first date 2023-01-01, last 2024-12-31.

## 6. Create the three relationships

**Model view** (third left icon). Delete any relationship Power BI created automatically that is not in the table below (right-click line → Delete). Then **Home > Manage relationships > New**:

| From table (column) | To table (column) | Cardinality | Cross-filter direction | Make active |
|---|---|---|---|---|
| `Dim_Date` (`Date`) | `Fact_Sales` (`Order_Date`) | One to many (1:*) | Single | ✔ |
| `Dim_Customer` (`Customer_ID`) | `Fact_Sales` (`Customer_ID`) | One to many (1:*) | Single | ✔ |
| `Dim_Product` (`Product`) | `Fact_Sales` (`Product`) | One to many (1:*) | Single | ✔ |

The "one" side must be the dimension. If Power BI proposes *many-to-many* it means a key is not unique: stop and re-run `python main.py`. In Model view the three lines must show `1` at the dimension end and `*` at `Fact_Sales`, with a single arrow pointing at `Fact_Sales`.

## 7. Create the measures

1. **Home > Enter data** → rename the table (bottom) to `_Measures` → **Load**.
2. Select `_Measures` → **New measure** → paste **one block** from `dax/measures.dax` (the name, `=` and its formula; comment lines starting `//` may be pasted or left out) → Enter. Repeat for every block (46 measures in total). Paste one measure at a time.
3. After the first measure exists, delete the empty `Column1` of `_Measures` (right-click → Delete from model).
4. Set formats (select the measure → **Measure tools**): 

| Measure(s) | Format | Decimals |
|---|---|---:|
| `Total Revenue`, `Average Order Value`, `Average Selling Price`, `Average Revenue per Customer`, `Regional Revenue`, `Customer Revenue`, `Revenue Previous Month`, `Revenue Previous Year`, `Revenue YTD`, `Highest Region Revenue`, `Lowest Region Revenue` | Currency → `₹ English (India)` | 0 |
| `Total Orders`, `Total Customers`, `Total Units Sold`, `Products Sold`, `Repeat Customers`, `One-time Customers`, `Repeat Customers (Lifetime Flag)`, `One-time Customers (Lifetime Flag)`, `Product Revenue Rank`, `Regional Revenue Rank`, `Repeat Min Orders` | Whole number, thousands separator **on** | 0 |
| every measure ending in `%` (also `Cumulative Revenue %`, `Revenue vs Regional Average %`) | Percentage | 1 |
| `ABC A Threshold`, `ABC B Threshold` | Percentage | 0 |
| `Orders per Customer` | Decimal number | 2 |
| `Last Order Date` | Date `yyyy-mm-dd` | – |

5. Display folders (Properties pane → *Display folder*): use the "Folder:" names in the comments (`1 Core KPIs`, `2 Time`, `3 Product`, `4 Region`, `5 Customer`, `6 Payment`).
6. Hide helper columns (right-click → Hide in report view): `Fact_Sales[Order_ID]`, `[Unit_Price]`, `[Sales]`, `[Quantity]`, `Dim_Customer[Monetary]`, `Dim_Product[Cumulative_Revenue_Percent]`.

**Checkpoint A – do this before any visual.** Report view → add a *Card* per measure and compare with the table in section 12. If a number differs, stop here and fix it (usually a wrong relationship or a mistyped formula).

## 8. Apply the theme

**View > Themes (dropdown) > Browse for themes** → select `powerbi/dashboard_design/theme/SmartMart_Theme.json`. The accent colours become Cronus blue `#3669AB` and green `#69A147`.

## 9. Page setup and the shared slicer bar

1. Create four pages (**+** at the bottom). Rename by double-click: `1 Executive Overview`, `2 Product Performance`, `3 Regional Performance`, `4 Customer & Payment`.
2. For every page: **Format page > Canvas settings > Type = 16:9** (1280 × 720). Page background colour `#F4F7FB`.
3. **Positioning recipe used everywhere below:** select the visual → **Format > General tab > Properties** → *Size* (Width / Height) and *Position* (Horizontal / Vertical). The tables give `x, y, w, h` in pixels.
4. **Slicer bar (build on page 1, then sync):** add five slicers at y = 64, h = 52.

| Slicer | Field | Type (Format > Slicer settings > Options > Style) | x | w |
|---|---|---|---:|---:|
| Date | `Dim_Date[Date]` | **Between** | 16 | 280 |
| Region | `Fact_Sales[Region]` | **Dropdown** | 306 | 200 |
| Category | `Dim_Product[Category]` | Dropdown | 516 | 200 |
| Product | `Dim_Product[Product]` | Dropdown (turn on *Search* from the visual's ⋯ menu) | 726 | 260 |
| Payment Mode | `Fact_Sales[Payment_Mode]` | Dropdown | 996 | 268 |

   Then **View > Sync slicers**: select a slicer → in the Sync slicers pane tick **Sync** for all four pages **and Visible** for all four pages (do this for each of the five slicers). Copy/paste the slicers onto pages 2–4 only if you prefer not to use sync; sync is the cleaner method.
5. Header on each page: *Insert > Text box* `x16 y8 w820 h44` (font Segoe UI Semibold 22, colour `#1B3A5C`) with the page title; *Insert > Buttons > Navigator > Page navigator* at `x860 y10 w404 h40`.

## 10. Build the visuals

**Recipes.**
- **KPI card:** Visualizations pane → *Card* → drag the measure into *Fields*. Format → Callout value colour `#3669AB`, size 24; Category label on; Title on with the text given.
- **Chart:** click the visual icon → drop fields into the wells named below (*X-axis / Y-axis / Legend / Values / Details*).
- **Sort:** visual ⋯ → **Sort axis** → choose the field and Ascending/Descending.
- **Top N / Bottom N:** select the visual → *Filters on this visual* → expand the axis field (e.g. `Product`) → **Filter type: Top N** → **Show items: Top** (or **Bottom**) **10** → **By value:** drag `Total Revenue` → **Apply filter**.
- **Data labels:** Format → Visual → Data labels On; Display units *Auto* or *Millions*.
- **Drill down:** for visuals with a hierarchy in the axis, switch on the drill-down arrow (top-right of the visual) and use the *Drill down* / *Expand all* buttons.

### Page 1 – Executive Overview

| # | Visual | Fields | x | y | w | h | Notes |
|--:|---|---|--:|--:|--:|--:|---|
| 1 | Card "Total Revenue" | `[Total Revenue]` | 16 | 124 | 200 | 84 | |
| 2 | Card "Total Orders" | `[Total Orders]` | 226 | 124 | 200 | 84 | |
| 3 | Card "Total Customers" | `[Total Customers]` | 436 | 124 | 200 | 84 | |
| 4 | Card "Total Units Sold" | `[Total Units Sold]` | 646 | 124 | 200 | 84 | |
| 5 | Card "Average Order Value" | `[Average Order Value]` | 856 | 124 | 200 | 84 | |
| 6 | Card "Average Selling Price" | `[Average Selling Price]` | 1066 | 124 | 198 | 84 | |
| 7 | **Line chart** "Monthly Revenue Trend" | X-axis `Dim_Date[Date Hierarchy]` (Year>Quarter>Month Name); Y-axis `[Total Revenue]` | 16 | 218 | 720 | 240 | Drill down enabled; or use `Dim_Date[Year-Month]` to see all 24 months at once |
| 8 | **Clustered bar** "Revenue by Category" | Y-axis `Dim_Product[Category Hierarchy]`; X-axis `[Total Revenue]`; Tooltip `[Category Revenue Contribution %]` | 746 | 218 | 518 | 240 | Sort by `Total Revenue` descending; data labels on |
| 9 | **Clustered column** "Revenue by Region" | X-axis `Fact_Sales[Region]`; Y-axis `[Total Revenue]` | 16 | 468 | 400 | 244 | Sort descending |
| 10 | **Clustered bar** "Top 5 Products" | Y-axis `Dim_Product[Product]`; X-axis `[Total Revenue]` | 426 | 468 | 420 | 244 | Top N filter: **Top 5** by `Total Revenue` |
| 11 | **Clustered column** "Revenue by Year" | X-axis `Dim_Date[Year]`; Y-axis `[Total Revenue]` | 856 | 468 | 408 | 176 | Data labels on |
| 12 | Card "YoY Growth (latest year)" | `[Latest Year YoY Growth %]` | 856 | 652 | 200 | 60 | |
| 13 | Card "Peak Month" | `[Peak Revenue Month]` | 1066 | 652 | 198 | 60 | |

### Page 2 – Product Performance

| # | Visual | Fields | x | y | w | h | Notes |
|--:|---|---|--:|--:|--:|--:|---|
| 1 | Clustered bar "Top 10 Products by Revenue" | Y `Dim_Product[Product]`; X `[Total Revenue]` | 16 | 124 | 340 | 230 | Top N: **Top 10** by `Total Revenue`; sort descending |
| 2 | Clustered bar "Bottom 10 Products by Revenue" | same fields | 366 | 124 | 340 | 230 | Top N: **Bottom 10** by `Total Revenue`; bar colour `#8795A8` |
| 3 | Donut "Revenue by Category" | Legend `Dim_Product[Category]`; Values `[Total Revenue]` | 716 | 124 | 250 | 230 | Detail labels: category + percentage |
| 4 | Clustered bar "Quantity Sold by Product" | Y `Dim_Product[Product]`; X `[Total Units Sold]` | 976 | 124 | 288 | 230 | Top N: **Top 10** by `Total Units Sold` (title says "Top 10") |
| 5 | **Line and clustered column** "Pareto Analysis" | X `Dim_Product[Product]`; Column Y `[Total Revenue]`; Line Y `[Cumulative Revenue %]` | 16 | 364 | 520 | 348 | **Sort axis by `Total Revenue` descending** (essential). Line on secondary axis, min 0 max 1 (100 %). Optionally add constant lines at 0.8 and 0.95 (Format > Y-axis constant line). |
| 6 | **Scatter** "Product Performance Comparison" | X `[Total Units Sold]`; Y `[Total Revenue]`; Legend `Dim_Product[Category]`; Details `Dim_Product[Product]`; Size `[Average Selling Price]` | 546 | 364 | 350 | 348 | |
| 7 | **Matrix** "ABC Classification Summary" | Rows `Dim_Product[ABC_Class]`; Values `[Products Sold]`, `[Total Revenue]`, `[Product Contribution %]` | 906 | 364 | 358 | 150 | Python (static) classes, whole period |
| 8 | **Table** "Product Detail" | `Dim_Product[Product]`, `[Total Revenue]`, `[Product Contribution %]`, `[Product Revenue Rank]`, `[ABC Class (Dynamic)]` | 906 | 524 | 358 | 188 | Format > Cell elements > Data bars on `Product Contribution %`; sort by rank ascending |

### Page 3 – Regional Performance

| # | Visual | Fields | x | y | w | h | Notes |
|--:|---|---|--:|--:|--:|--:|---|
| 1 | Card "Highest Performing Region" | `[Highest Performing Region]` | 16 | 124 | 300 | 84 | |
| 2 | Card "Lowest Performing Region" | `[Lowest Performing Region]` | 326 | 124 | 300 | 84 | |
| 3 | Card "Highest Region Revenue" | `[Highest Region Revenue]` | 636 | 124 | 300 | 84 | |
| 4 | Card "Lowest Region Revenue" | `[Lowest Region Revenue]` | 946 | 124 | 318 | 84 | |
| 5 | Clustered column "Revenue by Region" | X `Fact_Sales[Geography]` (Region>City); Y `[Total Revenue]` | 16 | 218 | 300 | 240 | Drill down Region → City |
| 6 | Clustered column "Orders by Region" | X `Fact_Sales[Region]`; Y `[Total Orders]` | 326 | 218 | 300 | 240 | |
| 7 | Clustered column "Average Order Value by Region" | X `Fact_Sales[Region]`; Y `[Average Order Value]` | 636 | 218 | 300 | 240 | |
| 8 | Donut "Regional Revenue Share" | Legend `Fact_Sales[Region]`; Values `[Total Revenue]` | 946 | 218 | 318 | 240 | |
| 9 | Clustered bar "Revenue by City" | Y `Fact_Sales[City]`; X `[Total Revenue]` | 16 | 468 | 420 | 244 | Sort descending; note the `Unknown` city (60 rows) is real data |
| 10 | Line chart "Regional Sales Trends" | X `Dim_Date[Year-Month]`; Y `[Total Revenue]`; Legend `Fact_Sales[Region]` | 446 | 468 | 520 | 244 | |
| 11 | Table "Regional Performance Comparison" | `Fact_Sales[Region]`, `[Total Revenue]`, `[Total Orders]`, `[Average Order Value]`, `[Regional Revenue Contribution %]`, `[Regional Revenue Rank]`, `[Revenue vs Regional Average %]` | 976 | 468 | 288 | 244 | Conditional formatting (Cell elements > Background colour) on `Revenue vs Regional Average %`: green > 0, red < 0 |

### Page 4 – Customer and Payment Analysis

| # | Visual | Fields | x | y | w | h | Notes |
|--:|---|---|--:|--:|--:|--:|---|
| 1 | Card "Total Unique Customers" | `[Total Customers]` | 16 | 124 | 200 | 84 | |
| 2 | Card "Repeat Customers" | `[Repeat Customers]` | 226 | 124 | 200 | 84 | Responds to the date slicer (see section 12 note) |
| 3 | Card "One-time Customers" | `[One-time Customers]` | 436 | 124 | 200 | 84 | |
| 4 | Card "Repeat Customer Rate" | `[Repeat Customer Rate %]` | 646 | 124 | 200 | 84 | |
| 5 | Card "Avg Revenue per Customer" | `[Average Revenue per Customer]` | 856 | 124 | 200 | 84 | |
| 6 | Card "Orders per Customer" | `[Orders per Customer]` | 1066 | 124 | 198 | 84 | |
| 7 | Donut "Customer Segmentation" | Legend `Dim_Customer[Segment]`; Values `[Total Customers]` | 16 | 218 | 310 | 240 | |
| 8 | Clustered bar "Revenue by Segment" | Y `Dim_Customer[Segment]`; X `[Customer Revenue]` | 336 | 218 | 310 | 240 | |
| 9 | Donut "Revenue by Customer Type" | Legend `Fact_Sales[Customer_Type]`; Values `[Customer Revenue]` | 656 | 218 | 280 | 240 | |
| 10 | Clustered bar "Top 10 Customers by Revenue" | Y `Fact_Sales[Customer_ID]`; X `[Customer Revenue]`; Tooltip `[Customer Contribution %]` | 946 | 218 | 318 | 240 | Top N: **Top 10** by `Customer Revenue` |
| 11 | Donut "Payment Method Distribution" | Legend `Fact_Sales[Payment_Mode]`; Values `[Total Orders]` | 16 | 468 | 300 | 244 | |
| 12 | Clustered bar "Revenue by Payment Method" | Y `Fact_Sales[Payment_Mode]`; X `[Total Revenue]` | 326 | 468 | 320 | 244 | |
| 13 | Table "Payment Summary" | `Fact_Sales[Payment_Mode]`, `[Total Orders]`, `[Payment Order Share %]`, `[Total Revenue]`, `[Payment Revenue Share %]` | 656 | 468 | 300 | 244 | |
| 14 | Table "Segment Detail" | `Dim_Customer[Segment]`, `[Total Customers]`, `[Total Revenue]`, `[Average Revenue per Customer]` | 966 | 468 | 298 | 244 | |

## 11. Interactions and polish

1. **Cross-filtering:** it is on by default. Check by clicking a Region bar on page 1: the Category chart, Top 5 products and KPI cards must change.
2. **Edit interactions** (select a visual → **Format > Edit interactions**), set the filter icon to *None* ⊘ for: the KPI cards that should not react to other charts (none required), and on page 2 set **Pareto → None** for the *Top 10* and *Bottom 10* bar charts so a Pareto click does not blank them.
3. **Drill-down check:** Monthly Revenue Trend → arrow → *Drill down* shows quarters → months; Revenue by Category → *Drill down* shows products; page 3 *Revenue by Region* drills to city.
4. **Titles:** every visual needs a title (Format → General → Title). Use the names in the tables.
5. **Alt text** (Format → General → Alt text) on each visual: one short sentence.
6. **Reset button (optional):** on page 1 add a bookmark with all slicers cleared (**View > Bookmarks > Add**, name `Clear filters`, untick *Data* only if you want the view kept) and a *Button > Bookmark* linked to it.
7. Make sure no visual overlaps another and nothing sits outside the 1280 × 720 canvas.

## 12. Verify against Python (Checkpoints B and C)

**With every slicer cleared**, the values on the cards must equal these Python results (all taken from `python main.py` output of this project):

| Item | Expected value |
|---|---:|
| Total Revenue | ₹189,024,945.86 (shown as ₹189,024,946 with 0 decimals) |
| Total Orders | 14,970 |
| Total Customers | 2,953 |
| Total Units Sold | 30,256 |
| Average Order Value | ₹12,626.92 |
| Average Selling Price | ₹6,247.52 |
| Latest Year YoY Growth % | 5.1 % |
| Peak Revenue Month / Lowest | 2023-11 / 2023-02 |
| Top Product / Lowest Product | Laptop / Biscuits (Pack) |
| Highest / Lowest Region | East ₹39,657,536.84 / West ₹36,133,852.44 |
| Repeat Customers / One-time | 2,435 / 518 (82.5 %) |
| Segments (customers) | High Value 574 · Loyal 1,186 · Regular 675 · One-time 518 |

Full tables for category, region, payment, month and segment values are in `powerbi/verification/reconciliation_report.md` (compare the "Python value" column with what your visuals show).

**Known, expected differences (not bugs):**
1. **Repeat Customers under a date slicer.** `[Repeat Customers]` counts customers with ≥ 2 orders *inside the selected period*, so with `Year = 2024` it shows 1,596, not 2,435. `[Repeat Customers (Lifetime Flag)]` uses the whole-period order count from Python and shows 2,198 for 2024 (customers active in 2024 who are repeat buyers overall). Python's figure of 2,435 is whole-period only.
2. **ABC class of Jeans.** Its cumulative share is 95.004 %. Python rounds to 2 decimals before applying the 95 % threshold (class B). The shipped `[ABC Class (Dynamic)]` rounds the same way, so it also shows B. Without rounding it would be C.
3. **YoY card** ignores the date slicer on purpose (compares the latest selected year with the previous full year). Use `[YoY Revenue Growth %]` in a table by Year/Month for slicer-aware growth.

**Checkpoint D – slicer test.** Select `Region = East` and `Year = 2024` → revenue and orders must change on every page, and the same selection must persist across pages (sync). Then select `Category = Electronics` and confirm Top 5 Products shows only Electronics products.

If a number differs: do **not** edit the DAX or the data to force a match. Check, in order: (1) relationships (section 6), (2) the row counts in section 1, (3) a typo in the measure, (4) whether a slicer is still active.

## 13. What has and has not been verified (before you started)

| Item | Status |
|---|---|
| Python pipeline run from a clean state, 35 tests (real pytest) | **Executed.** See `docs/Testing_Report.md`. |
| Customer/product dimension keys unique, 0 orphan rows | **Executed** (reconciliation script). |
| DAX and M files: syntax-level static checks against real CSV headers | **Executed** (`validate_powerbi_assets.py`). Not a substitute for running them in Power BI. |
| DAX logic reproduces Python KPIs (pandas emulation, 109 checks) | **Executed**, 106 match, 3 expected-by-design. Not a Power BI run. |
| DAX/M executed in Power BI Desktop | **Not done. Needs you.** |
| `.pbix` created, visuals rendered, slicers tested | **Not done. Needs you.** |
| Power BI screenshots | Done: `screenshots/01_...04_*.png` (captured from the delivered report; naming differs from section 14). |

## 14. Capture screenshots for the documentation

1. In Power BI Desktop use **View > Fit to page**, clear all slicers, and capture each page at full size (Windows: `Win + Shift + S`, or **File > Export > Export to PDF** and convert the pages to PNG).
2. Original naming plan (the delivered files are `01_Executive_Overview.png` ... `04_Customer_Payment.png`): `powerbi/screenshots/page1_executive_overview.png`, `page2_product_performance.png`, `page3_regional_performance.png`, `page4_customer_payment.png`, plus optionally `model_view.png` (Model view showing the three relationships) and `slicer_demo.png` (a page with Region = East, Year = 2024).
3. Rebuild the report with the screenshots included: `pip install python-docx` then `python docs/build_documentation.py`, or paste the images into the marked placeholders in the DOCX.

## 15. Refreshing after Python regenerates the data

1. `python main.py` (rewrites all three CSV files).
2. Power BI: **Home > Refresh**.
3. If the project folder moved: **Home > Transform data > Edit parameters** → update `DataFolderPath` → OK → Apply changes.

## 16. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `DataSource.NotFound` | `DataFolderPath` wrong or missing the final `\`. |
| `Expression.Error: The column 'X' of the table wasn't found` | The CSV columns changed. Re-run `python main.py` and re-paste the M query. |
| Relationship dialog suggests *many-to-many* | A key is not unique. Re-run `python main.py` so all three CSVs come from the same run. |
| `[YoY Revenue Growth %]` blank on a card | Expected when no prior-year data is in scope. Use `[Latest Year YoY Growth %]` on cards. |
| Months sort alphabetically | Set *Sort by column* (step 5.4). |
| Pareto line is not rising | Axis not sorted by `Total Revenue` descending (step 10, page 2 visual 5). |
| A slicer does not change another page | Slicer not synced to that page (step 9.4). |
| Currency shows `$` | Select the measure → Format → Currency → `₹ English (India)`. |
