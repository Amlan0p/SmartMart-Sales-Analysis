"""
chapters_c.py - chapters 19-28 and appendices: Power BI, reconciliation,
testing, results, limitations, conclusion. Power BI screenshots (01_..04_*.png)
are inserted only if the real files exist in powerbi/screenshots/; otherwise a
clearly marked placeholder is shown.
"""

from __future__ import annotations

import config
from chapters_a import chapter_title
from doc_context import DocContext, money, pct, whole
from docx_helpers import (
    add_bullets, add_callout, add_code, add_figure, add_heading, add_paragraph, add_placeholder_box, add_table,
)


# --------------------------------------------------------------------------
# Chapter 19 - Power BI integration, Power Query and data model
# --------------------------------------------------------------------------
def ch19_powerbi_integration(document, ctx: DocContext) -> None:
    chapter_title(document, "19. Power BI Integration and Data Model")
    add_heading(document, "19.1 Integration approach", 2)
    add_paragraph(document, "Power BI was made compulsory by the mentor, so the project adds a dedicated `powerbi/` folder next to the existing "
                  "Python application. The integration follows one rule: **Python prepares the data, Power BI presents it.** Power BI reads the "
                  "cleaned CSV and two small dimension tables; it does not re-clean or re-derive anything the Python pipeline already "
                  "produced. The existing Python modules were not modified beyond one additive pipeline step.")
    add_table(document, ["Python change", "File", "Why"], [
        ["New module exporting two dimension CSVs", "src/powerbi_export.py", "Python's RFM segment and ABC class are not available in the cleaned CSV"],
        ["Three path constants added at the end of config.py", "config.py", "Keep configuration out of business logic"],
        ["Step 9 added to the pipeline; TOTAL_STEPS 8 \u2192 9", "main.py", "Export the dimension tables after the analysis"],
        ["New tests for the export and for output integrity", "tests/test_powerbi_export.py, tests/test_output_integrity.py", "Prove keys are unique and no row is orphaned"],
    ], [6.0, 5.2, 5.4], caption=ctx.next_table("The complete list of changes made to the Python project"), font_size=9)
    add_paragraph(document, "A line-by-line comparison with the original upload showed no other differences in the Python source files. "
                  "The original ZIP was preserved unchanged as a backup before any modification.")
    add_heading(document, "19.2 Why dimension tables are exported", 2)
    add_paragraph(document, "Power BI could recompute product rankings in DAX, but the customer RFM segmentation uses quantile scoring that is "
                  "awkward to reproduce faithfully. Re-implementing it would create two competing definitions of 'High Value customer'. "
                  "Exporting Python's result keeps one definition. The customer dimension has exactly one row per customer "
                  f"({whole(len(ctx.customers_dim))} rows), and the export raises an error if a duplicate `Customer_ID` appears, "
                  "which prevents incorrect many-to-many relationships in the Power BI model.")
    add_code(document, "src/powerbi_export.py - build_customer_dimension", ctx.function_source("src/powerbi_export.py", "build_customer_dimension"), font_size=8)
    add_heading(document, "19.2 Star-schema data model", 2)
    add_figure(document, ctx.diagram("star_schema.png"), ctx.next_figure("Intended star schema (key integrity verified in Python; the delivered .pbix uses the same four tables - see the note below)"), width_cm=15.0)
    add_table(document, ["Table", "Source", "Rows", "Grain / key"], [
        ["Fact_Sales", "cleaned_sales_data.csv", whole(len(ctx.df)), "one order; Order_ID unique"],
        ["Dim_Customer", "customer_segments.csv", whole(len(ctx.customers_dim)), "one customer; Customer_ID unique"],
        ["Dim_Product", "product_classification.csv", whole(len(ctx.products_dim)), "one product; Product unique"],
        ["Dim_Date", "DAX calendar table", "731", "one day; Date unique and contiguous"],
    ], [3.2, 5.6, 2.0, 5.8], align=["l", "l", "r", "l"], caption=ctx.next_table("Model tables"), font_size=9.5)
    add_paragraph(document, "Three one-to-many relationships with single-direction filtering connect each dimension to `Fact_Sales`: "
                  "`Dim_Date[Date]` \u2192 `Order_Date`, `Dim_Customer[Customer_ID]` \u2192 `Customer_ID`, `Dim_Product[Product]` \u2192 `Product`. "
                  "`Region`, `City`, `Payment_Mode` and `Customer_Type` stay on the fact table because a city does not map cleanly to a "
                  "single region (the 60 'Unknown' cities fall in all five regions).")
    add_callout(document, "As built in the delivered .pbix",
                "The model diagram stored in the .pbix lists four tables: dim_customer, dim_product, Fact_Sales and Dim_Date. The dimension tables therefore carry "
                "lower-case names, and the measures live in Fact_Sales instead of a separate `_Measures` table, unlike the names used in this chapter and in the build guide. "
                "Visuals slice Fact_Sales measures by dim_product, dim_customer and Dim_Date columns and show the correct totals, which is consistent with working "
                "relationships; the relationships themselves (cardinality and direction) could not be read because the model is stored in compressed form.",
                fill_hex="E8F1FB", bar_hex="3669AB")
    add_heading(document, "19.3 Order-level versus transaction-level calculations", 2)
    add_paragraph(document, f"In this dataset one row is one order line and `Order_ID` is unique ({whole(ctx.df['Order_ID'].nunique())} distinct values in "
                  f"{whole(len(ctx.df))} rows), so counting rows and counting distinct orders give the same number today. The DAX measures "
                  "nevertheless use `DISTINCTCOUNT` for orders, customers and products and `SUM` for revenue and quantity, so the model "
                  "stays correct if multi-line orders are introduced later and customers can never be double-counted.")
    add_heading(document, "19.5 Power Query (M)", 2)
    add_paragraph(document, "Three queries import the CSV files, set explicit data types and keep only the columns that are not duplicated by "
                  "other tables. A text parameter, `DataFolderPath`, stores the folder path so the whole model can be re-pointed in one place "
                  "and refreshed after Python regenerates the files.")
    m_code = ctx.text_file("powerbi/power_query/sales_data.m")
    m_code = m_code[m_code.index("let"):]
    add_code(document, "powerbi/power_query/sales_data.m (query Fact_Sales)", m_code, font_size=7.5)
    add_paragraph(document, "**Explanation.** `Csv.Document` reads the file, `Table.PromoteHeaders` uses the first row as column names, "
                  "`Table.TransformColumnTypes` applies the types with the `en-US` culture so dates and decimals parse the same on any computer, "
                  "and `Table.RemoveColumns` drops `Year`, `Month`, `Month_Name`, `Quarter`, `Category` and `Order_Value`, which are supplied by "
                  "`Dim_Date`, `Dim_Product` and the Sales column respectively. The column list and the `Columns = 17` setting were checked "
                  "against the real CSV header by `validate_powerbi_assets.py`.")


