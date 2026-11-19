"""
ui_pages.py - the seven pages. Each page receives the DatasetManager and
the FILTERED view of the active data, and never reads any other data source.
"""

from __future__ import annotations

import platform

import pandas as pd
import streamlit as st

from src import data_cleaning as C
from src import dynamic_analytics as A
from src import report_export as R
from src import visualizations as V
from src.dataset_manager import DatasetManager
from src.ui_components import (empty_state, kpi_cards, page_header, section, show_chart,
                               show_table, stretch, upload_panel, is_dark)


# ------------------------------------------------------------------ shared
def memo(name: str, sig: tuple, fn):
    """Tiny per-session cache so reruns (e.g. on widget changes) do not recompute."""
    store = st.session_state.setdefault("_memo", {})
    if store.get(name, (None, None))[0] != sig:
        store[name] = (sig, fn())
    return store[name][1]


def sig_of(dm: DatasetManager, spec: A.FilterSpec | None) -> tuple:
    return (dm.dataset_id, dm.revision, repr(spec))


def guard(dm: DatasetManager, df: pd.DataFrame) -> bool:
    """Show an empty/no-match state and return False when nothing can be analysed."""
    if dm.is_empty:
        if dm.has_columns:
            empty_state("The dataset has no rows yet",
                        "Use “＋ Add Row” to enter records, upload a file, or load the default dashboard.")
        else:
            empty_state("Your workspace is empty",
                        "Use “＋ Add Row” to create a dataset by hand, “Upload CSV / Excel” to bring your own data, "
                        "or “Load Default Dashboard” to restore the SmartMart demo.")
        return False
    if df.empty:
        empty_state("No rows match the current filters", "Open the sidebar filters and press “Reset filters”.")
        return False
    return True


def insight_list(items: list[str]) -> None:
    for t in items:
        st.markdown(f'<div class="sm-insight">{t}</div>', unsafe_allow_html=True)


# ------------------------------------------------------------------ 1 Overview
def page_overview(dm, df, spec):
    page_header("Overview", "Key metrics and charts for the active dataset.", dm, A.describe_filters(spec))
    if not guard(dm, df):
        return
    schema, dark, cur = dm.schema, is_dark(), dm.currency
    sig = sig_of(dm, spec)
    kpis = memo("kpis", sig, lambda: A.compute_kpis(df, schema))
    kpi_cards(kpis, cur)
    if len(df) != len(dm.working_df):
        st.caption(f"Showing {len(df):,} of {len(dm.working_df):,} rows after filters.")

    if A.has_sales_shape(df, schema):
        c1, c2 = st.columns([3, 2])
        with c1:
            show_chart(V.trend_line(A.monthly_trend(df, schema), "Revenue", "Monthly revenue", dark), "ov_trend")
        with c2:
            show_chart(V.donut(A.revenue_breakdown(df, schema, "category"), schema.roles.get("category") or "",
                               "Revenue", "Revenue share by category", dark), "ov_cat")
        c3, c4 = st.columns(2)
        with c3:
            b = A.revenue_breakdown(df, schema, "product", top=10)
            if b is not None:
                show_chart(V.bar_breakdown(b, b.columns[0], "Revenue", "Top 10 products by revenue", True, 10, dark), "ov_prod")
        with c4:
            b = A.revenue_breakdown(df, schema, "location")
            if b is not None:
                show_chart(V.bar_breakdown(b, b.columns[0], "Revenue", f"Revenue by {b.columns[0].replace('_', ' ').lower()}", False, 15, dark), "ov_loc")
    else:
        c1, c2 = st.columns(2)
        with c1:
            cats = schema.columns_of("categorical")
            if cats:
                show_chart(V.category_bar(A.category_distribution(df, cats[0]), cats[0], dark), "ov_cat_generic")
        with c2:
            nums = schema.columns_of("numeric")
            if nums:
                show_chart(V.histogram(df, nums[0], 30, dark), "ov_hist")
        dc, nums = schema.columns_of("datetime"), schema.columns_of("numeric")
        if dc:
            show_chart(V.time_series(df, dc[0], nums[0] if nums else None, "mean" if nums else "sum", "M", dark), "ov_ts")
        show_chart(V.corr_heatmap(A.correlations(df), dark), "ov_corr")

    ins = memo("insights", sig, lambda: A.generate_insights(df, schema, A.describe_filters(spec)))
    section("Top findings", "Calculated from the data currently shown")
    if ins["sufficient"]:
        insight_list(ins["findings"][:5])
    else:
        st.info(ins["note"])
    with st.expander("Data preview"):
        show_table(df.head(200), 320)


