"""Electricity module UI."""

from __future__ import annotations

import streamlit as st

from core import calculators, factors as F
from ui import charts, components as C, theme as T


def render(inputs: dict, profile: dict) -> None:
    C.section(
        "⚡ Electricity",
        "Your metered grid consumption. v1 divided the bill by a flat ₹7 and "
        "multiplied by one number; this version accounts for the tariff you "
        "actually pay, the grid you are actually on, who shares the meter, and "
        "anything you generate yourself.",
    )

    left, right = st.columns([1, 1], gap="large")

    with left:
        inputs["entry_mode"] = st.radio(
            "How do you want to enter this?",
            ["Monthly bill (₹)", "Monthly units (kWh)"],
            index=0 if inputs.get("entry_mode", "").startswith("Monthly bill") else 1,
            horizontal=True,
            help="Units are more accurate if your bill shows them - tariffs are "
                 "slab-based, so dividing a bill by an average rate is an estimate.",
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
            help="If the bill covers a whole family or hostel room, your personal "
                 "share is the bill divided by the people on it. Skipping this is "
                 "the most common way a household footprint gets counted several "
                 "times over.",
        )

    with right:
        inputs["solar_kw"] = st.slider(
            "Rooftop solar installed (kW)", 0.0, 10.0,
            float(inputs.get("solar_kw", 0.0)), step=0.5,
            help=f"Each kW generates about {F.SOLAR_KWH_PER_KW_PER_DAY:g} kWh a day "
                 "on an annual average in India.",
        )
        inputs["green_tariff_share"] = st.slider(
            "Share of supply on a green/renewable tariff (%)", 0, 100,
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

    C.assumptions([
        f"Grid factor: {metrics['grid_ef']:.3f} kg CO₂ per kWh at your meter "
        f"({profile.get('grid_preset')}"
        + (f" + {F.TD_LOSS_FRACTION:.0%} T&D losses)" if profile.get("include_td_losses")
           else ")"),
        f"Tariff: ₹{profile.get('tariff'):.2f} per kWh ({profile.get('tariff_preset')}).",
        "Change either of these in the sidebar - an EV, a geyser and a grid factor "
        "are all connected, and every module updates together.",
    ])
