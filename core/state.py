"""
Session state: the single place the app stores what the user told us.

ARCHITECTURE NOTE (this is the v2 change that matters):
v1 computed a number inside each tab and threw it away, so no tab knew about
any other and there was no such thing as a total footprint. v2 stores only
INPUTS here and derives every result with pure functions in core/calculators.py.
That means the dashboard, the recommendation engine, the net-zero pathway and
the report all read one consistent picture, and any module can be recomputed
without touching the UI.
"""

from __future__ import annotations

import copy
from typing import Any

from core import factors as F

# ---------------------------------------------------------------------------
# Defaults describe a realistic Indian engineering student living in a hostel.
# They exist so the dashboard is populated and demo-able the instant it loads --
# nobody should have to fill six forms before seeing the point.
# ---------------------------------------------------------------------------

DEFAULT_PROFILE: dict[str, Any] = {
    "name": "",
    "persona": "Student (hosteller)",
    "campus": "Aditya University",
    "location": "Kakinada / Surampalem (AP)",
    "household_size": 4,
    "grid_preset": "India national average",
    "grid_ef": F.DEFAULT_GRID_EF,
    "include_td_losses": True,
    "tariff_preset": "Domestic average",
    "tariff": F.DEFAULT_TARIFF,
    "campus_population": 8000,
    # Electricity can be measured two ways and they describe THE SAME kWh.
    # Adding both would double-count, so exactly one is authoritative and the
    # other becomes a diagnostic cross-check. See core/engine.py.
    "electricity_source": "bill",
}

PERSONAS = [
    "Student (hosteller)",
    "Student (day scholar)",
    "Faculty / research scholar",
    "Non-teaching staff",
]

DEFAULT_INPUTS: dict[str, dict[str, Any]] = {
    # ---- Electricity -------------------------------------------------------
    "electricity": {
        "entry_mode": "Monthly bill (₹)",
        "monthly_bill": 1800.0,
        "monthly_units": 257.0,
        "share_with_household": True,
        "solar_kw": 0.0,
        "green_tariff_share": 0.0,
    },
    # ---- Commute -----------------------------------------------------------
    # A list of legs, so "bus then walk" is expressible instead of one mode.
    "commute": {
        "legs": [
            {"mode": "City bus", "distance_km": 8.0, "days_per_week": 5,
             "round_trip": True, "occupancy": 1},
            {"mode": "Walk", "distance_km": 1.2, "days_per_week": 5,
             "round_trip": True, "occupancy": 1},
        ],
        "wfh_days": 0,
        "intercity": [
            {"mode": "Train (sleeper / non-AC)", "distance_km": 350.0, "trips_per_year": 8},
        ],
    },
    # ---- Appliances --------------------------------------------------------
    "appliances": {
        "has_ac": True,
        "ac_tons": 1.5,
        "ac_class": "3-star, non-inverter",
        "ac_hours": 6.0,
        "ac_temp": 24.0,
        "ac_months": 6,
        "wash_mode": "Cold wash, full load",
        "wash_cycles_week": 3.0,
        "dryer_cycles_week": 0.0,
        "share_with_household": True,
        "devices": {name: spec["count"] for name, spec in F.APPLIANCES.items()},
        "device_hours": {name: spec["hours"] for name, spec in F.APPLIANCES.items()},
    },
    # ---- Water -------------------------------------------------------------
    "water": {
        "source": "Campus / hostel supply",
        "quantities": {name: spec["default_qty"] for name, spec in F.WATER_END_USES.items()},
        "heater_type": "Electric geyser",
        "has_ro": True,
        "ro_litres_day": 4.0,
        "bottled_litres_week": 2.0,
        "roof_area_m2": 0.0,
        "leaking_taps": 1,
    },
    # ---- Waste -------------------------------------------------------------
    "waste": {
        "streams": {
            name: {"kg_week": spec["default_kg_week"],
                   "route": list(spec["routes"].keys())[0]}
            for name, spec in F.WASTE_STREAMS.items()
        },
    },
    # ---- Campus life -------------------------------------------------------
    "campus": {
        "meals": {
            "Vegetarian thali": 12.0,
            "Egg-based meal": 4.0,
            "Chicken meal": 4.0,
            "Mutton / goat meal": 1.0,
        },
        "beverages": {"Tea with milk": 14.0, "Milk coffee / latte": 2.0},
        "consumables": {
            "Bottled water (1 L)": 4.0,
            "Disposable cup": 7.0,
            "A4 page printed": 40.0,
            "Food delivery order": 3.0,
            "Plastic carry bag": 4.0,
        },
        "digital": {
            "Video streaming (HD, per hour)": 14.0,
            "Social media / short video (per hour)": 21.0,
            "Video calls (per hour)": 3.0,
            "AI assistant use (per hour)": 5.0,
        },
        "goods": {"T-shirt": 4, "Jeans / trousers": 2, "Shoes / sneakers": 1,
                  "Smartphone": 1, "Laptop": 1, "Printed textbook": 4},
        "plate_waste_g_day": 120.0,
        "laundry_kg_week": 0.0,
    },
    # ---- Net-zero planning -------------------------------------------------
    "plan": {
        "target_year": 2030,
        "target_reduction_pct": 50,
        "pledged": [],
    },
}


