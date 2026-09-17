"""
Chart builders.

Every chart in this file follows one procedure: pick the form from the data's
job, then assign colour by the job it does (identity / magnitude / polarity /
emphasis), then apply fixed mark specs. Rules that are never broken here:

  * one y-axis, ever -- no dual-scale charts
  * thin marks (<= 24px bars), 4px rounded data ends, solid hairline gridlines
  * a 2px surface-coloured gap separates touching marks; no borders around marks
  * a legend whenever there are 2+ series, none when there is 1
  * labels are selective (tips and endpoints), never a number on every point
  * text wears ink tokens, never the series colour
  * every chart ships a table-view twin, so no value is gated behind a tooltip
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ui import theme as T

PLOTLY_CONFIG = {
    "displaylogo": False,
    "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d", "zoomIn2d", "zoomOut2d"],
    "responsive": True,
}

BAR_MAX_PX = 24


def _layout(height: int, showlegend: bool = False, **kwargs) -> dict:
    base = dict(
        height=height,
        paper_bgcolor=T.SURFACE,
        plot_bgcolor=T.SURFACE,
        font=dict(family=T.FONT, color=T.TEXT_2, size=12),
        margin=dict(l=8, r=18, t=10, b=8),
        showlegend=showlegend,
        legend=dict(orientation="h", yanchor="top", y=-0.22, x=0,
                    font=dict(color=T.TEXT_2, size=11),
                    bgcolor="rgba(0,0,0,0)"),
        hoverlabel=dict(bgcolor=T.SURFACE_RAISED, bordercolor=T.BORDER,
                        font=dict(color=T.TEXT_1, family=T.FONT, size=12)),
        xaxis=dict(gridcolor=T.GRID, griddash="solid", zeroline=False,
                   linecolor=T.AXIS, tickfont=dict(color=T.TEXT_MUTED, size=11),
                   title=dict(font=dict(color=T.TEXT_MUTED, size=11))),
        yaxis=dict(gridcolor=T.GRID, griddash="solid", zeroline=False,
                   linecolor=T.AXIS, tickfont=dict(color=T.TEXT_MUTED, size=11),
                   title=dict(font=dict(color=T.TEXT_MUTED, size=11))),
    )
    base.update(kwargs)
    return base


def render(fig: go.Figure, table: pd.DataFrame | None = None,
           table_label: str = "View the numbers", key: str | None = None) -> None:
    """Draw a chart plus its table-view twin."""
    st.plotly_chart(fig, config=PLOTLY_CONFIG, width="stretch", key=key)
    if table is not None and not table.empty:
        with st.expander(table_label):
            st.dataframe(table, width="stretch", hide_index=True)


# ---------------------------------------------------------------------------
# Part-to-whole: where the footprint comes from
# ---------------------------------------------------------------------------

def footprint_split(counted: dict[str, float], labels: dict[str, str],
                    colors: dict[str, str]) -> tuple[go.Figure, pd.DataFrame]:
    """
    Job: part-to-whole across 5-6 long-named categories.
    Form: a single horizontal stacked bar (not a pie -- a pie of six close
    values is unreadable and part-to-whole at a glance caps out at six).
    Colour: categorical identity, fixed per module.
    """
    total = sum(counted.values()) or 1.0
    fig = go.Figure()
    for module, value in sorted(counted.items(), key=lambda kv: kv[1], reverse=True):
        fig.add_trace(go.Bar(
            x=[value], y=["Annual footprint"], orientation="h",
            name=labels.get(module, module),
            marker=dict(
                color=colors.get(module, T.SERIES[0]),
                # A 1px line in the SURFACE colour reads as a 2px gap between
                # segments. It is negative space, not a border around the mark.
                line=dict(color=T.SURFACE, width=1),
            ),
            hovertemplate=(f"<b>{labels.get(module, module)}</b><br>"
                           "%{x:,.0f} kg CO₂e/yr<br>"
                           f"{value / total:.0%} of total<extra></extra>"),
        ))
    # Height covers the bar, the legend beneath it and the x-axis band, so the
    # card never grows a nested scrollbar to reach its own axis labels.
    fig.update_layout(**_layout(
        190, showlegend=True, barmode="stack", bargap=0.6,
        xaxis=dict(gridcolor=T.GRID, griddash="solid", zeroline=False,
                   linecolor=T.AXIS, tickfont=dict(color=T.TEXT_MUTED, size=11),
                   title=dict(text="kg CO₂e per year", font=dict(color=T.TEXT_MUTED, size=11))),
        yaxis=dict(showgrid=False, showticklabels=False, zeroline=False,
                   linecolor="rgba(0,0,0,0)"),
    ))
    table = pd.DataFrame(
        [{"Module": labels.get(m, m), "kg CO₂e / year": round(v),
          "Share": f"{v / total:.1%}"}
         for m, v in sorted(counted.items(), key=lambda kv: kv[1], reverse=True)]
    )
    return fig, table


def ranked_modules(counted: dict[str, float], labels: dict[str, str],
                   colors: dict[str, str]) -> tuple[go.Figure, pd.DataFrame]:
    """
    Job: compare magnitude, low -> high, across named categories.
    Form: horizontal bars, sorted. Colour stays the module's own identity hue
    so it matches the stacked chart above -- never a value ramp, which would
    just re-encode bar length as darkness.
    """
    rows = sorted(counted.items(), key=lambda kv: kv[1])
    names = [labels.get(m, m) for m, _ in rows]
    values = [v for _, v in rows]
    fig = go.Figure(go.Bar(
        x=values, y=names, orientation="h",
        marker=dict(color=[colors.get(m, T.SERIES[0]) for m, _ in rows],
                    cornerradius=4),
        text=[f"{v:,.0f}" for v in values],
        textposition="outside",
        textfont=dict(color=T.TEXT_2, size=11),
        hovertemplate="<b>%{y}</b><br>%{x:,.0f} kg CO₂e/yr<extra></extra>",
        width=[0.55] * len(rows),
    ))
    top = max(values) if values else 1
    fig.update_layout(**_layout(
        max(180, 44 * len(rows) + 60),
        xaxis=dict(gridcolor=T.GRID, griddash="solid", zeroline=False,
                   linecolor=T.AXIS, tickfont=dict(color=T.TEXT_MUTED, size=11),
                   range=[0, top * 1.18],
                   title=dict(text="kg CO₂e per year", font=dict(color=T.TEXT_MUTED, size=11))),
        yaxis=dict(showgrid=False, zeroline=False, linecolor="rgba(0,0,0,0)",
                   tickfont=dict(color=T.TEXT_2, size=12)),
    ))
    table = pd.DataFrame([{"Module": n, "kg CO₂e / year": round(v)}
                          for n, v in zip(reversed(names), reversed(values))])
    return fig, table


def item_breakdown(breakdown: dict[str, float], unit: str = "kg CO₂e / year",
                   limit: int = 10, color: str | None = None
                   ) -> tuple[go.Figure, pd.DataFrame]:
    """
    Job: rank the line items inside one module.
    Form: horizontal bars, one series -> ONE colour and no legend box (the
    section heading already says what is plotted).
    """
    rows = sorted(breakdown.items(), key=lambda kv: kv[1], reverse=True)
    shown = list(reversed(rows[:limit]))
    names = [k for k, _ in shown]
    values = [v for _, v in shown]
    hue = color or T.SERIES[0]
    fig = go.Figure(go.Bar(
        x=values, y=names, orientation="h",
        marker=dict(color=hue, cornerradius=4),
        text=[f"{v:,.0f}" for v in values],
        textposition="outside",
        textfont=dict(color=T.TEXT_2, size=11),
        hovertemplate="<b>%{y}</b><br>%{x:,.1f} " + unit + "<extra></extra>",
        width=[0.6] * len(shown),
    ))
    top = max(values) if values else 1
    fig.update_layout(**_layout(
        max(170, 38 * len(shown) + 60),
        xaxis=dict(gridcolor=T.GRID, griddash="solid", zeroline=False,
                   linecolor=T.AXIS, tickfont=dict(color=T.TEXT_MUTED, size=11),
                   range=[0, top * 1.2],
                   title=dict(text=unit, font=dict(color=T.TEXT_MUTED, size=11))),
        yaxis=dict(showgrid=False, zeroline=False, linecolor="rgba(0,0,0,0)",
                   tickfont=dict(color=T.TEXT_2, size=11)),
    ))
    table = pd.DataFrame([{"Item": k, unit: round(v, 1)} for k, v in rows])
    return fig, table


# ---------------------------------------------------------------------------
# Emphasis: you against the world
# ---------------------------------------------------------------------------

def benchmark_chart(rows: list[tuple[str, float]]) -> tuple[go.Figure, pd.DataFrame]:
    """
    Job: one series is the point, the rest are context.
    Form: EMPHASIS -- "You" in the accent hue, every reference marker in the
    de-emphasis grey. One series, so no legend.
    """
    ordered = sorted(rows, key=lambda kv: kv[1])
    names = [n for n, _ in ordered]
    values = [v for _, v in ordered]
    colors = [T.SERIES[0] if n == "You" else T.DEEMPHASIS for n in names]
    fig = go.Figure(go.Bar(
        x=values, y=names, orientation="h",
        marker=dict(color=colors, cornerradius=4),
        text=[f"{v:,.0f}" for v in values],
        textposition="outside",
        textfont=dict(color=T.TEXT_2, size=11),
        hovertemplate="<b>%{y}</b><br>%{x:,.0f} kg CO₂e per person per year<extra></extra>",
        width=[0.55] * len(ordered),
    ))
    top = max(values) if values else 1
    fig.update_layout(**_layout(
        max(200, 42 * len(ordered) + 60),
        xaxis=dict(gridcolor=T.GRID, griddash="solid", zeroline=False,
                   linecolor=T.AXIS, tickfont=dict(color=T.TEXT_MUTED, size=11),
                   range=[0, top * 1.18],
                   title=dict(text="kg CO₂e per person per year",
                              font=dict(color=T.TEXT_MUTED, size=11))),
        yaxis=dict(showgrid=False, zeroline=False, linecolor="rgba(0,0,0,0)",
                   tickfont=dict(color=T.TEXT_2, size=12)),
    ))
    table = pd.DataFrame([{"Reference": n, "kg CO₂e / person / year": round(v)}
                          for n, v in reversed(ordered)])
    return fig, table


# ---------------------------------------------------------------------------
# Polarity: signed values
# ---------------------------------------------------------------------------

def diverging_bars(rows: list[tuple[str, float]], unit: str = "kg CO₂e / year",
                   pos_label: str = "emits", neg_label: str = "avoids"
                   ) -> tuple[go.Figure, pd.DataFrame]:
    """
    Job: above/below a baseline.
    Form: diverging bars around zero. Colour: a warm/cool pair reading as
    opposites (blue = avoided, red = emitted) with a neutral zero rule --
    never a hue at the midpoint.
    """
    ordered = sorted(rows, key=lambda kv: kv[1])
    names = [n for n, _ in ordered]
    values = [v for _, v in ordered]
    colors = [T.DIVERGE_POS if v > 0 else T.DIVERGE_NEG for v in values]
    fig = go.Figure(go.Bar(
        x=values, y=names, orientation="h",
        marker=dict(color=colors, cornerradius=4),
        text=[f"{v:,.0f}" for v in values],
        textposition="outside",
        textfont=dict(color=T.TEXT_2, size=11),
        customdata=[pos_label if v > 0 else neg_label for v in values],
        hovertemplate="<b>%{y}</b><br>%{customdata} %{x:,.0f} " + unit + "<extra></extra>",
        width=[0.58] * len(ordered),
    ))
    span = max((abs(v) for v in values), default=1) * 1.25
    fig.update_layout(**_layout(
        max(200, 40 * len(ordered) + 70),
        xaxis=dict(gridcolor=T.GRID, griddash="solid", zeroline=True,
                   zerolinecolor=T.AXIS, zerolinewidth=1,
                   linecolor="rgba(0,0,0,0)", range=[-span, span],
                   tickfont=dict(color=T.TEXT_MUTED, size=11),
                   title=dict(text=unit, font=dict(color=T.TEXT_MUTED, size=11))),
        yaxis=dict(showgrid=False, zeroline=False, linecolor="rgba(0,0,0,0)",
                   tickfont=dict(color=T.TEXT_2, size=11)),
    ))
    table = pd.DataFrame([{"Item": n, unit: round(v, 1)}
                          for n, v in reversed(ordered)])
    return fig, table


def macc_chart(actions: list[dict]) -> tuple[go.Figure, pd.DataFrame, int]:
    """
    Marginal abatement cost curve: the analyst's chart for "what should I do
    first". Bar WIDTH is how much carbon an action saves; bar HEIGHT is what
    each tonne costs (negative height = the action pays you back).

    Job: polarity against a zero cost line -> diverging colour.
    """
    ordered = sorted(actions, key=lambda a: a["cost_per_tonne"])
    fig = go.Figure()
    cumulative = 0.0
    for action in ordered:
        tonnes = max(action["tonnes"], 0.001)
        cost = action["cost_per_tonne"]
        fig.add_trace(go.Bar(
            x=[cumulative + tonnes / 2], y=[cost], width=[tonnes],
            marker=dict(color=T.DIVERGE_NEG if cost < 0 else T.DIVERGE_POS,
                        line=dict(color=T.SURFACE, width=1)),
            name=action["title"], showlegend=False,
            hovertemplate=(f"<b>{action['title']}</b><br>"
                           f"Saves {action['annual_kg']:,.0f} kg CO₂e/yr<br>"
                           f"Net cost ₹{cost:,.0f} per tonne avoided<extra></extra>"),
        ))
        cumulative += tonnes
    # A behaviour change can score -300,000 rupees per tonne, which would flatten
    # every other bar to a hairline. The axis is clamped to a readable window and
    # the table view carries the exact numbers, so nothing is hidden.
    costs = [a["cost_per_tonne"] for a in ordered] or [0.0]
    clamp = 10_000.0
    low = max(min(costs) * 1.15, -clamp)
    high = min(max(max(costs) * 1.15, 1_000.0), clamp)
    clipped = [a for a in ordered if not (low <= a["cost_per_tonne"] <= high)]

    fig.update_layout(**_layout(
        320, barmode="overlay",
        xaxis=dict(gridcolor=T.GRID, griddash="solid", zeroline=False,
                   linecolor=T.AXIS, tickfont=dict(color=T.TEXT_MUTED, size=11),
                   title=dict(text="Cumulative CO₂e avoided (tonnes per year)",
                              font=dict(color=T.TEXT_MUTED, size=11))),
        yaxis=dict(gridcolor=T.GRID, griddash="solid", zeroline=True,
                   zerolinecolor=T.AXIS, zerolinewidth=1, linecolor="rgba(0,0,0,0)",
                   tickfont=dict(color=T.TEXT_MUTED, size=11), range=[low, high],
                   title=dict(text="₹ per tonne avoided",
                              font=dict(color=T.TEXT_MUTED, size=11))),
    ))
    fig.add_annotation(
        x=0, y=0, xref="paper", yref="y", xanchor="left", yshift=9,
        text="above this line costs money · below it saves money",
        showarrow=False, font=dict(color=T.TEXT_MUTED, size=10),
    )
    table = pd.DataFrame([
        {"Action": a["title"], "kg CO₂e saved / year": round(a["annual_kg"]),
         "₹ per tonne avoided": round(a["cost_per_tonne"]),
         "Net ₹ / year": round(a["annual_net_inr"])}
        for a in ordered
    ])
    return fig, table, len(clipped)


# ---------------------------------------------------------------------------
# Change over time
# ---------------------------------------------------------------------------

def pathway_chart(years: list[int], baseline: list[float], planned: list[float],
                  target_value: float, target_label: str
                  ) -> tuple[go.Figure, pd.DataFrame]:
    """
    Job: trend over time, two series plus a threshold.
    Form: 2px lines with >=8px end markers carrying a 2px surface ring, direct
    end labels, and the budget as a dashed REFERENCE line -- dashing is
    legitimate on a threshold, never on a gridline.
    """
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=years, y=baseline, mode="lines+markers", name="If nothing changes",
        line=dict(color=T.DEEMPHASIS, width=2, shape="linear"),
        marker=dict(size=8, color=T.DEEMPHASIS,
                    line=dict(color=T.SURFACE, width=2)),
        hovertemplate="%{x}<br>%{y:,.0f} kg CO₂e<extra>If nothing changes</extra>",
    ))
    fig.add_trace(go.Scatter(
        x=years, y=planned, mode="lines+markers", name="With your plan",
        line=dict(color=T.SERIES[0], width=2),
        marker=dict(size=8, color=T.SERIES[0],
                    line=dict(color=T.SURFACE, width=2)),
        hovertemplate="%{x}<br>%{y:,.0f} kg CO₂e<extra>With your plan</extra>",
    ))
    fig.add_hline(y=target_value, line=dict(color=T.GOOD, width=2, dash="dash"),
                  annotation_text=target_label, annotation_position="top left",
                  annotation_font=dict(color=T.GOOD, size=11))
    # Direct end labels: the endpoint is the one place a label earns its space.
    for series, color, name in ((baseline, T.DEEMPHASIS, "no change"),
                                (planned, T.SERIES[0], "your plan")):
        fig.add_annotation(x=years[-1], y=series[-1], text=f"{series[-1]:,.0f}",
                           showarrow=False, xshift=26,
                           font=dict(color=T.TEXT_2, size=11))
    fig.update_layout(**_layout(
        330, showlegend=True, hovermode="x unified",
        xaxis=dict(gridcolor=T.GRID, griddash="solid", zeroline=False,
                   linecolor=T.AXIS, tickfont=dict(color=T.TEXT_MUTED, size=11),
                   dtick=1, title=dict(text="", font=dict(color=T.TEXT_MUTED))),
        yaxis=dict(gridcolor=T.GRID, griddash="solid", zeroline=False,
                   linecolor="rgba(0,0,0,0)", rangemode="tozero",
                   tickfont=dict(color=T.TEXT_MUTED, size=11),
                   title=dict(text="kg CO₂e per year",
                              font=dict(color=T.TEXT_MUTED, size=11))),
        margin=dict(l=8, r=60, t=24, b=8),
    ))
    table = pd.DataFrame({"Year": years,
                          "If nothing changes (kg)": [round(v) for v in baseline],
                          "With your plan (kg)": [round(v) for v in planned]})
    return fig, table


def dumbbell(rows: list[tuple[str, float, float]],
             before_label: str = "Now", after_label: str = "After changes",
             unit: str = "kg CO₂e / year") -> tuple[go.Figure, pd.DataFrame]:
    """
    Job: before -> after, per item.
    Form: dumbbell -- one hue in two shades, connected by a thin rule. Far
    clearer than two bar series side by side.
    """
    ordered = sorted(rows, key=lambda r: r[1])
    names = [r[0] for r in ordered]
    before = [r[1] for r in ordered]
    after = [r[2] for r in ordered]

    fig = go.Figure()
    for name, b, a in ordered:
        fig.add_trace(go.Scatter(
            x=[b, a], y=[name, name], mode="lines",
            line=dict(color=T.AXIS, width=2), showlegend=False,
            hoverinfo="skip",
        ))
    fig.add_trace(go.Scatter(
        x=before, y=names, mode="markers", name=before_label,
        marker=dict(size=11, color=T.SEQUENTIAL[2],
                    line=dict(color=T.SURFACE, width=2)),
        hovertemplate="<b>%{y}</b><br>" + before_label + ": %{x:,.0f} " + unit + "<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=after, y=names, mode="markers", name=after_label,
        marker=dict(size=11, color=T.SEQUENTIAL[6],
                    line=dict(color=T.SURFACE, width=2)),
        hovertemplate="<b>%{y}</b><br>" + after_label + ": %{x:,.0f} " + unit + "<extra></extra>",
    ))
    span = max(max(before, default=1), max(after, default=1)) * 1.15
    fig.update_layout(**_layout(
        max(200, 42 * len(ordered) + 70), showlegend=True,
        xaxis=dict(gridcolor=T.GRID, griddash="solid", zeroline=False,
                   linecolor=T.AXIS, range=[0, span],
                   tickfont=dict(color=T.TEXT_MUTED, size=11),
                   title=dict(text=unit, font=dict(color=T.TEXT_MUTED, size=11))),
        yaxis=dict(showgrid=False, zeroline=False, linecolor="rgba(0,0,0,0)",
                   tickfont=dict(color=T.TEXT_2, size=11)),
    ))
    table = pd.DataFrame([
        {"Item": n, f"{before_label} ({unit})": round(b),
         f"{after_label} ({unit})": round(a),
         "Reduction": f"{(b - a) / b:.0%}" if b else "-"}
        for n, b, a in reversed(ordered)
    ])
    return fig, table
