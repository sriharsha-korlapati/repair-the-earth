"""
Repair the Earth -- Carbon Intelligence v2
==========================================

An interactive carbon footprint dashboard for Indian students, faculty and
campuses: measure six domains, see one honest total, and get a costed,
ranked list of actions generated from your own numbers.

WHAT CHANGED FROM v1
--------------------
v1 was three isolated tabs (electricity, commute, appliances). Each computed a
number and discarded it, so there was no total footprint, no comparison, and no
advice. v2 adds:

  * three new modules -- water, waste and campus life -- where campus life is
    usually the largest slice of a student's footprint and was entirely absent
  * one aggregated footprint, with the electricity/appliance double-count
    resolved explicitly instead of silently
  * a recommendation engine that generates costed actions from the user's own
    inputs, ranked on a marginal abatement cost curve
  * a net-zero pathway with pledges, a glide path and campus scale-up
  * an optional Claude-powered coach layered on top of the deterministic engine
  * a methodology page that publishes every coefficient the model uses

v1 is preserved at legacy/app_v1.py so the two can be demonstrated side by side.

Run with:  streamlit run app.py
"""

from __future__ import annotations

import streamlit as st

from core import calculators, engine, factors as F, recommend as R, state
from modules import (
    about_page,
    actions_page,
    appliances,
    ask_page,
    campus,
    commute,
    dashboard,
    electricity,
    plan_page,
    waste,
    water,
)
from ui import components as C, theme as T

st.set_page_config(
    page_title="Repair the Earth · Carbon Intelligence",
    page_icon="🌍",
    layout="wide",
    # "auto" keeps the sidebar open on a desktop and collapsed on a phone.
    # With "expanded", a phone user landed on a full-screen nav panel with
    # the dashboard hidden behind it.
    initial_sidebar_state="auto",
)

C.inject_css()
state.init_state(st.session_state)

PROFILE = st.session_state["profile"]
INPUTS = st.session_state["inputs"]

# Page registry. Module pages are ordered as a person would work through them:
# see the total, drill into each source, then decide what to do.
MODULE_PAGES = {
    "electricity": electricity,
    "commute": commute,
    "appliances": appliances,
    "water": water,
    "waste": waste,
    "campus": campus,
}

NAV = [
    ("dashboard", "📊 Dashboard"),
    ("electricity", "⚡ Electricity"),
    ("commute", "🚌 Commute"),
    ("appliances", "🏠 Appliances"),
    ("water", "💧 Water"),
    ("waste", "♻️ Waste"),
    ("campus", "🎓 Campus life"),
    ("actions", "🎯 What to do"),
    ("plan", "📉 Net-zero plan"),
    ("ask", "💬 Ask anything"),
    ("about", "📖 Method & export"),
]


# ---------------------------------------------------------------------------
# Sidebar: the profile that every module computes against
# ---------------------------------------------------------------------------

