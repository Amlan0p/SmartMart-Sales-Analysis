"""
data_entry.py

Manual data entry: validation / coercion of typed values and construction
of new rows or brand-new empty datasets. Pure pandas - no Streamlit.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.schema_detection import SchemaResult

ENTRY_TYPES = ["text", "integer", "decimal", "date", "boolean", "category"]
_TRUE = {"true", "yes", "y", "1", "t"}
_FALSE = {"false", "no", "n", "0", "f"}


@dataclass
class ColumnSpec:
    name: str
    kind: str  # numeric | datetime | categorical | boolean | identifier | text
    is_integer: bool = False
    choices: list | None = None  # known values for categorical columns


class ValidationError(ValueError):
    """One or more fields failed validation; ``errors`` maps column -> message."""

    def __init__(self, errors: dict[str, str]):
        super().__init__("; ".join(f"{k}: {v}" for k, v in errors.items()))
        self.errors = errors


def is_blank(raw) -> bool:
    return raw is None or (isinstance(raw, str) and raw.strip() == "") or \
        (isinstance(raw, float) and np.isnan(raw))


def coerce_value(spec: ColumnSpec, raw):
    """Convert ``raw`` to the column's type. Blank -> NaN/NaT/None.
    Raises ValueError with a readable message when invalid."""
    if is_blank(raw):
        return pd.NaT if spec.kind == "datetime" else (np.nan if spec.kind == "numeric" else None)
    if spec.kind == "numeric":
        try:
            text = str(raw).replace(",", "").strip()
            value = float(text)
        except ValueError:
            raise ValueError(f"'{raw}' is not a number")
        if not np.isfinite(value):
            raise ValueError("value must be a finite number")
        if spec.is_integer:
            if value != int(value):
                raise ValueError(f"'{raw}' must be a whole number")
            return int(value)
        return value
    if spec.kind == "datetime":
        try:
            ts = pd.to_datetime(raw)
        except (ValueError, TypeError):
            raise ValueError(f"'{raw}' is not a valid date")
        if pd.isna(ts):
            raise ValueError(f"'{raw}' is not a valid date")
        return pd.Timestamp(ts)
    if spec.kind == "boolean":
        if isinstance(raw, (bool, np.bool_)):
            return bool(raw)
        t = str(raw).strip().lower()
        if t in _TRUE:
            return True
        if t in _FALSE:
            return False
        raise ValueError(f"'{raw}' is not a yes/no value")
    return str(raw).strip()


def specs_from_dataframe(df: pd.DataFrame, schema: SchemaResult, max_choices: int = 50) -> list[ColumnSpec]:
    specs = []
    for col in df.columns:
        prof = schema.profiles.get(col)
        kind = prof.kind if prof else "text"
        is_int = pd.api.types.is_integer_dtype(df[col])
        choices = None
        if kind == "categorical":
            vals = df[col].dropna().astype(str).value_counts().index.tolist()[:max_choices]
            choices = sorted(vals)
        specs.append(ColumnSpec(col, kind, is_integer=is_int, choices=choices))
    return specs


def validate_row(specs: list[ColumnSpec], raw_values: dict, allow_blank: bool = True,
                 schema: SchemaResult | None = None) -> dict:
    """Return a dict of coerced values or raise ValidationError."""
    errors: dict[str, str] = {}
    row: dict = {}
    non_negative = set()
    if schema:
        non_negative = {c for r in ("revenue", "quantity", "price")
                        if (c := schema.roles.get(r)) and c != "__derived__"}
    if allow_blank is False or all(is_blank(raw_values.get(s.name)) for s in specs):
        if all(is_blank(raw_values.get(s.name)) for s in specs):
            raise ValidationError({"_row": "Enter at least one value before adding the row."})
    for s in specs:
        raw = raw_values.get(s.name)
        if is_blank(raw) and not allow_blank:
            errors[s.name] = "required"
            continue
        try:
            value = coerce_value(s, raw)
        except ValueError as exc:
            errors[s.name] = str(exc)
            continue
        if s.name in non_negative and isinstance(value, (int, float)) and not pd.isna(value) and value < 0:
            errors[s.name] = "must not be negative"
            continue
        row[s.name] = value
    if errors:
        raise ValidationError(errors)
    return row


def append_row(df: pd.DataFrame, row: dict) -> pd.DataFrame:
    """Return a NEW DataFrame with ``row`` appended; previous rows and
    column dtypes are preserved. The input is never modified."""
    new = pd.DataFrame([{c: row.get(c, None) for c in df.columns}], columns=df.columns)
    base = df.copy()
    for col in df.columns:
        dtype = base[col].dtype
        if pd.api.types.is_datetime64_any_dtype(dtype):
            new[col] = pd.to_datetime(new[col])
        elif pd.api.types.is_numeric_dtype(dtype) and not pd.api.types.is_bool_dtype(dtype):
            new[col] = pd.to_numeric(new[col], errors="coerce")
    out = pd.concat([base, new], ignore_index=True) if len(base) else new.copy()
    for col in df.columns:  # restore integer dtypes when no NaN was introduced
        if pd.api.types.is_integer_dtype(df[col].dtype) and out[col].notna().all():
            out[col] = out[col].astype(df[col].dtype)
    return out


def new_dataset_from_definition(definition: list[tuple[str, str]]) -> pd.DataFrame:
    """Create an empty typed DataFrame from [(column name, entry type)]."""
    names = [n.strip() for n, _ in definition if n and n.strip()]
    if not names:
        raise ValueError("Define at least one column.")
    if len(set(n.lower() for n in names)) != len(names):
        raise ValueError("Column names must be unique (case-insensitive).")
    data = {}
    for name, typ in definition:
        if not name or not name.strip():
            continue
        name = name.strip()
        if typ == "integer":
            data[name] = pd.Series([], dtype="Int64")
        elif typ == "decimal":
            data[name] = pd.Series([], dtype="float64")
        elif typ == "date":
            data[name] = pd.Series([], dtype="datetime64[ns]")
        elif typ == "boolean":
            data[name] = pd.Series([], dtype="boolean")
        else:
            data[name] = pd.Series([], dtype="object")
    return pd.DataFrame(data)