# ------------------------------------------------------------------ 2 Data Management
def page_data_management(dm, df, spec):
    page_header("Data Management", "Manage the active working dataset.", dm)
    label, _ = dm.status
    kpi_cards([{"label": "Source", "value": {"default": "Built-in", "upload": "Upload", "manual": "Manual", "empty": "None"}[dm.source_kind], "kind": "text", "help": dm.display_name},
               {"label": "Status", "value": label, "kind": "text", "help": "Current state of the working copy"},
               {"label": "Rows", "value": len(dm.working_df), "kind": "int", "help": "In the working dataset"},
               {"label": "Columns", "value": dm.working_df.shape[1], "kind": "int", "help": "In the working dataset"}], "")
    tab_data, tab_up, tab_map, tab_src = st.tabs(["Working data", "Upload", "Column mapping", "Sources"])
    with tab_data:
        if not dm.has_columns:
            empty_state("No data", "Use the toolbar above to add rows, upload a file or load the default dashboard.")
        else:
            st.caption("Showing the filtered view of the working dataset." if spec and spec.is_active() else "Showing the working dataset.")
            show_table(df.tail(500) if len(df) > 500 else df, 420)
            st.download_button("Download filtered data (CSV)", R.csv_bytes(df), "filtered_data.csv", "text/csv", key="dm_dl")
            if dm.history:
                if st.button("Undo last cleaning step", key="undo"):
                    dm.undo_cleaning()
                    st.rerun()
    with tab_up:
        upload_panel(dm, "dmup")
    with tab_map:
        if dm.is_empty:
            st.info("Column mapping becomes available once the dataset has data.")
        else:
            schema = dm.schema
            st.caption("The app detected the role of each column from its name and values. Low-confidence matches are marked; "
                       "override any role below. Roles that are not mapped are never assumed.")
            rows = [{"Role": r, "Detected column": c or "—", "Confidence": f"{schema.confidence.get(r, 0):.0%}"}
                    for r, c in schema.roles.items()]
            show_table(pd.DataFrame(rows), 330)
            if schema.uncertain_roles():
                st.warning("Uncertain: " + ", ".join(schema.uncertain_roles()))
            with st.form("mapping_form"):
                cols = ["(none)"] + list(dm.working_df.columns)
                choice = {}
                grid = st.columns(3)
                for i, role in enumerate(schema.roles):
                    cur = schema.roles.get(role)
                    idx = cols.index(cur) if cur in cols else 0
                    choice[role] = grid[i % 3].selectbox(role.replace("_", " ").title(), cols, index=idx, key=f"map_{role}_{dm.dataset_id[:6]}")
                if st.form_submit_button("Apply mapping", type="primary"):
                    dm.set_mapping({r: (None if c == "(none)" else c) for r, c in choice.items()})
                    st.rerun()
    with tab_src:
        st.markdown("- **Built-in SmartMart data**: `data/processed/*.csv` (read-only; reloaded with “Load Default Dashboard”).\n"
                    "- **Uploaded source**: kept in memory exactly as uploaded; removing data never touches it.\n"
                    "- **Working dataset**: what every page uses; edits (added rows, cleaning) apply here only.")
        if dm.source_df is not None:
            st.download_button("Download original uploaded dataset (CSV)", R.csv_bytes(dm.source_df), "original_upload.csv", "text/csv", key="dm_src")


# ------------------------------------------------------------------ 3 Data Preparation
OPS = ["Remove duplicates", "Handle missing values", "Change data type", "Standardise categories",
       "Remove invalid records", "Remove outliers", "Apply transformation"]


