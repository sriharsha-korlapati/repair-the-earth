import sys
import os
import streamlit as st
import time

# -----------------------------
# Project Path Setup
# -----------------------------
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(PROJECT_ROOT)

from services.transport_pipeline import transport_impact_pipeline
from services.appliance_pipeline import appliance_impact_pipeline

# -----------------------------
# Constants (transparent & explainable)
# -----------------------------
COST_PER_KWH = 7.0
CO2_PER_KWH = 0.82          # kg
TREE_CO2_YEAR = 21.0        # kg
PHONE_CHARGE_CO2 = 0.005    # kg

# -----------------------------
# Session State
# -----------------------------
if "module" not in st.session_state:
    st.session_state.module = "electricity"

# -----------------------------
# Page Config
# -----------------------------
st.set_page_config(
    page_title="Repair the Earth – Carbon Intelligence",
    layout="centered"
)

# -----------------------------
# Styles (UNCHANGED)
# -----------------------------
st.markdown("""
<style>
body { background-color: #0f172a; }
h1, h2 { color: #e5e7eb; }

.nav {
    display: flex;
    gap: 0.4rem;
    justify-content: center;
    margin-bottom: 1.4rem;
}

.nav-btn {
    border-radius: 999px;
    padding: 0.55rem 1.2rem;
    font-size: 0.85rem;
    border: 1px solid #1e293b;
    background-color: #020617;
    color: #94a3b8;
}

.nav-btn-active {
    background-color: #22c55e !important;
    color: #052e16 !important;
    border-color: #22c55e !important;
}

.card {
    background-color: #020617;
    border-radius: 14px;
    padding: 1.1rem;
    border: 1px solid #1e293b;
    text-align: center;
}

.impact-number {
    font-size: 1.9rem;
    font-weight: 700;
    color: #22c55e;
}

.impact-label {
    color: #9ca3af;
    font-size: 0.85rem;
}

.explain {
    background-color: #020617;
    border-left: 5px solid #22c55e;
    border-radius: 12px;
    padding: 1.1rem;
    margin-top: 1.2rem;
    color: #e5e7eb;
}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# Header
# -----------------------------
st.markdown("""
<h1 style="text-align:center;">🌱 Repair the Earth</h1>
<p style="text-align:center;color:#9ca3af;">
Carbon intelligence for everyday actions
</p>
""", unsafe_allow_html=True)

# -----------------------------
# SINGLE CLICKABLE PILL NAV (UNCHANGED)
# -----------------------------
cols = st.columns(3)
modules = [
    ("⚡ Electricity", "electricity"),
    ("🚗 Commute", "commute"),
    ("🏠 Appliances", "appliances")
]

for col, (label, key) in zip(cols, modules):
    with col:
        if st.button(label, key=f"nav-{key}", use_container_width=True):
            st.session_state.module = key

# =====================================================================
# ⚡ ELECTRICITY
# =====================================================================
if st.session_state.module == "electricity":

    st.markdown("## ⚡ Electricity Impact")

    bill = st.number_input("Monthly electricity bill (₹)", min_value=0, value=356)

    units = bill / COST_PER_KWH
    monthly_co2 = units * CO2_PER_KWH
    yearly_co2 = monthly_co2 * 12

    c1, c2, c3 = st.columns(3)
    c1.markdown(f"<div class='card'><div class='impact-number'>{units:.1f}</div><div class='impact-label'>kWh / month</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='card'><div class='impact-number'>{monthly_co2:.1f}</div><div class='impact-label'>kg CO₂ / month</div></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='card'><div class='impact-number'>{yearly_co2:.0f}</div><div class='impact-label'>kg CO₂ / year</div></div>", unsafe_allow_html=True)

    st.markdown("### 🔎 What this equals to")
    r1, r2, r3 = st.columns(3)
    r1.markdown(f"<div class='card'>🌳 {yearly_co2 / TREE_CO2_YEAR:.1f} trees / year</div>", unsafe_allow_html=True)
    r2.markdown(f"<div class='card'>📱 {monthly_co2 / PHONE_CHARGE_CO2:.0f} phone charges</div>", unsafe_allow_html=True)
    r3.markdown(f"<div class='card'>💰 ₹{bill:.0f} / month</div>", unsafe_allow_html=True)

    st.markdown("""
    <div class="explain">
    💡 One tube-light left ON daily ≈ 18–20 kg CO₂ / year<br/>
    🌱 Reduce peak usage & switch off standby loads
    </div>
    """, unsafe_allow_html=True)

# =====================================================================
# 🚗 COMMUTE
# =====================================================================
if st.session_state.module == "commute":

    st.markdown("## 🚗 Daily Commute Impact")

    mode = st.selectbox("Mode", [
    "Walk / Cycle",
    "Bike (Petrol)",
    "EV Bike",
    "Bus",
    "Metro",
    "Car (Petrol)",
    "Car (Diesel)",
    "EV Car",
    "Ride-sharing Auto (Ola / Rapido)"
])

    distance = st.number_input("One-way distance (km)", value=5.0)
    days = st.slider("Days per week", 1, 7, 5)

    result = transport_impact_pipeline(mode, distance, days)
    monthly_co2 = result["co2"]["monthly_kg"]
    yearly_co2 = result["co2"]["yearly_kg"]
    monthly_cost = result["cost_inr"]["monthly"]

    c1, c2 = st.columns(2)
    c1.markdown(f"<div class='card'><div class='impact-number'>{monthly_co2:.1f}</div><div class='impact-label'>kg CO₂ / month</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='card'><div class='impact-number'>{yearly_co2:.0f}</div><div class='impact-label'>kg CO₂ / year</div></div>", unsafe_allow_html=True)

    st.markdown("### 🔎 What this equals to")
    r1, r2, r3 = st.columns(3)
    r1.markdown(f"<div class='card'>🌳 {yearly_co2 / TREE_CO2_YEAR:.1f} trees</div>", unsafe_allow_html=True)
    r2.markdown(f"<div class='card'>📱 {monthly_co2 / PHONE_CHARGE_CO2:.0f} phone charges</div>", unsafe_allow_html=True)
    r3.markdown(f"<div class='card'>💰 ₹{monthly_cost:.0f} / month</div>", unsafe_allow_html=True)

    st.markdown("""
    <div class="explain">
    💡 Switching 1 day/week to WFH cuts ~20% commute emissions<br/>
    🌱 Club trips & prefer public transport
    </div>
    """, unsafe_allow_html=True)

# =====================================================================
# 🏠 APPLIANCES
# =====================================================================
if st.session_state.module == "appliances":

    st.markdown("## 🏠 Home Appliance Habits")

    ac_hours = st.slider("AC hours/day", 0, 12, 6)
    ac_temp = st.slider("AC temperature (°C)", 18, 30, 26)
    wash_cycles = st.slider("Washing cycles/week", 0, 10, 3)
    load = st.selectbox("Wash load", ["Full Load", "Half Load"])

    result = appliance_impact_pipeline(ac_hours, ac_temp, wash_cycles, load)
    monthly_co2 = result["impact"]["monthly_co2_kg"]
    yearly_co2 = result["impact"]["annual_co2_kg"]
    monthly_cost = result["cost_inr"]["monthly"]

    c1, c2 = st.columns(2)
    c1.markdown(f"<div class='card'><div class='impact-number'>{monthly_co2:.1f}</div><div class='impact-label'>kg CO₂ / month</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='card'><div class='impact-number'>{yearly_co2:.0f}</div><div class='impact-label'>kg CO₂ / year</div></div>", unsafe_allow_html=True)

    st.markdown("### 🔎 What this equals to")
    r1, r2, r3 = st.columns(3)
    r1.markdown(f"<div class='card'>🌳 {yearly_co2 / TREE_CO2_YEAR:.1f} trees</div>", unsafe_allow_html=True)
    r2.markdown(f"<div class='card'>📱 {monthly_co2 / PHONE_CHARGE_CO2:.0f} phone charges</div>", unsafe_allow_html=True)
    r3.markdown(f"<div class='card'>💰 ₹{monthly_cost:.0f} / month</div>", unsafe_allow_html=True)

    st.markdown("""
    <div class="explain">
    💡 1°C higher AC setting saves ~6% energy<br/>
    🌱 Always wash full loads & air-dry when possible
    </div>
    """, unsafe_allow_html=True)
