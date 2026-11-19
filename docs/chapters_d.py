"""
chapters_d.py - Chapter 23: the Streamlit analytics platform.
Screenshots are the team's own captures of the running app (docs/assets/streamlit/); figures quoted from the
Overview page are recomputed from the project's data by DocContext, so the text cannot drift from the code.
"""

from __future__ import annotations

from pathlib import Path

from doc_context import DocContext, money, whole
from docx_helpers import add_bullets, add_callout, add_code, add_figure, add_heading, add_paragraph, add_table
from chapters_a import chapter_title

SHOTS = Path(__file__).parent / "assets" / "streamlit"
SHOT_NOTE = "team screenshot of the running app at localhost:8501, cropped to the browser viewport; no other editing"


def _shot(document, ctx, name: str, caption: str) -> None:
    add_figure(document, SHOTS / name, ctx.next_figure(f"{caption} ({SHOT_NOTE})"), width_cm=13.0, max_height_cm=6.2, compact=False)


def ch23_streamlit(document, ctx: DocContext) -> None:
    df = ctx.df
    revenue, orders = df["Sales"].sum(), df["Order_ID"].nunique()
    chapter_title(document, "23. Streamlit Analytics Platform")
    add_heading(document, "23.1 Purpose and design", 2)
    add_paragraph(document, "In addition to the Power BI report, the project includes a web application built with **Streamlit** and **Plotly**. "
                  "It reads the same processed CSV files that `main.py` writes, shows the SmartMart analysis in the browser, and goes one step "
                  "further: the user can upload their own CSV or Excel file, review and clean it, and see KPIs, charts and insights "
                  "calculated from *that* data. Nothing is typed in: every KPI, chart, table, filter and report is computed from the "
                  "**active dataset**, so a KPI whose column does not exist (for example Total Customers without a customer column) is simply not shown.")
    add_bullets(document, [
        "Default data:: on start the built-in SmartMart CSVs are loaded, so the app works immediately after `python main.py`.",
        "Any dataset:: column roles (revenue, date, customer, product, category, location, quantity, price, order id) are detected from names and content with a confidence score; uncertain roles can be re-mapped by hand.",
        "Original data is safe:: uploads, cleaning and manual rows only change a working copy in the browser session; the built-in CSV files and all project files are never modified.",
        "Original dashboard kept:: the earlier six-page SmartMart Streamlit app remains unchanged in `streamlit_app_classic.py`.",
    ])
    add_heading(document, "23.2 Architecture and how to run it", 2)
    add_paragraph(document, "The logic is separated from the screen code. The data modules contain no Streamlit imports and are covered by automated "
                  "tests; `ui_components.py` and `ui_pages.py` only lay out widgets and draw Plotly charts.")
    add_table(document, ["Module (src/)", "Lines", "Responsibility"], [
        ["schema_detection.py", "180", "Column types and business roles with confidence; manual mapping"],
        ["dataset_manager.py", "187", "The active dataset: load default, replace with upload, clear, add rows, apply / undo cleaning"],
        ["data_upload.py, data_entry.py", "158 + 166", "Reading CSV / .xlsx / .xls safely (encoding, delimiter); validated manual row entry"],
        ["data_cleaning.py", "277", "Quality reports and cleaning operations that return a new table plus a change message"],
        ["dynamic_analytics.py", "494", "Filters, KPIs by domain, breakdowns, trends, correlations, outliers and grounded insights"],
        ["visualizations.py, report_export.py", "245 + 210", "Plotly figure builders; CSV / Excel / text report builders"],
        ["ui_components.py, ui_pages.py", "442 + 544", "Sidebar, filters, dialogs and the seven pages"],
    ], [5.2, 2.2, 9.2], caption=ctx.next_table("Modules of the Streamlit platform (line counts from the delivered files)"), font_size=9)
    add_code(document, "Terminal commands", """python -m pip install -r requirements.txt
python main.py                              # once, if data/processed/*.csv are missing
python -m streamlit run streamlit_app.py    # opens http://localhost:8501""", font_size=8.5)
    add_heading(document, "23.3 Pages and workflow", 2)
    add_table(document, ["Page", "What it offers"], [
        ["Overview", "KPI cards and the main charts of the active dataset"],
        ["Data Management", "Working data, upload, column mapping and sources"],
        ["Data Preparation", "Quality score and reports; cleaning operations with before / after comparison, apply and undo"],
        ["Exploratory Analysis", "Distributions, relationships, correlation, categories, time series and outliers for any column"],
        ["Business Intelligence", "Performance, trends, customers and automatic insights (sales, HR, banking, inventory or generic analytics)"],
        ["Reports & Export", "Original, working, cleaned and filtered CSV; data-quality report; summary and insights; Excel reports"],
        ["Settings", "Session information and reset"],
    ], [4.2, 12.4], caption=ctx.next_table("The seven pages of the platform"), font_size=9)
    add_paragraph(document, "The sidebar shows the active dataset and its status and holds the global filters (date range, categories and numeric ranges, "
                  "with a reset). Every page uses the filtered rows, so all KPIs, charts and tables update together.")
    add_paragraph(document, f"Figure {ctx.figure_count + 1} shows the Overview page for the built-in dataset. Its cards show total revenue "
                  f"{money(revenue / 1e6, 2).replace(chr(0x20B9), chr(0x20B9))}M, {whole(orders)} orders, {whole(df['Quantity'].sum())} units, an average order value of "
                  f"{money(revenue / orders)}, an average selling price of {money(revenue / df['Quantity'].sum())}, {whole(df['Customer_ID'].nunique())} customers and "
                  f"{df['Product'].nunique()} products. These equal the Python results in Chapter 10 and the Power BI cards in Chapter 22.")
    _shot(document, ctx, "overview.png", "Streamlit Overview page for the built-in SmartMart dataset")
    add_heading(document, "23.4 Data management and the four action buttons", 2)
    add_paragraph(document, "Four buttons at the top of every page manage the working dataset:")
    add_table(document, ["Button", "Behaviour"], [
        ["Add Row", "Typed input form per column (numbers, dates, yes / no, category lists) with validation; rows are added one at a time. With no dataset it first asks for column names and types."],
        ["Remove All Data", "After confirmation, empties the *working* dataset (optionally keeping the headers). Built-in files and the uploaded source copy are untouched."],
        ["Upload CSV / Excel", "Drag-and-drop .csv, .xlsx or .xls; shows size, rows, columns, types, missing values and duplicates before the working dataset is replaced."],
        ["Load Default Dashboard", "After confirmation, re-reads the built-in SmartMart CSVs and restores the original dashboard whatever was done before."],
    ], [4.2, 12.4], caption=ctx.next_table("The four data-management buttons"), font_size=9)
    _shot(document, ctx, "data_management.png", "Data Management page with the four action buttons")
    _shot(document, ctx, "upload_dialog.png", "Upload CSV / Excel dialog (the file is read in memory only)")
    add_heading(document, "23.5 Data preparation", 2)
    add_paragraph(document, "The Data Preparation page first reports quality: a quality score, missing cells, duplicate rows, data types, invalid values and outliers "
                  "(IQR rule). The *Clean & transform* tab then offers removal of duplicates, handling of missing values, changing data types, standardising "
                  "category spellings, removing invalid rows or outliers, and numeric transformations. Each operation works on a copy, reports what it changed, "
                  "and the result can be compared before and after, applied to the working dataset, or undone.")
    _shot(document, ctx, "data_preparation.png", "Data Preparation page - quality reports for the built-in dataset (score 97.00, 0 missing cells, 0 duplicates)")
    add_heading(document, "23.6 Exploration and business intelligence", 2)
    add_paragraph(document, "The Exploratory Analysis page offers histograms and box plots, scatter plots, a correlation heatmap, category charts, time series and "
                  "outlier views for whichever columns the active dataset has; the time-series tab appears only if a date column exists. The Business "
                  "Intelligence page shows KPIs and breakdowns suited to the detected data (sales, HR, banking, inventory or generic) and a list of insights, "
                  "each of which is generated from calculated values and is withheld for very small samples.")
    _shot(document, ctx, "exploratory_analysis.png", "Exploratory Analysis page - distribution of Quantity")
    _shot(document, ctx, "business_intelligence.png", "Business Intelligence page - KPIs and revenue by category")
    add_heading(document, "23.7 Verification and limitations", 2)
    add_paragraph(document, "The platform's data layer is covered by automated tests (schema detection, dataset manager, entry and upload, cleaning, dynamic analytics, "
                  "reports). The full project suite, run with pytest on the delivered files when this report was built, gave **94 passed, 2 skipped**; the two "
                  "skipped tests start the real Streamlit app and are skipped when Streamlit is not installed in the build environment. The screenshots above "
                  "are the team's own captures of the app running in a browser, which is the evidence that the pages render; the KPI cards match the Python results.")
    add_callout(document, "Limitations", "Datasets live in the browser session: restarting the app (or Settings > Reset session) returns to the default data, and "
                "uploaded or manual data is not saved. Rows cannot be edited in place (add, clean, clear or upload only). HR, banking and inventory analytics are "
                "keyword-based and appear only when matching columns exist. Reading .xls files needs the optional `xlrd` package. The platform contains no machine-learning component.",
                fill_hex="FFF8E5", bar_hex="E0A030")
