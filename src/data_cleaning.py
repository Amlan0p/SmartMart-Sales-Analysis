"""
data_cleaning.py

Generic, schema-agnostic data-quality reports and cleaning operations.
Every operation takes a DataFrame and returns a NEW DataFrame (plus a short
log line where useful); nothing mutates its input, so the caller can show a
before/after comparison and only apply the result when the user confirms.
(The SmartMart-specific cleaning in preprocessing.py is untouched and still
drives the original pipeline.)
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.schema_detection import SchemaResult


# --------------------------------------------------------------------- reports
def missing_report(df: pd.DataFrame) -> pd.DataFrame:
    n = max(len(df), 1)
    m = df.isna().sum()
    out = pd.DataFrame({"Column": df.columns, "Missing": m.values,
                        "Missing %": (m.values / n * 100).round(2)})
    return out.sort_values("Missing", ascending=False).reset_index(drop=True)


def duplicate_report(df: pd.DataFrame, subset: list[str] | None = None) -> dict:
    dup_mask = df.duplicated(subset=subset, keep="first") if len(df.columns) else pd.Series(dtype=bool)
    return {"duplicate_rows": int(dup_mask.sum()),
            "duplicate_pct": round(float(dup_mask.mean() * 100), 2) if len(df) else 0.0,
            "examples": df[df.duplicated(subset=subset, keep=False)].head(20)}


def dtype_report(df: pd.DataFrame, schema: SchemaResult) -> pd.DataFrame:
    return pd.DataFrame({
        "Column": df.columns,
        "Pandas dtype": [str(df[c].dtype) for c in df.columns],
        "Detected kind": [schema.profiles[c].kind if c in schema.profiles else "?" for c in df.columns],
        "Distinct": [int(df[c].nunique(dropna=True)) for c in df.columns],
    })


def invalid_report(df: pd.DataFrame, schema: SchemaResult) -> pd.DataFrame:
    """Rows/values that are invalid for the column's meaning: negative
    revenue/quantity/price, unparseable dates (NaT in a date column that
    also has values), blank strings and text sitting in numeric columns."""
    rows = []
    for role in ("revenue", "quantity", "price"):
        col = schema.roles.get(role)
        if col and col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
            neg = int((df[col] < 0).sum())
            if neg:
                rows.append({"Column": col, "Issue": "Negative value", "Rows": neg})
    for col in df.columns:
        s = df[col]
        if pd.api.types.is_string_dtype(s) or s.dtype == object:
            blanks = int(s.dropna().astype(str).str.strip().eq("").sum())
            if blanks:
                rows.append({"Column": col, "Issue": "Blank text", "Rows": blanks})
    for col in schema.columns_of("datetime"):
        if col in df.columns:
            bad = int(df[col].isna().sum())
            if bad:
                rows.append({"Column": col, "Issue": "Missing/invalid date", "Rows": bad})
    return pd.DataFrame(rows, columns=["Column", "Issue", "Rows"])


def outlier_report(df: pd.DataFrame, factor: float = 1.5) -> pd.DataFrame:
    rows = []
    for col in df.select_dtypes(include="number").columns:
        s = df[col].dropna()
        if len(s) < 8 or s.nunique() < 4:
            continue
        q1, q3 = s.quantile(0.25), s.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            continue
        lo, hi = q1 - factor * iqr, q3 + factor * iqr
        n = int(((s < lo) | (s > hi)).sum())
        rows.append({"Column": col, "Lower bound": round(float(lo), 4), "Upper bound": round(float(hi), 4),
                     "Outliers": n, "Outlier %": round(n / len(s) * 100, 2)})
    return pd.DataFrame(rows, columns=["Column", "Lower bound", "Upper bound", "Outliers", "Outlier %"])


def quality_score(df: pd.DataFrame, schema: SchemaResult) -> dict:
    """0-100 score with the exact deductions shown, so it is explainable.

    completeness (40): share of non-missing cells
    uniqueness   (25): share of non-duplicated rows
    validity     (20): 1 - invalid values / rows
    consistency  (15): 1 - outlier values / numeric cells (capped)
    """
    if df.empty:
        return {"score": None, "components": {}, "label": "No data"}
    cells = df.shape[0] * df.shape[1]
    completeness = 1 - float(df.isna().sum().sum()) / max(cells, 1)
    uniqueness = 1 - float(df.duplicated().mean())
    inv = invalid_report(df, schema)
    validity = 1 - min(1.0, (int(inv["Rows"].sum()) if len(inv) else 0) / max(len(df), 1))
    out = outlier_report(df)
    num_cells = max(len(df) * max(len(out), 1), 1)
    consistency = 1 - min(1.0, (int(out["Outliers"].sum()) if len(out) else 0) / num_cells * 3)
    comp = {"Completeness (40)": 40 * completeness, "Uniqueness (25)": 25 * uniqueness,
            "Validity (20)": 20 * validity, "Consistency (15)": 15 * consistency}
    score = round(sum(comp.values()), 1)
    label = "Excellent" if score >= 90 else "Good" if score >= 75 else "Fair" if score >= 55 else "Poor"
    return {"score": score, "components": {k: round(v, 1) for k, v in comp.items()}, "label": label}


# ------------------------------------------------------------------ operations
def remove_duplicates(df: pd.DataFrame, subset: list[str] | None = None, keep: str = "first") -> tuple[pd.DataFrame, str]:
    out = df.drop_duplicates(subset=subset, keep=keep).reset_index(drop=True)
    return out, f"Removed {len(df) - len(out):,} duplicate row(s)."


def handle_missing(df: pd.DataFrame, strategy: str, columns: list[str] | None = None,
                   constant=None) -> tuple[pd.DataFrame, str]:
    """strategy: drop_rows | mean | median | mode | constant | ffill | bfill"""
    cols = [c for c in (columns or list(df.columns)) if c in df.columns]
    out = df.copy()
    before = int(out[cols].isna().sum().sum()) if cols else 0
    if strategy == "drop_rows":
        out = out.dropna(subset=cols).reset_index(drop=True)
        return out, f"Dropped {len(df) - len(out):,} row(s) with missing values in {len(cols)} column(s)."
    for c in cols:
        s = out[c]
        if not s.isna().any():
            continue
        if strategy in ("mean", "median"):
            if pd.api.types.is_numeric_dtype(s):
                fill = s.mean() if strategy == "mean" else s.median()
                out[c] = s.fillna(round(fill) if pd.api.types.is_integer_dtype(s) else fill)
        elif strategy == "mode":
            m = s.mode(dropna=True)
            if len(m):
                out[c] = s.fillna(m.iloc[0])
        elif strategy == "constant":
            if constant is None or str(constant) == "":
                raise ValueError("Enter a fill value.")
            try:
                val = pd.to_numeric(constant) if pd.api.types.is_numeric_dtype(s) else (
                    pd.to_datetime(constant) if pd.api.types.is_datetime64_any_dtype(s) else constant)
            except (ValueError, TypeError):
                raise ValueError(f"'{constant}' is not valid for column {c}.")
            out[c] = s.fillna(val)
        elif strategy == "ffill":
            out[c] = s.ffill()
        elif strategy == "bfill":
            out[c] = s.bfill()
        else:
            raise ValueError(f"Unknown strategy: {strategy}")
    after = int(out[cols].isna().sum().sum()) if cols else 0
    return out, f"Filled {before - after:,} missing value(s) using '{strategy}' ({after:,} remain)."


def change_dtype(df: pd.DataFrame, column: str, target: str) -> tuple[pd.DataFrame, str]:
    """target: number | integer | text | date | category | boolean. Values that
    cannot be converted become missing; the count is reported."""
    out = df.copy()
    before_missing = int(out[column].isna().sum())
    s = out[column]
    if target == "number":
        out[column] = pd.to_numeric(s.astype(str).str.replace(",", "", regex=False), errors="coerce") \
            if not pd.api.types.is_numeric_dtype(s) else s
    elif target == "integer":
        num = pd.to_numeric(s, errors="coerce")
        out[column] = num.round().astype("Int64")
    elif target == "text":
        out[column] = s.astype("object").where(s.isna(), s.astype(str))
    elif target == "date":
        out[column] = pd.to_datetime(s, errors="coerce", format="mixed")
    elif target == "category":
        out[column] = s.astype("object")
    elif target == "boolean":
        mapped = s.astype(str).str.strip().str.lower().map(
            {"true": True, "yes": True, "y": True, "1": True, "false": False, "no": False, "n": False, "0": False})
        out[column] = mapped.astype("boolean")
    else:
        raise ValueError(f"Unknown type: {target}")
    lost = int(out[column].isna().sum()) - before_missing
    return out, f"Converted '{column}' to {target}" + (f"; {lost:,} value(s) could not be converted and are now missing." if lost > 0 else ".")


def standardize_categories(df: pd.DataFrame, columns: list[str], case: str = "title",
                           mapping: dict | None = None) -> tuple[pd.DataFrame, str]:
    """Trim, collapse spaces, apply case (title|upper|lower|none) and an
    optional explicit value mapping. Reports how many distinct values merged."""
    out = df.copy()
    merged = 0
    for c in columns:
        s = out[c]
        before = s.nunique(dropna=True)
        t = s.astype("object").where(s.isna(), s.astype(str).str.strip().str.replace(r"\s+", " ", regex=True))
        if case == "title":
            t = t.where(t.isna(), t.astype(str).str.title())
        elif case == "upper":
            t = t.where(t.isna(), t.astype(str).str.upper())
        elif case == "lower":
            t = t.where(t.isna(), t.astype(str).str.lower())
        if mapping:
            t = t.replace(mapping)
        out[c] = t
        merged += before - t.nunique(dropna=True)
    return out, f"Standardised {len(columns)} column(s); {merged:,} distinct value(s) merged."


def remove_invalid(df: pd.DataFrame, schema: SchemaResult, drop_negative: bool = True,
                   drop_missing_dates: bool = False, drop_blank_text: bool = False) -> tuple[pd.DataFrame, str]:
    mask = pd.Series(False, index=df.index)
    if drop_negative:
        for role in ("revenue", "quantity", "price"):
            col = schema.roles.get(role)
            if col and col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
                mask |= df[col] < 0
    if drop_missing_dates:
        for col in schema.columns_of("datetime"):
            if col in df.columns:
                mask |= df[col].isna()
    if drop_blank_text:
        for col in df.columns:
            if pd.api.types.is_string_dtype(df[col]) or df[col].dtype == object:
                mask |= df[col].astype("object").map(lambda v: isinstance(v, str) and v.strip() == "")
    out = df[~mask].reset_index(drop=True)
    return out, f"Removed {int(mask.sum()):,} invalid record(s)."


def remove_outliers(df: pd.DataFrame, columns: list[str], factor: float = 1.5) -> tuple[pd.DataFrame, str]:
    mask = pd.Series(False, index=df.index)
    for c in columns:
        s = df[c]
        q1, q3 = s.quantile(0.25), s.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0 or pd.isna(iqr):
            continue
        mask |= (s < q1 - factor * iqr) | (s > q3 + factor * iqr)
    return df[~mask].reset_index(drop=True), f"Removed {int(mask.sum()):,} outlier row(s) (IQR x {factor})."


def apply_transform(df: pd.DataFrame, column: str, kind: str, new_name: str | None = None) -> tuple[pd.DataFrame, str]:
    """kind: log1p | sqrt | zscore | minmax | round0 | abs. Adds a NEW column
    (the original is kept) unless new_name equals the column."""
    s = pd.to_numeric(df[column], errors="coerce")
    if kind == "log1p":
        if (s.dropna() < -1).any():
            raise ValueError("log1p needs values >= -1.")
        res = np.log1p(s)
    elif kind == "sqrt":
        if (s.dropna() < 0).any():
            raise ValueError("sqrt needs non-negative values.")
        res = np.sqrt(s)
    elif kind == "zscore":
        sd = s.std()
        res = (s - s.mean()) / sd if sd and not pd.isna(sd) else s * np.nan
    elif kind == "minmax":
        rng = s.max() - s.min()
        res = (s - s.min()) / rng if rng else s * 0
    elif kind == "round0":
        res = s.round(0)
    elif kind == "abs":
        res = s.abs()
    else:
        raise ValueError(f"Unknown transformation: {kind}")
    name = (new_name or f"{column}_{kind}").strip()
    out = df.copy()
    out[name] = res
    return out, f"Created '{name}' from '{column}' using {kind}."


def before_after(before: pd.DataFrame, after: pd.DataFrame) -> pd.DataFrame:
    def stats(d):
        return {"Rows": len(d), "Columns": d.shape[1], "Missing cells": int(d.isna().sum().sum()),
                "Duplicate rows": int(d.duplicated().sum()) if d.shape[1] else 0}
    b, a = stats(before), stats(after)
    return pd.DataFrame({"Metric": list(b), "Before": list(b.values()), "After": list(a.values()),
                         "Change": [a[k] - b[k] for k in b]})
