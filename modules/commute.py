"""Commute and travel module UI: multi-leg journeys plus the trips home."""

from __future__ import annotations

import streamlit as st

from core import calculators, factors as F
from ui import charts, components as C, theme as T


def render(inputs: dict, profile: dict) -> None:
    C.section("🚌 Commute & travel",
              "Your daily legs, plus the trips home.")

    tab_daily, tab_long = st.tabs(["Daily journey", "Trips home & long distance"])

    with tab_daily:
        st.caption("One leg per mode, door to door.")
        legs = inputs.setdefault("legs", [])

        remove_index: int | None = None
        for index, leg in enumerate(legs):
            with st.container(border=True):
                cols = st.columns([2.4, 1.1, 1.1, 1.1, 0.7])
                mode_names = list(F.TRANSPORT_MODES.keys())
                leg["mode"] = cols[0].selectbox(
                    "Mode", mode_names,
                    index=mode_names.index(leg.get("mode", "Walk"))
                    if leg.get("mode") in mode_names else 0,
                    key=f"leg_mode_{index}",
                )
                leg["distance_km"] = cols[1].number_input(
                    "km (one way)", min_value=0.0, step=0.5,
                    value=float(leg.get("distance_km", 5.0)), key=f"leg_km_{index}",
                )
                leg["days_per_week"] = cols[2].number_input(
                    "days/week", min_value=0, max_value=7,
                    value=int(leg.get("days_per_week", 5)), key=f"leg_days_{index}",
                )
                spec = F.TRANSPORT_MODES[leg["mode"]]
                if spec["basis"] == "vehicle":
                    leg["occupancy"] = cols[3].number_input(
                        "people in it", min_value=1, max_value=6,
                        value=int(leg.get("occupancy", 1)), key=f"leg_occ_{index}",
                        help="Emissions are per vehicle, so they split between "
                             "everyone travelling in it.",
                    )
                else:
                    cols[3].caption("shared mode")
                    leg["occupancy"] = 1
                if cols[4].button("✕", key=f"leg_del_{index}", help="Remove this leg"):
                    remove_index = index
                st.caption(spec["note"])

        if remove_index is not None:
            legs.pop(remove_index)
            st.rerun()

        add_col, wfh_col = st.columns([1, 2])
        if add_col.button("＋ Add a leg", width="stretch"):
            legs.append({"mode": "City bus", "distance_km": 5.0,
                         "days_per_week": 5, "round_trip": True, "occupancy": 1})
            st.rerun()
        inputs["wfh_days"] = wfh_col.slider(
            "Days a week you do not travel at all", 0, 5,
            int(inputs.get("wfh_days", 0)),
            help="Remote days, or days you stay on campus. Applied to every leg.",
        )

    with tab_long:
        st.caption("Per year, counted as return journeys.")
        trips = inputs.setdefault("intercity", [])
        remove_index = None
        for index, trip in enumerate(trips):
            with st.container(border=True):
                cols = st.columns([2.4, 1.3, 1.3, 0.7])
                mode_names = list(F.INTERCITY_MODES.keys())
                trip["mode"] = cols[0].selectbox(
                    "Mode", mode_names,
                    index=mode_names.index(trip.get("mode", mode_names[0]))
                    if trip.get("mode") in mode_names else 0,
                    key=f"trip_mode_{index}",
                )
                trip["distance_km"] = cols[1].number_input(
                    "km each way", min_value=0.0, step=25.0,
                    value=float(trip.get("distance_km", 350.0)), key=f"trip_km_{index}",
                )
                trip["trips_per_year"] = cols[2].number_input(
                    "trips/year", min_value=0, max_value=100,
                    value=int(trip.get("trips_per_year", 4)), key=f"trip_n_{index}",
                )
                if cols[3].button("✕", key=f"trip_del_{index}"):
                    remove_index = index
                st.caption(F.INTERCITY_MODES[trip["mode"]]["note"])
        if remove_index is not None:
            trips.pop(remove_index)
            st.rerun()
        if st.button("＋ Add a trip", key="add_trip"):
            trips.append({"mode": "Train (sleeper / non-AC)", "distance_km": 350.0,
                          "trips_per_year": 4})
            st.rerun()

    # Every widget above has already written into `inputs` during this run, so
    # the result is computed HERE rather than passed in. Computing it before the
    # widgets render would show the user the numbers from their previous click.
    result = calculators.CALCULATORS["commute"](inputs, profile)

    metrics = result.metrics
    C.tile_row([
        {"label": "Distance travelled", "value": metrics["annual_km"], "unit": "km/yr"},
        {"label": "Emissions", "value": result.annual_kg, "unit": "kg CO₂e/yr"},
        {"label": "Average intensity", "value": metrics["kg_per_km"] * 1000,
         "unit": "g/km", "foot": "across every leg"},
        {"label": "What it costs you", "value": result.annual_cost, "unit": "₹/yr"},
    ])

    if result.breakdown:
        fig, table = charts.item_breakdown(
            result.breakdown, color=T.MODULE_COLORS["commute"], limit=8
        )
        st.markdown("###### Emissions by leg")
        charts.render(fig, table, key="commute_break")

    for note in result.notes:
        C.insight(note)

    with st.expander("Assumptions"):
        C.assumptions([
            "Private vehicles are per vehicle-km, divided by occupancy. Buses, "
            "metros and trains use per-passenger factors.",
            "Electric modes use kWh/km against your grid factor - never zero.",
            "Flights exclude high-altitude forcing, which would roughly double them.",
        ])
