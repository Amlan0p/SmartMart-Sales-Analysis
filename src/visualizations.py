"""
visualizations.py

Plotly figure builders for the dynamic dashboard. Each builder returns
``None`` when the data it needs is not available, so the UI can skip the
chart instead of drawing an empty or misleading one. Titles and axis labels
are generated from the column names that are passed in.

(The original matplotlib charts in src/visualization.py are unchanged and
still used by the batch pipeline.)
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

ACCENT = "#4F6BED"
PALETTE = ["#4F6BED", "#22A699", "#F2A65A", "#9B7EDE", "#E86A92", "#5BB4E5", "#8C9BAA", "#D4A72C"]
FONT = "Inter, Segoe UI, Roboto, Helvetica, Arial, sans-serif"

THEMES = {
    "light": {"bg": "#FFFFFF", "paper": "rgba(0,0,0,0)", "text": "#1F2937", "muted": "#6B7280",
              "grid": "#E5E7EB", "card": "#FFFFFF", "surface": "#F6F7F9", "border": "#E5E7EB"},
    "dark": {"bg": "#0F1218", "paper": "rgba(0,0,0,0)", "text": "#E5E7EB", "muted": "#9CA3AF",
             "grid": "#2A303B", "card": "#171B23", "surface": "#0F1218", "border": "#2A303B"},
}


def _plain(df: pd.DataFrame) -> pd.DataFrame:
    """Plotly-friendly copy (pandas string/Int64 dtypes -> object/float)."""
    out = df.copy()
    for c in out.columns:
        s = out[c]
        if isinstance(s.dtype, pd.StringDtype) or (pd.api.types.is_string_dtype(s) and not pd.api.types.is_numeric_dtype(s)):
            out[c] = s.astype(object)
        elif isinstance(s.dtype, pd.api.extensions.ExtensionDtype) and pd.api.types.is_numeric_dtype(s) \
                and not pd.api.types.is_bool_dtype(s):
            out[c] = s.astype("float64")
    return out


def style(fig: go.Figure, dark: bool = False, height: int = 380, title: str | None = None) -> go.Figure:
    t = THEMES["dark" if dark else "light"]
    fig.update_layout(
        template="plotly_dark" if dark else "plotly_white",
        height=height, margin=dict(l=12, r=12, t=52, b=12),
        paper_bgcolor=t["paper"], plot_bgcolor=t["paper"],
        font=dict(family=FONT, color=t["text"], size=12),
        title=dict(text=title or (fig.layout.title.text if fig.layout.title and fig.layout.title.text else ""),
                   font=dict(size=14, color=t["text"]), x=0, xanchor="left"),
        legend=dict(title_text="", orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    font=dict(color=t["text"], size=12)),
        colorway=PALETTE, hoverlabel=dict(font_family=FONT),
    )
    fig.update_xaxes(gridcolor=t["grid"], zerolinecolor=t["grid"], linecolor=t["grid"])
    fig.update_yaxes(gridcolor=t["grid"], zerolinecolor=t["grid"], linecolor=t["grid"])
    return fig


def _nice(name: str) -> str:
    return str(name).replace("_", " ")


# ------------------------------------------------------------- breakdowns
def bar_breakdown(frame: pd.DataFrame | None, label: str, value: str, title: str,
                  horizontal: bool = True, top: int = 15, dark: bool = False, currency: str = "") -> go.Figure | None:
    if frame is None or frame.empty or label not in frame.columns or value not in frame.columns:
        return None
    f = _plain(frame).head(top)
    if horizontal:
        f = f.iloc[::-1]
        fig = px.bar(f, x=value, y=label, orientation="h", color_discrete_sequence=[ACCENT])
    else:
        fig = px.bar(f, x=label, y=value, color_discrete_sequence=[ACCENT])
    fig.update_xaxes(title=_nice(value if horizontal else label))
    fig.update_yaxes(title=_nice(label if horizontal else value))
    if horizontal:
        fig.update_yaxes(type="category")
    return style(fig, dark, max(300, 26 * len(f) + 120) if horizontal else 360, title)


def donut(frame: pd.DataFrame | None, label: str, value: str, title: str, dark: bool = False, top: int = 8) -> go.Figure | None:
    if frame is None or frame.empty or (frame[value] < 0).any() or frame[value].sum() <= 0:
        return None
    f = _plain(frame).head(top)
    fig = px.pie(f, names=label, values=value, hole=0.58, color_discrete_sequence=PALETTE)
    fig.update_traces(textinfo="percent", sort=False)
    fig = style(fig, dark, 380, title)
    # legend below the ring so it can never collide with the title
    fig.update_layout(legend=dict(orientation="h", yanchor="top", y=-0.02, xanchor="center", x=0.5,
                                  font=dict(color=THEMES["dark" if dark else "light"]["text"], size=12)),
                      margin=dict(l=12, r=12, t=52, b=56))
    return fig


def trend_line(trend: pd.DataFrame | None, value: str, title: str | None = None, dark: bool = False) -> go.Figure | None:
    if trend is None or len(trend) < 2 or value not in trend.columns:
        return None
    t = _plain(trend)
    fig = px.line(t, x="Month", y=value, markers=True, color_discrete_sequence=[ACCENT])
    fig.update_xaxes(title="Month")
    fig.update_yaxes(title=_nice(value))
    return style(fig, dark, 360, title or f"{_nice(value)} by month")


def growth_bars(trend: pd.DataFrame | None, dark: bool = False) -> go.Figure | None:
    if trend is None or "MoM Growth %" not in trend.columns or trend["MoM Growth %"].dropna().empty:
        return None
    t = _plain(trend).dropna(subset=["MoM Growth %"])
    colors = ["#22A699" if v >= 0 else "#E5484D" for v in t["MoM Growth %"]]
    fig = go.Figure(go.Bar(x=t["Month"], y=t["MoM Growth %"], marker_color=colors))
    fig.update_xaxes(title="Month")
    fig.update_yaxes(title="Month-over-month change (%)")
    return style(fig, dark, 300, "Month-over-month growth")


# ------------------------------------------------------------- EDA charts
def histogram(df: pd.DataFrame, col: str, bins: int = 30, dark: bool = False) -> go.Figure | None:
    if col not in df.columns or not pd.api.types.is_numeric_dtype(df[col]) or df[col].dropna().empty:
        return None
    fig = px.histogram(_plain(df[[col]].dropna()), x=col, nbins=bins, color_discrete_sequence=[ACCENT])
    fig.update_xaxes(title=_nice(col))
    fig.update_yaxes(title="Count")
    fig.update_traces(marker_line_width=0)
    return style(fig, dark, 340, f"Distribution of {_nice(col)}")


def box_plot(df: pd.DataFrame, col: str, by: str | None = None, dark: bool = False) -> go.Figure | None:
    if col not in df.columns or not pd.api.types.is_numeric_dtype(df[col]) or df[col].dropna().empty:
        return None
    use = df[[col] + ([by] if by and by in df.columns else [])].dropna(subset=[col])
    if by and by in df.columns:
        top = use[by].astype(object).value_counts().head(12).index
        use = use[use[by].isin(top)]
        fig = px.box(_plain(use), x=by, y=col, points="outliers", color_discrete_sequence=[ACCENT])
        fig.update_xaxes(title=_nice(by))
        title = f"{_nice(col)} by {_nice(by)}"
    else:
        fig = px.box(_plain(use), y=col, points="outliers", color_discrete_sequence=[ACCENT])
        title = f"Spread of {_nice(col)}"
    fig.update_yaxes(title=_nice(col))
    return style(fig, dark, 360, title)


def scatter(df: pd.DataFrame, x: str, y: str, color: str | None = None, dark: bool = False,
            max_points: int = 5000) -> go.Figure | None:
    for c in (x, y):
        if c not in df.columns or not pd.api.types.is_numeric_dtype(df[c]):
            return None
    use = df[[x, y] + ([color] if color and color in df.columns else [])].dropna(subset=[x, y])
    if len(use) < 2:
        return None
    note = ""
    if len(use) > max_points:
        use = use.sample(max_points, random_state=0)
        note = f" (random sample of {max_points:,})"
    use = _plain(use)
    if color and color in use.columns and use[color].nunique() > 12:
        color = None
    fig = px.scatter(use, x=x, y=y, color=color if color in use.columns else None, opacity=0.65,
                     color_discrete_sequence=PALETTE)
    fig.update_xaxes(title=_nice(x))
    fig.update_yaxes(title=_nice(y))
    return style(fig, dark, 400, f"{_nice(y)} vs {_nice(x)}{note}")


def corr_heatmap(corr: pd.DataFrame | None, dark: bool = False) -> go.Figure | None:
    if corr is None or corr.shape[0] < 2:
        return None
    fig = go.Figure(go.Heatmap(z=corr.values, x=[_nice(c) for c in corr.columns], y=[_nice(c) for c in corr.index],
                               zmin=-1, zmax=1, colorscale="RdBu", reversescale=True,
                               text=np.round(corr.values, 2), texttemplate="%{text}",
                               hovertemplate="%{y} vs %{x}: %{z:.2f}<extra></extra>"))
    fig.update_yaxes(autorange="reversed")
    return style(fig, dark, max(340, 42 * len(corr) + 120), "Correlation matrix (Pearson)")


def category_bar(dist: pd.DataFrame | None, col: str, dark: bool = False) -> go.Figure | None:
    if dist is None or dist.empty or "Count" not in dist.columns:
        return None
    return bar_breakdown(dist, col, "Count", f"Distribution of {_nice(col)}", True, 20, dark)


def time_series(df: pd.DataFrame, date_col: str, value: str | None, agg: str = "sum", freq: str = "M",
                dark: bool = False) -> go.Figure | None:
    if date_col not in df.columns:
        return None
    d = pd.to_datetime(df[date_col], errors="coerce")
    ok = d.notna()
    if ok.sum() < 2:
        return None
    if value is None:
        s = pd.Series(1, index=df.index)[ok].groupby(d[ok].dt.to_period(freq)).sum()
        label, title = "Records", f"Records per {'month' if freq == 'M' else 'period'}"
    else:
        if value not in df.columns or not pd.api.types.is_numeric_dtype(df[value]):
            return None
        s = df.loc[ok, value].groupby(d[ok].dt.to_period(freq)).agg(agg)
        label, title = _nice(value), f"{agg.title()} of {_nice(value)} over time"
    t = s.rename(label).reset_index()
    t.columns = ["Period", label]
    t["Period"] = t["Period"].dt.to_timestamp()
    if len(t) < 2:
        return None
    fig = px.line(_plain(t), x="Period", y=label, markers=True, color_discrete_sequence=[ACCENT])
    fig.update_xaxes(title=_nice(date_col))
    fig.update_yaxes(title=label)
    return style(fig, dark, 360, title)


def outlier_plot(df: pd.DataFrame, col: str, factor: float = 1.5, dark: bool = False) -> go.Figure | None:
    if col not in df.columns or not pd.api.types.is_numeric_dtype(df[col]):
        return None
    s = df[col].dropna()
    if len(s) < 8 or s.nunique() < 4:
        return None
    q1, q3 = s.quantile(0.25), s.quantile(0.75)
    iqr = q3 - q1
    if iqr == 0:
        return None
    lo, hi = q1 - factor * iqr, q3 + factor * iqr
    if len(s) > 6000:
        s = s.sample(6000, random_state=0)
    is_out = (s < lo) | (s > hi)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=s.index[~is_out], y=s[~is_out], mode="markers", name="Within range",
                             marker=dict(color=ACCENT, size=5, opacity=0.5)))
    fig.add_trace(go.Scatter(x=s.index[is_out], y=s[is_out], mode="markers", name="Outlier",
                             marker=dict(color="#E5484D", size=7)))
    fig.add_hline(y=hi, line_dash="dash", line_color="#E5484D", annotation_text="upper bound")
    fig.add_hline(y=lo, line_dash="dash", line_color="#E5484D", annotation_text="lower bound")
    fig.update_xaxes(title="Row index")
    fig.update_yaxes(title=_nice(col))
    return style(fig, dark, 380, f"Outliers in {_nice(col)} (IQR x {factor:g})")


def quality_bar(missing: pd.DataFrame, dark: bool = False) -> go.Figure | None:
    m = missing[missing["Missing"] > 0]
    if m.empty:
        return None
    return bar_breakdown(m.rename(columns={"Missing %": "Missing percent"}), "Column", "Missing percent",
                         "Missing values by column (%)", True, 15, dark)
