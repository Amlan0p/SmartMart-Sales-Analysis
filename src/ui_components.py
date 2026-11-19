"""
ui_components.py

Streamlit building blocks: theme/CSS, KPI cards, formatted tables, the
sidebar, the four-button data-management toolbar and its dialogs. All data
logic is delegated to the backend modules; this file only draws and wires.
"""

from __future__ import annotations

import inspect

import pandas as pd
import streamlit as st

from src import data_entry, data_upload
from src import dynamic_analytics as A
from src.dataset_manager import DatasetManager
from src.schema_detection import detect_schema
from src.visualizations import THEMES

NAV_ITEMS = [("Overview", "◧"), ("Data Management", "▤"), ("Data Preparation", "✦"),
             ("Exploratory Analysis", "◔"), ("Business Intelligence", "▲"),
             ("Reports & Export", "⇩"), ("Settings", "⚙")]
NAV_LABELS = [f"{icon}  {name}" for name, icon in NAV_ITEMS]
ENTRY_LABELS = {"text": "Text", "integer": "Whole number", "decimal": "Decimal number",
                "date": "Date", "boolean": "Yes / No", "category": "Category (text)"}


# ------------------------------------------------------------------ helpers
def stretch(func) -> dict:
    """Full-width keyword for old and new Streamlit versions."""
    params = inspect.signature(func).parameters
    return {"width": "stretch"} if "width" in params else {"use_container_width": True}


def is_dark() -> bool:
    """The app is light-only (kept so chart helpers keep a single signature)."""
    return False


def get_dm() -> DatasetManager:
    if "dm" not in st.session_state:
        dm = DatasetManager()
        try:
            dm.load_default()
        except Exception as exc:  # built-in files missing: start empty and say why
            st.session_state["startup_error"] = str(exc)
        st.session_state["dm"] = dm
    return st.session_state["dm"]


def fmt_kpi(k: dict, currency: str = "") -> str:
    v = k["value"]
    if v is None or (isinstance(v, float) and v != v):
        return "n/a"
    kind = k["kind"]
    if kind == "money":
        a = abs(v)
        if a >= 1e9:
            return f"{currency}{v / 1e9:,.2f}B"
        if a >= 1e6:
            return f"{currency}{v / 1e6:,.2f}M"
        if a >= 1e5:
            return f"{currency}{v / 1e3:,.1f}K"
        return f"{currency}{v:,.2f}"
    if kind == "percent":
        return f"{v:.2f}%"
    if kind == "int":
        return f"{int(round(v)):,}"
    return f"{v:,.2f}" if isinstance(v, float) else str(v)