def init_state(session_state) -> None:
    """Populate Streamlit session state on first run. Idempotent."""
    if "profile" not in session_state:
        session_state["profile"] = copy.deepcopy(DEFAULT_PROFILE)
    if "inputs" not in session_state:
        session_state["inputs"] = copy.deepcopy(DEFAULT_INPUTS)
    if "page" not in session_state:
        session_state["page"] = "dashboard"
    if "visited" not in session_state:
        # Which modules the user has actually opened and reviewed. Defaults are
        # honest starting estimates, not measurements, and the UI distinguishes
        # the two so nobody presents a default as their own data.
        session_state["visited"] = set()
    if "chat" not in session_state:
        session_state["chat"] = []
    # A newer version of the app may add keys that an older session lacks.
    for module, defaults in DEFAULT_INPUTS.items():
        session_state["inputs"].setdefault(module, copy.deepcopy(defaults))
        for key, value in defaults.items():
            session_state["inputs"][module].setdefault(key, copy.deepcopy(value))
    for key, value in DEFAULT_PROFILE.items():
        session_state["profile"].setdefault(key, value)


# Keys the app manages itself; everything else in session state belongs to a
# keyed Streamlit widget.
_STRUCTURAL_KEYS = {"profile", "inputs", "visited", "chat", "page"}


def reset_state(session_state) -> None:
    """
    Back to the demo defaults.

    Resetting the `inputs` dict alone is NOT enough, and getting this wrong
    makes the reset button look broken. Most inputs are rendered by widgets
    with explicit keys (device counts, meal counts, waste routes, pledges), and
    Streamlit gives a keyed widget's stored state precedence over the `value`
    argument on re-render. So the old widget state would immediately overwrite
    the fresh defaults. Every widget key is cleared here as well, which also
    clears the pledge checkboxes.
    """
    for key in [k for k in list(session_state.keys()) if k not in _STRUCTURAL_KEYS]:
        del session_state[key]
    session_state["profile"] = copy.deepcopy(DEFAULT_PROFILE)
    session_state["inputs"] = copy.deepcopy(DEFAULT_INPUTS)
    session_state["visited"] = set()
    session_state["chat"] = []


def mark_visited(session_state, module: str) -> None:
    session_state["visited"] = set(session_state.get("visited", set())) | {module}


def household_divisor(profile: dict, share: bool) -> float:
    """
    Shared bills should be divided, or six flatmates each 'own' the whole meter.
    Hostellers are treated as sharing with their room, day scholars with the home.
    """
    if not share:
        return 1.0
    return max(1.0, float(profile.get("household_size", 1)))