def page_data_preparation(dm, df, spec):
    page_header("Data Preparation", "Inspect quality, clean the working dataset and compare before and after.", dm)
    if not guard(dm, dm.working_df):
        return
    work, schema = dm.working_df, dm.schema
    q = C.quality_score(work, schema)
    t_rep, t_clean = st.tabs(["Quality reports", "Clean & transform"])
    with t_rep:
        kpi_cards([{"label": "Quality score", "value": q["score"], "kind": "number", "help": q["label"]},
                   {"label": "Missing cells", "value": int(work.isna().sum().sum()), "kind": "int", "help": "Across all columns"},
                   {"label": "Duplicate rows", "value": int(work.duplicated().sum()), "kind": "int", "help": "Exact repeats"},
                   {"label": "Rows", "value": len(work), "kind": "int", "help": f"{work.shape[1]} columns"}], "")
        with st.expander("How the score is calculated"):
            show_table(pd.DataFrame({"Component": list(q["components"]), "Points": list(q["components"].values())}), None)
        a, b = st.columns(2)
        with a:
            section("Missing values")
            mr = C.missing_report(work)
            show_table(mr, 300)
            show_chart(V.quality_bar(mr, is_dark()), "prep_missing")
        with b:
            section("Data types")
            show_table(C.dtype_report(work, schema), 300)
        section("Duplicates")
        dup = C.duplicate_report(work)
        st.write(f"{dup['duplicate_rows']:,} duplicate row(s) ({dup['duplicate_pct']}%).")
        if dup["duplicate_rows"]:
            show_table(dup["examples"], 220)
        section("Invalid data")
        inv = C.invalid_report(work, schema)
        show_table(inv, 200) if len(inv) else st.success("No invalid values detected by the rules (negative amounts, blank text, bad dates).")
        section("Outliers (IQR rule)")
        orr = C.outlier_report(work)
        show_table(orr, 240) if len(orr) else st.info("No numeric column with enough spread for outlier detection.")

    with t_clean:
        st.caption("Operations work on a copy. Review the before/after comparison, then apply. Your original data is never changed silently, and an applied step can be undone.")
        op = st.selectbox("Operation", OPS, key=f"prep_op_{dm.dataset_id[:6]}")
        cols = list(work.columns)
        params: dict = {}
        if op == "Remove duplicates":
            params["subset"] = st.multiselect("Compare only these columns (empty = whole row)", cols, key="p_sub") or None
            params["keep"] = st.radio("Keep", ["first", "last"], horizontal=True, key="p_keep")
        elif op == "Handle missing values":
            has_missing = [c for c in cols if work[c].isna().any()]
            params["columns"] = st.multiselect("Columns", has_missing, default=has_missing, key="p_mcols")
            params["strategy"] = st.selectbox("Strategy", ["drop_rows", "mean", "median", "mode", "constant", "ffill", "bfill"], key="p_strat")
            if params["strategy"] == "constant":
                params["constant"] = st.text_input("Fill value", key="p_const")
        elif op == "Change data type":
            params["column"] = st.selectbox("Column", cols, key="p_dcol")
            params["target"] = st.selectbox("Convert to", ["number", "integer", "text", "date", "category", "boolean"], key="p_dtype")
        elif op == "Standardise categories":
            text_cols = [c for c in cols if not pd.api.types.is_numeric_dtype(work[c]) and not pd.api.types.is_datetime64_any_dtype(work[c])]
            params["columns"] = st.multiselect("Columns", text_cols, default=text_cols[:1], key="p_scols")
            params["case"] = st.selectbox("Letter case", ["title", "upper", "lower", "none"], key="p_case")
        elif op == "Remove invalid records":
            params["drop_negative"] = st.checkbox("Negative revenue / quantity / price", True, key="p_neg")
            params["drop_missing_dates"] = st.checkbox("Missing or invalid dates", False, key="p_nodate")
            params["drop_blank_text"] = st.checkbox("Blank text values", False, key="p_blank")
        elif op == "Remove outliers":
            nums = work.select_dtypes(include="number").columns.tolist()
            params["columns"] = st.multiselect("Columns", nums, default=nums[:1], key="p_ocols")
            params["factor"] = st.slider("IQR multiplier", 1.0, 3.0, 1.5, 0.1, key="p_ofac")
        elif op == "Apply transformation":
            nums = work.select_dtypes(include="number").columns.tolist()
            params["column"] = st.selectbox("Column", nums, key="p_tcol") if nums else None
            params["kind"] = st.selectbox("Transformation", ["log1p", "sqrt", "zscore", "minmax", "round0", "abs"], key="p_tkind")
            params["new_name"] = st.text_input("New column name (blank = automatic)", key="p_tname")

        if st.button("Preview result", type="primary", key="prep_preview_btn"):
            try:
                if op == "Remove duplicates":
                    new, log = C.remove_duplicates(work, params["subset"], params["keep"])
                elif op == "Handle missing values":
                    if not params["columns"]:
                        raise ValueError("Select at least one column with missing values.")
                    new, log = C.handle_missing(work, params["strategy"], params["columns"], params.get("constant"))
                elif op == "Change data type":
                    new, log = C.change_dtype(work, params["column"], params["target"])
                elif op == "Standardise categories":
                    if not params["columns"]:
                        raise ValueError("Select at least one column.")
                    new, log = C.standardize_categories(work, params["columns"], params["case"])
                elif op == "Remove invalid records":
                    new, log = C.remove_invalid(work, schema, params["drop_negative"], params["drop_missing_dates"], params["drop_blank_text"])
                elif op == "Remove outliers":
                    if not params["columns"]:
                        raise ValueError("Select at least one numeric column.")
                    new, log = C.remove_outliers(work, params["columns"], params["factor"])
                else:
                    if not params["column"]:
                        raise ValueError("No numeric column available.")
                    new, log = C.apply_transform(work, params["column"], params["kind"], params["new_name"] or None)
                st.session_state["prep_preview"] = {"rev": dm.revision, "df": new, "log": log}
            except (ValueError, KeyError) as exc:
                st.session_state.pop("prep_preview", None)
                st.error(str(exc))

        prev = st.session_state.get("prep_preview")
        if prev and prev["rev"] == dm.revision:
            st.success(prev["log"])
            section("Before vs after")
            show_table(C.before_after(work, prev["df"]), None)
            with st.expander("Preview of cleaned data"):
                show_table(prev["df"].head(100), 280)
            b1, b2 = st.columns(2)
            if b1.button("Apply to working dataset", type="primary", key="prep_apply", **stretch(st.button)):
                dm.apply_cleaned(prev["df"])
                st.session_state.pop("prep_preview", None)
                st.session_state["toast"] = "Cleaning step applied. Use Undo on Data Management to revert."
                st.rerun()
            if b2.button("Discard preview", key="prep_discard", **stretch(st.button)):
                st.session_state.pop("prep_preview", None)
                st.rerun()
        st.download_button("Download current working dataset (CSV)", R.csv_bytes(work), "cleaned_dataset.csv", "text/csv", key="prep_dl")
        if dm.history and st.button("Undo last applied step", key="prep_undo"):
            dm.undo_cleaning()
            st.session_state.pop("prep_preview", None)
            st.rerun()


