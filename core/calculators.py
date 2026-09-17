"""
Pure calculators: (inputs, profile) -> Result. No Streamlit, no globals.

Every function here is testable in isolation and returns the same shape, which
is what lets the dashboard, the recommendation engine and the report treat all
six modules identically.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from core import factors as F
from core.state import household_divisor

WEEKS_PER_MONTH = 52.0 / 12.0
DAYS_PER_MONTH = 365.0 / 12.0


@dataclass
class Result:
    """One module's contribution to the footprint."""

    module: str
    annual_kg: float = 0.0            # kg CO2e per year, this person's share
    annual_cost: float = 0.0          # rupees per year
    breakdown: dict[str, float] = field(default_factory=dict)  # annual kg by item
    metrics: dict[str, float] = field(default_factory=dict)    # module-specific numbers
    notes: list[str] = field(default_factory=list)             # plain-language findings

    @property
    def monthly_kg(self) -> float:
        return self.annual_kg / 12.0

    @property
    def monthly_cost(self) -> float:
        return self.annual_cost / 12.0

    def top_items(self, n: int = 5) -> list[tuple[str, float]]:
        ranked = sorted(self.breakdown.items(), key=lambda kv: abs(kv[1]), reverse=True)
        return ranked[:n]


def grid_ef(profile: dict) -> float:
    """Emissions per kWh at the user's meter."""
    return F.consumer_grid_ef(
        float(profile.get("grid_ef", F.DEFAULT_GRID_EF)),
        bool(profile.get("include_td_losses", True)),
    )


# ---------------------------------------------------------------------------
# ELECTRICITY
# ---------------------------------------------------------------------------

def electricity(inputs: dict, profile: dict) -> Result:
    res = Result("electricity")
    ef = grid_ef(profile)
    tariff = max(0.5, float(profile.get("tariff", F.DEFAULT_TARIFF)))

    if inputs.get("entry_mode", "").startswith("Monthly bill"):
        units = float(inputs.get("monthly_bill", 0.0)) / tariff
    else:
        units = float(inputs.get("monthly_units", 0.0))
    units = max(0.0, units)

    # Rooftop solar displaces grid import, capped at what you actually consume.
    solar_kw = max(0.0, float(inputs.get("solar_kw", 0.0)))
    solar_units = solar_kw * F.SOLAR_KWH_PER_KW_PER_DAY * DAYS_PER_MONTH
    solar_used = min(units, solar_units)

    # A green/renewable tariff cleans up whatever is left.
    green_share = min(1.0, max(0.0, float(inputs.get("green_tariff_share", 0.0)) / 100.0))
    grid_units = units - solar_used
    dirty_units = grid_units * (1.0 - green_share)

    divisor = household_divisor(profile, bool(inputs.get("share_with_household", True)))

    monthly_kg = dirty_units * ef / divisor
    res.annual_kg = monthly_kg * 12.0
    res.annual_cost = (grid_units * tariff / divisor) * 12.0

    res.breakdown = {"Grid electricity": res.annual_kg}
    if solar_used > 0:
        res.breakdown["Solar self-consumption (avoided)"] = 0.0
    res.metrics = {
        "monthly_units": units,
        "monthly_units_per_person": units / divisor,
        "solar_units_monthly": solar_used,
        "grid_ef": ef,
        "household_divisor": divisor,
        "avoided_kg_annual": (solar_used * ef / divisor) * 12.0
        + (grid_units * green_share * ef / divisor) * 12.0,
    }

    if units > 0:
        res.notes.append(
            f"You are drawing about {units:,.0f} units a month"
            + (f", or {units / divisor:,.0f} per person across {divisor:,.0f} people."
               if divisor > 1 else ".")
        )
    if solar_used > 0:
        res.notes.append(
            f"Your {solar_kw:g} kW of solar covers {solar_used / units * 100:,.0f}% "
            f"of consumption." if units else "Solar is generating more than you consume."
        )
    if bool(profile.get("include_td_losses", True)):
        res.notes.append(
            f"Grid factor used: {ef:.2f} kg CO₂/kWh, which includes "
            f"{F.TD_LOSS_FRACTION:.0%} transmission and distribution losses."
        )
    return res


# ---------------------------------------------------------------------------
# COMMUTE & TRAVEL
# ---------------------------------------------------------------------------

