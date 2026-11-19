"""
SmartMart Analytics Platform - dynamic Streamlit application.

    python -m pip install -r requirements.txt
    python -m streamlit run streamlit_app.py

All pages work on the ACTIVE dataset held by src/dataset_manager.py (built-in
SmartMart CSVs by default, or an uploaded / manually entered dataset). The
original six-page SmartMart dashboard is kept in streamlit_app_classic.py.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
if str(PROJECT_DIR) not in sys.path:   # make `config` and `src` importable from any working directory
    sys.path.insert(0, str(PROJECT_DIR))

import streamlit as st

st.set_page_config(page_title="SmartMart Analytics", page_icon="📊", layout="wide", initial_sidebar_state="expanded")

from src import dynamic_analytics as A                      # noqa: E402
from src import ui_components as U                          # noqa: E402
from src.ui_pages import PAGES                              # noqa: E402


def main() -> None:
    U.inject_css()
    dm = U.get_dm()
    page = U.render_sidebar(dm)
    spec = U.sidebar_filters(dm)
    df = A.apply_filters(dm.working_df, spec) if dm.has_columns else dm.working_df
    PAGES[page](dm, df, spec)


main()