def sidebar() -> str:
    """
    Navigation plus settings.

    Everything below the nav lives in collapsed expanders. On a phone the
    sidebar IS the screen while it is open, so it has to be a short list of
    destinations, not a long settings form the user must scroll past.
    """
    with st.sidebar:
        st.markdown("### 🌍 Repair the Earth")

        labels = [label for _, label in NAV]
        keys = [key for key, _ in NAV]
        current = st.session_state.get("page", "dashboard")
        index = keys.index(current) if current in keys else 0
        choice = st.radio("Go to", labels, index=index, label_visibility="collapsed")
        page = keys[labels.index(choice)]

        with st.expander("Profile"):
            PROFILE["name"] = st.text_input("Name (optional)", PROFILE.get("name", ""))
            PROFILE["persona"] = st.selectbox(
                "You are a", state.PERSONAS,
                index=state.PERSONAS.index(PROFILE.get("persona", state.PERSONAS[0]))
                if PROFILE.get("persona") in state.PERSONAS else 0,
            )
            PROFILE["campus"] = st.text_input("Campus", PROFILE.get("campus", ""))
            locations = list(F.RAINFALL_MM.keys())
            PROFILE["location"] = st.selectbox(
                "Location", locations,
                index=locations.index(PROFILE.get("location", locations[0]))
                if PROFILE.get("location") in locations else 0,
                help="Sets local rainfall for the rainwater estimate.",
            )
            PROFILE["household_size"] = st.number_input(
                "People sharing your bills", min_value=1, max_value=20,
                value=int(PROFILE.get("household_size", 4)),
                help="Shared electricity and water are divided by this.",
            )

        with st.expander("Grid & tariff"):
            presets = list(F.GRID_PRESETS.keys())
            PROFILE["grid_preset"] = st.selectbox(
                "Your grid", presets + ["Custom"],
                index=(presets + ["Custom"]).index(PROFILE.get("grid_preset", presets[0]))
                if PROFILE.get("grid_preset") in presets + ["Custom"] else 0,
            )
            if PROFILE["grid_preset"] == "Custom":
                PROFILE["grid_ef"] = st.number_input(
                    "kg CO₂ per kWh", min_value=0.1, max_value=1.5,
                    value=float(PROFILE.get("grid_ef", F.DEFAULT_GRID_EF)), step=0.01,
                )
            else:
                PROFILE["grid_ef"] = F.GRID_PRESETS[PROFILE["grid_preset"]]
            PROFILE["include_td_losses"] = st.checkbox(
                f"Add {F.TD_LOSS_FRACTION:.0%} grid losses",
                value=bool(PROFILE.get("include_td_losses", True)),
                help="About a tenth of generated power never reaches your meter.",
            )
            st.caption(f"At your meter: **{calculators.grid_ef(PROFILE):.3f} kg CO₂/kWh**")

            tariffs = list(F.TARIFF_PRESETS.keys())
            PROFILE["tariff_preset"] = st.selectbox(
                "Tariff band", tariffs + ["Custom"],
                index=(tariffs + ["Custom"]).index(PROFILE.get("tariff_preset", tariffs[1]))
                if PROFILE.get("tariff_preset") in tariffs + ["Custom"] else 1,
            )
            if PROFILE["tariff_preset"] == "Custom":
                PROFILE["tariff"] = st.number_input(
                    "₹ per kWh", min_value=0.5, max_value=30.0,
                    value=float(PROFILE.get("tariff", F.DEFAULT_TARIFF)), step=0.25,
                )
            else:
                PROFILE["tariff"] = F.TARIFF_PRESETS[PROFILE["tariff_preset"]]

        with st.expander("Electricity accounting"):
            st.caption(
                "Your bill and your appliance list measure the same kWh. One is "
                "the total; the other becomes a cross-check."
            )
            source_labels = {
                "bill": "My bill",
                "appliances": "My appliance model",
            }
            PROFILE["electricity_source"] = st.radio(
                "Authoritative source",
                list(source_labels.keys()),
                format_func=lambda key: source_labels[key],
                index=0 if PROFILE.get("electricity_source", "bill") == "bill" else 1,
            )

        if st.button("↺ Reset", width="stretch"):
            state.reset_state(st.session_state)
            st.rerun()
    return page


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

page = sidebar()
st.session_state["page"] = page

# Everything on every page derives from one computation, so no two pages can
# ever disagree about the same number.
footprint = engine.build(INPUTS, PROFILE)
actions = R.generate(INPUTS, PROFILE, footprint.results,
                     skip_modules=set(footprint.diagnostic))

subtitle = "Carbon intelligence for everyday actions"
if PROFILE.get("campus"):
    subtitle = f"{subtitle} · {PROFILE['campus']}"
C.header("Repair the Earth", subtitle, badge="v2")
st.write("")

if page == "dashboard":
    dashboard.render(footprint, PROFILE, actions,
                     set(st.session_state.get("visited", set())))

elif page in MODULE_PAGES:
    state.mark_visited(st.session_state, page)
    MODULE_PAGES[page].render(INPUTS[page], PROFILE)

    # Inputs may have changed this run, so recompute before showing the footer
    # numbers -- otherwise the summary lags one interaction behind.
    refreshed = engine.build(INPUTS, PROFILE)
    st.divider()
    meta = F.MODULE_META[page]
    is_counted = page in refreshed.counted
    share = refreshed.share_of(page) if is_counted else 0.0
    cols = st.columns([2, 1])
    with cols[0]:
        if is_counted:
            C.insight(
                f"{meta['icon']} <b>{meta['label']}</b> is "
                f"<b>{refreshed.counted[page]:,.0f} kg CO₂e a year</b>, "
                f"{share:.0%} of your total footprint of "
                f"{refreshed.annual_kg:,.0f} kg."
            )
        else:
            C.insight(
                f"{meta['icon']} <b>{meta['label']}</b> is measured as a "
                "cross-check and is not added to your total - see the sidebar.",
                "info",
            )
    with cols[1]:
        if st.button("📊 Back to the dashboard", width="stretch"):
            st.session_state["page"] = "dashboard"
            st.rerun()

elif page == "actions":
    actions_page.render(footprint, PROFILE, actions, INPUTS["plan"])

elif page == "plan":
    plan_page.render(footprint, PROFILE, actions, INPUTS["plan"])

elif page == "ask":
    ask_page.render(footprint, PROFILE, actions, st.session_state)

elif page == "about":
    about_page.render(footprint, PROFILE, actions, INPUTS["plan"])
