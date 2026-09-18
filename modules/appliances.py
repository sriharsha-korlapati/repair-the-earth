"""Appliances module UI: a real wattage model, not a flat per-hour guess."""

from __future__ import annotations

import streamlit as st

from core import calculators, factors as F
from ui import charts, components as C, theme as T


def render(inputs: dict, profile: dict) -> None:
    C.section("🏠 Appliances", "Rated watts × hours × count, device by device.")

    is_diagnostic = profile.get("electricity_source") == "bill"
    if is_diagnostic:
        C.insight(
            "A <b>cross-check</b>, not counted in your total - your bill is. "
            "Switch the source in the sidebar to count this instead.", "info",
        )

    tab_cool, tab_laundry, tab_devices = st.tabs(
        ["Cooling", "Laundry", "Every other device"]
    )

    with tab_cool:
        inputs["has_ac"] = st.checkbox(
            "I use an air conditioner", value=bool(inputs.get("has_ac", True))
        )
        if inputs["has_ac"]:
            cols = st.columns(2)
            inputs["ac_tons"] = cols[0].select_slider(
                "Capacity (tons)", options=[0.75, 1.0, 1.5, 2.0],
                value=float(inputs.get("ac_tons", 1.5)),
            )
            classes = list(F.AC_WATTS_PER_TON.keys())
            inputs["ac_class"] = cols[1].selectbox(
                "Efficiency class", classes,
                index=classes.index(inputs.get("ac_class", classes[0]))
                if inputs.get("ac_class") in classes else 0,
            )
            inputs["ac_hours"] = cols[0].slider(
                "Hours a day", 0.0, 16.0, float(inputs.get("ac_hours", 6.0)), step=0.5
            )
            inputs["ac_months"] = cols[1].slider(
                "Months a year you run it", 0, 12, int(inputs.get("ac_months", 6)),
                help="Five to eight months is typical. Annualising a summer habit "
                     "over twelve months overstates it badly.",
            )
            inputs["ac_temp"] = st.slider(
                "Thermostat setting (°C)", 18, 30, int(inputs.get("ac_temp", 24)),
                help=f"Reference is {F.AC_REFERENCE_TEMP_C:.0f} °C, the BEE-recommended "
                     f"default. Each degree below it adds about "
                     f"{F.AC_PERCENT_PER_DEGREE:.0%} to energy use.",
            )
            load = max(F.AC_MIN_LOAD_FACTOR,
                       1.0 + (F.AC_REFERENCE_TEMP_C - inputs["ac_temp"])
                       * F.AC_PERCENT_PER_DEGREE)
            C.meter(
                f"Energy draw at {inputs['ac_temp']} °C, relative to 24 °C",
                min(1.0, load / 1.4),
                color=T.CRITICAL if load > 1.2 else T.WARNING if load > 1.0 else T.GOOD,
                right_text=f"{load:.0%} of the 24 °C baseline",
            )

    with tab_laundry:
        modes = list(F.WASH_KWH_PER_CYCLE.keys())
        inputs["wash_mode"] = st.selectbox(
            "Wash setting", modes,
            index=modes.index(inputs.get("wash_mode", modes[0]))
            if inputs.get("wash_mode") in modes else 0,
            help="Heating water is nearly all of a wash cycle's energy.",
        )
        cols = st.columns(2)
        inputs["wash_cycles_week"] = cols[0].slider(
            "Wash cycles a week", 0.0, 14.0,
            float(inputs.get("wash_cycles_week", 3.0)), step=0.5,
        )
        inputs["dryer_cycles_week"] = cols[1].slider(
            "Tumble dryer cycles a week", 0.0, 14.0,
            float(inputs.get("dryer_cycles_week", 0.0)), step=0.5,
            help="Roughly five times a cold wash. Usually zero in India.",
        )

    with tab_devices:
        devices = inputs.setdefault("devices", {})
        hours_map = inputs.setdefault("device_hours", {})

        # Eighteen appliances in a four-column row was the single worst layout in
        # the app: on a phone each cell got ~90px and the labels collided. Now you
        # pick the devices you actually own, and only those get inputs — which
        # also turns an 18-row wall into a short list for most people.
        all_devices = list(F.APPLIANCES.keys())
        owned_now = [n for n in all_devices if float(devices.get(n, 0)) > 0]
        chosen = st.multiselect(
            "Devices you have", all_devices, default=owned_now,
            help="Add or remove appliances. Anything unticked counts as zero.",
        )
        for name in all_devices:
            if name not in chosen:
                devices[name] = 0

        if not chosen:
            st.caption("Pick the appliances you own to model them.")
        for name in chosen:
            spec = F.APPLIANCES[name]
            st.markdown(
                f"<div style='color:{T.TEXT_2};font-size:0.88rem;font-weight:600;"
                f"margin-top:6px;'>{name} "
                f"<span style='color:{T.TEXT_MUTED};font-weight:400;'>"
                f"· {spec['watts']} W</span></div>",
                unsafe_allow_html=True,
            )
            left, right = st.columns(2)
            devices[name] = left.number_input(
                "How many", min_value=0, max_value=30,
                value=max(1, int(devices.get(name, 0))),
                key=f"dev_n_{name}", help=spec["note"],
            )
            hours_map[name] = right.number_input(
                "Hours a day", min_value=0.0, max_value=24.0, step=0.5,
                value=float(hours_map.get(name, spec["hours"])),
                key=f"dev_h_{name}",
            )

    # Every widget above has already written into `inputs` during this run, so
    # the result is computed HERE rather than passed in. Computing it before the
    # widgets render would show the user the numbers from their previous click.
    result = calculators.CALCULATORS["appliances"](inputs, profile)

    metrics = result.metrics
    C.tile_row([
        {"label": "Modelled consumption", "value": metrics["monthly_kwh"],
         "unit": "kWh/mo"},
        {"label": "Your share", "value": metrics["kwh_per_person"] / 12.0,
         "unit": "kWh/mo", "foot": f"split {metrics['household_divisor']:,.0f} ways"},
        {"label": "Emissions", "value": result.annual_kg, "unit": "kg CO₂e/yr"},
        {"label": "Electricity cost", "value": result.annual_cost, "unit": "₹/yr"},
    ])

    if result.breakdown:
        st.markdown("###### Where the electricity actually goes")
        fig, table = charts.item_breakdown(
            result.breakdown, color=T.MODULE_COLORS["appliances"], limit=10
        )
        charts.render(fig, table, key="appl_break")

    for note in result.notes:
        C.insight(note)

    with st.expander("Assumptions"):
        C.assumptions([
            "kWh = watts ÷ 1000 × hours × count × 365.",
            f"AC load = 1 + {F.AC_PERCENT_PER_DEGREE:.0%} × "
            f"({F.AC_REFERENCE_TEMP_C:.0f} °C − your setting), floored at "
            f"{F.AC_MIN_LOAD_FACTOR:.0%}.",
            "Fridge watts are the compressor-cycle average, not peak draw.",
        ])