# ------------------------------------------------------------------ 4 EDA
def page_eda(dm, df, spec):
    page_header("Exploratory Analysis", "Interactive charts for any column of the active dataset.", dm, A.describe_filters(spec))
    if not guard(dm, df):
        return
    schema, dark = dm.schema, is_dark()
    nums = [c for c in df.select_dtypes(include="number").columns if df[c].notna().any()]
    cats = [c for c in df.columns if c not in nums and not pd.api.types.is_datetime64_any_dtype(df[c]) and 1 < df[c].nunique() <= 200]
    dates = [c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])]
    tabs = st.tabs(["Distributions", "Relationships", "Correlation", "Categories", "Time series", "Outliers"])
    with tabs[0]:
        if not nums:
            st.info("No numeric columns available for distributions.")
        else:
            c1, c2, c3 = st.columns(3)
            col = c1.selectbox("Numeric column", nums, key="eda_dcol")
            kind = c2.radio("Chart type", ["Histogram", "Box plot"], horizontal=True, key="eda_dkind")
            if kind == "Histogram":
                bins = c3.slider("Bins", 5, 100, 30, key="eda_bins")
                show_chart(V.histogram(df, col, bins, dark), "eda_hist")
            else:
                by = c3.selectbox("Group by (optional)", ["(none)"] + cats, key="eda_boxby")
                show_chart(V.box_plot(df, col, None if by == "(none)" else by, dark), "eda_box")
    with tabs[1]:
        if len(nums) < 2:
            st.info("Scatter plots need at least two numeric columns.")
        else:
            c1, c2, c3 = st.columns(3)
            x = c1.selectbox("X axis", nums, index=0, key="eda_sx")
            y = c2.selectbox("Y axis", nums, index=min(1, len(nums) - 1), key="eda_sy")
            color = c3.selectbox("Colour by (optional)", ["(none)"] + cats, key="eda_sc")
            fig = V.scatter(df, x, y, None if color == "(none)" else color, dark)
            show_chart(fig, "eda_scatter") if fig else st.info("Not enough valid points for this scatter plot.")
    with tabs[2]:
        corr = A.correlations(df)
        if corr is None:
            st.info("A correlation matrix needs at least two varying numeric columns and 5 rows.")
        else:
            show_chart(V.corr_heatmap(corr, dark), "eda_corr")
            st.markdown("**Strongest pairs**")
            show_table(A.top_correlations(df, 8), 260)
            st.caption("Correlation shows association, not causation.")
    with tabs[3]:
        if not cats:
            st.info("No suitable categorical columns (2-200 distinct values).")
        else:
            c1, c2 = st.columns(2)
            col = c1.selectbox("Category column", cats, key="eda_ccol")
            kind = c2.radio("Chart type", ["Bar", "Donut"], horizontal=True, key="eda_ckind")
            dist = A.category_distribution(df, col, 20)
            show_chart(V.category_bar(dist, col, dark) if kind == "Bar" else V.donut(dist, col, "Count", f"Share of {col.replace('_', ' ')}", dark), "eda_cat")
            show_table(dist, 260)
    with tabs[4]:
        if not dates:
            st.info("No date column found in this dataset, so time-series charts are not available.")
        else:
            c1, c2, c3 = st.columns(3)
            dcol = c1.selectbox("Date column", dates, key="eda_tdate")
            val = c2.selectbox("Value", ["(row count)"] + nums, key="eda_tval")
            agg = c3.selectbox("Aggregation", ["sum", "mean", "median", "max", "min"], key="eda_tagg")
            fig = V.time_series(df, dcol, None if val == "(row count)" else val, agg, "M", dark)
            show_chart(fig, "eda_ts") if fig else st.info("Not enough dated rows for a time series.")
    with tabs[5]:
        orr = C.outlier_report(df)
        if orr.empty:
            st.info("No numeric column with enough spread for outlier detection.")
        else:
            c1, c2 = st.columns([2, 1])
            col = c1.selectbox("Column", orr["Column"].tolist(), key="eda_ocol")
            fac = c2.slider("IQR multiplier", 1.0, 3.0, 1.5, 0.1, key="eda_ofac")
            show_chart(V.outlier_plot(df, col, fac, dark), "eda_out")
            show_table(C.outlier_report(df, fac), 220)


