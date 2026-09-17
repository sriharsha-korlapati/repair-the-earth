"""
Waste module UI -- new in v2.

The teaching point: the mass of your waste barely matters. The ROUTE it takes
decides its emissions. The same kilogram of food waste is 1.90 kg CO2e in a
landfill and 0.18 kg in a compost pit, and a kilogram of recycled metal is a
carbon CREDIT because it displaces smelting new metal out of ore.
"""

from __future__ import annotations

import streamlit as st

from core import calculators, factors as F
from ui import charts, components as C, theme as T


def render(inputs: dict, profile: dict) -> None:
    C.section(
        "♻️ Waste",
        "Not how much you throw away - where it goes. Choosing a route for each "
        "stream is the entire intervention, and for food waste it is the single "
        "biggest lever available to most Indian households.",
    )

    streams = inputs.setdefault("streams", {})

    st.markdown("###### Your weekly waste, stream by stream")
    for name, spec in F.WASTE_STREAMS.items():
        entry = streams.setdefault(
            name, {"kg_week": spec["default_kg_week"],
                   "route": list(spec["routes"].keys())[0]}
        )
        with st.container(border=True):
            cols = st.columns([1.5, 1.2, 1.8])
            cols[0].markdown(
                f"<div style='padding-top:4px;color:{T.TEXT_1};font-size:0.9rem;"
                f"font-weight:600;'>{name}</div>", unsafe_allow_html=True,
            )
            entry["kg_week"] = cols[1].number_input(
                "kg per week", min_value=0.0, max_value=100.0, step=0.05,
                value=float(entry.get("kg_week", spec["default_kg_week"])),
                key=f"waste_kg_{name}",
            )
            routes = list(spec["routes"].keys())
            entry["route"] = cols[2].selectbox(
                "Where it goes", routes,
                index=routes.index(entry.get("route", routes[0]))
                if entry.get("route") in routes else 0,
                key=f"waste_route_{name}",
            )
            chosen_ef = spec["routes"][entry["route"]]
            best_ef = min(spec["routes"].values())
            colour = T.GOOD if chosen_ef <= best_ef else T.WARNING if chosen_ef < 1.0 else T.CRITICAL
            st.markdown(
                f"<div style='font-size:0.78rem;color:{T.TEXT_MUTED};'>"
                f"<span style='color:{colour};font-weight:600;'>{chosen_ef:+.2f} kg CO₂e "
                f"per kg</span> on this route · "
                f"best available here is {best_ef:+.2f} · "
                f"scrap value about ₹{spec['value_per_kg']:,.0f}/kg. {spec['note']}</div>",
                unsafe_allow_html=True,
            )

    # Every widget above has already written into `inputs` during this run, so
    # the result is computed HERE rather than passed in. Computing it before the
    # widgets render would show the user the numbers from their previous click.
    result = calculators.CALCULATORS["waste"](inputs, profile)

    metrics = result.metrics
    C.tile_row([
        {"label": "Waste generated", "value": metrics["kg_per_week"], "unit": "kg/week",
         "foot": f"{metrics['kg_per_year']:,.0f} kg a year"},
        {"label": "Diverted from landfill", "value": f"{metrics['diversion_rate']:.0%}",
         "unit": "", "foot": "by mass"},
        {"label": "Net emissions", "value": result.annual_kg, "unit": "kg CO₂e/yr"},
        {"label": "Recoverable value", "value": metrics["recoverable_value_inr"],
         "unit": "₹/yr", "foot": "waste to wealth"},
    ])

    C.meter(
        "Segregation rate - the share of your waste that avoids landfill",
        metrics["diversion_rate"],
        color=(T.GOOD if metrics["diversion_rate"] >= 0.75
               else T.WARNING if metrics["diversion_rate"] >= 0.4 else T.CRITICAL),
        right_text=f"{metrics['diversion_rate']:.0%} diverted",
    )

    avoided = metrics["avoided_vs_landfill_kg"]
    if metrics["kg_per_week"] > 0:
        C.insight(
            f"Dumping everything would emit <b>{metrics['landfill_counterfactual_kg']:,.0f} "
            f"kg CO₂e a year</b>. Your current routing comes to "
            f"<b>{result.annual_kg:,.0f} kg</b> - a difference of "
            f"<b>{avoided:,.0f} kg</b> from nothing but segregation.",
            "good" if avoided > 20 else "warn",
        )

    if result.breakdown:
        st.markdown("###### Emissions and credits, by stream")
        st.caption(
            "Bars to the right emit. Bars to the left are credits - recycling "
            "displaces virgin material production, so it avoids more than the "
            "waste itself would ever have emitted."
        )
        fig, table = charts.diverging_bars(
            list(result.breakdown.items()), pos_label="emits", neg_label="avoids"
        )
        charts.render(fig, table, key="waste_diverge")

        st.markdown("###### What better routing would do")
        rows = []
        for name, spec in F.WASTE_STREAMS.items():
            entry = streams.get(name, {})
            mass = float(entry.get("kg_week", 0.0)) * 52.0
            if mass <= 0:
                continue
            current = mass * float(spec["routes"][entry.get("route",
                                   list(spec["routes"].keys())[0])])
            best = mass * min(spec["routes"].values())
            rows.append((name, current, best))
        if rows:
            # Shift both series above zero so a dumbbell reads correctly with
            # credits in play; the offset is stated so nobody misreads the axis.
            offset = min(0.0, min(min(r[1], r[2]) for r in rows))
            shifted = [(n, c - offset, b - offset) for n, c, b in rows]
            fig, table = charts.dumbbell(
                shifted, before_label="Current route", after_label="Best route",
                unit=f"kg CO₂e / year (offset by {-offset:,.0f} so credits fit the scale)",
            )
            charts.render(fig, table, key="waste_dumbbell")

    for note in result.notes:
        C.insight(note)

    C.assumptions([
        "Negative factors are avoided emissions: recycling a kilogram of metal "
        "saves the far larger emissions of smelting a kilogram from ore.",
        "Landfilled organic waste is charged for methane, which traps about 28 "
        "times more heat than CO₂ over a century - that is why food waste has by "
        "far the worst landfill factor here.",
        "Scrap values are indicative Indian kabadiwala rates and move with the "
        "commodity market.",
    ])
