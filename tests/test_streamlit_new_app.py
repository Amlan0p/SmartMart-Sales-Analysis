"""Runs the NEW app with streamlit's own test harness. Skipped (visibly) when streamlit/plotly
are not installed; on a normal install it must pass."""
import pytest

import config


def test_new_app_runs_every_page_and_empty_state():
    pytest.importorskip("streamlit.testing.v1")
    pytest.importorskip("plotly")
    from streamlit.testing.v1 import AppTest
    from src import dashboard_logic as L
    if L.missing_files():
        pytest.skip("run `python main.py` first")
    app = AppTest.from_file(str(config.BASE_DIR / "streamlit_app.py"), default_timeout=120)
    app.run()
    assert not app.exception
    from src.ui_components import NAV_LABELS
    for label in NAV_LABELS:
        app.session_state["nav"] = label
        app.run()
        assert not app.exception, label
    app.session_state["dm"].clear()          # Remove All Data equivalent
    for label in NAV_LABELS:
        app.session_state["nav"] = label
        app.run()
        assert not app.exception, f"empty workspace: {label}"
    app.session_state["dm"].load_default()   # Load Default Dashboard equivalent
    app.run()
    assert not app.exception