# ------------------------------------------------------------------ 5 Business Intelligence
def page_bi(dm, df, spec):
    page_header("Business Intelligence", "KPIs, performance breakdowns, trends and automatic insights.", dm, A.describe_filters(spec))
    if not guard(dm, df):
        return
    schema, dark, cur = dm.schema, is_dark(), dm.currency
    sig = sig_of(dm, spec)
    kpi_cards(memo("kpis", sig, lambda: A.compute_kpis(df, schema)), cur)
    sales = A.has_sales_shape(df, schema)
    if sales:
        tabs = st.tabs(["Performance", "Trends", "Customers", "Insights"])
        with tabs[0]:
            for role, nice in (("category", "Category"), ("product", "Product"), ("location", "Region / location")):
                if schema.roles.get(role) in df.columns if schema.roles.get(role) else False:
                    section(f"Revenue by {nice.lower()}")
                    n = st.slider("Show top", 3, 30, 10, key=f"bi_n_{role}") if df[schema.roles[role]].nunique() > 3 else 99
                    b = A.revenue_breakdown(df, schema, role)
                    c1, c2 = st.columns([3, 2])
                    with c1:
                        show_chart(V.bar_breakdown(b, b.columns[0], "Revenue", f"Revenue by {b.columns[0].replace('_', ' ').lower()}", True, n, dark, cur), f"bi_{role}")
                    with c2:
                        show_table(b.head(n), 320)
            if not any(schema.roles.get(r) in df.columns for r in ("category", "product", "location") if schema.roles.get(r)):
                st.info("No category, product or location column was detected. Use Data Management → Column mapping to assign them.")
        with tabs[1]:
            mt = A.monthly_trend(df, schema)
            if mt is None:
                st.info("Trend charts need a date column; none is mapped.")
            else:
                show_chart(V.trend_line(mt, "Revenue", "Monthly revenue", dark), "bi_trend")
                show_chart(V.growth_bars(mt, dark), "bi_growth")
                show_table(mt, 280)
        with tabs[2]:
            cb = A.customer_behaviour(df, schema)
            if cb is None:
                st.info("No customer column mapped, so customer behaviour is not shown.")
            else:
                kpi_cards([{"label": "Customers", "value": cb["customers"], "kind": "int", "help": "Distinct"},
                           {"label": "Avg orders / customer", "value": cb["avg_orders_per_customer"], "kind": "number", "help": ""},
                           {"label": "Repeat customers", "value": cb["repeat_rate_pct"], "kind": "percent", "help": f"{cb['repeat_customers']:,} placed 2+ orders"}]
                          + ([{"label": "Top 10% revenue share", "value": cb["top10pct_revenue_share"], "kind": "percent", "help": "Concentration"}] if "top10pct_revenue_share" in cb else []), cur)
                c1, c2 = st.columns(2)
                with c1:
                    show_chart(V.bar_breakdown(cb["orders_distribution"], "Orders", "Customers", "Customers by number of orders", False, 20, dark), "bi_ord")
                with c2:
                    if "top_customers" in cb:
                        st.markdown("**Top customers by revenue**")
                        show_table(cb["top_customers"], 320)
                seg = dm.extras.get("segments")
                ccol = schema.roles.get("customer")
                if seg is not None and ccol and ccol in df.columns and "Segment" in seg.columns:
                    section("RFM segments (from the pipeline's customer_segments.csv)")
                    sub = seg[seg["Customer_ID"].isin(df[ccol].astype(str))]
                    show_chart(V.bar_breakdown(sub["Segment"].value_counts().rename_axis("Segment").reset_index(name="Customers"),
                                               "Segment", "Customers", "Customers by RFM segment", True, 12, dark), "bi_seg")
        with tabs[3]:
            _insights_block(dm, df, spec)
    else:
        tabs = st.tabs(["Statistics", "Categories", "Correlations", "Outliers", "Trend", "Insights"])
        with tabs[0]:
            ns = A.numeric_summary(df)
            show_table(ns, 380) if not ns.empty else st.info("No numeric columns.")
        with tabs[1]:
            cats = [c for c in df.columns if not pd.api.types.is_numeric_dtype(df[c]) and not pd.api.types.is_datetime64_any_dtype(df[c]) and 1 < df[c].nunique() <= 100]
            if not cats:
                st.info("No categorical columns with 2-100 values.")
            for c in cats[:4]:
                d = A.category_distribution(df, c, 12)
                a, b = st.columns([3, 2])
                with a:
                    show_chart(V.category_bar(d, c, dark), f"bi_gcat_{c}")
                with b:
                    show_table(d, 300)
        with tabs[2]:
            corr = A.correlations(df)
            show_chart(V.corr_heatmap(corr, dark), "bi_gcorr") if corr is not None else st.info("Need two varying numeric columns.")
        with tabs[3]:
            orr = C.outlier_report(df)
            show_table(orr, 260) if len(orr) else st.info("No outlier analysis possible.")
        with tabs[4]:
            dc, nums = schema.columns_of("datetime"), schema.columns_of("numeric")
            if dc:
                show_chart(V.time_series(df, dc[0], nums[0] if nums else None, "mean" if nums else "sum", "M", dark), "bi_gts")
            else:
                st.info("No date column, so trend analysis is not available for this dataset.")
        with tabs[5]:
            _insights_block(dm, df, spec)