def _leg_factors(mode: str, profile: dict) -> tuple[float, float, float, str]:
    """(kg per vehicle-or-passenger km, rupees per km, kmph, basis)."""
    spec = F.TRANSPORT_MODES.get(mode)
    if spec is None:
        return 0.0, 0.0, 20.0, "passenger"
    if "kwh_per_km" in spec:
        ef = spec["kwh_per_km"] * grid_ef(profile)
    else:
        ef = float(spec["ef"])
    return ef, float(spec["cost_per_km"]), float(spec["speed_kmph"]), spec["basis"]


def commute(inputs: dict, profile: dict) -> Result:
    res = Result("commute")
    total_kg = 0.0
    total_cost = 0.0
    total_km = 0.0
    total_hours = 0.0

    wfh = max(0, int(inputs.get("wfh_days", 0)))

    for leg in inputs.get("legs", []):
        mode = leg.get("mode", "Walk")
        ef, cost_km, speed, basis = _leg_factors(mode, profile)
        distance = max(0.0, float(leg.get("distance_km", 0.0)))
        days = max(0, int(leg.get("days_per_week", 0))) - wfh
        days = max(0, days)
        trips = 2 if leg.get("round_trip", True) else 1
        occupancy = max(1.0, float(leg.get("occupancy", 1)))

        weekly_km = distance * trips * days
        annual_km = weekly_km * 52.0

        # Private vehicles are shared between everyone inside them; public modes
        # already carry a per-passenger factor.
        share = occupancy if basis == "vehicle" else 1.0
        annual_kg = annual_km * ef / share
        annual_cost = annual_km * cost_km / share

        label = f"{mode} ({distance:g} km)"
        res.breakdown[label] = res.breakdown.get(label, 0.0) + annual_kg
        total_kg += annual_kg
        total_cost += annual_cost
        total_km += annual_km
        total_hours += annual_km / max(1.0, speed)

    for trip in inputs.get("intercity", []):
        mode = trip.get("mode", "Train (sleeper / non-AC)")
        spec = F.INTERCITY_MODES.get(mode, {"ef": 0.0, "cost_per_km": 0.0})
        distance = max(0.0, float(trip.get("distance_km", 0.0)))
        count = max(0, int(trip.get("trips_per_year", 0)))
        annual_km = distance * count * 2.0  # a trip home is a return journey
        annual_kg = annual_km * float(spec["ef"])
        label = f"{mode} ({count}x/yr)"
        res.breakdown[label] = res.breakdown.get(label, 0.0) + annual_kg
        total_kg += annual_kg
        total_cost += annual_km * float(spec["cost_per_km"])
        total_km += annual_km

    res.annual_kg = total_kg
    res.annual_cost = total_cost
    res.metrics = {
        "annual_km": total_km,
        "annual_hours": total_hours,
        "kg_per_km": total_kg / total_km if total_km else 0.0,
    }

    if total_km:
        res.notes.append(
            f"{total_km:,.0f} km a year at an average intensity of "
            f"{total_kg / total_km * 1000:,.0f} g CO₂e per km."
        )
    if total_hours > 1:
        res.notes.append(f"That is about {total_hours:,.0f} hours a year spent travelling.")
    intercity_kg = sum(v for k, v in res.breakdown.items() if "/yr)" in k)
    if intercity_kg > 0 and total_kg > 0 and intercity_kg / total_kg > 0.35:
        res.notes.append(
            f"Long-distance trips are {intercity_kg / total_kg:.0%} of your travel carbon - "
            "more than the daily commute. Mode choice on those trips matters most."
        )
    return res


# ---------------------------------------------------------------------------
# APPLIANCES
# ---------------------------------------------------------------------------

