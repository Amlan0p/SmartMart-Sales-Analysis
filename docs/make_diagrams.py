"""
make_diagrams.py

Draws the architecture / data-flow / data-model diagrams and the planned
dashboard WIREFRAMES used in the documentation. All diagrams are generated
with matplotlib. The wireframes are layout plans only - they are labelled as
such in the figure itself and are NOT Power BI screenshots.

Run:  python docs/make_diagrams.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

OUTPUT_DIR = Path(__file__).resolve().parent / "assets" / "diagrams"
BLUE, GREEN, NAVY, GREY, LIGHT = "#3669AB", "#69A147", "#1B3A5C", "#8795A8", "#EAF1F8"
plt.rcParams["font.family"] = ["Carlito", "DejaVu Sans"]


def _box(ax, x, y, w, h, text, fill=LIGHT, edge=BLUE, color=NAVY, size=10, bold=False, weight=None):
    patch = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08",
                           linewidth=1.6, edgecolor=edge, facecolor=fill)
    ax.add_patch(patch)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=size, color=color,
            fontweight="bold" if bold else (weight or "normal"), linespacing=1.25)


def _arrow(ax, x1, y1, x2, y2, color=NAVY):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color=color, lw=1.8, shrinkA=2, shrinkB=2))


def _canvas(width, height):
    fig, ax = plt.subplots(figsize=(width, height))
    ax.set_xlim(0, width)
    ax.set_ylim(0, height)
    ax.axis("off")
    return fig, ax


def architecture_overview() -> None:
    fig, ax = _canvas(11, 6.2)
    ax.text(5.5, 5.85, "SmartMart end-to-end architecture", ha="center", fontsize=15, color=NAVY, fontweight="bold")
    _box(ax, 0.3, 4.3, 2.3, 0.9, "Synthetic retail\nsales dataset\n(generate_dataset.py)", fill="#FFF8E5", edge="#E0A030")
    _arrow(ax, 2.6, 4.75, 3.2, 4.75)
    ax.add_patch(FancyBboxPatch((3.2, 1.7), 4.1, 3.6, boxstyle="round,pad=0.02,rounding_size=0.1",
                                linewidth=2, edgecolor=BLUE, facecolor="white"))
    ax.text(5.25, 5.08, "PYTHON PIPELINE  (main.py)", ha="center", fontsize=10.5, color=BLUE, fontweight="bold")
    steps = ["Load + validate (data_loader)", "Clean + preprocess (preprocessing)",
             "Feature engineering", "Analysis + KPIs (analysis)", "Charts / Excel / Insights"]
    for index, label in enumerate(steps):
        _box(ax, 3.4, 4.3 - index * 0.55, 3.7, 0.42, label, size=9)
        if index < len(steps) - 1:
            _arrow(ax, 5.25, 4.3 - index * 0.55, 5.25, 4.3 - (index + 1) * 0.55 + 0.42, color=GREY)
    _arrow(ax, 7.3, 3.5, 7.9, 3.5)
    _box(ax, 7.9, 3.0, 2.8, 1.0, "Cleaned CSV +\ncustomer & product\ndimension CSVs", fill="#EAF5E3", edge=GREEN)
    _arrow(ax, 9.3, 3.0, 9.3, 2.5)
    ax.add_patch(FancyBboxPatch((7.6, 0.2), 3.2, 2.3, boxstyle="round,pad=0.02,rounding_size=0.1",
                                linewidth=2, edgecolor=GREEN, facecolor="white"))
    ax.text(9.2, 2.28, "MICROSOFT POWER BI", ha="center", fontsize=10.5, color=GREEN, fontweight="bold")
    _box(ax, 7.8, 1.5, 2.8, 0.45, "Power Query (import, types)", size=9, edge=GREEN)
    _box(ax, 7.8, 0.95, 2.8, 0.45, "Data model + DAX measures", size=9, edge=GREEN)
    _box(ax, 7.8, 0.4, 2.8, 0.45, "4 interactive dashboard pages", size=9, edge=GREEN)
    _box(ax, 3.2, 0.2, 4.1, 1.1, "Python outputs:\n10 PNG charts \u2022 Excel report \u2022 data-quality\nworkbook \u2022 business-insights report",
         fill="#F3F5F8", edge=GREY, size=9)
    _arrow(ax, 5.25, 1.7, 5.25, 1.3, color=GREY)
    fig.savefig(OUTPUT_DIR / "architecture_overview.png", dpi=170, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def cleaning_flow() -> None:
    fig, ax = _canvas(11, 3.2)
    ax.text(5.5, 2.95, "Row flow through the cleaning stage (actual run)", ha="center", fontsize=13, color=NAVY, fontweight="bold")
    items = [("Raw CSV", "15,075 rows", "#FFF8E5", "#E0A030"),
             ("Fill / impute", "City 60, Payment 60,\nUnit_Price 59 (no row loss)", LIGHT, BLUE),
             ("Drop duplicates", "\u221275 rows \u2192 15,000", LIGHT, BLUE),
             ("Drop invalid\nQty / Price \u2264 0", "\u221230 rows \u2192 14,970", LIGHT, BLUE),
             ("Cleaned CSV", "14,970 rows", "#EAF5E3", GREEN)]
    for index, (title, detail, fill, edge) in enumerate(items):
        x = 0.2 + index * 2.15
        _box(ax, x, 0.9, 1.85, 1.3, f"{title}\n\n{detail}", fill=fill, edge=edge, size=9)
        if index < len(items) - 1:
            _arrow(ax, x + 1.85, 1.55, x + 2.15, 1.55)
    fig.savefig(OUTPUT_DIR / "cleaning_flow.png", dpi=170, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def module_diagram() -> None:
    fig, ax = _canvas(11, 5.2)
    ax.text(5.5, 4.9, "Python module architecture", ha="center", fontsize=15, color=NAVY, fontweight="bold")
    _box(ax, 4.2, 3.9, 2.6, 0.6, "main.py  (orchestration only)", fill=BLUE, color="white", edge=BLUE, bold=True, size=10.5)
    middle = ["generate_dataset", "data_loader", "preprocessing", "data_quality", "analysis"]
    lower = ["visualization", "excel_report", "insights", "powerbi_export"]
    for index, name in enumerate(middle):
        x = 0.3 + index * 2.1
        _box(ax, x, 2.45, 1.85, 0.6, f"src/{name}.py", size=9)
        _arrow(ax, 5.5, 3.9, x + 0.92, 3.05, color=GREY)
    for index, name in enumerate(lower):
        x = 0.9 + index * 2.5
        fill = "#EAF5E3" if name == "powerbi_export" else LIGHT
        edge = GREEN if name == "powerbi_export" else BLUE
        _box(ax, x, 1.2, 2.1, 0.6, f"src/{name}.py", size=9, fill=fill, edge=edge)
        _arrow(ax, 8.9, 2.45, x + 1.05, 1.8, color=GREY)
    _box(ax, 0.3, 0.1, 4.9, 0.6, "config.py  (paths, seed, thresholds, constants)", fill="#FFF8E5", edge="#E0A030", size=9.5)
    _box(ax, 5.8, 0.1, 4.9, 0.6, "src/utils.py  (logging, formatting, safe_divide, directories)", fill="#F3F5F8", edge=GREY, size=9.5)
    ax.text(10.9, 1.5, "new\n(Power BI)", fontsize=8, color=GREEN, ha="right", style="italic")
    fig.savefig(OUTPUT_DIR / "module_architecture.png", dpi=170, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def star_schema() -> None:
    fig, ax = _canvas(11, 5.4)
    ax.text(5.5, 5.1, "Power BI star schema", ha="center", fontsize=15, color=NAVY, fontweight="bold")
    tables = {
        "Dim_Date": (0.4, 3.0, ["Date  (PK)", "Year", "Quarter", "Month Number / Name", "Year-Month"], GREEN),
        "Dim_Customer": (0.4, 0.3, ["Customer_ID  (PK)", "Segment", "R / F / M / RFM score", "Recency_Days, Frequency", "Monetary, Last_Order_Date"], GREEN),
        "Dim_Product": (7.8, 1.6, ["Product  (PK)", "Category", "Revenue_Rank", "ABC_Class", "Cumulative_Revenue_Percent"], GREEN),
        "Fact_Sales": (4.1, 1.2, ["Order_ID  (unique)", "Order_Date  (FK)", "Customer_ID  (FK)", "Product  (FK)", "Quantity, Unit_Price, Sales",
                                  "Region, City, Payment_Mode", "Customer_Type"], BLUE),
    }
    for name, (x, y, columns, colour) in tables.items():
        height = 0.38 * (len(columns) + 1)
        ax.add_patch(FancyBboxPatch((x, y), 2.9, height, boxstyle="round,pad=0.02,rounding_size=0.06",
                                    linewidth=1.8, edgecolor=colour, facecolor="white"))
        ax.add_patch(FancyBboxPatch((x, y + height - 0.38), 2.9, 0.38, boxstyle="round,pad=0.02,rounding_size=0.06",
                                    linewidth=0, facecolor=colour))
        ax.text(x + 1.45, y + height - 0.19, name, ha="center", va="center", color="white", fontsize=10.5, fontweight="bold")
        for index, column in enumerate(columns):
            ax.text(x + 0.12, y + height - 0.38 - 0.34 * (index + 0.65), column, fontsize=8.8, color=NAVY, va="center")
    for (x1, y1, x2, y2) in [(3.3, 3.5, 4.1, 3.2), (3.3, 1.2, 4.1, 2.2), (7.8, 2.6, 7.0, 2.6)]:
        _arrow(ax, x1, y1, x2, y2, color=NAVY)
    ax.text(3.35, 3.55, "1", fontsize=10, color=NAVY, fontweight="bold")
    ax.text(3.75, 3.0, "*", fontsize=13, color=NAVY, fontweight="bold")
    ax.text(3.35, 1.25, "1", fontsize=10, color=NAVY, fontweight="bold")
    ax.text(3.75, 2.05, "*", fontsize=13, color=NAVY, fontweight="bold")
    ax.text(7.55, 2.7, "1", fontsize=10, color=NAVY, fontweight="bold")
    ax.text(7.1, 2.35, "*", fontsize=13, color=NAVY, fontweight="bold")
    ax.text(5.5, 0.15, "One-to-many relationships, single cross-filter direction (dimension \u2192 fact)", ha="center", fontsize=9.5, color=GREY, style="italic")
    fig.savefig(OUTPUT_DIR / "star_schema.png", dpi=170, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def wireframes() -> None:
    """Planned layouts from the dashboard specification (1280 x 720 canvas)."""
    pages = {
        "page1_executive_overview": ("Page 1 - Executive Overview", [
            ("Slicers: Date | Region | Category | Product | Payment", 16, 64, 1248, 52, "#E8EEF5"),
            *[(label, 16 + i * 210, 124, 200, 84, "#DCE8F5") for i, label in enumerate(
                ["Total Revenue", "Total Orders", "Total Customers", "Total Units", "Avg Order Value", "Avg Selling Price"])],
            ("Monthly Revenue Trend (line)", 16, 218, 720, 240, "#EAF5E3"),
            ("Revenue by Category (bar)", 746, 218, 518, 240, "#EAF5E3"),
            ("Revenue by Region", 16, 468, 400, 244, "#EAF5E3"),
            ("Top 5 Products", 426, 468, 420, 244, "#EAF5E3"),
            ("Revenue by Year", 856, 468, 408, 176, "#EAF5E3"),
            ("YoY growth", 856, 652, 200, 60, "#DCE8F5"),
            ("Peak month", 1066, 652, 198, 60, "#DCE8F5"),
        ]),
        "page2_product_performance": ("Page 2 - Product Performance", [
            ("Slicers (synced)", 16, 64, 1248, 52, "#E8EEF5"),
            ("Top 10 Products", 16, 124, 340, 230, "#EAF5E3"),
            ("Bottom 10 Products", 366, 124, 340, 230, "#EAF5E3"),
            ("Revenue by Category (donut)", 716, 124, 250, 230, "#EAF5E3"),
            ("Quantity Sold by Product", 976, 124, 288, 230, "#EAF5E3"),
            ("Pareto Analysis (columns + cumulative % line)", 16, 364, 520, 348, "#FFF1D6"),
            ("Product Performance Comparison (scatter)", 546, 364, 350, 348, "#EAF5E3"),
            ("ABC Classification (matrix)", 906, 364, 358, 150, "#FFF1D6"),
            ("Product detail table", 906, 524, 358, 188, "#EAF5E3"),
        ]),
        "page3_regional_performance": ("Page 3 - Regional Performance", [
            ("Slicers (synced)", 16, 64, 1248, 52, "#E8EEF5"),
            *[(label, 16 + i * 310, 124, 300, 84, "#DCE8F5") for i, label in enumerate(
                ["Highest Region", "Lowest Region", "Highest Region Revenue", "Lowest Region Revenue"])],
            ("Revenue by Region", 16, 218, 300, 240, "#EAF5E3"),
            ("Orders by Region", 326, 218, 300, 240, "#EAF5E3"),
            ("Avg Order Value by Region", 636, 218, 300, 240, "#EAF5E3"),
            ("Regional share (donut)", 946, 218, 318, 240, "#EAF5E3"),
            ("Revenue by City", 16, 468, 420, 244, "#EAF5E3"),
            ("Regional Sales Trends (line)", 446, 468, 520, 244, "#EAF5E3"),
            ("Comparison table", 976, 468, 288, 244, "#FFF1D6"),
        ]),
        "page4_customer_payment": ("Page 4 - Customer and Payment Analysis", [
            ("Slicers (synced)", 16, 64, 1248, 52, "#E8EEF5"),
            *[(label, 16 + i * 210, 124, 200, 84, "#DCE8F5") for i, label in enumerate(
                ["Unique Customers", "Repeat", "One-time", "Repeat rate", "Revenue / customer", "Orders / customer"])],
            ("Customer Segmentation (donut)", 16, 218, 310, 240, "#EAF5E3"),
            ("Revenue by Segment", 336, 218, 310, 240, "#EAF5E3"),
            ("Revenue by Customer Type", 656, 218, 280, 240, "#EAF5E3"),
            ("Top 10 Customers", 946, 218, 318, 240, "#EAF5E3"),
            ("Payment Method Distribution", 16, 468, 300, 244, "#EAF5E3"),
            ("Revenue by Payment Method", 326, 468, 320, 244, "#EAF5E3"),
            ("Payment Summary", 656, 468, 300, 244, "#FFF1D6"),
            ("Segment Detail", 966, 468, 298, 244, "#FFF1D6"),
        ]),
    }
    for filename, (title, boxes) in pages.items():
        fig, ax = plt.subplots(figsize=(10, 5.9))
        ax.set_xlim(0, 1280)
        ax.set_ylim(720, 0)
        ax.axis("off")
        ax.add_patch(plt.Rectangle((0, 0), 1280, 720, facecolor="#F4F7FB", edgecolor=GREY, linewidth=1.2))
        ax.add_patch(plt.Rectangle((0, 0), 1280, 56, facecolor=BLUE, edgecolor="none"))
        ax.text(20, 30, f"SmartMart  |  {title}", color="white", fontsize=12, fontweight="bold", va="center")
        ax.text(1264, 30, "PLANNED LAYOUT WIREFRAME - NOT A SCREENSHOT", color="#FFE9B0", fontsize=8.5, ha="right", va="center", fontweight="bold")
        for label, x, y, w, h, fill in boxes:
            ax.add_patch(plt.Rectangle((x, y), w, h, facecolor=fill, edgecolor=BLUE, linewidth=0.9))
            ax.text(x + w / 2, y + h / 2, label, ha="center", va="center", fontsize=7.6, color=NAVY, wrap=True)
        fig.savefig(OUTPUT_DIR / f"wireframe_{filename}.png", dpi=150, bbox_inches="tight", facecolor="white")
        plt.close(fig)


def distribution_chart() -> None:
    """Histogram of order value and quantity from the REAL cleaned dataset
    (EDA 'sales distribution'). Uses a log x-axis because order values span
    three orders of magnitude."""
    import sys

    import numpy as np
    import pandas as pd

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import config

    df = pd.read_csv(config.CLEANED_SALES_DATA_PATH)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    bins = np.logspace(np.log10(df["Sales"].min()), np.log10(df["Sales"].max()), 40)
    axes[0].hist(df["Sales"], bins=bins, color=BLUE, edgecolor="white")
    axes[0].set_xscale("log")
    axes[0].set_title("Distribution of order value (log scale)", color=NAVY, fontweight="bold")
    axes[0].set_xlabel("Order value (\u20B9, log scale)")
    axes[0].set_ylabel("Number of orders")
    counts = df["Quantity"].value_counts().sort_index()
    axes[1].bar(counts.index.astype(str), counts.values, color=GREEN, edgecolor="white")
    axes[1].set_title("Distribution of quantity per order", color=NAVY, fontweight="bold")
    axes[1].set_xlabel("Quantity")
    axes[1].set_ylabel("Number of orders")
    for axis in axes:
        axis.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "sales_distribution.png", dpi=170, facecolor="white")
    plt.close(fig)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    architecture_overview()
    cleaning_flow()
    module_diagram()
    star_schema()
    wireframes()
    distribution_chart()
    print(f"Diagrams written to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
