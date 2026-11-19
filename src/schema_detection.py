"""
schema_detection.py

Confidence-based detection of column types and business roles for any
uploaded dataset. Nothing here assumes SmartMart column names; a role is
only reported when it is found, and low-confidence matches are flagged so
the UI can ask the user to confirm a manual mapping.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import pandas as pd

# Role -> keywords (normalised, lower-case, no separators).
ROLE_KEYWORDS: dict[str, list[str]] = {
    "revenue": ["sales", "revenue", "totalamount", "amount", "total", "sale", "turnover"],
    "date": ["orderdate", "transactiondate", "createdat", "date", "timestamp", "datetime", "time"],
    "customer": ["customerid", "clientid", "userid", "customer", "client", "user"],
    "product": ["productname", "product", "item", "sku"],
    "category": ["category", "department", "segment", "type", "class"],
    "location": ["region", "city", "location", "area", "state", "country", "zone"],
    "quantity": ["quantity", "qty", "units", "unitssold", "count"],
    "price": ["unitprice", "price", "sellingprice", "rate", "cost"],
    "order_id": ["orderid", "transactionid", "invoiceid", "invoice", "orderno", "order"],
}

CONFIDENCE_THRESHOLD = 0.6


def _norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(name).lower())


@dataclass
class ColumnProfile:
    name: str
    kind: str  # numeric | datetime | categorical | boolean | identifier | text
    dtype: str
    missing: int
    unique: int


@dataclass
class SchemaResult:
    profiles: dict[str, ColumnProfile] = field(default_factory=dict)
    roles: dict[str, str | None] = field(default_factory=dict)
    confidence: dict[str, float] = field(default_factory=dict)
    dataset_type: str = "generic"

    def uncertain_roles(self) -> list[str]:
        return [r for r, c in self.confidence.items() if 0 < c < CONFIDENCE_THRESHOLD]

    def columns_of(self, kind: str) -> list[str]:
        return [n for n, p in self.profiles.items() if p.kind == kind]


def _looks_like_date(series: pd.Series) -> bool:
    if pd.api.types.is_datetime64_any_dtype(series):
        return True
    if pd.api.types.is_numeric_dtype(series) or pd.api.types.is_bool_dtype(series):
        return False
    sample = series.dropna().astype(str).head(200)
    if sample.empty:
        return False
    if not sample.str.contains(r"\d", regex=True).mean() > 0.9:
        return False
    parsed = pd.to_datetime(sample, errors="coerce", format="mixed")
    return parsed.notna().mean() >= 0.9


def profile_column(series: pd.Series, name: str) -> ColumnProfile:
    n = len(series)
    unique = int(series.nunique(dropna=True))
    if pd.api.types.is_bool_dtype(series):
        kind = "boolean"
    elif _looks_like_date(series):
        kind = "datetime"
    elif pd.api.types.is_numeric_dtype(series):
        # Integer columns whose values are (nearly) all unique are identifiers.
        is_int = pd.api.types.is_integer_dtype(series)
        kind = "identifier" if (is_int and n > 20 and unique / max(n, 1) > 0.95
                                and re.search(r"id$|^id|key|no$", _norm(name))) else "numeric"
    else:
        ratio = unique / max(n, 1)
        if re.search(r"id$|^id|key|code$", _norm(name)) and ratio > 0.5:
            kind = "identifier"
        elif unique <= 50 or ratio < 0.5:
            kind = "categorical"
        else:
            kind = "text"
    return ColumnProfile(name, kind, str(series.dtype), int(series.isna().sum()), unique)


def _score(col: str, keywords: list[str]) -> float:
    n = _norm(col)
    for i, kw in enumerate(keywords):
        if n == kw:
            return 1.0 - 0.02 * i
    for kw in keywords:
        if len(kw) >= 4 and kw in n:
            return 0.65
    return 0.0


def detect_schema(df: pd.DataFrame) -> SchemaResult:
    """Profile every column and assign business roles with confidence."""
    result = SchemaResult()
    if df is None or df.shape[1] == 0:
        return result
    for col in df.columns:
        result.profiles[col] = profile_column(df[col], col)

    allowed_kinds = {
        "revenue": {"numeric"}, "quantity": {"numeric"}, "price": {"numeric"},
        "date": {"datetime"},
        "customer": {"identifier", "categorical", "text"},
        "order_id": {"identifier", "categorical", "text"},
        "product": {"categorical", "text", "identifier"},
        "category": {"categorical"},
        "location": {"categorical"},
    }
    used: set[str] = set()
    for role, keywords in ROLE_KEYWORDS.items():
        best, best_score = None, 0.0
        for col in df.columns:
            if col in used or result.profiles[col].kind not in allowed_kinds[role]:
                continue
            s = _score(col, keywords)
            if s > best_score:
                best, best_score = col, s
        result.roles[role] = best
        result.confidence[role] = round(best_score, 2) if best else 0.0
        if best and best_score >= CONFIDENCE_THRESHOLD:
            used.add(best)

    # Revenue can be derived from quantity * price when no direct column exists.
    if not result.roles.get("revenue") and result.roles.get("quantity") and result.roles.get("price"):
        result.roles["revenue"] = "__derived__"
        result.confidence["revenue"] = 0.5

    result.dataset_type = _classify(df, result)
    return result


def _classify(df: pd.DataFrame, s: SchemaResult) -> str:
    names = " ".join(_norm(c) for c in df.columns)
    if s.roles.get("revenue") and (s.roles.get("product") or s.roles.get("customer")
                                   or s.roles.get("order_id")) \
            and s.confidence.get("revenue", 0) >= CONFIDENCE_THRESHOLD:
        return "sales"
    if any(k in names for k in ("salary", "employee", "attrition", "department")):
        return "hr"
    if any(k in names for k in ("account", "balance", "transaction")):
        return "banking"
    if any(k in names for k in ("stock", "inventory", "reorder", "sku")):
        return "inventory"
    return "generic"


def apply_manual_mapping(schema: SchemaResult, mapping: dict[str, str | None]) -> SchemaResult:
    """Override detected roles with the user's choices (confidence = 1.0)."""
    for role, col in mapping.items():
        if col and col in schema.profiles:
            schema.roles[role] = col
            schema.confidence[role] = 1.0
        elif col in (None, ""):
            schema.roles[role] = None
            schema.confidence[role] = 0.0
    return schema


def coerce_types(df: pd.DataFrame, schema: SchemaResult) -> pd.DataFrame:
    """Return a copy with datetime columns parsed (never mutates input)."""
    out = df.copy()
    for col in schema.columns_of("datetime"):
        out[col] = pd.to_datetime(out[col], errors="coerce", format="mixed")
    return out