def appliances(inputs: dict, profile: dict) -> Result:
    res = Result("appliances")
    ef = grid_ef(profile)
    tariff = max(0.5, float(profile.get("tariff", F.DEFAULT_TARIFF)))
    divisor = household_divisor(profile, bool(inputs.get("share_with_household", True)))

    kwh_by_item: dict[str, float] = {}

    # --- Air conditioner: the temperature setpoint is the lever people can feel.
    if inputs.get("has_ac", False):
        tons = max(0.5, float(inputs.get("ac_tons", 1.5)))
        watts_per_ton = F.AC_WATTS_PER_TON.get(
            inputs.get("ac_class", "3-star, non-inverter"), 1100.0
        )
        temp = float(inputs.get("ac_temp", F.AC_REFERENCE_TEMP_C))
        load_factor = max(
            F.AC_MIN_LOAD_FACTOR,
            1.0 + (F.AC_REFERENCE_TEMP_C - temp) * F.AC_PERCENT_PER_DEGREE,
        )
        hours = max(0.0, float(inputs.get("ac_hours", 0.0)))
        months = max(0, int(inputs.get("ac_months", 12)))
        annual_kwh = (tons * watts_per_ton / 1000.0) * load_factor * hours * 30.0 * months
        kwh_by_item["Air conditioner"] = annual_kwh

    # --- Washing machine and dryer, priced per cycle.
    wash_kwh = F.WASH_KWH_PER_CYCLE.get(inputs.get("wash_mode", "Cold wash, full load"), 0.45)
    cycles = max(0.0, float(inputs.get("wash_cycles_week", 0.0)))
    if cycles:
        kwh_by_item["Washing machine"] = wash_kwh * cycles * 52.0
    dryer = max(0.0, float(inputs.get("dryer_cycles_week", 0.0)))
    if dryer:
        kwh_by_item["Clothes dryer"] = F.DRYER_KWH_PER_CYCLE * dryer * 52.0

    # --- Everything else, from rated watts x hours x count.
    devices = inputs.get("devices", {})
    device_hours = inputs.get("device_hours", {})
    for name, spec in F.APPLIANCES.items():
        count = max(0.0, float(devices.get(name, 0)))
        if count <= 0:
            continue
        hours = max(0.0, float(device_hours.get(name, spec["hours"])))
        annual_kwh = (spec["watts"] / 1000.0) * hours * count * 365.0
        if annual_kwh > 0:
            kwh_by_item[name] = annual_kwh

    total_kwh = sum(kwh_by_item.values())
    res.breakdown = {k: v * ef / divisor for k, v in kwh_by_item.items()}
    res.annual_kg = sum(res.breakdown.values())
    res.annual_cost = total_kwh * tariff / divisor
    res.metrics = {
        "annual_kwh": total_kwh,
        "monthly_kwh": total_kwh / 12.0,
        "kwh_per_person": total_kwh / divisor,
        "household_divisor": divisor,
    }

    if total_kwh:
        top = max(kwh_by_item.items(), key=lambda kv: kv[1])
        res.notes.append(
            f"{top[0]} alone is {top[1] / total_kwh:.0%} of your appliance electricity "
            f"({top[1]:,.0f} kWh a year)."
        )
        res.notes.append(
            f"Modelled consumption is {total_kwh / 12.0:,.0f} kWh a month. Compare that "
            "with your actual bill in the Electricity module - a big gap means a device "
            "is missing here or the bill is shared differently."
        )
    if inputs.get("has_ac") and float(inputs.get("ac_temp", 24)) < 24:
        res.notes.append(
            f"Your AC is set to {float(inputs['ac_temp']):.0f} °C. Every degree below "
            f"24 °C adds about {F.AC_PERCENT_PER_DEGREE:.0%} to its energy use."
        )
    return res


# ---------------------------------------------------------------------------
# WATER  (new in v2)
# ---------------------------------------------------------------------------

