"""Recommendations page: ranked actions, marginal abatement curve, pledges."""

from __future__ import annotations

import streamlit as st

from core import factors as F, recommend as R
from core.engine import Footprint
from ui import charts, components as C, theme as T

EFFORT_CLASS = {"Easy": "easy", "Medium": "medium", "Hard": "hard"}


def render(fp: Footprint, profile: dict, actions: list[R.Action], plan: dict) -> None:
    C.section(
        "🎯 What to do about it",
        "Every action here is generated from your own inputs and costed. Nothing "
        "on this page is a generic tip - if you do not own an AC, no AC advice "
        "appears.",
    )

    if not actions:
        C.insight(
            "No actions found. That usually means the modules are still at zero - "
            "fill in a module or two and come back.", "warn",
        )
        return

    # Quick wins are a preview of the list below, shown WITHOUT a pledge
    # checkbox on purpose: one action must have exactly one checkbox, or the two
    # widgets fight each other over the same pledge and neither wins.
    wins = R.quick_wins(actions)
    if wins:
        st.markdown("##### Start here: easy, and they pay for themselves")
        st.caption("Tick them in the full list below to add them to your plan.")
        for action in wins:
            _action_card(action, plan)
        st.write("")

    st.markdown("##### The marginal abatement cost curve")
    st.caption(
        "The analyst's view of the same list. Each bar is one action: how wide it "
        "is shows how much carbon it saves; how tall it is shows what each tonne "
        "costs. Anything below the zero line pays you to do it - work left to right."
    )
    fig, table, clipped = charts.macc_chart([a.as_dict() for a in actions])
    charts.render(fig, table, table_label="Every action, with exact economics",
                  key="macc")
    if clipped:
        st.caption(
            f"{clipped} action(s) run past the scale of this chart - a habit change "
            "with no capital cost can save thousands of rupees per tonne avoided. "
            "Their exact figures are in the table above."
        )

    st.divider()
    col_sort, col_filter = st.columns([1, 1])
    sort_by = col_sort.radio(
        "Rank by", ["Impact", "Cost per tonne", "Least effort"],
        horizontal=True, key="action_sort",
    )
    modules = ["All modules"] + [F.MODULE_META[m]["label"] for m in F.MODULE_ORDER]
    module_filter = col_filter.selectbox("Module", modules, key="action_module")

    key_map = {"Impact": "impact", "Cost per tonne": "cost", "Least effort": "effort"}
    shown = R.rank(actions, key_map[sort_by])
    if module_filter != "All modules":
        shown = [a for a in shown
                 if F.MODULE_META[a.module]["label"] == module_filter]

    st.markdown(f"##### All {len(shown)} actions")
    st.caption("Tick an action to pledge it. Your plan updates on the net-zero page.")

    # The pledge set is rebuilt from the checkboxes that actually rendered this
    # run. Actions filtered out of view keep their existing pledge untouched,
    # so switching the module filter never silently drops a commitment.
    pledged = set(plan.get("pledged", []))
    for action in shown:
        checked = _action_card(action, plan, pledgeable=True,
                               currently_pledged=action.id in pledged)
        if checked:
            pledged.add(action.id)
        else:
            pledged.discard(action.id)
    plan["pledged"] = sorted(pledged)

    if plan["pledged"]:
        chosen = [a for a in actions if a.id in set(plan["pledged"])]
        saved = sum(a.annual_kg for a in chosen)
        net = sum(a.annual_net_inr for a in chosen)
        C.insight(
            f"<b>{len(chosen)} actions pledged</b>, worth <b>{saved:,.0f} kg CO₂e a "
            f"year</b> ({saved / fp.annual_kg:.0%} of your footprint)"
            + (f" and <b>₹{-net:,.0f} a year back in your pocket</b>."
               if net <= 0 else f" at a net <b>₹{net:,.0f} a year</b>.")
            + " Open the net-zero plan to see the glide path.", "good",
        )


def _action_card(action: R.Action, plan: dict, pledgeable: bool = False,
                 currently_pledged: bool = False) -> bool:
    """Render one action. Returns its pledge state when pledgeable."""
    chips: list[tuple[str, str]] = [
        ("save", f"−{action.annual_kg:,.0f} kg CO₂e/yr"),
        (EFFORT_CLASS.get(action.effort, "medium"), action.effort),
    ]
    if action.annual_net_inr < 0:
        chips.append(("save", f"Pays back ₹{-action.annual_net_inr:,.0f}/yr"))
    elif action.annual_net_inr > 0:
        chips.append(("cost", f"Costs ₹{action.annual_net_inr:,.0f}/yr net"))
    if action.capex_inr > 0:
        chips.append(("cost", f"₹{action.capex_inr:,.0f} up front"))
    if action.payback_years:
        chips.append(("save", f"Payback {action.payback_years:.1f} yr"))
    chips.append(("", f"₹{action.cost_per_tonne:+,.0f} per tonne"))
    for sdg in action.sdgs[:2]:
        if sdg in R.SDG:
            chips.append(("", R.SDG[sdg]))

    detail = action.detail
    if action.co_benefit:
        detail = f"{detail} {action.co_benefit}"

    if not pledgeable:
        C.action_card(action.title, detail, chips)
        return False

    col_main, col_check = st.columns([6, 1])
    with col_main:
        C.action_card(action.title, detail, chips)
    with col_check:
        st.write("")
        return st.checkbox("Pledge", value=currently_pledged,
                           key=f"pledge_{action.id}")