def plain(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    for c in out.columns:
        if pd.api.types.is_string_dtype(out[c]) and not pd.api.types.is_numeric_dtype(out[c]):
            out[c] = out[c].astype(object)
    return out


def show_table(frame: pd.DataFrame, height: int | None = 340, key: str | None = None) -> None:
    kwargs = dict(hide_index=True, **stretch(st.dataframe))
    if height:
        kwargs["height"] = height
    st.dataframe(plain(frame), **kwargs)


def show_chart(fig, key: str) -> None:
    if fig is None:
        return
    st.plotly_chart(fig, key=key, **stretch(st.plotly_chart))


def section(title: str, caption: str = "") -> None:
    st.markdown(f'<div class="sm-section"><h3>{title}</h3>' + (f"<p>{caption}</p>" if caption else "") + "</div>",
                unsafe_allow_html=True)


def empty_state(title: str, message: str) -> None:
    st.markdown(f'<div class="sm-empty"><div class="sm-empty-icon">◌</div><h4>{title}</h4><p>{message}</p></div>',
                unsafe_allow_html=True)


def kpi_cards(kpis: list[dict], currency: str = "", per_row: int = 4) -> None:
    for start in range(0, len(kpis), per_row):
        chunk = kpis[start:start + per_row]
        cols = st.columns(per_row)
        for col, k in zip(cols, chunk):
            with col:
                tip = k.get("help", "").replace('"', "'")
                st.markdown(f'<div class="sm-kpi" title="{tip}"><div class="sm-kpi-label">{k["label"]}</div>'
                            f'<div class="sm-kpi-value">{fmt_kpi(k, currency)}</div>'
                            f'<div class="sm-kpi-help">{k.get("help", "")}</div></div>', unsafe_allow_html=True)


# ------------------------------------------------------------------ CSS
def inject_css() -> None:
    t = THEMES["dark" if is_dark() else "light"]
    accent = "#6F86FF" if is_dark() else "#4F6BED"
    st.markdown(f"""
<style>
:root {{ --sm-bg:{t['bg']}; --sm-card:{t['card']}; --sm-surface:{t['surface']}; --sm-text:{t['text']};
  --sm-muted:{t['muted']}; --sm-border:{t['border']}; --sm-accent:{accent}; --sm-radius:12px; }}
html, body, [class*="css"], .stApp {{ font-family: Inter, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }}
.stApp {{ background: var(--sm-surface); color: var(--sm-text); }}
header[data-testid="stHeader"] {{ background: transparent; }}
.block-container {{ padding-top: 1.1rem; padding-bottom: 3rem; max-width: 1360px; }}
h1,h2,h3,h4,h5, .stMarkdown p, label, .stRadio label, .stCheckbox label, .stSelectbox label {{ color: var(--sm-text); }}
h1 {{ font-size: 1.55rem !important; font-weight: 650 !important; letter-spacing: -0.01em; margin-bottom: .1rem; }}
h3 {{ font-size: 1.02rem !important; font-weight: 600 !important; }}
.sm-sub {{ color: var(--sm-muted); font-size: .9rem; margin: 0 0 1rem 0; }}
/* sidebar */
section[data-testid="stSidebar"] {{ background: var(--sm-card); border-right: 1px solid var(--sm-border); }}
section[data-testid="stSidebar"] * {{ color: var(--sm-text); }}
.sm-brand {{ display:flex; align-items:center; gap:.6rem; padding:.2rem 0 .8rem; }}
.sm-logo {{ width:32px;height:32px;border-radius:9px;background:var(--sm-accent);color:#fff!important;display:flex;
  align-items:center;justify-content:center;font-weight:700; }}
.sm-brand b {{ font-size:1.02rem; }} .sm-brand span {{ display:block; color:var(--sm-muted); font-size:.72rem; }}
.sm-ds {{ border:1px solid var(--sm-border); border-radius:10px; padding:.6rem .75rem; margin-bottom:.9rem; background:var(--sm-surface); }}
.sm-ds .n {{ font-weight:600; font-size:.86rem; word-break:break-word; }} .sm-ds .m {{ color:var(--sm-muted); font-size:.74rem; }}
.sm-dot {{ display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px; }}
.sm-ok {{ background:#22A699; }} .sm-info {{ background:#4F6BED; }} .sm-warn {{ background:#F2A65A; }} .sm-muted {{ background:#9CA3AF; }}
section[data-testid="stSidebar"] div[role="radiogroup"] > label {{ padding:.42rem .65rem; border-radius:8px; margin:1px 0;
  transition: background .15s ease; width:100%; }}
section[data-testid="stSidebar"] div[role="radiogroup"] > label:hover {{ background: var(--sm-surface); }}
section[data-testid="stSidebar"] div[role="radiogroup"] > label > div:first-child {{ display:none; }}
section[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) {{ background: color-mix(in srgb, var(--sm-accent) 14%, transparent);
  font-weight:600; }}
/* cards */
.sm-kpi {{ background:var(--sm-card); border:1px solid var(--sm-border); border-radius:var(--sm-radius); padding:.9rem 1rem;
  box-shadow:0 1px 2px rgba(16,24,40,.05); margin-bottom:.75rem; min-height:98px; transition: box-shadow .15s ease, transform .15s ease; }}
.sm-kpi:hover {{ box-shadow:0 4px 14px rgba(16,24,40,.09); transform: translateY(-1px); }}
.sm-kpi-label {{ color:var(--sm-muted); font-size:.74rem; font-weight:550; text-transform:uppercase; letter-spacing:.04em; }}
.sm-kpi-value {{ font-size:1.5rem; font-weight:650; margin-top:.15rem; letter-spacing:-0.01em; }}
.sm-kpi-help {{ color:var(--sm-muted); font-size:.72rem; margin-top:.1rem; }}
.sm-section h3 {{ margin:1.1rem 0 .1rem; }} .sm-section p {{ color:var(--sm-muted); font-size:.82rem; margin:0 0 .5rem; }}
.sm-empty {{ border:1px dashed var(--sm-border); border-radius:var(--sm-radius); padding:2.2rem 1rem; text-align:center; background:var(--sm-card); }}
.sm-empty-icon {{ font-size:2rem; color:var(--sm-muted); }} .sm-empty h4 {{ margin:.3rem 0 .2rem; }} .sm-empty p {{ color:var(--sm-muted); margin:0; }}
.sm-pill {{ display:inline-block; padding:.1rem .55rem; border-radius:999px; font-size:.72rem; font-weight:600;
  border:1px solid var(--sm-border); color:var(--sm-muted); margin-right:.3rem; }}
.sm-insight {{ border-left:3px solid var(--sm-accent); background:var(--sm-card); border-radius:8px; padding:.55rem .8rem; margin:.35rem 0;
  border-top:1px solid var(--sm-border); border-right:1px solid var(--sm-border); border-bottom:1px solid var(--sm-border); font-size:.9rem; }}
/* widgets */
div[data-testid="stButton"] > button, div[data-testid="stDownloadButton"] > button {{ border-radius:9px; border:1px solid var(--sm-border);
  font-weight:550; transition: all .15s ease; background: var(--sm-card); color: var(--sm-text); }}
div[data-testid="stButton"] > button:hover, div[data-testid="stDownloadButton"] > button:hover {{ border-color: var(--sm-accent); color: var(--sm-accent); }}
div[data-testid="stButton"] > button[kind="primary"] {{ background: var(--sm-accent); border-color: var(--sm-accent); color:#fff; }}
div[data-testid="stButton"] > button[kind="primary"]:hover {{ filter:brightness(1.08); color:#fff; }}
div[data-baseweb="select"] > div, div[data-baseweb="input"] > div, textarea {{ border-radius:9px !important; }}
div[data-testid="stExpander"] {{ border:1px solid var(--sm-border); border-radius:var(--sm-radius); background:var(--sm-card); }}
div[data-testid="stDataFrame"] {{ border:1px solid var(--sm-border); border-radius:10px; overflow:hidden; }}
div[data-testid="stFileUploaderDropzone"] {{ border:2px dashed var(--sm-border); border-radius:var(--sm-radius); background:var(--sm-surface); padding:1.6rem; }}
button[data-baseweb="tab"] {{ font-weight:550; }}
hr {{ border-color: var(--sm-border); }}
#MainMenu, footer {{ visibility:hidden; }}
</style>""", unsafe_allow_html=True)


# ------------------------------------------------------------------ sidebar
def render_sidebar(dm: DatasetManager) -> str:
    sb = st.sidebar
    sb.markdown('<div class="sm-brand"><div class="sm-logo">S</div><div><b>SmartMart</b>'
                '<span>Analytics Platform</span></div></div>', unsafe_allow_html=True)
    label, tone = dm.status
    rows = f"{len(dm.working_df):,} rows · {dm.working_df.shape[1]} cols" if dm.has_columns else "No data loaded"
    sb.markdown(f'<div class="sm-ds"><div class="m">ACTIVE DATASET</div><div class="n">{dm.display_name}</div>'
                f'<div class="m"><span class="sm-dot sm-{tone}"></span>{label} · {rows}</div></div>', unsafe_allow_html=True)
    if "nav" not in st.session_state:
        st.session_state["nav"] = NAV_LABELS[0]
    choice = sb.radio("Navigation", NAV_LABELS, key="nav", label_visibility="collapsed")
    return choice.split("  ", 1)[1]


def goto(page_name: str) -> None:
    """Callback helper: switch page (use as on_click)."""
    for name, icon in NAV_ITEMS:
        if name == page_name:
            st.session_state["nav"] = f"{icon}  {name}"


def sidebar_filters(dm: DatasetManager) -> A.FilterSpec | None:
    """Dynamic filters built from the ACTIVE dataset's columns."""
    sb = st.sidebar
    if dm.is_empty:
        return None
    df, schema = dm.working_df, dm.schema
    epoch = f"{dm.dataset_id[:8]}_{st.session_state.get('filter_epoch', 0)}"
    cand = A.filter_candidates(df, schema)
    spec = A.FilterSpec()
    sb.markdown('<div class="sm-ds"><div class="m">GLOBAL FILTERS</div></div>', unsafe_allow_html=True)
    with sb.expander("Filters", expanded=False):
        dcol = cand["date"]
        if dcol:
            d = pd.to_datetime(df[dcol], errors="coerce").dropna()
            if len(d):
                lo, hi = d.min().date(), d.max().date()
                rng = st.date_input(f"{dcol}", value=(lo, hi), min_value=lo, max_value=hi, key=f"f_date_{epoch}")
                if isinstance(rng, (tuple, list)) and len(rng) == 2 and (rng[0] != lo or rng[1] != hi):
                    spec.date_col, spec.date_range = dcol, (rng[0], rng[1])
        for c in cand["categorical"]:
            vals = sorted(df[c].dropna().astype(str).unique().tolist())
            sel = st.multiselect(c, vals, key=f"f_cat_{c}_{epoch}")
            if sel:
                spec.categorical[c] = sel
        for c in cand["numeric"]:
            s = df[c].dropna()
            if s.empty or s.min() == s.max():
                continue
            lo, hi = float(s.min()), float(s.max())
            sel = st.slider(c, lo, hi, (lo, hi), key=f"f_num_{c}_{epoch}")
            if sel != (lo, hi):
                spec.numeric[c] = (float(sel[0]), float(sel[1]))
        if st.button("Reset filters", key="reset_filters", **stretch(st.button)):
            st.session_state["filter_epoch"] = st.session_state.get("filter_epoch", 0) + 1
            st.rerun()
    return spec


# ------------------------------------------------------------------ dialogs
def _dialog(title: str):
    deco = getattr(st, "dialog", None) or getattr(st, "experimental_dialog")
    return deco(title, width="large") if "width" in inspect.signature(deco).parameters else deco(title)


@_dialog("Remove all data")
def dialog_remove_all() -> None:
    dm = get_dm()
    st.warning("Are you sure you want to remove all current data? This action cannot be undone.")
    st.caption("Only the active working dataset is cleared. Built-in CSV files, your uploaded files and the "
               "project files are not touched; you can reload the default dashboard at any time.")
    keep = st.checkbox("Keep the column structure (headers) so I can enter new rows in the same format",
                       value=False, disabled=not dm.has_columns)
    c1, c2 = st.columns(2)
    if c1.button("Yes, remove all data", type="primary", key="dlg_remove_yes", **stretch(st.button)):
        dm.clear(keep_columns=keep)
        st.session_state["filter_epoch"] = st.session_state.get("filter_epoch", 0) + 1
        st.session_state["toast"] = "Working dataset cleared."
        st.rerun()
    if c2.button("Cancel", key="dlg_remove_no", **stretch(st.button)):
        st.rerun()


@_dialog("Load default dashboard")
def dialog_load_default() -> None:
    dm = get_dm()
    st.warning("Load the default SmartMart dataset? Your current working data will be replaced.")
    st.caption("The data is read from the project's built-in CSV files (data/processed/...); nothing is hard-coded.")
    c1, c2 = st.columns(2)
    if c1.button("Yes, load SmartMart", type="primary", key="dlg_default_yes", **stretch(st.button)):
        try:
            dm.load_default()
        except Exception as exc:
            st.error(f"Could not load the built-in data: {exc}")
            return
        st.session_state["filter_epoch"] = st.session_state.get("filter_epoch", 0) + 1
        st.session_state["toast"] = "Default SmartMart dashboard restored."
        st.rerun()
    if c2.button("Cancel", key="dlg_default_no", **stretch(st.button)):
        st.rerun()


def upload_panel(dm: DatasetManager, key_prefix: str = "up") -> None:
    """Drag-and-drop uploader, preview, quality summary and replace-confirmation.
    Used inside the Upload dialog and on the Data Management page."""
    file = st.file_uploader("Drag and drop a CSV or Excel file here", type=["csv", "xlsx", "xls"],
                            key=f"{key_prefix}_file_{st.session_state.get('upload_epoch', 0)}", help="Supported: .csv, .xlsx, .xls")
    if file is None:
        st.caption("Supported formats: CSV, Excel XLSX, Excel XLS. The file is read in memory only.")
        return
    data = file.getvalue()
    sheet = None
    try:
        sheets = data_upload.excel_sheet_names(data, file.name)
        if len(sheets) > 1:
            sheet = st.selectbox("Worksheet", sheets, key=f"{key_prefix}_sheet")
        df = data_upload.read_upload(data, file.name, sheet)
    except data_upload.UploadError as exc:
        st.error(str(exc))
        return
    schema = detect_schema(df)
    s = data_upload.summarize(df, file.name, len(data), schema)
    a, b, c, d = st.columns(4)
    a.metric("File", s["filename"] if len(s["filename"]) < 18 else s["filename"][:15] + "…")
    b.metric("Size", s["size"])
    c.metric("Rows", f"{s['rows']:,}")
    d.metric("Columns", f"{s['columns']:,}")
    st.markdown(f'<span class="sm-pill">Detected: {s["dataset_type"]}</span>'
                f'<span class="sm-pill">Missing: {s["missing_total"]:,} ({s["missing_pct"]}%)</span>'
                f'<span class="sm-pill">Duplicates: {s["duplicate_rows"]:,}</span>', unsafe_allow_html=True)
    k = s["kinds"]
    st.caption(f"Numeric: {', '.join(k['numeric']) or '—'}  |  Categorical: {', '.join(k['categorical']) or '—'}  |  "
               f"Date: {', '.join(k['datetime']) or '—'}  |  Identifier: {', '.join(k['identifier']) or '—'}")
    for note in s["notes"]:
        st.warning(note)
    t1, t2 = st.tabs(["Preview", "Columns & types"])
    with t1:
        show_table(df.head(50), 260)
    with t2:
        show_table(s["column_table"], 260)
    st.markdown("**Do you want to replace your current working dataset with this uploaded file?**")
    if s["rows"] == 0:
        st.error("The file has no records, so it cannot become the working dataset.")
        return
    if st.button("Yes, replace working dataset", type="primary", key=f"{key_prefix}_confirm"):
        dm.replace_with_upload(df, file.name)
        st.session_state["upload_epoch"] = st.session_state.get("upload_epoch", 0) + 1
        st.session_state["filter_epoch"] = st.session_state.get("filter_epoch", 0) + 1
        st.session_state["toast"] = f"Loaded {file.name}: {len(df):,} rows."
        st.rerun()


@_dialog("Upload CSV / Excel")
def dialog_upload() -> None:
    upload_panel(get_dm(), "dlgup")


def _entry_widget(spec: data_entry.ColumnSpec, key: str):
    if spec.kind == "numeric":
        return st.text_input(spec.name, key=key, placeholder="whole number" if spec.is_integer else "number",
                             help="Leave blank to store a missing value")
    if spec.kind == "datetime":
        return st.date_input(spec.name, value=None, key=key, help="Leave empty to store a missing date")
    if spec.kind == "boolean":
        return st.selectbox(spec.name, ["", "Yes", "No"], key=key)
    if spec.kind == "categorical" and spec.choices:
        NEW = "➕ New value…"
        pick = st.selectbox(spec.name, [""] + spec.choices + [NEW], key=key)
        if pick == NEW:
            return st.text_input(f"{spec.name} (new value)", key=key + "_new")
        return pick
    return st.text_input(spec.name, key=key)


@_dialog("Add row")
def dialog_add_row() -> None:
    dm = get_dm()
    if not dm.has_columns:
        st.info("No dataset is loaded. Define the columns of a new dataset, then enter records one at a time.")
        defn = st.data_editor(
            pd.DataFrame({"Column name": ["", "", ""], "Type": ["text", "text", "decimal"]}),
            num_rows="dynamic", key="new_ds_editor", hide_index=True,
            column_config={"Type": st.column_config.SelectboxColumn("Type", options=data_entry.ENTRY_TYPES, required=True)},
            **stretch(st.data_editor))
        if st.button("Create dataset", type="primary", key="create_ds"):
            pairs = [(str(r["Column name"]), str(r["Type"])) for _, r in defn.iterrows()
                     if str(r["Column name"]).strip() not in ("", "nan", "None")]
            try:
                dm.create_manual_dataset(pairs)
            except ValueError as exc:
                st.error(str(exc))
                return
            st.rerun()
        return

    epoch = st.session_state.get("entry_epoch", 0)
    specs = data_entry.specs_from_dataframe(dm.working_df, dm.schema)
    st.caption(f"Adding a row to **{dm.display_name}** ({len(dm.working_df):,} rows). Column types were detected "
               "automatically; invalid values are rejected with a message.")
    cols = st.columns(2)
    for i, sp in enumerate(specs):
        with cols[i % 2]:
            _entry_widget(sp, f"entry_{epoch}_{sp.name}")

    def _add():
        # Read the CURRENT widget values from session state (a closure over
        # values captured during the previous run would be stale).
        raw = {}
        for sp in specs:
            key = f"entry_{epoch}_{sp.name}"
            val = st.session_state.get(key)
            if sp.kind == "categorical" and val == "➕ New value…":
                val = st.session_state.get(key + "_new")
            if sp.kind == "boolean":
                val = {"Yes": True, "No": False}.get(val)
            raw[sp.name] = val
        try:
            dm.add_row(raw)
        except data_entry.ValidationError as exc:
            st.session_state["entry_errors"] = exc.errors
            return
        st.session_state["entry_errors"] = {}
        st.session_state["entry_epoch"] = epoch + 1   # fresh empty fields for the next row
        st.session_state["entry_ok"] = f"Row added. The dataset now has {len(dm.working_df):,} rows."

    st.button("Add this row", type="primary", key=f"entry_add_{epoch}", on_click=_add)
    for col, msg in (st.session_state.get("entry_errors") or {}).items():
        st.error(f"{col}: {msg}" if col != "_row" else msg)
    if st.session_state.get("entry_ok"):
        st.success(st.session_state.pop("entry_ok"))
    if len(dm.working_df):
        st.markdown("**Most recent rows**")
        show_table(dm.working_df.tail(5), 210)
    if st.button("Done", key="entry_done"):
        st.session_state["entry_errors"] = {}
        st.rerun()


# ------------------------------------------------------------------ toolbar
def render_toolbar(dm: DatasetManager) -> None:
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("＋  Add Row", key="tb_add", **stretch(st.button)):
        dialog_add_row()
    if c2.button("Remove All Data", key="tb_remove", **stretch(st.button)):
        dialog_remove_all()
    if c3.button("Upload CSV / Excel", key="tb_upload", **stretch(st.button)):
        dialog_upload()
    if c4.button("Load Default Dashboard", key="tb_default", type="primary", **stretch(st.button)):
        dialog_load_default()
    toast = st.session_state.pop("toast", None)
    if toast:
        st.success(toast)
    err = st.session_state.pop("startup_error", None)
    if err:
        st.error(f"Built-in data could not be loaded at start-up: {err}")


def page_header(title: str, subtitle: str, dm: DatasetManager, spec_text: str | None = None) -> None:
    st.markdown(f"<h1>{title}</h1><p class='sm-sub'>{subtitle}</p>", unsafe_allow_html=True)
    render_toolbar(dm)
    if spec_text and "No filters" not in spec_text:
        st.caption(f"🔎 {spec_text}")
