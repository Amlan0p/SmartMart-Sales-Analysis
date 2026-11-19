"""
report_export.py

Builds every downloadable artefact as bytes (nothing is written into the
project folder): CSV exports, generic Excel report, data-quality report,
analytical summary, business-insight text and - when the active data has
the full SmartMart schema - the project's ORIGINAL multi-sheet Excel report
(src/excel_report.py is reused, not rewritten).
"""

from __future__ import annotations

import io
import tempfile
from datetime import datetime
from pathlib import Path

import pandas as pd

import config
from src import data_cleaning as C
from src import dynamic_analytics as A
from src.schema_detection import SchemaResult

SMARTMART_COLUMNS = list(config.REQUIRED_COLUMNS) + ["Year", "Month", "Month_Name", "Quarter",
                                                       "Order_Value", "Customer_Type"]
EXCEL_MAX_ROWS = 1_048_000


def csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8-sig")  # BOM so Excel on Windows reads UTF-8


def _sheet(name: str) -> str:
    bad = '[]:*?/\\'
    return "".join("_" if ch in bad else ch for ch in name)[:31] or "Sheet"


def _excel_safe(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for c in out.columns:
        if isinstance(out[c].dtype, pd.DatetimeTZDtype):
            out[c] = out[c].dt.tz_localize(None)
        elif out[c].dtype == "object":
            out[c] = out[c].map(lambda v: v if v is None or isinstance(v, (str, int, float, bool, pd.Timestamp)) else str(v))
    return out


def excel_bytes(sheets: dict[str, pd.DataFrame]) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        used = set()
        for name, frame in sheets.items():
            if frame is None:
                continue
            sn = _sheet(name)
            i = 1
            while sn in used:
                i += 1
                sn = _sheet(name)[:28] + f"_{i}"
            used.add(sn)
            f = _excel_safe(frame.head(EXCEL_MAX_ROWS))
            f.to_excel(xw, sheet_name=sn, index=False)
            ws = xw.sheets[sn]
            ws.freeze_panes = "A2"
            for idx, col in enumerate(f.columns, start=1):
                width = min(max(len(str(col)), *(len(str(v)) for v in f[col].head(200))) + 2, 48) if len(f) else len(str(col)) + 2
                ws.column_dimensions[ws.cell(row=1, column=idx).column_letter].width = width
    return buf.getvalue()


# ------------------------------------------------------------ quality report
def quality_report_bytes(df: pd.DataFrame, schema: SchemaResult, dataset_name: str = "") -> bytes:
    q = C.quality_score(df, schema)
    summary = pd.DataFrame({"Item": ["Dataset", "Generated", "Rows", "Columns", "Quality score (0-100)", "Rating"]
                            + list(q["components"]),
                            "Value": [dataset_name, datetime.now().strftime("%Y-%m-%d %H:%M"), len(df), df.shape[1],
                                      q["score"], q["label"]] + list(q["components"].values())})
    dup = C.duplicate_report(df)
    return excel_bytes({
        "Summary": summary,
        "Missing values": C.missing_report(df),
        "Duplicate rows": dup["examples"] if len(dup["examples"]) else pd.DataFrame({"Info": ["No duplicate rows"]}),
        "Invalid data": C.invalid_report(df, schema),
        "Outliers (IQR)": C.outlier_report(df),
        "Data types": C.dtype_report(df, schema),
    })


# ------------------------------------------------------------ text reports
def kpi_frame(kpis: list[dict]) -> pd.DataFrame:
    return pd.DataFrame([{"KPI": k["label"], "Value": k["value"], "Definition": k["help"]} for k in kpis])


def insights_text(ins: dict, dataset_name: str, filters_text: str = "") -> str:
    lines = [f"BUSINESS INSIGHTS - {dataset_name}", f"Generated: {datetime.now():%Y-%m-%d %H:%M}", filters_text, ""]
    if not ins.get("sufficient"):
        lines.append(ins.get("note") or "Not enough data for insights.")
        return "\n".join(lines)
    for title, key in (("KEY FINDINGS", "findings"), ("TRENDS", "trends"), ("HIGHEST PERFORMERS", "top"),
                       ("LOWEST PERFORMERS", "bottom"), ("UNUSUAL OBSERVATIONS", "unusual"),
                       ("DATA-QUALITY ISSUES", "quality"), ("RECOMMENDED ACTIONS", "recommendations")):
        if ins.get(key):
            lines.append(title)
            lines += [f"  {i}. {t}" for i, t in enumerate(ins[key], 1)]
            lines.append("")
    lines.append("All figures were calculated from the active (filtered) dataset.")
    return "\n".join(lines)


def analytical_summary_text(df: pd.DataFrame, schema: SchemaResult, kpis: list[dict], ins: dict,
                            dataset_name: str, filters_text: str, currency: str = "") -> str:
    out = [f"# Analytical summary - {dataset_name}", f"_Generated {datetime.now():%Y-%m-%d %H:%M}_", "",
           f"- Rows analysed: {len(df):,}", f"- Columns: {df.shape[1]}",
           f"- Detected dataset type: {schema.dataset_type}", f"- {filters_text}", ""]
    if kpis:
        out += ["## KPIs", ""] + [f"- **{k['label']}**: {_fmt(k, currency)}" for k in kpis] + [""]
    nums = A.numeric_summary(df)
    if not nums.empty:
        out += ["## Numeric columns", "", nums[["Column", "count", "mean", "min", "50%", "max"]].to_markdown(index=False)
                if _has_tabulate() else nums[["Column", "count", "mean", "min", "50%", "max"]].to_string(index=False), ""]
    out += ["## Insights", "", insights_text(ins, dataset_name, filters_text)]
    return "\n".join(out)


def _has_tabulate() -> bool:
    try:
        import tabulate  # noqa: F401
        return True
    except ImportError:
        return False


def _fmt(k: dict, currency: str = "") -> str:
    v = k["value"]
    if isinstance(v, float) and v != v:
        return "n/a"
    if k["kind"] == "money":
        return f"{currency}{v:,.2f}"
    if k["kind"] == "percent":
        return f"{v:.2f}%"
    if k["kind"] == "int":
        return f"{int(round(v)):,}"
    return f"{v:,.2f}" if isinstance(v, float) else str(v)


# ------------------------------------------------------------ Excel reports
def generic_excel_report_bytes(df: pd.DataFrame, schema: SchemaResult, dataset_name: str,
                               filters_text: str, ins: dict | None = None) -> bytes:
    kpis = A.compute_kpis(df, schema)
    ins = ins or A.generate_insights(df, schema, filters_text)
    sheets: dict[str, pd.DataFrame] = {
        "Summary": pd.concat([pd.DataFrame({"KPI": ["Dataset", "Filters"], "Value": [dataset_name, filters_text],
                                            "Definition": ["", ""]}), kpi_frame(kpis)], ignore_index=True)}
    if A.has_sales_shape(df, schema):
        for role in ("category", "product", "location"):
            b = A.revenue_breakdown(df, schema, role)
            if b is not None:
                sheets[f"Revenue by {role}"] = b
    else:
        for c in schema.columns_of("categorical")[:3]:
            sheets[f"Distribution {c}"] = A.category_distribution(df, c, 50)
    mt = A.monthly_trend(df, schema) if A.has_sales_shape(df, schema) or schema.columns_of("datetime") else None
    if mt is not None:
        sheets["Monthly trend"] = mt
    ns = A.numeric_summary(df)
    if not ns.empty:
        sheets["Numeric summary"] = ns
    corr = A.correlations(df)
    if corr is not None:
        sheets["Correlations"] = corr.round(4).reset_index().rename(columns={"index": "Column"})
    if ins.get("sufficient"):
        rows = [(sec, t) for sec in ("findings", "trends", "top", "bottom", "unusual", "quality", "recommendations")
                for t in ins.get(sec, [])]
        sheets["Insights"] = pd.DataFrame(rows, columns=["Section", "Insight"])
    sheets["Data quality"] = C.missing_report(df)
    return excel_bytes(sheets)


def can_use_smartmart_report(df: pd.DataFrame) -> bool:
    return all(c in df.columns for c in SMARTMART_COLUMNS) and not df[
        ["Order_ID", "Order_Date", "Sales", "Quantity", "Customer_ID", "Product", "Month", "Year"]].isna().any().any()


def smartmart_excel_report_bytes(df: pd.DataFrame) -> bytes:
    """The project's original 10-sheet report, built by the existing
    ``src.excel_report`` on the (filtered) data. Requires the full schema."""
    from src import analysis, excel_report, insights
    if not can_use_smartmart_report(df) or df.empty:
        raise ValueError("The active data does not have the full SmartMart schema.")
    work = df.copy()
    results = analysis.run_full_analysis(work)
    with tempfile.TemporaryDirectory() as tmp:
        path = excel_report.build_excel_report(results, Path(tmp) / "report.xlsx",
                                               findings=insights.build_findings(results))
        return Path(path).read_bytes()


# ------------------------------------------------------------ Power BI assets
def powerbi_assets() -> list[tuple[str, Path]]:
    base = config.POWERBI_DIR
    items = [("Power BI dashboard (.pbix)", base / "SmartMart_Sales_Dashboard_Final.pbix"),
             ("DAX measures", base / "dax" / "measures.dax"),
             ("DAX date table", base / "dax" / "date_table.dax"),
             ("Power BI theme", base / "dashboard_design" / "theme" / "SmartMart_Theme.json"),
             ("Cleaned sales CSV (Power BI source)", config.CLEANED_SALES_DATA_PATH),
             ("Customer segments CSV", config.CUSTOMER_SEGMENTS_PATH),
             ("Product classification CSV", config.PRODUCT_CLASSIFICATION_PATH),
             ("Original pipeline Excel report", config.EXCEL_REPORT_PATH)]
    return [(label, p) for label, p in items if p.is_file()]