def water(inputs: dict, profile: dict) -> Result:
    res = Result("water")
    ef = grid_ef(profile)
    tariff = max(0.5, float(profile.get("tariff", F.DEFAULT_TARIFF)))

    source = inputs.get("source", "Municipal piped supply")
    supply_kwh_per_kl = F.WATER_SOURCE_KWH_PER_KL.get(source, 0.55)

    # Who pays for the hot water, in carbon terms. "none" means another module
    # already owns it (or it is genuinely free, as with a solar heater), which
    # is how the dashboard avoids charging one geyser to two modules.
    heater = inputs.get("heater_type", "Electric geyser")
    heater_spec = F.WATER_HEATER_TYPES.get(heater, {"ef_source": "grid"})
    heat_source = heater_spec["ef_source"]

    quantities = inputs.get("quantities", {})
    litres_by_use: dict[str, float] = {}
    hot_litres_by_use: dict[str, float] = {}

    for name, spec in F.WATER_END_USES.items():
        qty = max(0.0, float(quantities.get(name, 0.0)))
        if qty <= 0:
            continue
        unit = spec["unit"]
        # Normalise every end use to litres per day.
        if unit in ("bath", "flush", "use", "minute", "day"):
            per_day = qty * spec["litres"]
        elif unit in ("cycle", "wash"):
            per_day = qty * spec["litres"]  # quantity is already entered per day
        else:
            per_day = qty * spec["litres"]
        litres_by_use[name] = per_day
        hot_litres_by_use[name] = per_day * float(spec["hot_share"])

    # RO purifiers reject water to flush the membrane -- invisible on any bill.
    ro_litres = 0.0
    if inputs.get("has_ro", False):
        pure = max(0.0, float(inputs.get("ro_litres_day", 0.0)))
        ro_litres = pure * F.RO_REJECT_RATIO
        litres_by_use["RO purifier reject"] = ro_litres
        hot_litres_by_use["RO purifier reject"] = 0.0

    # A dripping tap is ~15 litres a day and nobody notices it.
    leaks = max(0, int(inputs.get("leaking_taps", 0)))
    if leaks:
        litres_by_use["Leaking taps"] = leaks * 15.0
        hot_litres_by_use["Leaking taps"] = 0.0

    litres_day = sum(litres_by_use.values())
    hot_litres_day = sum(hot_litres_by_use.values())

    # Carbon comes from three places: moving it, heating it, treating it after.
    annual_kl = litres_day * 365.0 / 1000.0
    supply_kwh = annual_kl * supply_kwh_per_kl
    sewage_kwh = annual_kl * F.WASTEWATER_KWH_PER_KL
    heating_kwh_useful = hot_litres_day * 365.0 * F.HOT_WATER_KWH_PER_LITRE

    if heat_source == "grid":
        heating_kg = heating_kwh_useful * ef
        heating_kwh = heating_kwh_useful
    elif heat_source == "lpg":
        heating_kg = heating_kwh_useful * F.LPG_CO2_PER_USEFUL_KWH
        heating_kwh = 0.0
    else:
        heating_kg = 0.0
        heating_kwh = 0.0

    breakdown = {
        "Pumping & supply": supply_kwh * ef,
        "Water heating": heating_kg,
        "Wastewater treatment": sewage_kwh * ef,
    }

    # Bottled water is packaging carbon, not pumping carbon.
    bottled_week = max(0.0, float(inputs.get("bottled_litres_week", 0.0)))
    if bottled_week:
        breakdown["Bottled water"] = bottled_week * 52.0 * F.BOTTLED_WATER_EF_PER_LITRE

    res.breakdown = {k: v for k, v in breakdown.items() if v > 0}
    res.annual_kg = sum(res.breakdown.values())
    res.annual_cost = (
        annual_kl * F.WATER_TARIFF_PER_KL
        + (supply_kwh + heating_kwh) * tariff
        + bottled_week * 52.0 * 20.0
    )
    res.metrics["electric_kwh"] = supply_kwh + heating_kwh + sewage_kwh

    # Rainwater harvesting potential, if the user gave a roof area.
    roof = max(0.0, float(inputs.get("roof_area_m2", 0.0)))
    rainfall = F.RAINFALL_MM.get(profile.get("location", ""), 900.0)
    harvest_litres = roof * rainfall * F.RAINWATER_RUNOFF_COEFF

    res.metrics = {
        "litres_per_day": litres_day,
        "hot_litres_per_day": hot_litres_day,
        "annual_kl": annual_kl,
        "supply_kwh": supply_kwh,
        "heating_kwh": heating_kwh,
        "sewage_kwh": sewage_kwh,
        "ro_reject_litres_day": ro_litres,
        "leak_litres_day": leaks * 15.0,
        "rainwater_litres_year": harvest_litres,
        "rainfall_mm": rainfall,
    }

    if litres_day:
        res.notes.append(
            f"You are using about {litres_day:,.0f} litres a day. "
            f"The UN considers 50-100 litres per person per day sufficient for "
            "all domestic needs."
        )
    if hot_litres_day and heat_source == "grid":
        share = breakdown["Water heating"] / res.annual_kg if res.annual_kg else 0
        res.notes.append(
            f"Heating water is {share:.0%} of your water carbon, from just "
            f"{hot_litres_day:,.0f} hot litres a day. Hot water is where water "
            "becomes an energy problem."
        )
    if hot_litres_day and heat_source == "lpg":
        res.notes.append(
            f"Your gas geyser emits {breakdown['Water heating']:,.0f} kg CO₂e a year. "
            f"An electric geyser on your grid would emit "
            f"{heating_kwh_useful * ef:,.0f} kg - gas wins until the grid cleans up."
        )
    if hot_litres_day and heat_source == "none":
        res.notes.append(
            f"Hot-water energy is not charged to this module "
            f"({F.WATER_HEATER_TYPES.get(heater, {}).get('note', '')})"
        )
    if ro_litres:
        res.notes.append(
            f"Your RO purifier quietly rejects {ro_litres:,.0f} litres a day. "
            "That reject water is clean enough for mopping, flushing and plants."
        )
    if leaks:
        res.notes.append(
            f"{leaks} dripping tap(s) waste about {leaks * 15 * 365:,.0f} litres a year."
        )
    if harvest_litres:
        res.notes.append(
            f"A {roof:,.0f} m² roof at {rainfall:,.0f} mm of rainfall could harvest "
            f"{harvest_litres / 1000:,.0f} kilolitres a year - "
            f"{harvest_litres / (litres_day * 365) * 100:,.0f}% of your annual use."
            if litres_day else ""
        )
    return res


