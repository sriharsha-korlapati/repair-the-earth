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
    """
    A labelled number input per item, two to a row.

    The previous version put a markdown label div beside the widget in a fixed
    three-column row. Those columns never stack, so on a phone the label and
    the input were fighting over 90px each. A widget's own label wraps, aligns
    and stacks for free, and the per-item note moves into its tooltip.
    """
    st.markdown(f"###### {title}")
    st.caption(caption)
    items = list(catalogue.items())
    for index in range(0, len(items), 2):
        for col, (name, spec) in zip(st.columns(2), items[index:index + 2]):
            with col:
                store[name] = st.number_input(
                    name, min_value=0.0, max_value=max_value, step=0.5,
                    value=float(store.get(name, 0.0)),
                    key=f"{key_prefix}_{name}",
                    help=f"{spec['ef']:.3f} kg CO₂e each. {spec['note']}",
                )


def render(inputs: dict, profile: dict) -> None:
    C.section("🎓 Campus life",
              "Food, single-use, screens, and what you own.")

    tab_food, tab_single, tab_digital, tab_goods = st.tabs(
        ["Food & drink", "Single-use", "Digital", "Things you own"]
    )

    with tab_food:
        st.markdown("###### Meals a week")
        st.caption("Three a day is 21 a week. Mess, canteen, home and outside.")
        meals = inputs.setdefault("meals", {})
        meal_items = list(F.MEALS.items())
        for index in range(0, len(meal_items), 2):
            for col, (name, spec) in zip(st.columns(2), meal_items[index:index + 2]):
                with col:
                    meals[name] = st.number_input(
                        name, min_value=0.0, max_value=25.0, step=1.0,
                        value=float(meals.get(name, 0.0)), key=f"meal_{name}",
                        help=f"{spec['ef']:.2f} kg CO₂e per meal. {spec['note']}",
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
            help=f"{F.PLATE_WASTE_EF:g} kg CO₂e per kg - wasted food carries "
                 "everything spent growing and cooking it. A mess plate leaves 100-200 g.",
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
            "Hours a week (cloud storage is per month). Network and data centre "
            "only - device charging sits under Appliances.",
            F.DIGITAL, inputs.setdefault("digital", {}), "per week", "dig", 168.0,
        )

    with tab_goods:
        st.markdown("###### Things you own")
        st.caption("Manufacturing carbon, spread over the item's life. Keeping "
                   "something longer is a real cut.")
        goods = inputs.setdefault("goods", {})
        goods_items = list(F.GOODS.items())
        for index in range(0, len(goods_items), 2):
            for col, (name, spec) in zip(st.columns(2), goods_items[index:index + 2]):
                with col:
                    goods[name] = st.number_input(
                        name, min_value=0, max_value=30, value=int(goods.get(name, 0)),
                        key=f"goods_{name}",
                        help=f"{spec['ef']:,.0f} kg CO₂e to make, over an assumed "
                             f"{spec['life_years']}-year life. {spec['note']}",
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

    with st.expander("Assumptions"):
        C.assumptions([
            "Meal factors cover farming, processing and cooking. Ruminant meat "
            "dominates because of enteric methane.",
            "Digital is network + data centre only; charging sits in Appliances.",
            "Goods are amortised over their service life.",
        ])
