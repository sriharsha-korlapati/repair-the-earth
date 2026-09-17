"""The unified overview: the page v1 never had."""

from __future__ import annotations

import streamlit as st

from core import factors as F, insights
from core.engine import Footprint
from ui import charts, components as C, theme as T


def render(fp: Footprint, profile: dict, actions: list, visited: set) -> None:
    grade, grade_note = fp.grade
    paris_ratio = fp.annual_kg / F.PARIS_2030_BUDGET

    C.hero(
        "Your total annual footprint",
        f"{fp.tonnes:,.2f}",
        "tonnes CO₂e per year",
        f"{fp.annual_kg:,.0f} kg a year · {fp.monthly_kg:,.0f} kg a month · "
        f"{paris_ratio:.1f}× the 1.5 °C per-person budget",
        grade=(grade, grade_note),
    )

    st.write("")
    C.tile_row([
        {"label": "Per month", "value": fp.monthly_kg, "unit": "kg CO₂e"},
        {"label": "Measured running cost", "value": fp.annual_cost, "unit": "₹/yr",
         "foot": "energy, travel, water, minus scrap value"},
        {"label": "Actions available to you", "value": len(actions), "unit": "",
         "foot": f"{sum(1 for a in actions if a.annual_net_inr <= 0)} pay for themselves"},
        {"label": "Reducible", "value": f"{min(1.0, sum(a.annual_kg for a in actions) / fp.annual_kg):.0%}"
         if fp.annual_kg else "-", "unit": "", "foot": "of your footprint, on paper"},
    ])

    # --- Data completeness: defaults are honest estimates, not measurements ---
    st.write("")
    missing = [m for m in F.MODULE_ORDER if m not in visited]
    if missing:
        names = ", ".join(F.MODULE_META[m]["label"] for m in missing)
        C.insight(
            f"You are still on starting estimates for <b>{names}</b>. The total below "
            "is a realistic profile, not your measurement, until you have opened each "
            "module and checked its inputs.", "warn",
        )

    st.divider()

    left, right = st.columns([1.15, 1], gap="large")

    with left:
        st.markdown("##### Where it comes from")
        labels = {m: F.MODULE_META[m]["label"] for m in F.MODULE_ORDER}
        fig, table = charts.footprint_split(fp.counted, labels, T.MODULE_COLORS)
        charts.render(fig, table, key="dash_split")

        fig, table = charts.ranked_modules(fp.counted, labels, T.MODULE_COLORS)
        charts.render(fig, table, key="dash_ranked")

        if fp.diagnostic:
            excluded = ", ".join(F.MODULE_META[m]["label"] for m in fp.diagnostic)
            source = ("your electricity bill" if profile.get("electricity_source") == "bill"
                      else "your appliance model")
            st.caption(
                f"{excluded} is excluded from this total on purpose. It describes the "
                f"same kilowatt-hours as {source}, and adding both would double-count "
                "them. It is shown as a cross-check on its own page."
            )

    with right:
        st.markdown("##### How you compare")
        fig, table = charts.benchmark_chart(fp.vs_benchmarks())
        charts.render(fig, table, key="dash_bench")
        st.caption(
            "These markers come from national and global per-person statistics whose "
            "scopes differ slightly from this dashboard's. Read them as signposts for "
            "the order of magnitude, not as a precise score."
        )

    st.divider()
    st.markdown("##### What this actually means")
    C.equivalence_chips(fp.equivalences()[:3])
    st.write("")
    C.equivalence_chips(fp.equivalences()[3:])

    st.divider()
    st.markdown("##### What the engine found")
    for kind, text in insights.build_all(fp, profile, actions):
        C.insight(text, kind)

    note = insights.reconciliation_note(fp)
    if note:
        C.insight(note, "info")

    st.divider()
    st.markdown("##### Biggest single line items, across every module")
    st.caption(
        "Ignoring module boundaries entirely: these are the individual things "
        "driving your number."
    )
    items = dict(sorted(fp.all_items().items(), key=lambda kv: kv[1],
                        reverse=True)[:10])
    if items:
        fig, table = charts.item_breakdown(items, color=T.SERIES[0], limit=10)
        charts.render(fig, table, key="dash_items")