# --------------------------------------------------------------------------
# Chapter 20 - DAX
# --------------------------------------------------------------------------
def ch20_dax(document, ctx: DocContext) -> None:
    chapter_title(document, "20. DAX Measures and Calculations")
    add_heading(document, "20.1 Calendar table", 2)
    date_code = ctx.text_file("powerbi/dax/date_table.dax")
    date_code = date_code[date_code.index("Dim_Date ="):date_code.index("// Column settings")].rstrip()
    add_code(document, "powerbi/dax/date_table.dax", date_code, font_size=8)
    add_paragraph(document, "The table spans whole calendar years (2023-01-01 to 2024-12-31, 731 days) and is marked as the model's date table, "
                  "which time-intelligence functions such as `SAMEPERIODLASTYEAR` require. Month Name is sorted by Month Number so months "
                  "do not appear alphabetically.")
    add_heading(document, "20.2 Core KPI measures", 2)
    add_code(document, "powerbi/dax/measures.dax - core KPIs",
             "\n\n".join(ctx.dax_measure(n) for n in ["Total Revenue", "Total Orders", "Total Customers", "Total Units Sold",
                                                      "Average Order Value", "Average Selling Price"]), font_size=8.5)
    add_paragraph(document, "**Logic.** `SUM` for additive values; `DISTINCTCOUNT` for orders and customers; `DIVIDE` instead of `/` so a zero "
                  "denominator returns blank rather than an error. They mirror `overall_sales_summary` in Python one-to-one.")
    add_heading(document, "20.3 Growth and contribution measures", 2)
    add_code(document, "powerbi/dax/measures.dax - Latest Year YoY Growth %", ctx.dax_measure("Latest Year YoY Growth %"), font_size=8)
    add_code(document, "powerbi/dax/measures.dax - Category Revenue Contribution %", ctx.dax_measure("Category Revenue Contribution %"), font_size=8.5)
    add_paragraph(document, "`Latest Year YoY Growth %` captures values in variables, removes the date filter and compares the latest year with the "
                  "previous one; it mirrors Python's year-over-year table and is meant for cards. `YoY Revenue Growth %` (using "
                  "`SAMEPERIODLASTYEAR`) is slicer-aware and is meant for charts by month or year. Contribution measures divide by "
                  "`ALLSELECTED`, so percentages respect the user's slicer choices but still add up to 100% across the visual.")
    add_heading(document, "20.3 Customer measures", 2)
    add_code(document, "powerbi/dax/measures.dax - Repeat Customers", ctx.dax_measure("Repeat Customers"), font_size=8)
    add_code(document, "powerbi/dax/measures.dax - Repeat Customers (Lifetime Flag)", ctx.dax_measure("Repeat Customers (Lifetime Flag)"), font_size=8)
    add_paragraph(document, "Two definitions are provided on purpose. `[Repeat Customers]` counts customers with at least two orders **inside the "
                  "current filters**, so it changes with the date slicer. `[Repeat Customers (Lifetime Flag)]` uses the whole-period order count "
                  "exported by Python, which is the definition behind the Python figure. Chapter 22 shows how they differ under a filter.")
    add_heading(document, "20.5 Pareto and ABC measures", 2)
    add_code(document, "powerbi/dax/measures.dax - Cumulative Revenue %", ctx.dax_measure("Cumulative Revenue %"), font_size=8)
    add_code(document, "powerbi/dax/measures.dax - ABC Class (Dynamic)", ctx.dax_measure("ABC Class (Dynamic)"), font_size=8)
    add_paragraph(document, "For each product the cumulative measure sums the revenue of every selected product that earns at least as much, "
                  "divided by the revenue of all selected products. The ABC class applies the same 80% / 95% thresholds as Python, after "
                  "rounding to two decimals of a percentage as Python does.")
    add_heading(document, "20.3 Measure catalogue", 2)
    add_table(document, ["Group", "Measures", "Python counterpart"], [
        ["Core KPIs (10)", "Total Revenue, Total Orders, Total Customers, Total Units Sold, Average Order Value, Average Selling Price, Average Revenue per Customer, Orders per Customer, Products Sold, Last Order Date", "overall_sales_summary"],
        ["Time (8)", "Revenue Previous Month, Revenue Growth %, Revenue Previous Year, YoY Revenue Growth %, Latest Year YoY Growth %, Revenue YTD, Peak / Lowest Revenue Month", "monthly_sales_analysis, year_over_year_analysis"],
        ["Product (9)", "Category Revenue Contribution %, Product Contribution %, Product Revenue Rank, Top / Lowest Product, ABC thresholds, Cumulative Revenue %, ABC Class (Dynamic)", "product_analysis, category_analysis, pareto_analysis"],
        ["Region (8)", "Regional Revenue, Contribution %, Rank, Highest / Lowest Performing Region and their revenues, Revenue vs Regional Average %", "regional_analysis"],
        ["Customer (9)", "Customer Revenue, Customer Contribution %, Repeat Min Orders, Repeat / One-time Customers (both definitions), Repeat Customer Rate % (both)", "customer_analysis"],
        ["Payment (2)", "Payment Revenue Share %, Payment Order Share %", "payment_analysis"],
    ], [3.0, 9.6, 4.0], caption=ctx.next_table("The 46 DAX measures in powerbi/dax/measures.dax (design catalogue; statically validated)"), font_size=8.5)
    add_callout(document, "Which measures are used in the delivered .pbix",
                "The report's visuals use 11 measures, all stored in Fact_Sales: Total Revenue, Total Orders, Total Customers, Total Units Sold, Average Order Value, "
                "Average Selling Price, Average Revenue per Customer, Products Sold, Revenue Previous Year, One-time Customers and Repeat Customers. Their values agree with "
                "Python (Section 22.5). The other 35 catalogue measures (for example Cumulative Revenue %, ABC Class (Dynamic) and Latest Year YoY Growth %) are not used by any "
                "visual, and because the model cannot be read outside Power BI it is not known whether they were added to the .pbix.", fill_hex="E8F1FB", bar_hex="3669AB")


# --------------------------------------------------------------------------
# Chapter 21 - Dashboard: design principles, as-built pages, deviations
# --------------------------------------------------------------------------
SCREENSHOT_NOTE = ("Screenshot supplied by the team (Power BI Desktop at 52% zoom), cropped to the report canvas; no other editing.")


def _page_block(document, ctx, title, purpose, built_rows, observations, screenshot_name):
    heading = add_heading(document, title, 2)
    add_paragraph(document, purpose)
    path = ctx.screenshot(screenshot_name)
    if path:
        add_figure(document, path, ctx.next_figure(f"{title.split(' ', 1)[1]} - Power BI Desktop screenshot (as built)"), width_cm=16.0, max_height_cm=9.4)
    else:
        add_placeholder_box(document, f"Insert {screenshot_name}",
                            f"Save the Power BI page capture as powerbi/screenshots/{screenshot_name}, then run python docs/build_documentation.py.",
                            height_cm=4.2)
    add_paragraph(document, "**Visuals (from the .pbix):** " + "; ".join(f"{kind} - {fields}" for kind, fields in built_rows) + ".", size=9.5)
    add_bullets(document, observations)


