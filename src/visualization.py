"""
visualization.py

Generates all charts required for the SmartMart sales analysis and
saves them as image files under ``outputs/charts/``. No chart values
are hard-coded - every figure is built directly from the analysis
results dictionary produced by ``analysis.run_full_analysis``.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # Non-interactive backend suitable for script/CLI use

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns

from config import CHARTS_DIR, CHART_DPI, CHART_FIGSIZE_SQUARE, CHART_FIGSIZE_WIDE
from src.utils import ensure_directories, get_logger

logger = get_logger(__name__)

sns.set_theme(style="whitegrid")
plt.rcParams["font.size"] = 11
plt.rcParams["axes.titlesize"] = 14
plt.rcParams["axes.titleweight"] = "bold"


def _currency_formatter(value: float, _position=None) -> str:
    return f"₹{value:,.0f}"


def _save_figure(fig: plt.Figure, filename: str, output_dir: Path = CHARTS_DIR) -> Path:
    ensure_directories(output_dir)
    output_path = output_dir / filename
    fig.tight_layout()
    fig.savefig(output_path, dpi=CHART_DPI, bbox_inches="tight")
    plt.close(fig)
    logger.info("Chart saved: %s", output_path)
    return output_path


def plot_monthly_revenue(monthly_table, output_dir: Path = CHARTS_DIR) -> Path:
    """Line chart of monthly revenue over time, with the peak and
    lowest revenue months automatically identified and annotated.

    The "Period" labels (e.g. "January 2023") are plotted against an
    explicit numeric x-position rather than passed to Matplotlib as
    strings. Matplotlib's categorical-axis converter treats strings
    that look like dates as a special case and logs an informational
    "Using categorical units..." notice; using numeric positions with
    manually-assigned tick labels avoids that ambiguity entirely and
    gives identical, warning-free output.
    """
    table = monthly_table.reset_index(drop=True)
    x_positions = range(len(table))

    fig, ax = plt.subplots(figsize=CHART_FIGSIZE_WIDE)
    ax.plot(x_positions, table["Revenue"], marker="o", color="#2563EB", linewidth=2)
    ax.set_title("Monthly Revenue Trend")
    ax.set_xlabel("Month")
    ax.set_ylabel("Revenue")
    ax.set_xticks(list(x_positions))
    ax.set_xticklabels(table["Period"], rotation=45, ha="right")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(_currency_formatter))

    if len(table) > 0:
        peak_pos = int(table["Revenue"].idxmax())
        low_pos = int(table["Revenue"].idxmin())
        peak_row = table.loc[peak_pos]
        low_row = table.loc[low_pos]

        ax.annotate(
            f"Peak: {_currency_formatter(peak_row['Revenue'])}",
            xy=(peak_pos, peak_row["Revenue"]),
            xytext=(0, 15), textcoords="offset points",
            ha="center", fontsize=9, fontweight="bold", color="#166534",
            arrowprops=dict(arrowstyle="->", color="#166534"),
        )
        if low_pos != peak_pos:
            ax.annotate(
                f"Lowest: {_currency_formatter(low_row['Revenue'])}",
                xy=(low_pos, low_row["Revenue"]),
                xytext=(0, -25), textcoords="offset points",
                ha="center", fontsize=9, fontweight="bold", color="#991B1B",
                arrowprops=dict(arrowstyle="->", color="#991B1B"),
            )

    return _save_figure(fig, "monthly_revenue_trend.png", output_dir)


def plot_revenue_by_category(category_table, output_dir: Path = CHARTS_DIR) -> Path:
    """Bar chart of total revenue by category."""
    fig, ax = plt.subplots(figsize=CHART_FIGSIZE_WIDE)
    data = category_table.sort_values("Revenue", ascending=False)
    sns.barplot(data=data, x="Category", y="Revenue", hue="Category", legend=False, palette="viridis", ax=ax)
    ax.set_title("Revenue by Category")
    ax.set_xlabel("Category")
    ax.set_ylabel("Revenue")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(_currency_formatter))
    ax.tick_params(axis="x", rotation=20)
    return _save_figure(fig, "revenue_by_category.png", output_dir)


def plot_top_products(top_products_table, output_dir: Path = CHARTS_DIR) -> Path:
    """Horizontal bar chart of the top 10 products by revenue."""
    fig, ax = plt.subplots(figsize=CHART_FIGSIZE_WIDE)
    data = top_products_table.sort_values("Revenue", ascending=True)
    sns.barplot(data=data, y="Product", x="Revenue", hue="Product", legend=False, palette="crest", ax=ax)
    ax.set_title("Top 10 Products by Revenue")
    ax.set_xlabel("Revenue")
    ax.set_ylabel("Product")
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(_currency_formatter))
    return _save_figure(fig, "top_10_products.png", output_dir)


def plot_regional_sales(region_table, output_dir: Path = CHARTS_DIR) -> Path:
    """Bar chart of revenue by region."""
    fig, ax = plt.subplots(figsize=CHART_FIGSIZE_WIDE)
    data = region_table.sort_values("Revenue", ascending=False)
    sns.barplot(data=data, x="Region", y="Revenue", hue="Region", legend=False, palette="mako", ax=ax)
    ax.set_title("Revenue by Region")
    ax.set_xlabel("Region")
    ax.set_ylabel("Revenue")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(_currency_formatter))
    return _save_figure(fig, "regional_sales.png", output_dir)


def plot_payment_distribution(payment_table, output_dir: Path = CHARTS_DIR) -> Path:
    """Pie chart of order-share distribution across payment methods."""
    fig, ax = plt.subplots(figsize=CHART_FIGSIZE_SQUARE)
    data = payment_table.sort_values("Orders", ascending=False)
    colors = sns.color_palette("Set2", n_colors=len(data))
    ax.pie(
        data["Orders"],
        labels=data["Payment_Mode"],
        autopct="%1.1f%%",
        startangle=90,
        colors=colors,
        wedgeprops={"edgecolor": "white", "linewidth": 1},
    )
    ax.set_title("Payment Method Distribution (by Orders)")
    ax.axis("equal")
    return _save_figure(fig, "payment_method_distribution.png", output_dir)


def plot_top_customers(top_customers_table, output_dir: Path = CHARTS_DIR) -> Path:
    """Horizontal bar chart of the top customers by total spending."""
    fig, ax = plt.subplots(figsize=CHART_FIGSIZE_WIDE)
    data = top_customers_table.sort_values("Total_Spending", ascending=True)
    sns.barplot(data=data, y="Customer_ID", x="Total_Spending", hue="Customer_ID",
                legend=False, palette="flare", ax=ax)
    ax.set_title("Top Customers by Total Spending")
    ax.set_xlabel("Total Spending")
    ax.set_ylabel("Customer ID")
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(_currency_formatter))
    return _save_figure(fig, "top_customers.png", output_dir)


def plot_customer_type_distribution(customer_results: dict, output_dir: Path = CHARTS_DIR) -> Path:
    """Bar chart comparing repeat vs one-time customer counts."""
    fig, ax = plt.subplots(figsize=(7, 5))
    labels = ["Repeat Customers", "One-time Customers"]
    values = [customer_results["repeat_customers"], customer_results["one_time_customers"]]
    sns.barplot(x=labels, y=values, hue=labels, legend=False, palette=["#2563EB", "#94A3B8"], ax=ax)
    ax.set_title("Customer Type Distribution")
    ax.set_ylabel("Number of Customers")
    for index, value in enumerate(values):
        ax.text(index, value, f"{value:,}", ha="center", va="bottom", fontweight="bold")
    return _save_figure(fig, "customer_type_distribution.png", output_dir)


def plot_average_order_value_by_region(region_table, output_dir: Path = CHARTS_DIR) -> Path:
    """Bar chart of average order value by region."""
    fig, ax = plt.subplots(figsize=CHART_FIGSIZE_WIDE)
    data = region_table.sort_values("Average_Order_Value", ascending=False)
    sns.barplot(data=data, x="Region", y="Average_Order_Value", hue="Region",
                legend=False, palette="rocket", ax=ax)
    ax.set_title("Average Order Value by Region")
    ax.set_xlabel("Region")
    ax.set_ylabel("Average Order Value")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(_currency_formatter))
    return _save_figure(fig, "avg_order_value_by_region.png", output_dir)


def plot_pareto(pareto_results: dict, output_dir: Path = CHARTS_DIR) -> Path:
    """Pareto chart: product revenue bars (top 15) with a cumulative
    revenue-percentage line, marking the point where ~80% of revenue is
    reached."""
    table = pareto_results["pareto_table"].head(15)

    fig, ax1 = plt.subplots(figsize=CHART_FIGSIZE_WIDE)
    ax1.bar(table["Product"], table["Revenue"], color="#3B82F6", label="Revenue")
    ax1.set_xlabel("Product (ranked by revenue)")
    ax1.set_ylabel("Revenue")
    ax1.yaxis.set_major_formatter(mticker.FuncFormatter(_currency_formatter))
    ax1.tick_params(axis="x", rotation=60)

    ax2 = ax1.twinx()
    ax2.plot(table["Product"], table["Cumulative_Revenue_Percent"], color="#DC2626",
              marker="o", linewidth=2, label="Cumulative %")
    ax2.axhline(80, color="#16A34A", linestyle="--", linewidth=1)
    ax2.set_ylabel("Cumulative Revenue %")
    ax2.set_ylim(0, 110)

    pct = pareto_results["percent_of_products_for_80_percent_revenue"]
    ax2.text(len(table) - 1, 83, f"~80% line ({pct:.1f}% of products)",
              color="#16A34A", fontsize=9, ha="right", fontweight="bold")

    ax1.set_title("Pareto Analysis: Product Revenue Concentration")
    return _save_figure(fig, "pareto_analysis.png", output_dir)


def build_executive_dashboard(analysis_results: dict, output_path=None) -> Path:
    """Build a single-image executive dashboard combining headline KPIs
    with monthly revenue, category and regional summaries, suitable for
    an offline demonstration. Every value is read directly from the
    analysis results - nothing is typed in manually."""
    from config import EXECUTIVE_DASHBOARD_PATH

    output_path = output_path or EXECUTIVE_DASHBOARD_PATH
    ensure_directories(output_path.parent)

    summary = analysis_results["summary"]
    monthly = analysis_results["monthly"]["monthly_table"]
    categories = analysis_results["categories"]
    regions = analysis_results["regions"]

    fig = plt.figure(figsize=(16, 10))
    fig.suptitle("SmartMart E-Commerce — Executive Sales Dashboard", fontsize=18, fontweight="bold")

    grid = fig.add_gridspec(3, 3, height_ratios=[0.7, 1.3, 1.3], hspace=0.6, wspace=0.35)

    kpis = [
        ("Total Revenue", _currency_formatter(summary["Total Revenue"])),
        ("Total Orders", f"{summary['Total Orders']:,}"),
        ("Total Customers", f"{summary['Total Customers']:,}"),
        ("Total Quantity Sold", f"{summary['Total Quantity Sold']:,}"),
        ("Avg Order Value", _currency_formatter(summary["Average Order Value"])),
    ]
    kpi_ax = fig.add_subplot(grid[0, :])
    kpi_ax.axis("off")
    for index, (label, value) in enumerate(kpis):
        x = 0.02 + index * 0.20
        kpi_ax.text(x, 0.6, value, fontsize=15, fontweight="bold", color="#1F4E78",
                     transform=kpi_ax.transAxes)
        kpi_ax.text(x, 0.15, label, fontsize=10, color="#444444", transform=kpi_ax.transAxes)

    monthly_reset = monthly.reset_index(drop=True)
    monthly_positions = range(len(monthly_reset))

    ax_monthly = fig.add_subplot(grid[1, :])
    ax_monthly.plot(monthly_positions, monthly_reset["Revenue"], marker="o", color="#2563EB", linewidth=2)
    ax_monthly.set_title("Monthly Revenue Trend")
    ax_monthly.set_xticks(list(monthly_positions))
    ax_monthly.set_xticklabels(monthly_reset["Period"], rotation=45, ha="right", fontsize=8)
    ax_monthly.yaxis.set_major_formatter(mticker.FuncFormatter(_currency_formatter))

    ax_category = fig.add_subplot(grid[2, 0])
    cat_sorted = categories.sort_values("Revenue", ascending=False)
    ax_category.bar(cat_sorted["Category"], cat_sorted["Revenue"], color="#0EA5E9")
    ax_category.set_title("Revenue by Category", fontsize=11)
    ax_category.tick_params(axis="x", rotation=45, labelsize=7)
    ax_category.yaxis.set_major_formatter(mticker.FuncFormatter(_currency_formatter))

    ax_region = fig.add_subplot(grid[2, 1])
    reg_sorted = regions.sort_values("Revenue", ascending=False)
    ax_region.bar(reg_sorted["Region"], reg_sorted["Revenue"], color="#7C3AED")
    ax_region.set_title("Revenue by Region", fontsize=11)
    ax_region.tick_params(axis="x", rotation=45, labelsize=7)
    ax_region.yaxis.set_major_formatter(mticker.FuncFormatter(_currency_formatter))

    ax_payment = fig.add_subplot(grid[2, 2])
    payments = analysis_results["payments"].sort_values("Orders", ascending=False)
    colors = sns.color_palette("Set2", n_colors=len(payments))
    ax_payment.pie(payments["Orders"], labels=payments["Payment_Mode"], autopct="%1.0f%%",
                   colors=colors, textprops={"fontsize": 7})
    ax_payment.set_title("Payment Mix", fontsize=11)

    ensure_directories(output_path.parent)
    fig.savefig(output_path, dpi=CHART_DPI, bbox_inches="tight")
    plt.close(fig)
    logger.info("Executive dashboard saved: %s", output_path)
    return output_path


def generate_all_charts(analysis_results: dict, output_dir: Path = CHARTS_DIR) -> list[Path]:
    """Generate the full required set of charts (plus a few useful
    extras) from the analysis results dictionary."""
    logger.info("Generating charts...")

    saved_paths = [
        plot_monthly_revenue(analysis_results["monthly"]["monthly_table"], output_dir),
        plot_revenue_by_category(analysis_results["categories"], output_dir),
        plot_top_products(analysis_results["products"]["top_by_revenue"], output_dir),
        plot_regional_sales(analysis_results["regions"], output_dir),
        plot_payment_distribution(analysis_results["payments"], output_dir),
        plot_top_customers(analysis_results["customers"]["top_customers"], output_dir),
        plot_customer_type_distribution(analysis_results["customers"], output_dir),
        plot_average_order_value_by_region(analysis_results["regions"], output_dir),
        plot_pareto(analysis_results["pareto"], output_dir),
    ]

    saved_paths.append(build_executive_dashboard(analysis_results))

    logger.info("Generated %d chart(s).", len(saved_paths))
    return saved_paths
