"""
Campus life module UI -- new in v2.

This is the module built specifically for a college audience, and it covers
the things a conventional carbon calculator misses entirely: what you eat,
what you throw away on the plate, what you print, what you stream, and the
manufacturing carbon of the things you buy.

For most students the single biggest number on this whole dashboard turns up
on this page, which is exactly why it exists.
"""

from __future__ import annotations

import streamlit as st

from core import calculators, factors as F
from ui import charts, components as C, theme as T


def _quantity_rows(title: str, caption: str, catalogue: dict, store: dict,
                   unit: str, key_prefix: str, max_value: float = 60.0) -> None:
    st.markdown(f"###### {title}")
    st.caption(caption)
    for name, spec in catalogue.items():
        cols = st.columns([2.4, 1.1, 2.0])
        cols[0].markdown(
            f"<div style='padding-top:6px;color:{T.TEXT_2};font-size:0.88rem;'>{name}"
            f"</div>", unsafe_allow_html=True,
        )
        store[name] = cols[1].number_input(
            unit, min_value=0.0, max_value=max_value, step=0.5,
            value=float(store.get(name, 0.0)),
            key=f"{key_prefix}_{name}", label_visibility="collapsed",
        )
        cols[2].markdown(
            f"<div style='padding-top:6px;color:{T.TEXT_MUTED};font-size:0.77rem;'>"
            f"{spec['ef']:.3f} kg CO₂e each · {spec['note']}</div>",
            unsafe_allow_html=True,
        )


def render(inputs: dict, profile: dict) -> None:
    C.section(
        "🎓 Campus life",
        "Food, single-use plastic, printing, screen time and the embodied carbon "
        "of what you own. None of this was in v1, and for most students it is the "
        "largest slice of the whole footprint.",
    )

    tab_food, tab_single, tab_digital, tab_goods = st.tabs(
        ["Food & drink", "Single-use", "Digital", "Things you own"]
    )

    with tab_food:
        st.markdown("###### Meals a week, by type")
        st.caption(
            "Three meals a day is 21 a week. Count what you actually eat - mess, "
            "canteen, home and outside together."
        )
        meals = inputs.setdefault("meals", {})
        for name, spec in F.MEALS.items():
            cols = st.columns([2.2, 1.1, 2.2])
            cols[0].markdown(
                f"<div style='padding-top:6px;color:{T.TEXT_2};font-size:0.88rem;'>"
                f"{name}</div>", unsafe_allow_html=True,
            )
            meals[name] = cols[1].number_input(
                "per week", min_value=0.0, max_value=25.0, step=1.0,
                value=float(meals.get(name, 0.0)),
                key=f"meal_{name}", label_visibility="collapsed",
            )
            cols[2].markdown(
                f"<div style='padding-top:6px;color:{T.TEXT_MUTED};font-size:0.77rem;'>"
                f"{spec['ef']:.2f} kg CO₂e per meal · {spec['note']}</div>",
                unsafe_allow_html=True,
            )

        total_meals = sum(float(v) for v in meals.values())
        if total_meals:
            st.caption(f"Total: {total_meals:,.0f} meals a week "
                       f"({total_meals / 7:,.1f} a day).")

        st.divider()
        _quantity_rows(
            "Drinks a week", "Tea, coffee and anything packaged.",
            F.BEVERAGES, inputs.setdefault("beverages", {}), "per week", "bev", 60.0,
        )

        st.divider()
        inputs["plate_waste_g_day"] = st.slider(
            "Food left on your plate (grams a day)", 0.0, 500.0,
            float(inputs.get("plate_waste_g_day", 120.0)), step=10.0,
            help=f"Charged at {F.PLATE_WASTE_EF:g} kg CO₂e per kg, because wasted food "
                 "carries everything spent growing, moving and cooking it. A typical "
                 "mess plate leaves 100-200 g.",
        )
        inputs["laundry_kg_week"] = st.slider(
            "Clothes sent to a laundry service (kg a week)", 0.0, 20.0,
            float(inputs.get("laundry_kg_week", 0.0)), step=0.5,
        )

    with tab_single:
        _quantity_rows(
            "Single-use items a week",
            "The things that exist for a few minutes and then for centuries.",
            F.CONSUMABLES, inputs.setdefault("consumables", {}),
            "per week", "cons", 200.0,
        )

    with tab_digital:
        _quantity_rows(
            "Digital use",
            "Hours a week, except cloud storage which is per month. This counts "
            "network and data-centre energy only - your laptop and phone charging "
            "are already measured under Appliances, so nothing is double-counted.",
            F.DIGITAL, inputs.setdefault("digital", {}), "per week", "dig", 168.0,
        )

    with tab_goods:
        st.markdown("###### Things you own")
        st.caption(
            "Manufacturing carbon, spread over the item's service life. This is the "
            "footprint you already paid for and keep paying off - which is why "
            "keeping something longer is a real climate action."
        )
        goods = inputs.setdefault("goods", {})
        for name, spec in F.GOODS.items():
            cols = st.columns([2.2, 1.1, 2.2])
            cols[0].markdown(
                f"<div style='padding-top:6px;color:{T.TEXT_2};font-size:0.88rem;'>"
                f"{name}</div>", unsafe_allow_html=True,
            )
            goods[name] = cols[1].number_input(
                "owned", min_value=0, max_value=30, value=int(goods.get(name, 0)),
                key=f"goods_{name}", label_visibility="collapsed",
            )
            cols[2].markdown(
                f"<div style='padding-top:6px;color:{T.TEXT_MUTED};font-size:0.77rem;'>"
                f"{spec['ef']:,.0f} kg CO₂e to make · assumed "
                f"{spec['life_years']}-year life · {spec['note']}</div>",
                unsafe_allow_html=True,
            )

    # Every widget above has already written into `inputs` during this run, so
    # the result is computed HERE rather than passed in. Computing it before the
    # widgets render would show the user the numbers from their previous click.
    result = calculators.CALCULATORS["campus"](inputs, profile)

    metrics = result.metrics
    C.tile_row([
        {"label": "Food & drink", "value": metrics["food_kg"], "unit": "kg CO₂e/yr"},
        {"label": "Single-use items", "value": metrics["single_use_kg"],
         "unit": "kg CO₂e/yr"},
        {"label": "Digital life", "value": metrics["digital_kg"], "unit": "kg CO₂e/yr"},
        {"label": "Things you own", "value": metrics["goods_kg"], "unit": "kg CO₂e/yr"},
    ])

    if result.breakdown:
        st.markdown("###### Biggest campus-life line items")
        fig, table = charts.item_breakdown(
            result.breakdown, color=T.MODULE_COLORS["campus"], limit=12
        )
        charts.render(fig, table, key="campus_break")

    for note in result.notes:
        C.insight(note)

    C.assumptions([
        "Meal factors are per-meal averages for Indian portions and cover farming, "
        "processing and cooking. Ruminant meat dominates because of enteric methane.",
        "Digital factors are network plus data centre only. Device charging lives in "
        "the Appliances module - the boundary is deliberate and stated so the two "
        "modules can be added together safely.",
        "Goods are amortised: a 300 kg laptop over a five-year life is 60 kg a year, "
        "which is why the model rewards keeping it a sixth year.",
    ])