# ---------------------------------------------------------------------------
# WASTE  (new in v2)
# ---------------------------------------------------------------------------

def waste(inputs: dict, profile: dict) -> Result:
    res = Result("waste")
    streams = inputs.get("streams", {})

    total_kg_week = 0.0
    diverted_kg_week = 0.0
    recoverable_value = 0.0
    landfill_counterfactual = 0.0

    for name, spec in F.WASTE_STREAMS.items():
        entry = streams.get(name, {})
        mass_week = max(0.0, float(entry.get("kg_week", 0.0)))
        if mass_week <= 0:
            continue
        routes = spec["routes"]
        route = entry.get("route") or list(routes.keys())[0]
        route_ef = float(routes.get(route, list(routes.values())[0]))

        annual_mass = mass_week * 52.0
        res.breakdown[f"{name} → {route}"] = annual_mass * route_ef

        total_kg_week += mass_week
        if route not in F.LANDFILL_ROUTES:
            diverted_kg_week += mass_week
            recoverable_value += annual_mass * float(spec["value_per_kg"])
        # What this stream would have emitted if it all went to a dump -- the
        # baseline the user is being compared against.
        dump_ef = float(routes.get("Landfill / dump", route_ef))
        landfill_counterfactual += annual_mass * dump_ef

    res.annual_kg = sum(res.breakdown.values())
    # Recovered material is money, not a cost -- so it reduces annual cost.
    res.annual_cost = -recoverable_value

    diversion = diverted_kg_week / total_kg_week if total_kg_week else 0.0
    res.metrics = {
        "kg_per_week": total_kg_week,
        "kg_per_year": total_kg_week * 52.0,
        "diversion_rate": diversion,
        "recoverable_value_inr": recoverable_value,
        "landfill_counterfactual_kg": landfill_counterfactual,
        "avoided_vs_landfill_kg": landfill_counterfactual - res.annual_kg,
    }

    if total_kg_week:
        res.notes.append(
            f"You generate about {total_kg_week:,.1f} kg a week, "
            f"{total_kg_week * 52:,.0f} kg a year, and divert {diversion:.0%} of it "
            "away from landfill."
        )
        avoided = res.metrics["avoided_vs_landfill_kg"]
        if avoided > 1:
            res.notes.append(
                f"Your current routing avoids {avoided:,.0f} kg CO₂e a year compared "
                "with dumping everything - segregation is doing real work."
            )
    if recoverable_value > 0:
        res.notes.append(
            f"The material you divert is worth roughly ₹{recoverable_value:,.0f} a year "
            "at scrap-market rates. That is the 'waste to wealth' number."
        )
    food = streams.get("Food & kitchen (wet)", {})
    if float(food.get("kg_week", 0)) > 0 and food.get("route") == "Landfill / dump":
        res.notes.append(
            "Your food waste is going to landfill, where it emits methane. Composting "
            "the same waste cuts its emissions by about 90% - the single biggest waste "
            "lever available to you."
        )
    return res


# ---------------------------------------------------------------------------
# CAMPUS LIFE  (new in v2)
# ---------------------------------------------------------------------------

