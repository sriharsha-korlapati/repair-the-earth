"""
Emission, cost and resource factors for the Repair the Earth carbon engine.

DESIGN RULE: every number a calculation uses lives here, with a unit and a note.
Nothing is hard-coded inside a calculator or a UI file. That is what makes the
dashboard explainable -- the "Assumptions" page renders this module directly, so
a judge or a reviewer can audit every single coefficient.

Values are India-relevant approximations compiled from public literature (CEA
CO2 baseline database, BEE star-rating data, IPCC/DEFRA waste and food factors,
published transport life-cycle studies). They are good enough for decision
support -- "which lever matters most" -- and are NOT audit-grade inventory
numbers. Treat them as v2 defaults that a user can override in the UI.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# 1. ELECTRICITY GRID
# ---------------------------------------------------------------------------

# kg CO2 per kWh delivered at the generator busbar.
GRID_PRESETS: dict[str, float] = {
    "India national average": 0.71,
    "Coal-heavy state grid": 0.85,
    "Balanced state grid": 0.75,
    "High-renewable state grid": 0.55,
}
DEFAULT_GRID_EF = 0.71

# Transmission & distribution losses: ~10% of generation never reaches the meter,
# so a consumer-side kWh carries more emissions than a busbar kWh.
TD_LOSS_FRACTION = 0.10

# Rupees per kWh. Domestic tariffs are slab-based and vary by state/DISCOM;
# these are representative bands, not a tariff schedule.
TARIFF_PRESETS: dict[str, float] = {
    "Domestic subsidised (low slab)": 4.5,
    "Domestic average": 7.0,
    "Domestic high slab": 9.5,
    "Commercial / institutional": 11.0,
}
DEFAULT_TARIFF = 7.0

# Rooftop solar in India: ~4.0 kWh generated per kW installed per day (annual avg).
SOLAR_KWH_PER_KW_PER_DAY = 4.0
SOLAR_CAPEX_PER_KW = 45_000.0  # rupees, after residential subsidy
SOLAR_LIFETIME_YEARS = 25


# ---------------------------------------------------------------------------
# 2. TRANSPORT
# ---------------------------------------------------------------------------
# "ef" is kg CO2e per kilometre travelled by the VEHICLE for private modes
# (divide by occupancy to get per-passenger) and per PASSENGER-km for shared
# public modes, where average loading is already baked in.
#
# Electric modes store kwh_per_km instead of ef, so their emissions move with
# whichever grid factor the user selects -- an EV is only as clean as its grid.

TRANSPORT_MODES: dict[str, dict] = {
    "Walk": {
        "ef": 0.0, "cost_per_km": 0.0, "basis": "passenger",
        "occupancy": 1, "speed_kmph": 4.5, "active": True,
        "note": "Zero tailpipe and zero fuel cost.",
    },
    "Bicycle": {
        "ef": 0.0, "cost_per_km": 0.15, "basis": "passenger",
        "occupancy": 1, "speed_kmph": 14.0, "active": True,
        "note": "Cost is tyre/chain maintenance only.",
    },
    "Motorcycle (petrol)": {
        "ef": 0.051, "cost_per_km": 2.3, "basis": "vehicle",
        "occupancy": 1, "speed_kmph": 30.0,
        "note": "45 km/l at 2.31 kg CO2 per litre of petrol.",
    },
    "Scooter (petrol)": {
        "ef": 0.058, "cost_per_km": 2.6, "basis": "vehicle",
        "occupancy": 1, "speed_kmph": 28.0,
        "note": "40 km/l at 2.31 kg CO2 per litre.",
    },
    "Electric two-wheeler": {
        "kwh_per_km": 0.030, "cost_per_km": 0.35, "basis": "vehicle",
        "occupancy": 1, "speed_kmph": 28.0,
        "note": "30 Wh/km at the wall; emissions follow your grid factor.",
    },
    "Car (petrol)": {
        "ef": 0.154, "cost_per_km": 7.0, "basis": "vehicle",
        "occupancy": 1, "speed_kmph": 25.0,
        "note": "15 km/l hatchback. Per-person impact falls with every extra rider.",
    },
    "Car (diesel)": {
        "ef": 0.149, "cost_per_km": 5.5, "basis": "vehicle",
        "occupancy": 1, "speed_kmph": 25.0,
        "note": "18 km/l at 2.68 kg CO2 per litre of diesel.",
    },
    "Car (CNG)": {
        "ef": 0.138, "cost_per_km": 3.5, "basis": "vehicle",
        "occupancy": 1, "speed_kmph": 25.0,
        "note": "20 km/kg at 2.75 kg CO2 per kg of CNG.",
    },
    "Electric car": {
        "kwh_per_km": 0.150, "cost_per_km": 1.5, "basis": "vehicle",
        "occupancy": 1, "speed_kmph": 25.0,
        "note": "150 Wh/km at the wall; emissions follow your grid factor.",
    },
    "City bus": {
        "ef": 0.030, "cost_per_km": 1.2, "basis": "passenger",
        "occupancy": 1, "speed_kmph": 18.0,
        "note": "Diesel bus at typical Indian occupancy (~40 passengers).",
    },
    "Metro / local train": {
        "kwh_per_km": 0.030, "cost_per_km": 1.8, "basis": "passenger",
        "occupancy": 1, "speed_kmph": 32.0,
        "note": "30 Wh per passenger-km; the lowest-carbon motorised city option.",
    },
    "Auto rickshaw (CNG)": {
        "ef": 0.107, "cost_per_km": 12.0, "basis": "vehicle",
        "occupancy": 2, "speed_kmph": 20.0,
        "note": "Shared autos split both the fare and the carbon.",
    },
    "Bike taxi (Rapido)": {
        "ef": 0.058, "cost_per_km": 6.0, "basis": "vehicle",
        "occupancy": 1, "speed_kmph": 28.0,
        "note": "Scooter factor; ignores the rider's empty approach trip.",
    },
    "Cab / ride-hail (Ola, Uber)": {
        "ef": 0.216, "cost_per_km": 15.0, "basis": "vehicle",
        "occupancy": 1, "speed_kmph": 24.0,
        "note": "Petrol car factor x1.4 to account for empty deadhead kilometres.",
    },
}

# Long-distance travel: kg CO2e per passenger-km. Charged as trips per year, not
# daily commute -- for a hosteller, going home can outweigh the whole semester.
INTERCITY_MODES: dict[str, dict] = {
    "Train (sleeper / non-AC)": {"ef": 0.012, "cost_per_km": 0.5,
                                 "note": "Most carbon-efficient way to cross India."},
    "Train (AC coach)": {"ef": 0.020, "cost_per_km": 1.2,
                         "note": "Air-conditioning roughly doubles rail intensity."},
    "Bus (intercity)": {"ef": 0.030, "cost_per_km": 1.3,
                        "note": "Similar to a city bus per passenger-km."},
    "Car (shared, 4 people)": {"ef": 0.039, "cost_per_km": 1.8,
                               "note": "Petrol car split four ways."},
    "Domestic flight (economy)": {"ef": 0.135, "cost_per_km": 4.5,
                                  "note": "Short-haul economy; excludes high-altitude "
                                          "radiative forcing, which could nearly double it."},
}


# ---------------------------------------------------------------------------
# 3. APPLIANCES
# ---------------------------------------------------------------------------
# Rated power in watts and typical daily usage. kWh = watts/1000 * hours * count.

APPLIANCES: dict[str, dict] = {
    "Ceiling fan (conventional)": {"watts": 70, "hours": 10.0, "count": 1,
                                   "note": "Induction-motor fan."},
    "Ceiling fan (BLDC, 5-star)": {"watts": 32, "hours": 10.0, "count": 0,
                                   "note": "Half the power for the same airflow."},
    "LED bulb / tube": {"watts": 10, "hours": 6.0, "count": 3, "note": "9-12 W typical."},
    "CFL bulb": {"watts": 15, "hours": 6.0, "count": 0, "note": "Replace with LED."},
    "Incandescent bulb": {"watts": 60, "hours": 6.0, "count": 0,
                          "note": "90% of the energy becomes heat, not light."},
    "Laptop": {"watts": 50, "hours": 6.0, "count": 1, "note": "Charging plus use."},
    "Desktop computer + monitor": {"watts": 160, "hours": 4.0, "count": 0,
                                   "note": "Roughly 3x a laptop for the same work."},
    "Phone / tablet charging": {"watts": 10, "hours": 2.0, "count": 1,
                                "note": "Small, but everyone asks about it."},
    "LED television": {"watts": 55, "hours": 3.0, "count": 0, "note": "32-inch class."},
    "Refrigerator (250 L, 3-star)": {"watts": 50, "hours": 24.0, "count": 0,
                                     "note": "~1.2 kWh/day averaged over the compressor cycle."},
    "Geyser / water heater (15 L)": {"watts": 2000, "hours": 0.5, "count": 0,
                                     "note": "The single biggest watt-hog in most homes."},
    "Air cooler (desert cooler)": {"watts": 180, "hours": 8.0, "count": 0,
                                   "note": "About a tenth of an AC's power draw."},
    "Microwave oven": {"watts": 1200, "hours": 0.25, "count": 0, "note": "Short bursts."},
    "Induction cooktop": {"watts": 1800, "hours": 1.0, "count": 0,
                          "note": "Cleaner than LPG only on a clean grid."},
    "Electric kettle": {"watts": 1500, "hours": 0.2, "count": 0, "note": "Hostel favourite."},
    "RO water purifier": {"watts": 60, "hours": 2.0, "count": 0,
                          "note": "Also rejects 2-3 litres per litre purified."},
    "Iron (clothes)": {"watts": 1000, "hours": 0.2, "count": 0, "note": "High watts, short use."},
    "Standby / phantom load": {"watts": 15, "hours": 24.0, "count": 1,
                               "note": "Set-top boxes, chargers and TVs left plugged in."},
}

# Air conditioner: average power drawn per tonne of cooling, by efficiency class.
AC_WATTS_PER_TON: dict[str, float] = {
    "3-star, non-inverter": 1100.0,
    "5-star, non-inverter": 950.0,
    "3-star, inverter": 900.0,
    "5-star, inverter": 750.0,
}
AC_REFERENCE_TEMP_C = 24.0        # BEE-recommended default setpoint
AC_PERCENT_PER_DEGREE = 0.06      # ~6% more energy for every degree below 24 C
AC_MIN_LOAD_FACTOR = 0.55         # floor, so a very high setpoint never reads as free

# Washing machine energy per cycle, by water temperature and load.
WASH_KWH_PER_CYCLE: dict[str, float] = {
    "Cold wash, full load": 0.45,
    "Cold wash, half load": 0.32,
    "Warm wash, full load": 1.10,
    "Warm wash, half load": 0.80,
}
DRYER_KWH_PER_CYCLE = 2.5  # tumble dryer; air-drying is free in most of India


# ---------------------------------------------------------------------------
# 4. WATER  (the water-energy-carbon nexus)
# ---------------------------------------------------------------------------
# Water has no emissions of its own. It carries carbon because we pump it,
# treat it, heat it and then treat it again as sewage. That chain is what this
# module makes visible.

WATER_END_USES: dict[str, dict] = {
    "Bucket bath": {"litres": 25.0, "unit": "bath", "hot_share": 0.5, "default_qty": 1.0,
                    "note": "A bucket is 15-25 L."},
    "Shower": {"litres": 9.0, "unit": "minute", "hot_share": 0.5, "default_qty": 0.0,
               "note": "9 L per minute for a standard head; 6 L with an aerator."},
    "Toilet flush (full)": {"litres": 10.0, "unit": "flush", "hot_share": 0.0, "default_qty": 5.0,
                            "note": "Older single-flush cisterns."},
    "Toilet flush (dual, half)": {"litres": 4.0, "unit": "flush", "hot_share": 0.0,
                                  "default_qty": 0.0, "note": "Dual-flush half button."},
    "Washbasin / brushing / hand wash": {"litres": 3.0, "unit": "use", "hot_share": 0.1,
                                         "default_qty": 6.0, "note": "A running tap is ~6 L/min."},
    "Dishwashing by hand": {"litres": 25.0, "unit": "day", "hot_share": 0.2, "default_qty": 1.0,
                            "note": "Running-tap washing; a filled sink halves it."},
    "Laundry (machine cycle)": {"litres": 70.0, "unit": "cycle", "hot_share": 0.1,
                                "default_qty": 0.43, "note": "Front-load ~60 L, top-load ~90 L."},
    "Laundry (hand wash)": {"litres": 35.0, "unit": "wash", "hot_share": 0.1,
                            "default_qty": 0.0, "note": "Bucket wash."},
    "Drinking & cooking": {"litres": 8.0, "unit": "day", "hot_share": 0.3, "default_qty": 1.0,
                           "note": "Includes boiling and rinsing."},
    "Floor cleaning / garden / vehicle": {"litres": 20.0, "unit": "day", "hot_share": 0.0,
                                          "default_qty": 1.0,
                                          "note": "A hosed-down bike is 80-100 L; a bucket is 15 L."},
}

# Electricity embodied in delivering one kilolitre (1,000 L) to your tap.
WATER_SOURCE_KWH_PER_KL: dict[str, float] = {
    "Municipal piped supply": 0.55,
    "Borewell (own pump)": 0.40,
    "Tanker delivered": 1.60,
    "Campus / hostel supply": 0.50,
}
WASTEWATER_KWH_PER_KL = 0.30   # sewage collection + treatment
WATER_TARIFF_PER_KL = 25.0     # rupees per kilolitre, typical urban domestic

# Heating one litre by 25 C: 4.18 kJ/kg/K x 25 K / 3600 kJ/kWh / 0.9 efficiency.
HOT_WATER_KWH_PER_LITRE = 0.0324

# Heating water with LPG instead of a geyser. 1 kg of LPG carries ~13.8 kWh of
# heat and emits 2.98 kg CO2; a gas burner delivers ~70% of it to the water.
# On a coal-heavy grid a gas geyser is therefore LOWER-carbon than an electric
# one -- one of the few places where burning fossil fuel directly wins.
LPG_CO2_PER_USEFUL_KWH = 2.98 / (13.8 * 0.70)

# How hot water can be paid for. "Counted in Appliances" exists so the geyser
# is never charged twice when a user fills in both modules.
WATER_HEATER_TYPES: dict[str, dict] = {
    "Electric geyser": {"ef_source": "grid", "note": "Counted here, in the Water module."},
    "Electric geyser (already counted in Appliances)": {
        "ef_source": "none",
        "note": "Hot-water energy is attributed to the geyser you listed under "
                "Appliances, so it is not charged again here.",
    },
    "Solar water heater": {"ef_source": "none",
                           "note": "Effectively zero operating emissions."},
    "LPG / gas geyser": {"ef_source": "lpg",
                         "note": "Emits directly, but often less than a coal-grid geyser."},
    "No hot water": {"ef_source": "none", "note": "Cold water only."},
}

# RO purifiers reject water to flush the membrane.
RO_REJECT_RATIO = 2.5          # litres rejected per litre purified
BOTTLED_WATER_EF_PER_LITRE = 0.20   # kg CO2e: PET bottle + transport + chilling

# Rainwater harvesting: annual rainfall in mm, by location.
RAINFALL_MM: dict[str, float] = {
    "Guntur / Amaravati (AP)": 900.0,
    "Kakinada / Surampalem (AP)": 1100.0,
    "Visakhapatnam (AP)": 1000.0,
    "Hyderabad": 800.0,
    "Bengaluru": 970.0,
    "Chennai": 1400.0,
    "Delhi NCR": 790.0,
    "Mumbai": 2200.0,
}
RAINWATER_RUNOFF_COEFF = 0.80  # fraction of roof rainfall actually capturable


# ---------------------------------------------------------------------------
# 5. WASTE  (route matters more than mass)
# ---------------------------------------------------------------------------
# kg CO2e per kg of waste, BY DISPOSAL ROUTE. Negative numbers are avoided
# emissions: recycling displaces virgin material production, so it is a credit.
# This is the module's core teaching point -- the same banana peel is 1.9 kg
# CO2e in a landfill (anaerobic methane) and 0.18 kg in a compost pit.

WASTE_STREAMS: dict[str, dict] = {
    "Food & kitchen (wet)": {
        "routes": {"Landfill / dump": 1.90, "Composting": 0.18, "Biogas plant": 0.05},
        "value_per_kg": 4.0, "default_kg_week": 3.0,
        "note": "Landfilled food waste decomposes without oxygen and emits methane, "
                "which traps ~28x more heat than CO2. Composting is the single "
                "highest-leverage waste action in India.",
    },
    "Paper & cardboard": {
        "routes": {"Landfill / dump": 1.30, "Recycling": -0.90, "Composting": 0.20},
        "value_per_kg": 12.0, "default_kg_week": 1.0,
        "note": "Recycling avoids virgin pulp; landfilling emits methane.",
    },
    "Plastic": {
        "routes": {"Landfill / dump": 0.05, "Recycling": -1.40, "Incineration": 2.70},
        "value_per_kg": 15.0, "default_kg_week": 0.8,
        "note": "Inert in landfill but never breaks down; burning it is the worst "
                "option for both carbon and air quality.",
    },
    "Glass": {
        "routes": {"Landfill / dump": 0.02, "Recycling": -0.30},
        "value_per_kg": 2.0, "default_kg_week": 0.3,
        "note": "Infinitely recyclable; heavy, so transport dominates.",
    },
    "Metal (cans, scrap)": {
        "routes": {"Landfill / dump": 0.02, "Recycling": -2.00},
        "value_per_kg": 40.0, "default_kg_week": 0.2,
        "note": "Recycled aluminium needs ~95% less energy than smelting new metal.",
    },
    "E-waste": {
        "routes": {"Landfill / dump": 1.40, "Formal recycling": -3.20,
                   "Informal scrap dealer": 0.60},
        "value_per_kg": 90.0, "default_kg_week": 0.05,
        "note": "Highest value and highest toxicity per kg. Formal recovery of gold, "
                "copper and rare earths avoids enormous mining emissions.",
    },
    "Textiles": {
        "routes": {"Landfill / dump": 1.00, "Reuse / donation": -1.80, "Recycling": -0.60},
        "value_per_kg": 8.0, "default_kg_week": 0.15,
        "note": "Reuse beats recycling: it displaces a whole new garment.",
    },
}
LANDFILL_ROUTES = {"Landfill / dump", "Incineration"}  # everything else counts as diverted


# ---------------------------------------------------------------------------
# 6. CAMPUS LIFE  (food, digital, paper, consumption)
# ---------------------------------------------------------------------------
# kg CO2e per meal. Food is typically 20-30% of a student's footprint and is
# almost never in a "carbon calculator" -- which is exactly why it belongs here.

MEALS: dict[str, dict] = {
    "Vegan meal (no dairy)": {"ef": 0.65, "note": "Lowest-carbon full meal."},
    "Vegetarian thali": {"ef": 1.00, "note": "Rice/roti, dal, sabzi, curd."},
    "Paneer / heavy dairy meal": {"ef": 1.80, "note": "Dairy is the hidden cost of "
                                                      "many 'vegetarian' meals."},
    "Egg-based meal": {"ef": 1.45, "note": "Eggs are the cheapest animal protein, "
                                           "carbon-wise."},
    "Fish meal": {"ef": 1.90, "note": "Varies hugely with species and fishing method."},
    "Chicken meal": {"ef": 2.60, "note": "About 2.5x a veg thali."},
    "Mutton / goat meal": {"ef": 5.60, "note": "Ruminant methane makes this the "
                                               "highest-carbon common meal in India."},
}

BEVERAGES: dict[str, dict] = {
    "Tea with milk": {"ef": 0.06, "note": "Milk is most of it."},
    "Black tea / black coffee": {"ef": 0.02, "note": "Skipping the milk cuts it by two-thirds."},
    "Milk coffee / latte": {"ef": 0.32, "note": "Cafe-size milk drink."},
    "Packaged soft drink (500 ml)": {"ef": 0.25, "note": "Bottle, sugar and chilling."},
    "Packaged juice / energy drink": {"ef": 0.30, "note": "Similar to a soft drink."},
}

CONSUMABLES: dict[str, dict] = {
    "Bottled water (1 L)": {"ef": 0.20, "note": "A reusable bottle pays back in ~2 uses."},
    "Disposable cup": {"ef": 0.033, "note": "Paper cups are plastic-lined and rarely recycled."},
    "Paper plate / disposable box": {"ef": 0.06, "note": "Canteen and event catering."},
    "Plastic cutlery / straw set": {"ef": 0.04, "note": "Single-use by design."},
    "A4 page printed": {"ef": 0.0055, "note": "Paper plus toner; double-siding halves it."},
    "Food delivery order": {"ef": 0.75, "note": "Packaging plus a dedicated last-mile trip."},
    "Plastic carry bag": {"ef": 0.03, "note": "Small each, enormous in aggregate."},
}

# Digital emissions = network transport + data centre only. Device charging is
# NOT counted here, because it is already measured in the Appliances module.
# Saying so out loud is the difference between a model and a guess.
DIGITAL: dict[str, dict] = {
    "Video streaming (HD, per hour)": {"ef": 0.036,
        "note": "Network + data centre. Recent studies put this far below the "
                "'1 hour = 1 kg' myth that circulated in 2019."},
    "Video calls (per hour)": {"ef": 0.055, "note": "Two-way upload costs more than streaming."},
    "Social media / short video (per hour)": {"ef": 0.020, "note": "Mostly mobile network."},
    "Online gaming (per hour)": {"ef": 0.030, "note": "Excludes the console's own power draw."},
    "AI assistant use (per hour)": {"ef": 0.010, "note": "Inference is small per query; "
                                                         "training is amortised across users."},
    "Cloud storage & mailbox (per month)": {"ef": 0.40, "note": "Always-on replicated storage."},
}

# Embodied carbon of manufacturing, amortised over the item's service life.
GOODS: dict[str, dict] = {
    "T-shirt": {"ef": 5.5, "life_years": 3, "note": "Cotton is water- and carbon-intensive."},
    "Jeans / trousers": {"ef": 20.0, "life_years": 4, "note": "~2,000 L of water too."},
    "Shoes / sneakers": {"ef": 14.0, "life_years": 2, "note": "Mixed materials, hard to recycle."},
    "Smartphone": {"ef": 60.0, "life_years": 3,
                   "note": "80% of a phone's lifetime carbon is manufacturing, not charging. "
                           "Keeping it one extra year is a real climate action."},
    "Laptop": {"ef": 300.0, "life_years": 5, "note": "Same story as the phone, five times over."},
    "Printed textbook": {"ef": 3.0, "life_years": 4, "note": "Share or buy used."},
    "Backpack / luggage": {"ef": 12.0, "life_years": 5, "note": "Synthetic fabric and zips."},
}

# Food thrown away carries everything spent growing, moving and cooking it.
PLATE_WASTE_EF = 2.5  # kg CO2e per kg of edible food wasted

# Laundry sent to a hostel/dhobi service: energy per kg of clothes.
LAUNDRY_SERVICE_EF_PER_KG = 0.45


# ---------------------------------------------------------------------------
# 7. EQUIVALENCES & BENCHMARKS
# ---------------------------------------------------------------------------

TREE_CO2_PER_YEAR = 21.0        # kg absorbed by one mature tree per year
PETROL_CO2_PER_LITRE = 2.31
PHONE_CHARGE_CO2 = 0.0085       # 12 Wh per full charge at the national grid factor
LPG_CYLINDER_CO2 = 42.3         # 14.2 kg domestic cylinder
FLIGHT_1000KM_CO2 = 135.0       # one-way domestic economy
AC_HOUR_CO2 = 0.78              # one hour of a 1.5-ton 3-star AC
BEEF_BURGER_CO2 = 3.0
OFFSET_COST_PER_TONNE = 800.0   # rupees per tCO2e for a credible Indian offset

# Annual kg CO2e per person, for context. SCOPES DIFFER between these markers
# and this dashboard, so they are signposts, not scorecards -- the UI says so.
BENCHMARKS: dict[str, dict] = {
    "India average": {"value": 2100.0,
                      "note": "Roughly the national per-person figure. Most of the world's "
                              "poorest live well below it."},
    "World average": {"value": 4700.0,
                      "note": "The global mean per-person footprint."},
    "Paris-aligned by 2030": {"value": 2300.0,
                              "note": "Per-person budget consistent with holding warming "
                                      "to 1.5 C this decade."},
    "Net-zero pathway 2050": {"value": 700.0,
                              "note": "What a fair share looks like by mid-century."},
}
PARIS_2030_BUDGET = 2300.0

# Letter grade bands on annual kg CO2e per person.
GRADE_BANDS: list[tuple[float, str, str]] = [
    (1000.0, "A+", "Exceptional - below a net-zero-2050 fair share"),
    (1500.0, "A", "Excellent - well inside the 1.5 C budget"),
    (2300.0, "B", "Good - within the Paris-aligned 2030 budget"),
    (3500.0, "C", "Above the Paris budget - clear room to cut"),
    (5000.0, "D", "High - roughly the world average or above"),
    (float("inf"), "E", "Very high - a few large levers dominate your footprint"),
]

MODULE_ORDER = ["electricity", "commute", "appliances", "water", "waste", "campus"]

MODULE_META: dict[str, dict] = {
    "electricity": {"label": "Electricity", "icon": "⚡",
                    "blurb": "Grid power billed to your home or hostel."},
    "commute": {"label": "Commute & travel", "icon": "🚌",
                "blurb": "Daily travel plus the trips home each year."},
    "appliances": {"label": "Appliances", "icon": "🏠",
                   "blurb": "What each device actually draws, hour by hour."},
    "water": {"label": "Water", "icon": "💧",
              "blurb": "Pumping, heating and treating every litre you use."},
    "waste": {"label": "Waste", "icon": "♻️",
              "blurb": "Where your waste goes decides what it emits."},
    "campus": {"label": "Campus life", "icon": "🎓",
               "blurb": "Food, devices, paper and the things you buy."},
}


def grade_for(annual_kg: float) -> tuple[str, str]:
    """Return (letter, description) for an annual per-person footprint."""
    for ceiling, letter, description in GRADE_BANDS:
        if annual_kg < ceiling:
            return letter, description
    return GRADE_BANDS[-1][1], GRADE_BANDS[-1][2]


def consumer_grid_ef(busbar_ef: float, include_td_losses: bool = True) -> float:
    """Emissions per kWh measured at YOUR meter, not at the power station."""
    return busbar_ef * (1.0 + TD_LOSS_FRACTION) if include_td_losses else busbar_ef
