"""
dynamic_analytics.py

Schema-driven analytics. Every function receives the (already filtered)
active DataFrame plus its SchemaResult and only reports what the data
supports: a KPI whose required column is missing is simply not returned, so
the UI never shows an invented or misleading number.

Nothing in here contains a SmartMart column name or a fixed KPI value.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import numpy as np
import pandas as pd

from src.schema_detection import SchemaResult


# =============================================================== filters
@dataclass
class FilterSpec:
    date_col: str | None = None
    date_range: tuple[date, date] | None = None
    categorical: dict[str, list] = field(default_factory=dict)      # column -> selected values
    numeric: dict[str, tuple[float, float]] = field(default_factory=dict)

    def is_active(self) -> bool:
        return bool(self.date_range or any(self.categorical.values()) or self.numeric)


def apply_filters(df: pd.DataFrame, spec: FilterSpec | None) -> pd.DataFrame:
    """Return a filtered COPY (the active dataset is never modified)."""
    if spec is None or df.empty:
        return df.copy()
    mask = pd.Series(True, index=df.index)
    if spec.date_col and spec.date_col in df.columns and spec.date_range:
        s = pd.to_datetime(df[spec.date_col], errors="coerce")
        lo, hi = (pd.Timestamp(spec.date_range[0]), pd.Timestamp(spec.date_range[1]) + pd.Timedelta(days=1))
        mask &= (s >= lo) & (s < hi)
    for col, values in spec.categorical.items():
        if values and col in df.columns:
            mask &= df[col].astype("object").isin(values)
    for col, (lo, hi) in spec.numeric.items():
        if col in df.columns:
            mask &= df[col].between(lo, hi)
    return df[mask].copy()


def describe_filters(spec: FilterSpec | None) -> str:
    if spec is None or not spec.is_active():
        return "No filters applied (all rows)."
    parts = []
    if spec.date_range:
        parts.append(f"{spec.date_col} from {spec.date_range[0]} to {spec.date_range[1]}")
    for c, v in spec.categorical.items():
        if v:
            parts.append(f"{c} in [{', '.join(map(str, v[:6]))}{'...' if len(v) > 6 else ''}]")
    for c, (lo, hi) in spec.numeric.items():
        parts.append(f"{c} between {lo:g} and {hi:g}")
    return "Filters: " + "; ".join(parts) + "."


def filter_candidates(df: pd.DataFrame, schema: SchemaResult, max_cat: int = 3, max_num: int = 2) -> dict:
    """Which columns to offer as filters (roles first, then other categoricals)."""
    date_col = schema.roles.get("date")
    date_col = date_col if date_col in df.columns else (schema.columns_of("datetime") or [None])[0]
    cats: list[str] = []
    for role in ("location", "category", "product"):
        c = schema.roles.get(role)
        if c and c in df.columns and c not in cats and 1 < df[c].nunique() <= 200:
            cats.append(c)
    for c in schema.columns_of("categorical"):
        if c not in cats and 1 < df[c].nunique() <= 30:
            cats.append(c)
    nums: list[str] = []
    rev = schema.roles.get("revenue")
    if rev and rev in df.columns:
        nums.append(rev)
    for c in schema.columns_of("numeric"):
        if c not in nums and df[c].nunique() > 1:
            nums.append(c)
    return {"date": date_col, "categorical": cats[:max_cat + 2], "numeric": nums[:max_num]}


# =============================================================== helpers
def _col(schema: SchemaResult, df: pd.DataFrame, role: str) -> str | None:
    c = schema.roles.get(role)
    if c == "__derived__" or c is None or c not in df.columns:
        return None
    return c


def revenue(df: pd.DataFrame, schema: SchemaResult) -> pd.Series | None:
    """Revenue per row: the mapped column, or quantity x price when derived."""
    c = _col(schema, df, "revenue")
    if c is not None and pd.api.types.is_numeric_dtype(df[c]):
        return df[c]
    q, p = _col(schema, df, "quantity"), _col(schema, df, "price")
    if schema.roles.get("revenue") == "__derived__" and q and p:
        return df[q] * df[p]
    return None


def has_sales_shape(df: pd.DataFrame, schema: SchemaResult) -> bool:
    return revenue(df, schema) is not None and schema.confidence.get("revenue", 0) >= 0.5 \
        and schema.dataset_type == "sales"


def _num(x) -> float:
    return float(x) if pd.notna(x) else float("nan")


def kpi(label: str, value, kind: str = "number", help: str = "") -> dict:
    return {"label": label, "value": value, "kind": kind, "help": help}


# =============================================================== KPIs
def compute_kpis(df: pd.DataFrame, schema: SchemaResult) -> list[dict]:
    """Applicable KPIs for the active data. Empty list when nothing applies."""
    if df is None or df.empty:
        return []
    if has_sales_shape(df, schema):
        return _sales_kpis(df, schema)
    if schema.dataset_type == "hr":
        k = _hr_kpis(df)
        if k:
            return k
    if schema.dataset_type == "banking":
        k = _banking_kpis(df, schema)
        if k:
            return k
    if schema.dataset_type == "inventory":
        k = _inventory_kpis(df)
        if k:
            return k
    return _generic_kpis(df, schema)


def _sales_kpis(df, schema) -> list[dict]:
    rev = revenue(df, schema)
    oid, cust = _col(schema, df, "order_id"), _col(schema, df, "customer")
    qty, price, prod = _col(schema, df, "quantity"), _col(schema, df, "price"), _col(schema, df, "product")
    total = rev.sum()
    out = [kpi("Total Revenue", _num(total), "money", f"Sum of {schema.roles['revenue']}")]
    orders = int(df[oid].nunique()) if oid else int(len(df))
    out.append(kpi("Total Orders" if oid else "Total Transactions", orders, "int",
                   f"Distinct {oid}" if oid else "Row count (no order id column found)"))
    if qty:
        out.append(kpi("Total Units Sold", _num(df[qty].sum()), "int", f"Sum of {qty}"))
    if orders:
        if oid:
            aov = rev.groupby(df[oid]).sum().mean()
        else:
            aov = total / orders
        out.append(kpi("Average Order Value", _num(aov), "money", "Revenue per order"))
    if qty and df[qty].sum() > 0:
        out.append(kpi("Avg Selling Price", _num(total / df[qty].sum()), "money", "Revenue / units sold"))
    elif price:
        out.append(kpi("Avg Selling Price", _num(df[price].mean()), "money", f"Mean of {price}"))
    if cust:
        out.append(kpi("Total Customers", int(df[cust].nunique()), "int", f"Distinct {cust}"))
    if prod:
        out.append(kpi("Products Sold", int(df[prod].nunique()), "int", f"Distinct {prod}"))
    return out


def _find(df, *keywords, numeric=False) -> str | None:
    for c in df.columns:
        n = "".join(ch for ch in str(c).lower() if ch.isalnum())
        if any(k in n for k in keywords) and (not numeric or pd.api.types.is_numeric_dtype(df[c])):
            return c
    return None


def _hr_kpis(df) -> list[dict]:
    out = [kpi("Employee Count", int(len(df)), "int", "Rows in the data")]
    sal = _find(df, "salary", "pay", "wage", numeric=True)
    if sal:
        out += [kpi("Average Salary", _num(df[sal].mean()), "money", f"Mean of {sal}"),
                kpi("Median Salary", _num(df[sal].median()), "money", f"Median of {sal}")]
    att = _find(df, "attrition", "left", "resign", "churn")
    if att:
        s = df[att]
        flag = s.astype(str).str.strip().str.lower().isin(["yes", "y", "true", "1", "left"])
        if s.dropna().astype(str).str.strip().str.lower().isin(["yes", "y", "true", "1", "left", "no", "n", "false", "0", "stayed"]).all():
            out.append(kpi("Attrition Rate", float(flag.mean() * 100), "percent", f"Share of rows where {att} is yes/true"))
    dep = _find(df, "department", "dept")
    if dep:
        out.append(kpi("Departments", int(df[dep].nunique()), "int", f"Distinct {dep}"))
    return out if len(out) > 1 else []


def _banking_kpis(df, schema) -> list[dict]:
    amt = _find(df, "amount", "value", numeric=True)
    out = [kpi("Transaction Volume", int(len(df)), "int", "Number of transactions (rows)")]
    if amt:
        out += [kpi("Transaction Amount", _num(df[amt].sum()), "money", f"Sum of {amt}"),
                kpi("Average Transaction", _num(df[amt].mean()), "money", f"Mean of {amt}")]
    acc = _find(df, "account")
    if acc:
        out.append(kpi("Active Accounts", int(df[acc].nunique()), "int", f"Distinct {acc}"))
    return out if len(out) > 1 else []


def _inventory_kpis(df) -> list[dict]:
    stock = _find(df, "stock", "onhand", "inventory", "quantity", numeric=True)
    if not stock:
        return []
    out = [kpi("Items Tracked", int(len(df)), "int", "Rows in the data"),
           kpi("Total Stock Units", _num(df[stock].sum()), "int", f"Sum of {stock}"),
           kpi("Average Stock Level", _num(df[stock].mean()), "number", f"Mean of {stock}")]
    reorder = _find(df, "reorder", numeric=True)
    if reorder and reorder != stock:
        out.append(kpi("Items Below Reorder Level", int((df[stock] < df[reorder]).sum()), "int",
                       f"Rows where {stock} < {reorder}"))
    return out


def _generic_kpis(df, schema) -> list[dict]:
    nums = schema.columns_of("numeric")
    out = [kpi("Records", int(len(df)), "int", "Rows in the active data"),
           kpi("Columns", int(df.shape[1]), "int"),
           kpi("Numeric Columns", len(nums), "int"),
           kpi("Categorical Columns", len(schema.columns_of("categorical")), "int")]
    miss = float(df.isna().sum().sum()) / max(df.size, 1) * 100
    out.append(kpi("Missing Cells", miss, "percent", "Share of empty cells"))
    return out


# =============================================================== breakdowns
def breakdown(df: pd.DataFrame, by: str, value: str | pd.Series | None = None, agg: str = "sum",
              top: int | None = None, ascending: bool = False) -> pd.DataFrame:
    """Group ``df`` by column ``by``. ``value`` may be a column name, a Series
    aligned to df (e.g. derived revenue), or None for row counts."""
    if df.empty or by not in df.columns:
        return pd.DataFrame(columns=[by, "Value", "Share %", "Rows"])
    key = df[by].astype("object").fillna("(missing)")
    if value is None:
        g = key.groupby(key).size().rename("Value").to_frame()
        g["Rows"] = g["Value"]
    else:
        v = df[value] if isinstance(value, str) else value
        g = v.groupby(key).agg(agg).rename("Value").to_frame()
        g["Rows"] = key.groupby(key).size()
    total = g["Value"].sum() if agg in ("sum", "count") or value is None else np.nan
    g["Share %"] = (g["Value"] / total * 100).round(2) if total and not pd.isna(total) else np.nan
    g = g.reset_index().rename(columns={"index": by})
    g.columns = [by if i == 0 else c for i, c in enumerate(g.columns)]
    g = g.sort_values("Value", ascending=ascending).reset_index(drop=True)
    return g.head(top) if top else g


def revenue_breakdown(df, schema, role: str, top: int | None = None, ascending=False) -> pd.DataFrame | None:
    col, rev = _col(schema, df, role), revenue(df, schema)
    if col is None or rev is None or df.empty:
        return None
    out = breakdown(df, col, rev, "sum", top, ascending)
    return out.rename(columns={"Value": "Revenue"})


def monthly_trend(df, schema, value: str | None = None, agg: str = "sum") -> pd.DataFrame | None:
    """Monthly series. value=None -> revenue when available."""
    dcol = _col(schema, df, "date")
    if dcol is None:
        dc = schema.columns_of("datetime")
        dcol = dc[0] if dc else None
    if dcol is None or df.empty:
        return None
    d = pd.to_datetime(df[dcol], errors="coerce")
    series = revenue(df, schema) if value is None else (df[value] if value in df.columns else None)
    if value is None and series is None:
        series = pd.Series(1, index=df.index)
        agg, label = "sum", "Records"
    else:
        label = "Revenue" if value is None else value
    if series is None:
        return None
    ok = d.notna()
    if ok.sum() == 0:
        return None
    m = series[ok].groupby(d[ok].dt.to_period("M")).agg(agg)
    out = m.rename(label).reset_index()
    out.columns = ["Month", label]
    out["Month"] = out["Month"].dt.to_timestamp()
    out["MoM Growth %"] = (out[label].pct_change() * 100).round(2).replace([np.inf, -np.inf], np.nan)
    return out


def customer_behaviour(df, schema) -> dict | None:
    cust = _col(schema, df, "customer")
    if cust is None or df.empty:
        return None
    oid, rev = _col(schema, df, "order_id"), revenue(df, schema)
    orders = df.groupby(cust)[oid].nunique() if oid else df.groupby(cust).size()
    res = {"customers": int(orders.shape[0]),
           "avg_orders_per_customer": _num(orders.mean()),
           "repeat_customers": int((orders >= 2).sum()),
           "repeat_rate_pct": _num((orders >= 2).mean() * 100)}
    if rev is not None:
        spend = rev.groupby(df[cust]).sum().sort_values(ascending=False)
        res["avg_spend_per_customer"] = _num(spend.mean())
        res["top_customers"] = spend.head(10).rename("Revenue").reset_index()
        k = max(int(np.ceil(len(spend) * 0.1)), 1)
        res["top10pct_revenue_share"] = _num(spend.head(k).sum() / spend.sum() * 100) if spend.sum() else float("nan")
    res["orders_distribution"] = orders.value_counts().sort_index().rename_axis("Orders").reset_index(name="Customers")
    return res


# =============================================================== generic stats
def numeric_summary(df: pd.DataFrame) -> pd.DataFrame:
    nums = df.select_dtypes(include="number")
    nums = nums.loc[:, [c for c in nums.columns if nums[c].notna().any()]]
    if nums.empty:
        return pd.DataFrame()
    d = nums.describe().T
    d["missing"] = nums.isna().sum()
    d["skew"] = nums.skew()
    return d.round(4).reset_index().rename(columns={"index": "Column"})


def category_distribution(df: pd.DataFrame, col: str, top: int = 15) -> pd.DataFrame:
    if col not in df.columns or df.empty:
        return pd.DataFrame(columns=[col, "Count", "Share %"])
    vc = df[col].astype("object").fillna("(missing)").value_counts()
    out = vc.head(top).rename("Count").rename_axis(col).reset_index()
    out["Share %"] = (out["Count"] / len(df) * 100).round(2)
    return out


def correlations(df: pd.DataFrame, min_rows: int = 5) -> pd.DataFrame | None:
    nums = df.select_dtypes(include="number")
    nums = nums.loc[:, [c for c in nums.columns if nums[c].nunique() > 1]]
    if nums.shape[1] < 2 or len(nums) < min_rows:
        return None
    return nums.corr()


def top_correlations(df: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    corr = correlations(df)
    if corr is None:
        return pd.DataFrame(columns=["Column A", "Column B", "Correlation"])
    pairs = []
    cols = list(corr.columns)
    for i, a in enumerate(cols):
        for b in cols[i + 1:]:
            v = corr.loc[a, b]
            if pd.notna(v):
                pairs.append((a, b, round(float(v), 3)))
    pairs.sort(key=lambda t: abs(t[2]), reverse=True)
    return pd.DataFrame(pairs[:n], columns=["Column A", "Column B", "Correlation"])


def outlier_summary(df: pd.DataFrame, factor: float = 1.5) -> pd.DataFrame:
    from src.data_cleaning import outlier_report
    return outlier_report(df, factor)


def group_stat(df: pd.DataFrame, group_col: str, measure: str, agg: str = "mean", top: int = 15) -> pd.DataFrame:
    if group_col not in df.columns or measure not in df.columns or df.empty:
        return pd.DataFrame()
    g = df.groupby(df[group_col].astype("object").fillna("(missing)"))[measure].agg(["count", agg]).reset_index()
    g.columns = [group_col, "Count", f"{agg} of {measure}"]
    return g.sort_values(f"{agg} of {measure}", ascending=False).head(top).round(4)


# =============================================================== insights
def generate_insights(df: pd.DataFrame, schema: SchemaResult, filters_text: str = "") -> dict:
    """Findings, trends, best/worst, anomalies, quality issues and
    recommendations - each string carries the numbers it was derived from.
    Returns sufficient=False (and no fabricated findings) for tiny data."""
    from src import data_cleaning as C
    res = {"sufficient": False, "findings": [], "trends": [], "top": [], "bottom": [],
           "unusual": [], "quality": [], "recommendations": [], "note": ""}
    if df is None or df.empty:
        res["note"] = "No data in the active dataset."
        return res
    if len(df) < 5:
        res["note"] = f"Only {len(df)} row(s): too few to draw reliable conclusions."
        return res
    res["sufficient"] = True
    cur = ""
    findings: list[str] = []

    # ---- quality (valid for every dataset)
    miss = C.missing_report(df)
    miss = miss[miss["Missing"] > 0]
    total_missing_pct = df.isna().sum().sum() / max(df.size, 1) * 100
    if len(miss):
        top_m = miss.iloc[0]
        res["quality"].append(f"{int(df.isna().sum().sum()):,} missing cells ({total_missing_pct:.2f}% of all cells); "
                              f"worst column: {top_m['Column']} ({top_m['Missing %']:.2f}% missing).")
        if total_missing_pct >= 1:
            res["recommendations"].append(
                f"Review data capture: {total_missing_pct:.1f}% of cells are empty, so totals may understate reality.")
    dups = int(df.duplicated().sum())
    if dups:
        res["quality"].append(f"{dups:,} fully duplicated row(s) ({dups / len(df) * 100:.2f}%); totals may be inflated.")
        res["recommendations"].append("Remove or investigate duplicate records on the Data Preparation page before reporting totals.")
    inv = C.invalid_report(df, schema)
    for _, r in inv.iterrows():
        res["quality"].append(f"{r['Rows']:,} row(s): {r['Issue'].lower()} in '{r['Column']}'.")

    rev = revenue(df, schema)
    sales = has_sales_shape(df, schema)

    if sales:
        total = rev.sum()
        findings.append(f"Total revenue is {total:,.2f} across {len(df):,} records "
                        f"(average {rev.mean():,.2f} per record).")
        for role, nice in (("category", "category"), ("product", "product"), ("location", "location")):
            b = revenue_breakdown(df, schema, role)
            if b is None or len(b) < 2:
                continue
            name = b.columns[0]
            hi, lo = b.iloc[0], b.iloc[-1]
            res["top"].append(f"Top {nice} by revenue: {hi[name]} = {hi['Revenue']:,.2f} ({hi['Share %']:.1f}% of total).")
            res["bottom"].append(f"Lowest {nice} by revenue: {lo[name]} = {lo['Revenue']:,.2f} ({lo['Share %']:.1f}% of total).")
            findings.append(f"{name}: '{hi[name]}' leads with {hi['Share %']:.1f}% of revenue; "
                            f"'{lo[name]}' is lowest at {lo['Share %']:.1f}%.")
            if hi["Share %"] >= 40:
                res["recommendations"].append(
                    f"Revenue is concentrated in {name} '{hi[name]}' ({hi['Share %']:.1f}%): "
                    f"protect it and look for growth elsewhere to reduce dependency.")
            if len(b) >= 4 and lo["Share %"] < 3:
                res["recommendations"].append(
                    f"Review {nice} '{lo[name]}' ({lo['Share %']:.1f}% of revenue): reposition, bundle or de-prioritise.")
        mt = monthly_trend(df, schema)
        if mt is not None and len(mt) >= 3:
            best, worst = mt.loc[mt.iloc[:, 1].idxmax()], mt.loc[mt.iloc[:, 1].idxmin()]
            first, last = mt.iloc[0, 1], mt.iloc[-1, 1]
            res["trends"].append(f"Best month: {best['Month']:%b %Y} ({best['Revenue']:,.2f}); weakest: "
                                 f"{worst['Month']:%b %Y} ({worst['Revenue']:,.2f}).")
            if first:
                chg = (last - first) / first * 100
                res["trends"].append(f"Monthly revenue moved from {first:,.2f} ({mt.iloc[0]['Month']:%b %Y}) to "
                                     f"{last:,.2f} ({mt.iloc[-1]['Month']:%b %Y}): {chg:+.1f}%.")
            g = mt["MoM Growth %"].dropna()
            if len(g):
                res["trends"].append(f"Average month-over-month change is {g.mean():+.2f}% "
                                     f"(range {g.min():+.1f}% to {g.max():+.1f}%). "
                                     "The first and last months may be partial.")
            findings.append(res["trends"][0])
        cb = customer_behaviour(df, schema)
        if cb:
            findings.append(f"{cb['repeat_rate_pct']:.1f}% of {cb['customers']:,} customers placed 2+ orders "
                            f"(average {cb['avg_orders_per_customer']:.2f} orders per customer).")
            if cb["repeat_rate_pct"] < 30:
                res["recommendations"].append(
                    f"Only {cb['repeat_rate_pct']:.1f}% of customers repeat: consider retention campaigns for one-time buyers.")
    else:
        nums = schema.columns_of("numeric")
        findings.append(f"{len(df):,} records, {df.shape[1]} columns ({len(nums)} numeric, "
                        f"{len(schema.columns_of('categorical'))} categorical).")
        for c in nums[:3]:
            s = df[c].dropna()
            if len(s):
                findings.append(f"{c}: mean {s.mean():,.3f}, median {s.median():,.3f}, min {s.min():,.3f}, max {s.max():,.3f}.")
        for c in schema.columns_of("categorical")[:2]:
            d = category_distribution(df, c, 3)
            if len(d):
                findings.append(f"{c}: most common value '{d.iloc[0][c]}' ({d.iloc[0]['Share %']:.1f}% of records).")
                res["top"].append(f"Most frequent {c}: {d.iloc[0][c]} ({int(d.iloc[0]['Count']):,} records).")
                if df[c].nunique() > 1:
                    last = category_distribution(df, c, 1000).iloc[-1]
                    res["bottom"].append(f"Least frequent {c}: {last[c]} ({int(last['Count']):,} records).")
        tc = top_correlations(df, 1)
        if len(tc):
            r = tc.iloc[0]
            findings.append(f"Strongest numeric relationship: {r['Column A']} vs {r['Column B']} (r = {r['Correlation']:+.2f}); "
                            "correlation does not prove causation.")
        dcols = schema.columns_of("datetime")
        if dcols and nums:
            mt = monthly_trend(df, schema, value=nums[0], agg="mean")
            if mt is not None and len(mt) >= 3:
                v = mt.iloc[:, 1]
                res["trends"].append(f"Monthly mean of {nums[0]} ranges from {v.min():,.3f} to {v.max():,.3f}.")

    # ---- anomalies (all datasets)
    out = C.outlier_report(df)
    for _, r in out[out["Outliers"] > 0].sort_values("Outlier %", ascending=False).head(3).iterrows():
        res["unusual"].append(f"{int(r['Outliers']):,} outlier values ({r['Outlier %']:.1f}%) in '{r['Column']}' "
                              f"outside [{r['Lower bound']:,.2f}, {r['Upper bound']:,.2f}] (IQR rule). "
                              "Outliers are not necessarily errors.")
    res["findings"] = (findings + res["top"] + res["bottom"] + res["unusual"] + res["quality"])[:max(5, len(findings))][:8]
    if len(res["findings"]) < 5:
        res["findings"] = (findings + res["trends"] + res["top"] + res["bottom"] + res["unusual"] + res["quality"])[:5]
    if not res["recommendations"]:
        res["recommendations"].append("No data-driven issue crossed the alert thresholds; keep monitoring the trends above.")
    res["note"] = filters_text
    return res
