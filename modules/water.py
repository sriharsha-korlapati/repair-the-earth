"""
Water module UI -- new in v2.

The teaching point of this module: water has no emissions of its own. It
carries carbon because we pump it, heat it, and then treat it as sewage. So
the biggest water saving on this page is almost never the biggest volume - it
is whichever litres were hot.
"""

from __future__ import annotations

import streamlit as st

from core import calculators, factors as F
from ui import charts, components as C, theme as T


def render(inputs: dict, profile: dict) -> None:
    C.section(
        "💧 Water",
        "The water-energy-carbon nexus. Every litre is pumped, often heated, and "
        "then treated again on the way out - and each of those steps runs on the "
        "same grid as everything else on this dashboard.",
    )

    left, right = st.columns([1, 1], gap="large")

    with left:
        sources = list(F.WATER_SOURCE_KWH_PER_KL.keys())
        inputs["source"] = st.selectbox(
            "Where does your water come from?", sources,
            index=sources.index(inputs.get("source", sources[0]))
            if inputs.get("source") in sources else 0,
            help="Tanker water carries roughly three times the energy of piped "
                 "supply, because it is trucked instead of pumped.",
        )
        st.caption(
            f"{F.WATER_SOURCE_KWH_PER_KL[inputs['source']]:.2f} kWh of electricity "
            f"per kilolitre delivered, plus {F.WASTEWATER_KWH_PER_KL:.2f} kWh per "
            "kilolitre to treat it as sewage afterwards."
        )

        heaters = list(F.WATER_HEATER_TYPES.keys())
        inputs["heater_type"] = st.selectbox(
            "How is your water heated?", heaters,
            index=heaters.index(inputs.get("heater_type", heaters[0]))
            if inputs.get("heater_type") in heaters else 0,
        )
        st.caption(F.WATER_HEATER_TYPES[inputs["heater_type"]]["note"])

    with right:
        inputs["has_ro"] = st.checkbox(
            "I use an RO water purifier", value=bool(inputs.get("has_ro", True))
        )
        if inputs["has_ro"]:
            inputs["ro_litres_day"] = st.slider(
                "Purified water used (litres/day)", 0.0, 30.0,
                float(inputs.get("ro_litres_day", 4.0)), step=0.5,
                help=f"RO rejects about {F.RO_REJECT_RATIO:g} litres for every litre "
                     "it purifies. That reject water never appears on any bill and "
                     "is almost always thrown away.",
            )
        inputs["bottled_litres_week"] = st.slider(
            "Bottled water bought (litres/week)", 0.0, 30.0,
            float(inputs.get("bottled_litres_week", 2.0)), step=0.5,
        )
        inputs["leaking_taps"] = st.number_input(
            "Dripping taps you have been ignoring", min_value=0, max_value=10,
            value=int(inputs.get("leaking_taps", 1)),
            help="A single dripping tap is about 15 litres a day.",
        )

    st.markdown("###### Daily water use, by what you use it for")
    st.caption(
        "Enter how many times a day, or how many minutes a day, for each one. "
        "The hot-water share of each use is what drives the carbon."
    )
    quantities = inputs.setdefault("quantities", {})
    for name, spec in F.WATER_END_USES.items():
        cols = st.columns([2.3, 1.2, 1.6])
        cols[0].markdown(
            f"<div style='padding-top:6px;color:{T.TEXT_2};font-size:0.88rem;'>{name}"
            f"</div>", unsafe_allow_html=True,
        )
        quantities[name] = cols[1].number_input(
            f"per day ({spec['unit']})", min_value=0.0, max_value=60.0, step=0.5,
            value=float(quantities.get(name, spec["default_qty"])),
            key=f"water_q_{name}", label_visibility="collapsed",
        )
        hot = f" · {spec['hot_share']:.0%} hot" if spec["hot_share"] else ""
        cols[2].markdown(
            f"<div style='padding-top:6px;color:{T.TEXT_MUTED};font-size:0.78rem;'>"
            f"{spec['litres']:g} L per {spec['unit']}{hot}</div>",
            unsafe_allow_html=True,
        )

    with st.expander("Rainwater harvesting potential"):
        inputs["roof_area_m2"] = st.slider(
            "Roof area available (m²)", 0.0, 2000.0,
            float(inputs.get("roof_area_m2", 0.0)), step=10.0,
            help="A hostel block roof is often 400-1,500 m². This is the single "
                 "highest-impact water intervention a campus can make.",
        )
        rainfall = F.RAINFALL_MM.get(profile.get("location", ""), 900.0)
        # Computed inline from the slider just read, not from the result object,
        # so the figure updates on the same interaction that moves the slider.
        harvest_kl = (inputs["roof_area_m2"] * rainfall
                      * F.RAINWATER_RUNOFF_COEFF / 1000.0)
        st.caption(
            f"{profile.get('location')} receives about {rainfall:,.0f} mm of rain a "
            f"year. At a {F.RAINWATER_RUNOFF_COEFF:.0%} runoff coefficient, "
            f"{inputs['roof_area_m2']:,.0f} m² could capture "
            f"{harvest_kl:,.1f} kilolitres."
        )

    # Every widget above has already written into `inputs` during this run, so
    # the result is computed HERE rather than passed in. Computing it before the
    # widgets render would show the user the numbers from their previous click.
    result = calculators.CALCULATORS["water"](inputs, profile)

    metrics = result.metrics
    C.tile_row([
        {"label": "Water used", "value": metrics["litres_per_day"], "unit": "L/day",
         "foot": f"{metrics['annual_kl']:,.1f} kL a year"},
        {"label": "Of that, heated", "value": metrics["hot_litres_per_day"],
         "unit": "L/day"},
        {"label": "Emissions", "value": result.annual_kg, "unit": "kg CO₂e/yr"},
        {"label": "Water + energy cost", "value": result.annual_cost, "unit": "₹/yr"},
    ])

    # The UN sufficiency band is the right yardstick here, not a national average.
    C.meter(
        "Your use against 100 litres per person per day (the UN sufficiency benchmark)",
        metrics["litres_per_day"] / 100.0,
        color=(T.GOOD if metrics["litres_per_day"] <= 100
               else T.WARNING if metrics["litres_per_day"] <= 150 else T.CRITICAL),
        right_text=f"{metrics['litres_per_day']:,.0f} of 100 L",
    )

    if result.breakdown:
        col_a, col_b = st.columns(2, gap="large")
        with col_a:
            st.markdown("###### Carbon, by stage of the water chain")
            fig, table = charts.item_breakdown(
                result.breakdown, color=T.MODULE_COLORS["water"], limit=6
            )
            charts.render(fig, table, key="water_carbon")
        with col_b:
            st.markdown("###### Volume, by end use")
            volumes = {
                name: float(quantities.get(name, 0.0)) * spec["litres"]
                for name, spec in F.WATER_END_USES.items()
                if float(quantities.get(name, 0.0)) > 0
            }
            if metrics["ro_reject_litres_day"]:
                volumes["RO reject"] = metrics["ro_reject_litres_day"]
            if metrics["leak_litres_day"]:
                volumes["Leaking taps"] = metrics["leak_litres_day"]
            if volumes:
                fig, table = charts.item_breakdown(
                    volumes, unit="litres / day",
                    color=T.SEQUENTIAL[4], limit=8
                )
                charts.render(fig, table, key="water_volume")

    for note in result.notes:
        if note:
            C.insight(note)

    C.assumptions([
        f"Heating a litre by 25 °C takes {F.HOT_WATER_KWH_PER_LITRE:.4f} kWh at 90% "
        "heater efficiency (4.18 kJ/kg/K ÷ 3600).",
        f"Wastewater treatment adds {F.WASTEWATER_KWH_PER_KL:.2f} kWh per kilolitre.",
        "If you also listed a geyser under Appliances, set the heater above to "
        "'already counted in Appliances' so the same hot water is not charged twice.",
    ])
