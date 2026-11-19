"""
dataset_manager.py

Single source of truth for "which data is the application showing right now".
Pure Python / pandas (no Streamlit) so it can be unit-tested; the Streamlit
app keeps one instance in ``st.session_state``.

Four things are kept strictly separate:

1. built-in SmartMart data   - read from the project's CSV files every time
                               it is loaded; never held as the working copy
                               and never written to.
2. uploaded source dataset   - the user's file exactly as parsed (``source_df``)
3. active working dataset    - what every page, filter and report uses
4. manual / cleaned changes  - applied to the working copy only

Every method that changes the working data bumps ``revision`` (so cached
results can be invalidated) and ``dataset_id`` changes whenever a different
dataset is loaded (upload / default / clear / new), which the UI uses
to reset dataset-specific state.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

import pandas as pd

from src import data_entry
from src.schema_detection import SchemaResult, apply_manual_mapping, coerce_types, detect_schema

DEFAULT_NAME = "SmartMart (built-in demo)"


@dataclass
class DatasetManager:
    working_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    source_df: pd.DataFrame | None = None        # uploaded file as parsed
    source_name: str = ""
    source_kind: str = "empty"                    # default | upload | manual | empty
    extras: dict = field(default_factory=dict)    # default only: segments / classification
    cleaned_df: pd.DataFrame | None = None        # last cleaned copy applied
    mapping_overrides: dict = field(default_factory=dict)
    modified: bool = False
    revision: int = 0
    dataset_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    manual_rows_added: int = 0
    history: list = field(default_factory=list)   # undo stack for cleaning
    _schema: SchemaResult | None = None
    _schema_rev: int = -1

    # ------------------------------------------------------------------ state
    @property
    def is_empty(self) -> bool:
        return self.working_df is None or self.working_df.shape[1] == 0 or len(self.working_df) == 0

    @property
    def has_columns(self) -> bool:
        return self.working_df is not None and self.working_df.shape[1] > 0

    @property
    def display_name(self) -> str:
        return {"default": DEFAULT_NAME, "empty": "Empty workspace",
                "manual": self.source_name or "Manual dataset"}.get(self.source_kind, self.source_name)

    @property
    def status(self) -> tuple[str, str]:
        """(label, tone) tone in {ok, info, warn, muted}."""
        if self.source_kind == "empty" or self.is_empty:
            return ("Empty", "muted")
        base = {"default": "Default", "upload": "Uploaded", "manual": "Manual"}[self.source_kind]
        return (f"{base} · modified", "warn") if self.modified else (base, "ok" if base == "Default" else "info")

    @property
    def currency(self) -> str:
        return "₹" if self.source_kind == "default" else ""

    @property
    def schema(self) -> SchemaResult:
        if self._schema is None or self._schema_rev != self.revision:
            schema = detect_schema(self.working_df)
            if self.mapping_overrides:
                valid = {r: c for r, c in self.mapping_overrides.items()
                         if c is None or c in self.working_df.columns}
                schema = apply_manual_mapping(schema, valid)
            self._schema, self._schema_rev = schema, self.revision
        return self._schema

    def _touch(self, new_dataset: bool = False) -> None:
        self.revision += 1
        if new_dataset:
            self.dataset_id = uuid.uuid4().hex

    def _install(self, df: pd.DataFrame, kind: str, name: str, new_dataset: bool = True) -> None:
        df = df.reset_index(drop=True)
        schema = detect_schema(df)
        self.working_df = coerce_types(df, schema)
        self.source_kind, self.source_name = kind, name
        self.modified = False
        self.cleaned_df = None
        self.mapping_overrides = {}
        self.history = []
        self.manual_rows_added = 0
        self._touch(new_dataset)

    # ---------------------------------------------------------------- button 4
    def load_default(self) -> None:
        """Rebuild the working data from the built-in SmartMart CSV files."""
        from src import dashboard_logic as L  # local import keeps this module light
        if L.missing_files():
            raise L.DataNotReadyError(L.MISSING_FILES_MESSAGE)
        sales, _info = L.load_sales()
        self._install(sales, "default", DEFAULT_NAME)
        self.source_df = None            # the upload slot is separate from built-in data
        self.extras = {"segments": L.load_segments(), "classification": L.load_classification()}

    # ---------------------------------------------------------------- button 3
    def replace_with_upload(self, df: pd.DataFrame, filename: str) -> None:
        """Make an uploaded dataset the working dataset (caller confirms first)."""
        self.source_df = df.copy()      # pristine copy of what the user uploaded
        self.extras = {}
        self._install(df.copy(), "upload", filename)

    # ---------------------------------------------------------------- button 2
    def clear(self, keep_columns: bool = False) -> None:
        """Empty the working dataset. Files on disk and the uploaded source
        copy are untouched."""
        cols = list(self.working_df.columns) if (keep_columns and self.has_columns) else []
        dtypes = {c: self.working_df[c].dtype for c in cols}
        empty = pd.DataFrame({c: pd.Series([], dtype=dtypes[c]) for c in cols})
        self.working_df = empty
        self.extras = {}
        self.source_kind = "manual" if cols else "empty"
        self.source_name = "Manual dataset" if cols else ""
        self.modified = False
        self.cleaned_df = None
        self.mapping_overrides = {}
        self.history = []
        self.manual_rows_added = 0
        self._touch(True)

    # ---------------------------------------------------------------- button 1
    def create_manual_dataset(self, definition: list[tuple[str, str]], name: str = "Manual dataset") -> None:
        self.working_df = data_entry.new_dataset_from_definition(definition)
        self.extras = {}
        self.source_df, self.cleaned_df = None, None
        self.source_kind, self.source_name = "manual", name
        self.modified, self.mapping_overrides, self.history = False, {}, []
        self.manual_rows_added = 0
        self._touch(True)

    def add_row(self, raw_values: dict, allow_blank: bool = True) -> dict:
        """Validate and append one row to the ACTIVE dataset only."""
        if not self.has_columns:
            raise data_entry.ValidationError({"_row": "No dataset yet - define columns first."})
        specs = data_entry.specs_from_dataframe(self.working_df, self.schema)
        row = data_entry.validate_row(specs, raw_values, allow_blank, self.schema)
        self.working_df = data_entry.append_row(self.working_df, row)
        if self.source_kind == "empty":
            self.source_kind = "manual"
        self.manual_rows_added += 1
        self.modified = self.source_kind != "manual" or self.modified
        self._touch(False)
        return row

    # ---------------------------------------------------------------- cleaning
    def apply_cleaned(self, cleaned: pd.DataFrame) -> None:
        """Replace the working data with a cleaned copy (previous state is kept for undo)."""
        self.history.append(self.working_df.copy())
        self.working_df = coerce_types(cleaned.reset_index(drop=True), detect_schema(cleaned))
        self.cleaned_df = self.working_df.copy()
        self.modified = True
        self._touch(False)

    def undo_cleaning(self) -> bool:
        if not self.history:
            return False
        self.working_df = self.history.pop()
        self.modified = bool(self.history) or (self.manual_rows_added > 0 and self.source_kind != "manual")
        self.cleaned_df = None if not self.history else self.working_df.copy()
        self._touch(False)
        return True

    def set_mapping(self, mapping: dict) -> None:
        self.mapping_overrides.update(mapping)
        self._touch(False)