def ch21_dashboard(document, ctx: DocContext) -> None:
    chapter_title(document, "21. Power BI Dashboard")
    add_heading(document, "21.1 Design principles (specification)", 2)
    add_paragraph(document, "The project specification (`powerbi/dashboard_design/dashboard_specification.md`) set the following design rules. "
                  "Section 21.2 shows what was actually built and Section 21.3 compares the two.")
    add_bullets(document, [
        "Canvas:: 16:9, five synced slicers in a band at the top: date range, Region, Category, Product, Payment Mode.",
        "Colour:: Cronus blue #3669AB for the primary measure, green #69A147 for highlights (theme file `SmartMart_Theme.json`).",
        "Formats:: ₹ currency with no decimals on cards and axes, percentages with one decimal.",
        "Interaction:: cross-filtering, drill-down on date, category and geography hierarchies, Top N filters for rankings.",
        "Honesty:: a footer note on every page stating that the data is synthetic.",
    ])
    add_callout(document, "How the as-built dashboard was checked",
                "The .pbix is a ZIP archive whose report part is plain JSON, so every page, visual, field binding, sort order, filter and slicer "
                "setting was read directly with `powerbi/verification/inspect_pbix.py`. The semantic model inside the file is compressed and could "
                "not be read by the audit. Figures visible in the screenshots were compared with Python (Section 22.5). The screenshots are the team's own captures from "
                "Power BI Desktop, where the team opened and tested the report (see Chapter 25); they are low-resolution captures of the 1920 x 1080 canvas at 52% zoom.", fill_hex="E8F1FB", bar_hex="3669AB")
    add_heading(document, "21.2 The four dashboard pages as built", 2)
    add_paragraph(document, "Every page uses a 1920 x 1080 (16:9) canvas. The same five slicers (Date, Region, Category, Product, Payment_Mode) exist on all four "
                  "pages and are synchronised; they are visible on page 1 and hidden on pages 2-4, so a selection made on page 1 filters the other pages. "
                  "The Cronus colour theme is applied. Pages contain 13, 11, 12 and 12 visuals respectively, including the five slicers on each page.")
    _page_block(document, ctx, "21.2.1 Page 1 - Executive Overview",
                "Gives the whole business on one screen: headline KPIs, revenue by payment mode, region, category and year, the monthly trend and the product ranking.",
                [["Multi-value card", "Average Order Value, Total Revenue, Total Orders, Total Units Sold, Total Customers"],
                 ["Slicers (visible, synced)", "Date (between), Region, Category, Product, Payment_Mode"],
                 ["Donut", "Total Revenue by Payment_Mode"],
                 ["Clustered bar", "Total Revenue by Region"],
                 ["Clustered column", "Total Revenue by dim_product[Category]"],
                 ["Clustered column", "Total Revenue by Year; tooltip: Revenue Previous Year"],
                 ["Line chart", "Total Revenue by Year-Month"],
                 ["Line chart", "Total Orders by Year-Month"],
                 ["Clustered bar", "Total Revenue by Product (all 35 products, scrollable)"]],
                ["Both line charts are sorted by their value (descending), so the Year-Month axis is not in date order; the screenshot shows the labels out of sequence.",
                 "The product chart is not limited to the Top 5 products: no Top N filter exists on any visual.",
                 "Average Selling Price, YoY growth and Peak month are not shown on this page; no page title or page navigator was added.",
                 "Visual titles are Power BI's automatic titles (for example 'Total Revenue by Region'); no custom titles or alt text were set."],
                "01_Executive_Overview.png")
    _page_block(document, ctx, "21.2.2 Page 2 - Product Performance",
                "Shows which products and categories drive revenue.",
                [["Multi-value card", "Total Revenue, Total Units Sold, Products Sold, Average Selling Price"],
                 ["Clustered column", "Total Revenue by dim_product[Category]"],
                 ["Clustered bar (two copies)", "Total Revenue by dim_product[Product]; both sorted descending, same fields"],
                 ["Line and clustered column", "Product on the axis; columns Total Revenue, line Total Units Sold (secondary axis)"],
                 ["Table", "Product, Category, Total Revenue, Total Units Sold, Average Selling Price (total row shown)"]],
                ["The two product bar charts are identical (both show all products, highest first); no Top 10 or Bottom 10 filter was applied.",
                 "The combo chart plots Total Units Sold as the line. It is therefore not the planned Pareto chart (which needs Cumulative Revenue %).",
                 "Planned visuals not present: revenue-by-category donut, quantity-sold ranking, units-vs-revenue scatter, ABC matrix, contribution %, rank and ABC class columns.",
                 "The slicers are present but hidden on this page; use page 1 to filter."],
                "02_Product_Performance.png")
    _page_block(document, ctx, "21.2.3 Page 3 - Regional Performance",
                "Compares the five regions and the cities.",
                [["Multi-value card", "Total Revenue, Total Orders, Total Customers, Average Revenue per Customer"],
                 ["Clustered bar", "Total Revenue by Region"],
                 ["Clustered bar", "Total Revenue by City (21 city groups, including 'Unknown')"],
                 ["Donut", "Total Revenue by Region"],
                 ["Clustered column", "Total Orders by Region"],
                 ["Clustered column", "Total Customers by Region"],
                 ["Table", "Region, Total Revenue, Total Customers, Total Orders, Average Revenue per Customer (total row shown)"]],
                ["Regional customers add up to more than the total (1,604 + 1,647 + 1,571 + 1,619 + 1,593 = 8,034 against 2,953) because customers buy in more than one region; "
                 "the total row correctly shows 2,953 distinct customers.",
                 "Planned items not present: highest / lowest region cards, average order value by region, regional trend lines, Region > City drill-down and conditional formatting.",
                 "Revenue by Region appears twice (bar and donut)."],
                "03_Regional_Performance.png")
    _page_block(document, ctx, "21.2.4 Page 4 - Customer & Payment",
                "Describes customer loyalty and payment preferences.",
                [["Multi-value card", "Total Customers, One-time Customers, Repeat Customers, Average Order Value"],
                 ["Clustered bar", "Total Revenue by dim_customer[Customer_ID] (all customers, scrollable)"],
                 ["Donut", "Total Revenue by City (21 slices)"],
                 ["Donut", "Total Revenue by Payment_Mode"],
                 ["Clustered bar", "Total Customers by City"],
                 ["Clustered column", "Total Orders by Payment_Mode"],
                 ["Table", "Customer_ID, City, Customer_Type, Total Orders, Total Revenue, Average Order Value, sorted by City descending"]],
                ["No Top 10 filter is applied to the customer ranking.",
                 "The Python RFM segments (`dim_customer[Segment]`) are not used by any visual, so there is no customer-segmentation chart; revenue by customer type is also absent.",
                 "The table lists one row per Customer_ID, City and Customer_Type, so a customer who bought in several cities appears several times and a 'Repeat Customer' can show one order on a row.",
                 "Repeat Customer Rate, Orders per Customer, the payment summary table and the Segment detail table from the specification were not built."],
                "04_Customer_Payment.png")
    add_heading(document, "21.3 As built versus specification", 2)
    add_table(document, ["Specification item", "Status in the .pbix"], [
        ["Four pages with the specified names", "Done - Executive Overview, Product Performance, Regional Performance, Customer & Payment"],
        ["Five synced slicers on all pages", "Done - all five synced on all four pages (visible on page 1, hidden on pages 2-4)"],
        ["Cronus colour theme", "Applied (custom theme registered in the file)"],
        ["Canvas 1280 x 720", "Different - built at 1920 x 1080 (also 16:9)"],
        ["Six KPI cards on page 1", "Partly - one multi-value card with five KPIs (no Average Selling Price on page 1)"],
        ["Top N / Bottom N filters (five visuals)", "Not done - no Top N filter exists"],
        ["Monthly trend with Year > Quarter > Month drill-down", "Different - flat Year-Month axis, sorted by value so not chronological"],
        ["Pareto chart with cumulative % line", "Not done - the combo chart shows units sold"],
        ["Highest / lowest region cards; YoY and peak-month cards", "Not done"],
        ["Customer segmentation visuals (RFM segments)", "Not done"],
        ["Drill-down hierarchies; conditional formatting; page navigator", "Not done"],
        ["Custom titles and alt text on every visual", "Not done - automatic titles, no alt text"],
        ["Rupee currency format on cards", "Not applied - cards show 189.02M, 14.97K etc. without the rupee sign"],
        ["Synthetic-data footer note on every page", "Not done"],
    ], [8.2, 8.4], caption=ctx.next_table("Specification versus the delivered .pbix (from inspect_pbix.py and the screenshots)"), font_size=9)
    add_paragraph(document, "These deviations do not make any displayed number wrong: Section 22.5 shows that every figure legible in the screenshots equals the "
                  "Python result. They do mean the delivered dashboard covers a subset of the planned analysis.")