def _insights_block(dm, df, spec):
    ins = memo("insights", sig_of(dm, spec), lambda: A.generate_insights(df, dm.schema, A.describe_filters(spec)))
    if not ins["sufficient"]:
        st.info(ins["note"])
        return
    for title, key in (("Key findings", "findings"), ("Significant trends", "trends"), ("Highest performers", "top"),
                       ("Lowest performers", "bottom"), ("Unusual observations", "unusual"),
                       ("Potential data-quality problems", "quality"), ("Recommended actions", "recommendations")):
        if ins.get(key):
            section(title)
            insight_list(ins[key])
    st.caption("Every statement above is computed from the filtered data; none is pre-written.")


# ------------------------------------------------------------------ 6 Reports & Export
def page_reports(dm, df, spec):
    page_header("Reports & Export", "Download datasets, reports and insights.", dm, A.describe_filters(spec))
    if not guard(dm, dm.working_df):
        return
    schema, ftxt, work = dm.schema, A.describe_filters(spec), dm.working_df
    sig = sig_of(dm, spec)
    ins = memo("insights", sig, lambda: A.generate_insights(df, schema, ftxt)) if len(df) else {"sufficient": False, "note": "No rows after filters."}
    kpis = memo("kpis", sig, lambda: A.compute_kpis(df, schema)) if len(df) else []
    section("Datasets")
    c1, c2, c3 = st.columns(3)
    if dm.source_df is not None:
        c1.download_button("Original uploaded dataset (CSV)", R.csv_bytes(dm.source_df), "original_upload.csv", "text/csv", key="rp_orig", **stretch(st.download_button))
    else:
        c1.button("Original uploaded dataset", disabled=True, help="Available after you upload a file.", key="rp_orig_off", **stretch(st.button))
    c2.download_button("Cleaned / working dataset (CSV)", R.csv_bytes(work), "working_dataset.csv", "text/csv", key="rp_work", **stretch(st.download_button))
    c3.download_button("Filtered dataset (CSV)", R.csv_bytes(df), "filtered_dataset.csv", "text/csv", key="rp_filt", **stretch(st.download_button))
    section("Summaries")
    c1, c2 = st.columns(2)
    if len(df):
        c1.download_button("Analytical summary (Markdown)", R.analytical_summary_text(df, schema, kpis, ins, dm.display_name, ftxt, dm.currency).encode("utf-8"),
                           "analytical_summary.md", "text/markdown", key="rp_sum", **stretch(st.download_button))
        c2.download_button("Business insights (TXT)", R.insights_text(ins, dm.display_name, ftxt).encode("utf-8"),
                           "business_insights.txt", "text/plain", key="rp_ins", **stretch(st.download_button))
    section("Excel reports", "Generated on demand")
    gen = st.session_state.setdefault("_reports", {})

    def make(name, fn):
        key = (name, sig)
        if st.button(f"Generate {name}", key=f"gen_{name}"):
            try:
                with st.spinner("Building workbook…"):
                    gen[name] = (sig, fn())
            except Exception as exc:
                st.error(f"Could not build {name}: {exc}")
        if name in gen and gen[name][0] == sig:
            st.download_button(f"Download {name}", gen[name][1], f"{name.lower().replace(' ', '_')}.xlsx",
                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=f"dl_{name}")

    a, b = st.columns(2)
    with a:
        make("Data quality report", lambda: R.quality_report_bytes(work, schema, dm.display_name))
        if len(df):
            make("Excel analysis report", lambda: R.generic_excel_report_bytes(df, schema, dm.display_name, ftxt, ins))
    with b:
        if len(df) and R.can_use_smartmart_report(df):
            make("SmartMart full report", lambda: R.smartmart_excel_report_bytes(df))
            st.caption("The project's original 10-sheet Excel report, built on the filtered data.")
        else:
            st.caption("The original 10-sheet SmartMart report is available when the active data has the full SmartMart schema.")
    section("Power BI & original pipeline assets", "Unchanged project files")
    for label, path in R.powerbi_assets():
        mime = "application/octet-stream"
        st.download_button(label, path.read_bytes(), path.name, mime, key=f"pbi_{path.name}")


# ------------------------------------------------------------------ 7 Settings
def page_settings(dm, df, spec):
    page_header("Settings", "Session information.", dm)
    section("Session")
    st.write(f"Active dataset: **{dm.display_name}** · status {dm.status[0]} · revision {dm.revision}")
    if st.button("Reset session (reload default data, clear filters)", key="reset_session"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()
    section("About")
    try:
        import streamlit
        sv = streamlit.__version__
    except Exception:
        sv = "?"
    st.caption(f"Python {platform.python_version()} · Streamlit {sv} · pandas {pd.__version__}")
    st.caption("Original Streamlit dashboard (6 SmartMart pages) is still available: `python -m streamlit run streamlit_app_classic.py`.")


PAGES = {"Overview": page_overview, "Data Management": page_data_management, "Data Preparation": page_data_preparation,
         "Exploratory Analysis": page_eda, "Business Intelligence": page_bi,
         "Reports & Export": page_reports, "Settings": page_settings}
