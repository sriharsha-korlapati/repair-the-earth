"""Electricity module UI."""

from __future__ import annotations

import streamlit as st

from core import calculators, factors as F
from ui import components as C


def render(inputs: dict, profile: dict) -> None:
    C.section("⚡ Electricity", "What the meter actually bills you for.")

    left, right = st.columns([1, 1], gap="large")

    with left:
        inputs["entry_mode"] = st.radio(
            "How do you want to enter this?",
            ["Monthly bill (₹)", "Monthly units (kWh)"],
            index=0 if inputs.get("entry_mode", "").startswith("Monthly bill") else 1,
            horizontal=True,
            help="Units are more accurate. Tariffs are slab-based, so dividing a "
                 "bill by an average rate is only an estimate.",
        )
        if inputs["entry_mode"].startswith("Monthly bill"):
            inputs["monthly_bill"] = st.number_input(
                "Monthly electricity bill (₹)", min_value=0.0, step=50.0,
                value=float(inputs.get("monthly_bill", 1800.0)),
            )
        else:
            inputs["monthly_units"] = st.number_input(
                "Monthly units consumed (kWh)", min_value=0.0, step=10.0,
                value=float(inputs.get("monthly_units", 257.0)),
            )

        inputs["share_with_household"] = st.checkbox(
            f"This meter is shared between {profile.get('household_size')} people",
            value=bool(inputs.get("share_with_household", True)),
            help="If the bill covers a family or hostel room, your share is the "
                 "bill divided by the people on it.",
        )

    with right:
        inputs["solar_kw"] = st.slider(
            "Rooftop solar (kW)", 0.0, 10.0,
            float(inputs.get("solar_kw", 0.0)), step=0.5,
            help=f"Each kW makes about {F.SOLAR_KWH_PER_KW_PER_DAY:g} kWh a day.",
        )
        inputs["green_tariff_share"] = st.slider(
            "On a green tariff (%)", 0, 100,
            int(inputs.get("green_tariff_share", 0)), step=10,
        )

    # Every widget above has already written into `inputs` during this run, so
    # the result is computed HERE rather than passed in. Computing it before the
    # widgets render would show the user the numbers from their previous click.
    result = calculators.CALCULATORS["electricity"](inputs, profile)

    metrics = result.metrics
    C.tile_row([
        {"label": "Units billed", "value": metrics["monthly_units"], "unit": "kWh/mo",
         "foot": f"{metrics['monthly_units_per_person']:,.0f} kWh per person"},
        {"label": "Your share of emissions", "value": result.monthly_kg,
         "unit": "kg CO₂e/mo"},
        {"label": "Annual emissions", "value": result.annual_kg, "unit": "kg CO₂e/yr"},
        {"label": "Your share of the cost", "value": result.monthly_cost,
         "unit": "₹/mo"},
    ])

    if metrics["avoided_kg_annual"] > 0:
        C.insight(
            f"Solar and green tariff between them avoid "
            f"<b>{metrics['avoided_kg_annual']:,.0f} kg CO₂e a year</b> that would "
            "otherwise have come off the grid.", "good",
        )

    for note in result.notes:
        C.insight(note)

    with st.expander("Assumptions"):
        C.assumptions([
            f"Grid factor: {metrics['grid_ef']:.3f} kg CO₂/kWh at your meter "
            f"({profile.get('grid_preset')}"
            + (f" + {F.TD_LOSS_FRACTION:.0%} losses)." if profile.get("include_td_losses")
               else ")."),
            f"Tariff: ₹{profile.get('tariff'):.2f}/kWh ({profile.get('tariff_preset')}).",
            "Both are set in the sidebar and every module uses them.",
        ])