# --------------------------------------------------------------------------
# Chapter 22 - Reconciliation
# --------------------------------------------------------------------------
def ch22_reconciliation(document, ctx: DocContext) -> None:
    rec = ctx.reconciliation
    chapter_title(document, "22. Python and Power BI Reconciliation")
    add_heading(document, "22.1 Method", 2)
    add_paragraph(document, "Python KPIs come from `src/analysis.py`. The comparison values were produced by "
                  "`powerbi/verification/reconcile_python_vs_dax.py`, which rebuilds the Power BI model's tables and relationships in pandas "
                  "and re-implements each DAX measure's logic independently. This Python-versus-DAX-equivalent reconciliation also checks model integrity (unique keys, no orphan rows, "
                  "contiguous calendar) and compares a set of slicer scenarios, emulated in pandas, against Python run on filtered data.")
    add_callout(document, "What this does and does not prove",
                "It proves that the *definitions* in the DAX measures reproduce the Python results on the model as designed, and that the "
                "dimension tables are sound. It is **not** a Power BI run (the team's testing in Power BI Desktop is described in Chapter 25) and cannot catch a DAX syntax error or an engine-specific behaviour. "
                "Section 22.5 adds the comparison with the values displayed in the delivered dashboard.", fill_hex="FFF8E5", bar_hex="E0A030")
    add_heading(document, "22.2 Summary of results", 2)
    summary_rows = []
    for group, block in rec.groupby("Group", sort=False):
        summary_rows.append([group, whole(len(block)), whole((block["Match"] == "YES").sum()), whole((block["Match"] == "NO").sum())])
    summary_rows.append(["Total", whole(len(rec)), whole((rec["Match"] == "YES").sum()), whole((rec["Match"] == "NO").sum())])
    add_table(document, ["Group", "Checks", "Matched", "Not matched"], summary_rows, [8.0, 2.8, 2.8, 3.0], align=["l", "r", "r", "r"],
              caption=ctx.next_table("Reconciliation summary (reconciliation_results.csv)"), font_size=9, bold_last_row=True)
    add_heading(document, "22.3 Headline KPIs", 2)
    head = rec[rec["Group"] == "Headline KPIs"]
    rows = [[r.Measure, f"{float(r._3):,.2f}", f"{float(r._4):,.2f}", r.Match] for r in head.itertuples()]
    add_table(document, ["Measure", "Python value", "DAX-equivalent", "Match"], rows, [6.0, 4.0, 4.0, 2.0], align=["l", "r", "r", "c"],
              caption=ctx.next_table("Headline KPI reconciliation"), font_size=9.5)
    add_heading(document, "22.4 Slicer scenarios", 2)
    scenarios = rec[rec["Group"].str.startswith("Slicer:")]
    rows = []
    for group, block in scenarios.groupby("Group", sort=False):
        rev = block[block["Measure"] == "Total Revenue"].iloc[0]
        orders = block[block["Measure"] == "Total Orders"].iloc[0]
        rows.append([group.replace("Slicer: ", ""), f"{float(rev['Python value']):,.2f}", f"{float(rev['DAX-equivalent value']):,.2f}",
                     whole(float(orders["Python value"])), "all 6 match" if (block["Match"] == "YES").all() else "see CSV"])
    add_table(document, ["Filter", "Revenue (Python)", "Revenue (DAX-equiv.)", "Orders", "Result"], rows, [5.4, 3.6, 3.6, 1.8, 2.2],
              align=["l", "r", "r", "r", "c"], caption=ctx.next_table("Filtered-context checks (each row checks six KPIs)"), font_size=9)
    add_heading(document, "22.4 Differences and how they are explained", 2)
    diff = rec[rec["Group"] == "Expected difference"]
    rows = [[r.Measure, f"{float(r._3):,.0f}", f"{float(r._4):,.0f}", r.Note] for r in diff.itertuples()]
    add_table(document, ["Item", "Python", "DAX-equiv.", "Explanation"], rows, [5.4, 1.8, 1.8, 7.6], align=["l", "r", "r", "l"],
              caption=ctx.next_table("The three documented differences (none is an error)"), font_size=8.5)
    add_bullets(document, [
        "Repeat customers under a filter:: the context-sensitive measure and the Python figure answer different questions (customers with 2+ orders "
        "within 2024 versus customers with 2+ orders overall). Both measures exist so a dashboard author can choose deliberately.",
        "ABC boundary:: found by this reconciliation. The first draft of the DAX measure did not round, which put one product in a different class "
        "than Python. The Python code was left unchanged (it is the authoritative, tested pipeline) and the DAX measure was aligned and commented.",
    ])
    add_heading(document, "22.5 Reconciliation with the delivered dashboard", 2)
    add_paragraph(document, "The values below were read from the team's screenshots (zoomed to confirm digits) and compared with Python recomputed from "
                  "`cleaned_sales_data.csv` when this report was built. The screenshot-to-Python reconciliation covers the unfiltered dashboard view and "
                  "verifies that the figures visible in the delivered report agree with the Python results. Slicer interactions were separately checked by the "
                  "project team in Power BI Desktop, as documented in Section 25.3 (manual Power BI Desktop testing by the project team). The independent "
                  "reconciliation script does not reproduce those interactive Power BI tests, and this comparison does not inspect the DAX inside the .pbix.")
    df = ctx.df
    rev = df["Sales"].sum()
    kpis = [
        ("Total Revenue (pages 1, 2, 3)", "189.02M", f"{rev / 1e6:.2f}M"),
        ("Total Orders (pages 1, 3)", "14.97K", f"{df['Order_ID'].nunique() / 1e3:.2f}K"),
        ("Total Customers (pages 1, 3, 4)", "2.953K", f"{df['Customer_ID'].nunique() / 1e3:.3f}K"),
        ("Total Units Sold (pages 1, 2)", "30.256K", f"{df['Quantity'].sum() / 1e3:.3f}K"),
        ("Average Order Value (pages 1, 4)", "12.63K", f"{rev / df['Order_ID'].nunique() / 1e3:.2f}K"),
        ("Average Selling Price (page 2)", "6.25K", f"{rev / df['Quantity'].sum() / 1e3:.2f}K"),
        ("Average Revenue per Customer (page 3)", "64.01K", f"{rev / df['Customer_ID'].nunique() / 1e3:.2f}K"),
        ("Products Sold (page 2)", "35", f"{df['Product'].nunique()}"),
        ("One-time Customers (page 4)", "518", f"{int((df['Customer_ID'].value_counts() == 1).sum())}"),
        ("Repeat Customers (page 4)", "2.435K", f"{int((df['Customer_ID'].value_counts() >= 2).sum()) / 1e3:.3f}K"),
    ]
    rows = [[n, d, p, "YES" if d == p else "NO"] for n, d, p in kpis]
    add_table(document, ["Card value", "Shown in dashboard", "Python (same rounding)", "Match"], rows, [6.8, 3.4, 4.2, 2.2],
              align=["l", "r", "r", "c"], caption=ctx.next_table("Dashboard card values versus Python"), font_size=9)

    def indian(value, decimals=2):
        whole_part, _, frac = f"{value:.{decimals}f}".partition(".")
        head, tail = whole_part[:-3], whole_part[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        return ",".join(groups + [tail]) + ("." + frac if frac else "")

    pay = df.groupby("Payment_Mode")["Sales"].sum().sort_values(ascending=False)
    pay_shown = {"UPI": "71.57M (37.86%)", "Cash on Delivery": "34.27M (18.13%)", "Credit Card": "32.75M (17.33%)",
                 "Debit Card": "31.11M (16.46%)", "Net Banking": "18.77M (9.93%)", "Unknown": "0.54M (0.29%)"}
    rows = []
    for mode, shown in pay_shown.items():
        py = f"{pay[mode] / 1e6:.2f}M ({pay[mode] / rev * 100:.2f}%)"
        rows.append([f"Page 1 donut - {mode}", shown, py, "YES" if shown == py else "NO"])
    reg = df.groupby("Region").agg(rev=("Sales", "sum"), cust=("Customer_ID", "nunique"), orders=("Order_ID", "nunique"))
    reg_shown = {"Central": ("3,67,83,935.89", "1604", "2991", "22,932.63"), "East": ("3,96,57,536.84", "1647", "3038", "24,078.65"),
                 "North": ("3,69,47,750.44", "1571", "2909", "23,518.62"), "South": ("3,95,01,870.25", "1619", "3023", "24,398.93"),
                 "West": ("3,61,33,852.44", "1593", "3009", "22,682.90")}
    for region, (r_s, c_s, o_s, a_s) in reg_shown.items():
        row = reg.loc[region]
        py = (indian(row.rev), str(int(row.cust)), str(int(row.orders)), f"{row.rev / row.cust:,.2f}")
        ok = (r_s, c_s, o_s, a_s) == py
        rows.append([f"Page 3 table - {region}", " | ".join((r_s, c_s, o_s, a_s)), " | ".join(py), "YES" if ok else "NO"])
    tot_py = (indian(rev), str(df["Customer_ID"].nunique()), str(df["Order_ID"].nunique()), f"{rev / df['Customer_ID'].nunique():,.2f}")
    tot_sh = ("18,90,24,945.86", "2953", "14970", "64,011.16")
    rows.append(["Page 3 table - Total", " | ".join(tot_sh), " | ".join(tot_py), "YES" if tot_sh == tot_py else "NO"])
    add_table(document, ["Item", "Shown in dashboard", "Python (same format)", "Match"], rows, [4.2, 5.4, 5.4, 1.6],
              align=["l", "r", "r", "c"], caption=ctx.next_table("Payment donut and regional table versus Python (region table columns: revenue | customers | orders | revenue per customer)"), font_size=8.5)

    prod = df.groupby("Product").agg(rev=("Sales", "sum"), q=("Quantity", "sum"))
    prod_shown = [("Air Cooler", "91,71,893.92", "1039", "8,827.62"), ("Backpack", "21,38,590.55", "1056", "2,025.18"),
                  ("Belt", "6,88,620.24", "948", "726.39"), ("Biscuits (Pack)", "43,850.09", "738", "59.42"),
                  ("Bluetooth Speaker", "20,40,030.39", "719", "2,837.32"), ("Bookshelf", "42,72,190.39", "932", "4,583.90"),
                  ("Coffee (200g)", "2,04,721.58", "751", "272.60"), ("Cooking Oil (1L)", "1,59,395.12", "842", "189.31"),
                  ("Dining Table", "1,85,88,891.86", "918", "20,249.34"), ("Electric Kettle", "14,34,385.03", "970", "1,478.75"),
                  ("Jacket", "28,78,394.38", "812", "3,544.82"), ("Jeans", "15,36,896.30", "850", "1,808.11"),
                  ("Keyboard", "10,49,810.52", "667", "1,573.93"), ("Kurta", "11,79,630.14", "847", "1,392.72"),
                  ("Laptop", "4,43,45,930.75", "741", "59,846.06"), ("Microwave Oven", "1,06,78,166.75", "1058", "10,092.79"),
                  ("Mixer Grinder", "37,43,602.34", "1033", "3,624.01"), ("Mobile Cover", "4,75,306.48", "1000", "475.31")]
    rows = []
    for name, r_s, q_s, a_s in prod_shown:
        p = prod.loc[name]
        py = (indian(p.rev), str(int(p.q)), f"{p.rev / p.q:,.2f}")
        rows.append([name, " | ".join((r_s, q_s, a_s)), " | ".join(py), "YES" if (r_s, q_s, a_s) == py else "NO"])
    add_table(document, ["Product (page 2 table)", "Shown: revenue | units | avg price", "Python", "Match"], rows, [3.6, 5.6, 5.6, 1.8],
              align=["l", "r", "r", "c"], caption=ctx.next_table("The 18 product rows visible in the page 2 table versus Python"), font_size=8)
    top15 = list(df.groupby("Customer_ID")["Sales"].sum().sort_values(ascending=False).head(15).index)
    bar_order = ["CUST01384", "CUST02593", "CUST00705", "CUST02949", "CUST00513", "CUST02501", "CUST02418", "CUST02772", "CUST01299",
                 "CUST02506", "CUST00284", "CUST00361", "CUST00632", "CUST00575", "CUST03184"]
    n_ok = sum(x == y for x, y in zip(top15, bar_order))
    n_match = sum(1 for r in rows if r[3] == "YES")
    add_paragraph(document, f"On page 4 the customer revenue bar lists the first 15 customers in the order {', '.join(bar_order[:3])}, ... {bar_order[-1]}; "
                  f"Python's top-15 customers by revenue give the same order for {n_ok} of 15 positions. All {len(prod_shown)} product rows "
                  f"({n_match} match) and every card, donut and regional figure above equal the Python results.")
    add_callout(document, "Scope of this evidence",
                "These checks show that the numbers displayed in the delivered report agree with Python for the unfiltered view. They do not prove that every "
                "one of the 46 catalogue measures exists or is correct in the .pbix (only 11 are used by visuals) and they do not test filtered views.",
                fill_hex="FFF8E5", bar_hex="E0A030")


# --------------------------------------------------------------------------
# Chapter 24 - Business insights
# --------------------------------------------------------------------------
def ch23_insights(document, ctx: DocContext) -> None:
    text = ctx.text_file("outputs/reports/business_insights.txt").splitlines()
    findings = [l.split(". ", 1)[1] for l in text if l[:2].strip(". ").isdigit() and ". " in l][:15]
    recs_start = next(i for i, l in enumerate(text) if "BUSINESS RECOMMENDATIONS" in l)
    recs = [l.split(". ", 1)[1] for l in text[recs_start:] if l[:1].isdigit() and ". " in l]
    chapter_title(document, "24. Business Insights and Recommendations")
    add_paragraph(document, "This chapter separates three things: **calculated findings** (generated by `src/insights.py` from the data), "
                  "**interpretation** (our reading, with caveats) and **recommendations**. Findings are reproduced from "
                  "`outputs/reports/business_insights.txt`.")
    add_heading(document, "24.1 Calculated findings", 2)
    add_table(document, ["#", "Finding (generated from the data)"], [[str(i + 1), f] for i, f in enumerate(findings)], [1.0, 15.6], font_size=9,
              caption=ctx.next_table("The fifteen generated findings"))
    add_heading(document, "24.2 Interpretation with caveats", 2)
    add_bullets(document, [
        "Concentration:: revenue depends on a handful of high-ticket Electronics and Furniture products; any supply problem there has an outsized effect.",
        "Seasonality:: the November peak and February trough are strong, but they were designed into the synthetic generator and must not be quoted as real market behaviour.",
        "Growth:: 2024 revenue growth came almost entirely from higher revenue per order; orders and units barely moved.",
        "Loyalty:: the 82.5% repeat rate is an artefact of the small simulated customer pool; real retail data would typically show far more one-time buyers.",
        "Regions and payments:: differences are small and mirror generator settings, so they are not evidence of real regional or payment preferences.",
    ])
    add_heading(document, "24.3 Recommendations generated by the project", 2)
    add_table(document, ["#", "Recommendation"], [[str(i + 1), r] for i, r in enumerate(recs)], [1.0, 15.6], font_size=9,
              caption=ctx.next_table("Generated recommendations (business_insights.txt)"))
    add_paragraph(document, "Recommendation 4 should be read together with the caveat above: before acting on retention figures, the same analysis should "
                  "be repeated on real customer data.")


# --------------------------------------------------------------------------
# Chapter 25 - Testing and validation
# --------------------------------------------------------------------------
def ch24_testing(document, ctx: DocContext) -> None:
    lines = ctx.test_lines
    passes = [l for l in lines if l.startswith("PASS")]
    fails = [l for l in lines if l.startswith("FAIL")]
    chapter_title(document, "25. Testing and Validation")
    add_heading(document, "25.1 Test strategy", 2)
    add_paragraph(document, "Unit tests use small hand-built DataFrames with expected values worked out by hand, so a failure points to a specific "
                  "function. Output-integrity tests inspect the real generated files. Power BI assets are checked statically and by reconciliation.")
    add_heading(document, "25.2 Test results", 2)
    modules = {}
    for l in passes + fails:
        parts = l.split()
        modules.setdefault(parts[1], []).append((parts[0], parts[2]))
    descriptions = {
        "test_data_loader": "Loader validation and exceptions",
        "test_preprocessing": "Cleaning, types, derived columns",
        "test_analysis": "KPI, category, product, monthly, regional calculations",
        "test_powerbi_export": "Dimension tables: unique keys, no orphans, files written",
        "test_output_integrity": "Real outputs: dataset, charts, Excel, insights, no notebooks, Power BI files",
    }
    rows = [[m, descriptions.get(m, ""), whole(len(t)), whole(sum(1 for s, _ in t if s == "PASS"))] for m, t in modules.items()]
    rows.append(["Total", "", whole(len(passes) + len(fails)), whole(len(passes))])
    add_table(document, ["Test module", "Covers", "Tests", "Passed"], rows, [4.4, 8.2, 1.9, 2.1], align=["l", "l", "r", "r"],
              caption=ctx.next_table("Automated tests of the Python pipeline and Power BI assets"), font_size=9.5, bold_last_row=True)
    add_paragraph(document, "Table above covers the original pipeline. The Streamlit platform (Chapter 23) adds tests for schema detection, the dataset manager, "
                  "entry and upload, cleaning, dynamic analytics and reports; run together with the pipeline tests, the whole project suite gave "
                  "**94 passed, 2 skipped** (real pytest, delivered files). The two skipped tests launch the real Streamlit app and need Streamlit installed.")
    add_callout(document, "How the tests were run",
                "The first preparation environment had no network access, so the unchanged tests were first executed with a small stand-in runner. "
                "They were then re-run with real pytest 9.1.1 (`pytest -q`) after a clean `python main.py`, and the recorded result below is from that real run. "
                f"Result: {len(passes)} passed, {len(fails)} failed. These tests cover the Python pipeline and the exported files only; "
                "the Power BI report was separately opened and tested by the project team in Power BI Desktop (Section 25.3), which is not part of these automated tests.", fill_hex="FFF8E5", bar_hex="E0A030")
    add_heading(document, "25.3 Example tests", 2)
    add_code(document, "tests/test_analysis.py - test_revenue_calculation and test_order_count",
             ctx.function_source("tests/test_analysis.py", "test_revenue_calculation") + "\n\n" + ctx.function_source("tests/test_analysis.py", "test_order_count"), font_size=8.5)
    add_code(document, "tests/test_powerbi_export.py - relationship safety",
             ctx.function_source("tests/test_powerbi_export.py", "test_customer_dimension_rejects_duplicate_keys") + "\n\n" +
             ctx.function_source("tests/test_powerbi_export.py", "test_every_sales_key_exists_in_dimensions"), font_size=8)
    add_heading(document, "25.3 Other verification performed", 2)
    add_paragraph(document, "Four different kinds of checking are listed below and are kept separate: automated Python tests, static validation, Python-versus-DAX-equivalent "
                  "reconciliation, and manual Power BI Desktop testing by the project team. The first three do not run the .pbix; only the manual testing does.", keep_with_next=True)
    add_table(document, ["Verification", "Result"], [
        ["Automated Python tests (`pytest -q`; test the Python pipeline and exported files, not the .pbix)", "35 pipeline and Power BI-asset tests passed, 0 failed; the full suite including the Streamlit platform modules gave 94 passed, 2 skipped (Section 25.2)"],
        ["Clean-state regeneration (all data and outputs deleted, `python main.py`)", "Completed; raw and cleaned CSV files byte-identical to the original upload (same SHA-256)"],
        ["Original Python source files compared with the upload", "Only config.py, main.py and the new files differ (additive changes)"],
        ["Static validation of the DAX and Power Query source files (validate_powerbi_assets.py)", "366 checks passed, 0 failed; checker confirmed to detect injected errors"],
        ["Python-versus-DAX-equivalent reconciliation (reconcile_python_vs_dax.py; pandas emulation, not a Power BI run)", "109 checks: 106 matched, 3 expected-by-design differences"],
        ["No notebook files in the project", "Verified by test_no_notebook_files_in_project"],
        ["Independent audit: .pbix report definition read directly (inspect_pbix.py)", "Four pages, 48 visuals, five synced slicers confirmed from the file; Top N filters, custom titles and alt text absent; trend axis sorted by value"],
        ["Screenshot-to-Python reconciliation (unfiltered view)", "Every figure legible in the four screenshots matches Python (Section 22.5)"],
        ["Manual Power BI Desktop testing by the project team", "The project team opened the delivered .pbix in Power BI Desktop. All four dashboard pages loaded and displayed their visuals correctly, and the team checked dashboard functionality and slicer interactions. These were manual team checks, not independently reproduced by the external/static audit; no further test details were recorded"],
        ["Independent audit: internal semantic model (measure formulas, relationships, Power Query steps)", "Limited - the compressed model could not be read outside Power BI; the audit instead used static validation of the DAX/M source files and compared displayed values with Python"],
    ], [8.8, 7.8], caption=ctx.next_table("Additional verification"), font_size=9)


# --------------------------------------------------------------------------
# Chapters 25-28
# --------------------------------------------------------------------------
def ch25_results(document, ctx: DocContext) -> None:
    r = ctx.results
    s = r["summary"]
    chapter_title(document, "26. Results and Discussion")
    add_heading(document, "26.1 Summary of calculated results", 2)
    add_table(document, ["Area", "Result (from the project outputs)"], [
        ["Scale", f"{money(s['Total Revenue'])} revenue; {whole(s['Total Orders'])} orders; {whole(s['Total Customers'])} customers; {whole(s['Total Quantity Sold'])} units"],
        ["Order economics", f"Average order value {money(s['Average Order Value'])}; average selling price {money(s['Average Selling Price'])}"],
        ["Products", f"Best: {r['products']['top_by_revenue'].iloc[0].Product}; lowest: {r['products']['bottom_performers'].iloc[0].Product}"],
        ["Categories", f"{r['categories'].iloc[0].Category} {pct(r['categories'].iloc[0].Revenue_Percentage)}, {r['categories'].iloc[1].Category} {pct(r['categories'].iloc[1].Revenue_Percentage)}, ... {r['categories'].iloc[-1].Category} {pct(r['categories'].iloc[-1].Revenue_Percentage, 2)}"],
        ["Trend", f"Peak {r['monthly']['peak_month']}; lowest {r['monthly']['lowest_month']}; 2024 vs 2023: {r['yoy']['yearly_table'].iloc[-1].Revenue_Growth_Percent:+.1f}%"],
        ["Regions", f"{r['regions'].iloc[0].Region} highest ({money(r['regions'].iloc[0].Revenue, 0)}); {r['regions'].iloc[-1].Region} lowest ({money(r['regions'].iloc[-1].Revenue, 0)})"],
        ["Customers", f"{whole(r['customers']['repeat_customers'])} repeat ({pct(r['customers']['repeat_customer_rate'])}), {whole(r['customers']['one_time_customers'])} one-time"],
        ["Segments", ", ".join(f"{x.Segment} {whole(x.Customers)}" for x in r["segmentation"]["segment_summary"].itertuples())],
        ["Payments", f"{r['payments'].iloc[0].Payment_Mode} leads with {pct(r['payments'].iloc[0].Order_Share_Percent)} of orders"],
        ["Concentration", f"{r['pareto']['products_for_80_percent_revenue']} of {r['pareto']['total_products']} products give ~80% of revenue; ABC = " +
         ", ".join(f"{x.ABC_Class}:{int(x.Products)}" for x in r["pareto"]["abc_summary"].itertuples())],
        ["Data quality", f"{whole(len(ctx.raw) - len(ctx.df))} of {whole(len(ctx.raw))} raw rows removed; zero remaining issues"],
    ], [3.3, 13.3], caption=ctx.next_table("Results at a glance"), font_size=9.5)
    add_heading(document, "26.2 Discussion", 2)
    add_paragraph(document, "The results show a business whose revenue is driven by a few high-priced products, with a clear seasonal pattern and modest growth that "
                  "comes from larger orders rather than more of them. Customer, regional and payment statistics are fairly even, which is "
                  "typical of synthetic data generated from fixed weights. The value of the project lies less in these particular numbers than in "
                  "the reproducible method: every figure above is recomputed from the data on each run, verified by tests, and defined identically in the Python "
                  "pipeline and the Power BI measures.")
    add_heading(document, "26.3 What each result is based on", 2)
    add_paragraph(document, "The report uses four different kinds of evidence. They are kept apart on purpose, and not every Python analysis has a Power BI visual.", keep_with_next=True)
    add_table(document, ["Evidence type", "What it covers", "What it does not show"], [
        ["Python-generated results", "All statistics and findings in Chapters 9-18 and 23, computed from the cleaned data by src/analysis.py and tested with pytest (35 pipeline tests passed)", "Anything about Power BI"],
        ["Power BI dashboard visuals", "The four pages in Chapter 21: KPI cards, category/region/product/city/payment charts and tables, customer rankings, one-time vs repeat counts", "Pareto, ABC, RFM segments, Top N rankings, regional trends, highest/lowest region cards (Python or catalogue only)"],
        ["Static validation", "validate_powerbi_assets.py: 366 checks of the DAX and Power Query source files; Python-versus-DAX-equivalent reconciliation in pandas (106 of 109 matched, 3 expected by design)", "Execution in Power BI; the formulas inside the .pbix. Not a substitute for, and not merged with, the team's manual testing"],
        ["Manual Power BI Desktop testing by the project team", "Manual opening and testing of the delivered report by the project team; all four pages loading and displaying their visuals; dashboard functionality and slicer interactions checked by the team; visible screenshot figures matching Python for the unfiltered view (screenshot-to-Python reconciliation, Section 22.5)", "Independent reproduction of the team's Power BI Desktop session by the audit; independent inspection of the compressed semantic model; verification of every DAX measure, relationship or Power Query step inside the .pbix; specific interaction tests beyond those actually recorded"],
    ], [3.4, 7.0, 6.2], caption=ctx.next_table("Evidence behind each kind of result"), font_size=9)
    add_heading(document, "26.2 Objectives review", 2)
    add_table(document, ["Objective", "Status"], [
        ["Synthetic dataset with controlled quality issues", "Achieved"],
        ["Validated, tested cleaning pipeline", "Achieved"],
        ["All required business metrics", "Achieved"],
        ["Charts and executive dashboard (Python)", "Achieved (10 charts)"],
        ["Excel workbook with multiple sheets and data-quality report", "Achieved (10 + 1 sheets)"],
        ["Business-insights report", "Achieved (15 findings, 5 recommendations)"],
        ["Power BI model, Power Query, DAX, specification, build guide", "Achieved as source files; statically validated"],
        ["Four-page Power BI dashboard (.pbix) with real screenshots", "Achieved with deviations - all four pages and synced slicers exist; part of the specified analysis is missing (Section 21.3)"],
        ["Python-vs-Power BI reconciliation", "Pandas emulation of the DAX (106 of 109 match, 3 explained) and a screenshot-to-Python comparison (all legible figures match)"],
    ], [10.4, 6.2], caption=ctx.next_table("Objectives and their status"), font_size=9.5)


def ch26_limitations(document, ctx: DocContext) -> None:
    chapter_title(document, "27. Challenges and Limitations")
    add_heading(document, "27.1 Challenges encountered", 2)
    add_table(document, ["Challenge", "How it was handled"], [
        ["Order grain and double counting in Power BI", "Verified that Order_ID is unique per row; used DISTINCTCOUNT for orders, customers and products"],
        ["Customer_Type is a whole-period flag", "Created a slicer-aware [Repeat Customers] measure and a Lifetime Flag variant; documented the difference"],
        ["RFM segments hard to reproduce in DAX", "Exported Python's segments as a one-row-per-customer dimension, with a uniqueness guard and tests"],
        ["ABC class disagreed for one product", "Reconciliation found a rounding boundary (Jeans, 95.004%); DAX aligned to Python's documented rounding"],
        ["City does not map to a single region ('Unknown' cities)", "City and Region kept as fact-table attributes instead of a geography dimension"],
        ["Power BI Desktop unavailable in the preparation environment", "Prepared all assets, validated statically and wrote a build guide; the team then built the .pbix, which was audited against the specification"],
        ["pytest not installable offline in the first environment", "Ran the unchanged tests with a stand-in runner first, then re-ran with real pytest 9.1.1; disclosed in Chapter 25"],
        ["'Occasional' segment can never be assigned", "Found while documenting; left unchanged to preserve tested behaviour; listed as future work"],
    ], [6.2, 10.4], caption=ctx.next_table("Challenges and responses"), font_size=9)
    add_heading(document, "27.2 Limitations", 2)
    add_bullets(document, [
        "Synthetic data:: all insights describe a simulated world. Seasonality, payment mix and regional balance are generator settings.",
        "No database:: the project is CSV-based; there is no SQL layer and none is claimed.",
        "Descriptive analytics only:: no forecasting, prediction or machine learning.",
        "One product per order:: market-basket analysis is not possible with this data structure.",
        "Static segments:: RFM segments are computed over the whole period and do not change with slicers.",
        "Dashboard coverage:: the delivered .pbix covers part of the planned analysis (no Top N filters, Pareto, customer segmentation or region highlight cards); see Section 21.3.",
        "Advanced product rankings:: Top 10 / Bottom 10 filters on the product and customer rankings are not implemented in the dashboard; the Python pipeline provides the rankings.",
        "Absent planned visuals:: Pareto cumulative line, ABC matrix, customer-segmentation chart, customer-type donut, regional trend line and highest/lowest region cards are not in the .pbix (they exist as Python results or DAX catalogue measures only).",
        "Trend axis order:: the two Year-Month line charts on page 1 are sorted by value, so months do not appear in date order.",
        "Customer city data:: 60 order records (58 customers) have the city 'Unknown'; they appear as an 'Unknown' city in the Power BI city visuals.",
        "Audit scope:: the audit could not reproduce the team's Power BI Desktop session, so slicer behaviour is reported from the team's own testing and the report definition rather than from an independent re-test.",
        "Accessibility:: visuals use Power BI's automatic titles and have no alt text.",
        "Semantic model inspection:: the independent audit could not read the compressed semantic model inside the .pbix, so measure formulas and relationships were not inspected by it; the team's Power BI Desktop testing and the comparison of displayed values with Python cover this part.",
        "Screenshot quality:: the screenshots are 52%-zoom captures (about 990 x 556 pixels after cropping); small text is hard to read.",
        "Single currency, single time zone, two years of data:: limits trend and seasonality conclusions.",
    ])


def ch27_future_conclusion(document, ctx: DocContext) -> None:
    s = ctx.results["summary"]
    chapter_title(document, "28. Future Scope and Conclusion")
    add_heading(document, "28.1 Future scope", 2)
    add_bullets(document, [
        "Complete the dashboard:: add the Top 10 / Bottom 10 product filters, Pareto cumulative line, ABC matrix, customer-segmentation and customer-type charts, regional trend line, highest/lowest region cards, chronological month sorting, custom titles and alt text (all specified in `powerbi/BUILD_GUIDE.md`; none implemented in the delivered .pbix).",
        "Real data:: connect to a real transaction source; the validation and cleaning modules already isolate data-quality problems.",
        "SQL layer:: load the cleaned data into a relational database and let Power BI use DirectQuery or import from SQL.",
        "Forecasting:: add time-series forecasting of monthly revenue (a future extension; nothing predictive is implemented now).",
        "Segmentation refinement:: make the 'Occasional' rule reachable, add customer lifetime value, and allow time-sliced segments.",
        "Multi-line orders:: extend the data model with order lines to enable basket analysis.",
        "Power BI Service:: publish, schedule refresh and add row-level security by region.",
        "Automation:: run tests and the pipeline in GitHub Actions on every commit.",
        "Configuration:: expose dataset size and seed as command-line options.",
    ])
    add_heading(document, "28.2 Conclusion", 2)
    add_paragraph(document, f"The SmartMart project delivers a complete, reproducible analytics solution: a Python pipeline that generates, cleans, analyses and reports on "
                  f"{whole(len(ctx.df))} synthetic transactions ({money(s['Total Revenue'])} in revenue), and a Power BI layer designed to turn the same data into four-page "
                  "dashboard, delivered as a .pbix report. The existing Python implementation was preserved and extended only additively; the extra work is "
                  "covered by tests and by a reconciliation that compares Python results with the Power BI measure definitions.")
    add_paragraph(document, "The Power BI report was built, opened and tested by the team in Power BI Desktop, and its displayed figures agree with the Python results, but it implements only part of the specified "
                  "analysis. The unbuilt visuals and corrections (chronological month sorting, Top N and Bottom N filters, a customer-segmentation visual, custom titles and alt text) are listed as future "
                  "scope in Section 28.1. We have said plainly where the "
                  "evidence stops, because a trustworthy analytics project depends as much on honest reporting of what was verified as on the calculations themselves.")
    add_paragraph(document, "We thank Cronus Consultants and our mentor, Mr. Subhashish Banerjee, for the guidance that shaped this work.", italic=True)


def ch28_references(document, ctx: DocContext) -> None:
    chapter_title(document, "29. References")
    add_paragraph(document, "Sources and further reading for the tools and methods used. The first two are the course documents supplied for this project.", keep_with_next=True)
    add_bullets(document, [
        "Cronus Consultants. *SmartMart Sales Performance Dashboard - Group A Student Project* (assignment document supplied to the team).",
        "Cronus Consultants. *Documentation Sample Format - Data Analytics Project* (format reference supplied to the team).",
        "Python library documentation: pandas (https://pandas.pydata.org/docs/), NumPy (https://numpy.org/doc/), Matplotlib (https://matplotlib.org/stable/), seaborn (https://seaborn.pydata.org/), openpyxl (https://openpyxl.readthedocs.io/), pytest (https://docs.pytest.org/), Streamlit (https://docs.streamlit.io/) and Plotly (https://plotly.com/python/).",
        "Microsoft documentation: Power BI Desktop (https://learn.microsoft.com/power-bi/), star schema guidance (https://learn.microsoft.com/power-bi/guidance/star-schema), DAX (https://learn.microsoft.com/dax/, https://dax.guide/) and Power Query M (https://learn.microsoft.com/powerquery-m/).",
        "Kimball, R. and Ross, M. *The Data Warehouse Toolkit*, 3rd ed. Wiley, 2013.",
        "Hughes, A. M. *Strategic Database Marketing* (introduces recency-frequency-monetary segmentation), McGraw-Hill.",
    ])



# --------------------------------------------------------------------------
# Appendices
# --------------------------------------------------------------------------
def appendix_a(document, ctx: DocContext) -> None:
    chapter_title(document, "Appendix A. Full Product Ranking")
    table = ctx.results["pareto"]["pareto_table"].merge(ctx.results["products"]["all_products"][["Product", "Category", "Quantity"]], on="Product")
    rows = [[int(r.Rank), r.Product, r.Category, money(r.Revenue, 0), whole(r.Quantity), f"{r.Cumulative_Revenue_Percent:.2f}%", r.ABC_Class]
            for r in table.itertuples()]
    add_table(document, ["Rank", "Product", "Category", "Revenue", "Units", "Cumulative", "ABC"], rows,
              [1.2, 3.8, 3.4, 3.2, 1.7, 2.3, 1.0], align=["c", "l", "l", "r", "r", "r", "c"],
              caption=ctx.next_table("All 35 products with cumulative revenue share and ABC class (src/analysis.py: pareto_analysis)"),
              font_size=8, row_pad=25)


def appendix_b(document, ctx: DocContext) -> None:
    chapter_title(document, "Appendix A. How to Run the Project")
    add_heading(document, "A.1 Python", 2)
    add_code(document, "Terminal commands", """cd SmartMart_Sales_Analytics_Final
python -m venv .venv
.venv\\Scripts\\activate          (Windows)   |   source .venv/bin/activate  (macOS/Linux)
pip install -r requirements.txt

python main.py                   # full pipeline (generate if needed, clean, analyse, report, Power BI export)
python main.py --generate-data   # only (re)generate the raw dataset
pytest -q                        # run all automated tests

python powerbi/verification/validate_powerbi_assets.py     # static check of DAX and M files
python powerbi/verification/reconcile_python_vs_dax.py     # Python vs DAX-equivalent reconciliation""", font_size=8.5)
    add_heading(document, "A.2 Streamlit analytics platform", 2)
    add_code(document, "Terminal commands", """python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py            # dynamic platform (7 pages), http://localhost:8501
python -m streamlit run streamlit_app_classic.py    # original six-page SmartMart dashboard""", font_size=8.5)
    add_paragraph(document, "If `data/processed/*.csv` are missing, run `python main.py` once. Streamlit 1.40 or newer is required; `xlrd` is needed only for `.xls` uploads.")
    add_heading(document, "A.3 Power BI", 2)
    add_paragraph(document, "Open `powerbi/SmartMart_Sales_Dashboard_Final.pbix` in Power BI Desktop for Windows (free). The file holds the report and the data "
                  "model, so it opens without the CSV files; press **Home > Refresh** only if the source folder still exists, and if refresh fails open **Transform data > "
                  "Data source settings** and point the sources at the project's `data/processed/` folder. The data sources stored inside the file were not inspected by the audit. "
                  "`powerbi/BUILD_GUIDE.md` documents the original build recipe and expected values, which can be used to rebuild or extend the report.")
    add_heading(document, "A.4 Rebuilding this document", 2)
    add_code(document, "Terminal commands", """pip install -r requirements-docs.txt
python docs/make_diagrams.py
python docs/build_documentation.py     # inserts powerbi/screenshots/01_..04_*.png; writes documentation/SmartMart_Final_Report.docx and .pdf
python powerbi/verification/inspect_pbix.py   # read-only inspection of the .pbix report definition""", font_size=8.5)
    add_paragraph(document, "Open the resulting DOCX in Word, right-click the table of contents and choose *Update Field* if page numbers have shifted. "
                  "Export to PDF from Word if you prefer Word's own layout.")


def appendix_c(document, ctx: DocContext) -> None:
    chapter_title(document, "Appendix C. Delivered Power BI Dashboard Layouts")
    add_paragraph(document, "These four figures show the **actual delivered dashboard pages** as they appear in the team's Power BI Desktop session, "
                  "not proposed wireframes. They are the team's screenshots of `SmartMart_Sales_Dashboard_Final.pbix`, cropped to the report canvas "
                  "with no other editing, and they show the real arrangement of KPI cards, charts, tables and slicers. Where the delivered report differs "
                  "from the original specification, see Section 21.3.", keep_with_next=True)
    pages = [("01_Executive_Overview.png", "Executive Overview"), ("02_Product_Performance.png", "Product Performance"),
             ("03_Regional_Performance.png", "Regional Performance"), ("04_Customer_Payment.png", "Customer & Payment")]
    for name, label in pages:
        add_figure(document, ctx.screenshot_dir / name,
                   ctx.next_figure(f"{label} - actual delivered dashboard (Power BI Desktop screenshot)"), width_cm=16.0, max_height_cm=9.4)
