"""
data_upload.py

Reads user-supplied CSV / XLSX / XLS files with pandas and builds the
upload summary (shape, types, missing values, duplicates, quality notes).
Nothing is written to disk: the uploaded bytes stay in memory, so no user
file is ever stored in or deleted from the project folder.
"""

from __future__ import annotations

import io
from pathlib import Path

import pandas as pd

from src.schema_detection import SchemaResult, detect_schema

SUPPORTED_EXTENSIONS = (".csv", ".xlsx", ".xls")
MAX_UPLOAD_MB = 200


class UploadError(ValueError):
    """Raised with a user-readable message when a file cannot be read."""


def human_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{num_bytes} B"


def _clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Strip names, name blank headers, make duplicate headers unique."""
    seen: dict[str, int] = {}
    names = []
    for i, col in enumerate(df.columns):
        name = str(col).strip() or f"Column_{i + 1}"
        if name.lower().startswith("unnamed:"):
            name = f"Column_{i + 1}"
        if name in seen:
            seen[name] += 1
            name = f"{name}_{seen[name]}"
        else:
            seen[name] = 0
        names.append(name)
    out = df.copy()
    out.columns = names
    return out


def excel_sheet_names(file_bytes: bytes, filename: str) -> list[str]:
    ext = Path(filename).suffix.lower()
    if ext not in (".xlsx", ".xls"):
        return []
    try:
        engine = "openpyxl" if ext == ".xlsx" else "xlrd"
        return list(pd.ExcelFile(io.BytesIO(file_bytes), engine=engine).sheet_names)
    except ImportError as exc:
        raise UploadError(_missing_engine_message(ext)) from exc
    except Exception as exc:  # corrupt workbook
        raise UploadError(f"Could not open the Excel workbook: {exc}") from exc


def _missing_engine_message(ext: str) -> str:
    pkg = "openpyxl" if ext == ".xlsx" else "xlrd"
    return f"Reading {ext} files needs the '{pkg}' package: python -m pip install {pkg}"


def read_upload(file_bytes: bytes, filename: str, sheet: str | int | None = None) -> pd.DataFrame:
    """Parse an uploaded file into a DataFrame (raises UploadError)."""
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise UploadError(f"Unsupported file type '{ext or 'unknown'}'. "
                          f"Please upload one of: {', '.join(SUPPORTED_EXTENSIONS)}.")
    if not file_bytes:
        raise UploadError("The uploaded file is empty.")
    if len(file_bytes) > MAX_UPLOAD_MB * 1024 * 1024:
        raise UploadError(f"The file is larger than {MAX_UPLOAD_MB} MB.")
    try:
        if ext == ".csv":
            df = _read_csv(file_bytes)
        else:
            engine = "openpyxl" if ext == ".xlsx" else "xlrd"
            df = pd.read_excel(io.BytesIO(file_bytes), engine=engine,
                               sheet_name=sheet if sheet is not None else 0)
    except UploadError:
        raise
    except ImportError as exc:
        raise UploadError(_missing_engine_message(ext)) from exc
    except pd.errors.EmptyDataError as exc:
        raise UploadError("The file contains no data.") from exc
    except Exception as exc:
        raise UploadError(f"The file could not be read: {exc}") from exc
    if df.shape[1] == 0:
        raise UploadError("The file has no columns.")
    df = _clean_columns(df)
    df = df.dropna(how="all").reset_index(drop=True)  # fully blank rows are not records
    return df


def _read_csv(file_bytes: bytes) -> pd.DataFrame:
    last_error: Exception | None = None
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return pd.read_csv(io.BytesIO(file_bytes), sep=None, engine="python",
                               encoding=encoding)
        except UnicodeDecodeError as exc:
            last_error = exc
        except pd.errors.ParserError:
            # delimiter sniffing failed: fall back to a plain comma
            return pd.read_csv(io.BytesIO(file_bytes), encoding=encoding, on_bad_lines="skip")
    raise UploadError(f"Could not decode the file: {last_error}")


def summarize(df: pd.DataFrame, filename: str, size_bytes: int,
              schema: SchemaResult | None = None) -> dict:
    """Everything the upload preview shows."""
    schema = schema or detect_schema(df)
    missing = df.isna().sum()
    total_cells = max(df.shape[0] * df.shape[1], 1)
    dup = int(df.duplicated().sum())
    kinds = {k: schema.columns_of(k) for k in
             ("numeric", "categorical", "datetime", "identifier", "boolean", "text")}
    notes = []
    if df.empty:
        notes.append("The file has headers but no records.")
    if int(missing.sum()):
        cols = missing[missing > 0].sort_values(ascending=False)
        notes.append(f"{int(missing.sum()):,} missing values in {len(cols)} column(s) "
                     f"(most: {cols.index[0]}, {int(cols.iloc[0]):,}).")
    if dup:
        notes.append(f"{dup:,} fully duplicated row(s).")
    const = [c for c in df.columns if df[c].nunique(dropna=True) <= 1 and len(df) > 1]
    if const:
        notes.append("Constant column(s): " + ", ".join(const[:5]) + ".")
    return {
        "filename": filename,
        "size": human_size(size_bytes),
        "rows": int(df.shape[0]),
        "columns": int(df.shape[1]),
        "missing_total": int(missing.sum()),
        "missing_pct": round(float(missing.sum()) / total_cells * 100, 2),
        "duplicate_rows": dup,
        "kinds": kinds,
        "dataset_type": schema.dataset_type,
        "notes": notes,
        "column_table": pd.DataFrame({
            "Column": df.columns,
            "Detected type": [schema.profiles[c].kind for c in df.columns],
            "Pandas dtype": [str(df[c].dtype) for c in df.columns],
            "Missing": missing.values,
            "Distinct": [int(df[c].nunique(dropna=True)) for c in df.columns],
        }),
    }