def campus(inputs: dict, profile: dict) -> Result:
    res = Result("campus")

    food_kg = 0.0
    for name, spec in F.MEALS.items():
        per_week = max(0.0, float(inputs.get("meals", {}).get(name, 0.0)))
        if per_week:
            annual = per_week * 52.0 * float(spec["ef"])
            res.breakdown[f"Meals: {name}"] = annual
            food_kg += annual

    bev_kg = 0.0
    for name, spec in F.BEVERAGES.items():
        per_week = max(0.0, float(inputs.get("beverages", {}).get(name, 0.0)))
        if per_week:
            annual = per_week * 52.0 * float(spec["ef"])
            res.breakdown[f"Drinks: {name}"] = annual
            bev_kg += annual

    # Plate waste carries the whole embodied cost of food nobody ate.
    plate_g = max(0.0, float(inputs.get("plate_waste_g_day", 0.0)))
    plate_kg = plate_g / 1000.0 * 365.0 * F.PLATE_WASTE_EF
    if plate_kg:
        res.breakdown["Food thrown away"] = plate_kg

    single_use_kg = 0.0
    for name, spec in F.CONSUMABLES.items():
        per_week = max(0.0, float(inputs.get("consumables", {}).get(name, 0.0)))
        if per_week:
            annual = per_week * 52.0 * float(spec["ef"])
            res.breakdown[f"Single-use: {name}"] = annual
            single_use_kg += annual

    digital_kg = 0.0
    for name, spec in F.DIGITAL.items():
        qty = max(0.0, float(inputs.get("digital", {}).get(name, 0.0)))
        if qty:
            # Monthly items are entered per month; hourly items per week.
            annual = qty * (12.0 if "per month" in name else 52.0) * float(spec["ef"])
            res.breakdown[f"Digital: {name}"] = annual
            digital_kg += annual

    goods_kg = 0.0
    for name, spec in F.GOODS.items():
        owned = max(0.0, float(inputs.get("goods", {}).get(name, 0)))
        if owned:
            # Embodied carbon spread over the item's service life.
            annual = owned * float(spec["ef"]) / float(spec["life_years"])
            res.breakdown[f"Things I own: {name}"] = annual
            goods_kg += annual

    laundry = max(0.0, float(inputs.get("laundry_kg_week", 0.0)))
    if laundry:
        res.breakdown["Laundry service"] = laundry * 52.0 * F.LAUNDRY_SERVICE_EF_PER_KG

    res.annual_kg = sum(res.breakdown.values())
    res.metrics = {
        "food_kg": food_kg + bev_kg + plate_kg,
        "single_use_kg": single_use_kg,
        "digital_kg": digital_kg,
        "goods_kg": goods_kg,
        "meals_per_week": sum(float(v) for v in inputs.get("meals", {}).values()),
    }

    if res.annual_kg:
        food_total = food_kg + bev_kg + plate_kg
        res.notes.append(
            f"Food and drink are {food_total / res.annual_kg:.0%} of your campus-life "
            f"footprint ({food_total:,.0f} kg CO₂e a year)."
        )
        if digital_kg:
            res.notes.append(
                f"Your digital life is {digital_kg:,.0f} kg CO₂e a year - real, but far "
                "smaller than the internet myths suggest. Device charging is counted "
                "under Appliances, not here, so nothing is double-counted."
            )
        if goods_kg:
            res.notes.append(
                f"The things you own carry {goods_kg:,.0f} kg CO₂e a year of "
                "manufacturing carbon. Keeping a phone or laptop one year longer is "
                "one of the cheapest cuts on this whole dashboard."
            )
    if plate_kg > 50:
        res.notes.append(
            f"Food left on your plate is {plate_kg:,.0f} kg CO₂e a year - "
            f"{plate_g:,.0f} g a day adds up to {plate_g * 365 / 1000:,.0f} kg of food."
        )
    return res


CALCULATORS = {
    "electricity": electricity,
    "commute": commute,
    "appliances": appliances,
    "water": water,
    "waste": waste,
    "campus": campus,
}


def compute_all(inputs: dict, profile: dict) -> dict[str, Result]:
    """Run every module against the current inputs."""
    return {
        name: fn(inputs.get(name, {}), profile)
        for name, fn in CALCULATORS.items()
    }
