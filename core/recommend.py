"""
The recommendation engine.

This is what separates a calculator from a decision tool. Every action below
is generated FROM THE USER'S OWN NUMBERS -- there is no generic tip list. If
you do not own an AC, no AC advice appears; if your AC is already at 26 °C,
the setpoint action is not offered. Each action carries:

  * how much CO2e it avoids per year, computed from your inputs
  * what it costs up front and what it saves per year
  * its marginal abatement cost in rupees per tonne avoided, which is the
    honest way to rank climate actions against each other
  * the effort it takes, so a student is not told to buy a 5-star AC first

Actions with a NEGATIVE cost per tonne pay for themselves. Those are the ones
to do first, and most people have several.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from core import factors as F
from core.calculators import Result, grid_ef

# SDG tags match the tracks on the TerraThon brief, so an action can be traced
# straight to the goal it serves.
SDG = {
    6: "SDG 6 Clean water",
    7: "SDG 7 Clean energy",
    11: "SDG 11 Sustainable cities",
    12: "SDG 12 Responsible consumption",
    13: "SDG 13 Climate action",
}


@dataclass
class Action:
    id: str
    module: str
    title: str
    detail: str
    annual_kg: float
    capex_inr: float = 0.0
    annual_savings_inr: float = 0.0
    lifetime_years: int = 5
    effort: str = "Easy"
    sdgs: list[int] = field(default_factory=lambda: [13])
    co_benefit: str = ""

    # -- derived economics --------------------------------------------------
    @property
    def annualised_capex(self) -> float:
        return self.capex_inr / max(1, self.lifetime_years)

    @property
    def annual_net_inr(self) -> float:
        """Positive = costs you money each year. Negative = pays you back."""
        return self.annualised_capex - self.annual_savings_inr

    @property
    def tonnes(self) -> float:
        return self.annual_kg / 1000.0

    @property
    def cost_per_tonne(self) -> float:
        return self.annual_net_inr / self.tonnes if self.tonnes > 0 else 0.0

    @property
    def payback_years(self) -> float | None:
        if self.capex_inr <= 0 or self.annual_savings_inr <= 0:
            return None
        return self.capex_inr / self.annual_savings_inr

    @property
    def pays_for_itself(self) -> bool:
        return self.annual_net_inr < 0

    def as_dict(self) -> dict:
        return {
            "id": self.id, "title": self.title, "module": self.module,
            "annual_kg": self.annual_kg, "tonnes": self.tonnes,
            "cost_per_tonne": self.cost_per_tonne,
            "annual_net_inr": self.annual_net_inr,
            "capex_inr": self.capex_inr,
            "annual_savings_inr": self.annual_savings_inr,
            "effort": self.effort,
        }


# ---------------------------------------------------------------------------
# Per-module generators
# ---------------------------------------------------------------------------

def _electricity_actions(inputs: dict, profile: dict, res: Result) -> list[Action]:
    out: list[Action] = []
    ef = grid_ef(profile)
    tariff = float(profile.get("tariff", F.DEFAULT_TARIFF))
    divisor = res.metrics.get("household_divisor", 1.0)
    monthly_units = res.metrics.get("monthly_units", 0.0)
    annual_units = monthly_units * 12.0

    if annual_units > 500 and float(inputs.get("solar_kw", 0.0)) <= 0:
        # Size the array to the load, capped at a sensible residential 3 kW.
        size_kw = min(3.0, max(1.0, round(monthly_units / (F.SOLAR_KWH_PER_KW_PER_DAY * 30) * 2) / 2))
        generation = size_kw * F.SOLAR_KWH_PER_KW_PER_DAY * 365.0
        displaced = min(annual_units, generation)
        out.append(Action(
            id="solar_rooftop", module="electricity",
            title=f"Install {size_kw:g} kW of rooftop solar",
            detail=(f"At {F.SOLAR_KWH_PER_KW_PER_DAY:g} kWh per kW per day, "
                    f"{size_kw:g} kW generates about {generation:,.0f} kWh a year and "
                    f"displaces {displaced:,.0f} kWh of grid import."),
            annual_kg=displaced * ef / divisor,
            capex_inr=size_kw * F.SOLAR_CAPEX_PER_KW / divisor,
            annual_savings_inr=displaced * tariff / divisor,
            lifetime_years=F.SOLAR_LIFETIME_YEARS,
            effort="Hard", sdgs=[7, 13],
            co_benefit="Insulates you from tariff rises for 25 years.",
        ))

    if float(inputs.get("green_tariff_share", 0.0)) < 100 and annual_units > 200:
        clean = annual_units * 0.5
        out.append(Action(
            id="green_tariff", module="electricity",
            title="Move half your consumption to a green tariff",
            detail=("Many DISCOMs now sell a renewable-backed tariff at a small premium. "
                    "No hardware, no behaviour change - just a different contract."),
            annual_kg=clean * ef / divisor,
            annual_savings_inr=-(clean * 1.0) / divisor,  # ~Rs 1/kWh premium
            effort="Easy", sdgs=[7, 13],
            co_benefit="Signals demand for renewables to the utility.",
        ))
    return out


def _appliance_actions(inputs: dict, profile: dict, res: Result) -> list[Action]:
    out: list[Action] = []
    ef = grid_ef(profile)
    tariff = float(profile.get("tariff", F.DEFAULT_TARIFF))
    divisor = res.metrics.get("household_divisor", 1.0)

    def money(kwh: float) -> float:
        return kwh * tariff / divisor

    def carbon(kwh: float) -> float:
        return kwh * ef / divisor

    # --- AC setpoint: free, instant, and the one everybody argues about.
    if inputs.get("has_ac"):
        temp = float(inputs.get("ac_temp", 24.0))
        tons = float(inputs.get("ac_tons", 1.5))
        watts = F.AC_WATTS_PER_TON.get(inputs.get("ac_class", "3-star, non-inverter"), 1100.0)
        hours = float(inputs.get("ac_hours", 0.0))
        months = int(inputs.get("ac_months", 12))
        base_kwh = (tons * watts / 1000.0) * hours * 30.0 * months

        def load(t: float) -> float:
            return max(F.AC_MIN_LOAD_FACTOR,
                       1.0 + (F.AC_REFERENCE_TEMP_C - t) * F.AC_PERCENT_PER_DEGREE)

        if temp < 26.0 and base_kwh > 0:
            saved_kwh = base_kwh * (load(temp) - load(26.0))
            out.append(Action(
                id="ac_setpoint", module="appliances",
                title=f"Set the AC to 26 °C instead of {temp:.0f} °C",
                detail=(f"Each degree costs about {F.AC_PERCENT_PER_DEGREE:.0%} more energy. "
                        f"Going from {temp:.0f} °C to 26 °C saves roughly "
                        f"{saved_kwh:,.0f} kWh a year. Costs nothing and takes one press "
                        "of the remote."),
                annual_kg=carbon(saved_kwh), annual_savings_inr=money(saved_kwh),
                effort="Easy", sdgs=[7, 13],
                co_benefit="Less thermal shock walking in and out of the room.",
            ))

        if "non-inverter" in inputs.get("ac_class", "") and base_kwh > 300:
            saved_kwh = base_kwh * (1 - F.AC_WATTS_PER_TON["5-star, inverter"] / watts)
            out.append(Action(
                id="ac_upgrade", module="appliances",
                title="Replace the AC with a 5-star inverter unit",
                detail=(f"A 5-star inverter draws {F.AC_WATTS_PER_TON['5-star, inverter']:,.0f} W "
                        f"per ton against your {watts:,.0f} W, saving about "
                        f"{saved_kwh:,.0f} kWh a year."),
                annual_kg=carbon(saved_kwh), capex_inr=38_000 / divisor,
                annual_savings_inr=money(saved_kwh), lifetime_years=10,
                effort="Hard", sdgs=[7, 12, 13],
                co_benefit="Quieter, and holds temperature far more evenly.",
            ))

    devices = inputs.get("devices", {})
    hours_map = inputs.get("device_hours", {})

    # --- Conventional fan -> BLDC. India's most overlooked retrofit.
    fans = float(devices.get("Ceiling fan (conventional)", 0))
    if fans > 0:
        hours = float(hours_map.get("Ceiling fan (conventional)", 10.0))
        saved_kwh = (70 - 32) / 1000.0 * hours * 365.0 * fans
        out.append(Action(
            id="bldc_fan", module="appliances",
            title=f"Swap {fans:,.0f} conventional fan(s) for BLDC fans",
            detail=(f"A BLDC fan moves the same air on 32 W instead of 70 W. Over "
                    f"{hours:g} hours a day that is {saved_kwh:,.0f} kWh a year."),
            annual_kg=carbon(saved_kwh), capex_inr=3_500 * fans / divisor,
            annual_savings_inr=money(saved_kwh), lifetime_years=10,
            effort="Medium", sdgs=[7, 13],
            co_benefit="Runs on an inverter or solar backup for far longer.",
        ))

    # --- Old lighting -> LED.
    for old_name, watts in (("Incandescent bulb", 60), ("CFL bulb", 15)):
        count = float(devices.get(old_name, 0))
        if count > 0:
            hours = float(hours_map.get(old_name, 6.0))
            saved_kwh = (watts - 10) / 1000.0 * hours * 365.0 * count
            out.append(Action(
                id=f"led_{old_name[:3].lower()}", module="appliances",
                title=f"Replace {count:,.0f} {old_name.lower()}(s) with LEDs",
                detail=(f"A 10 W LED replaces a {watts} W {old_name.lower()} one-for-one. "
                        f"Saves about {saved_kwh:,.0f} kWh a year and the bulbs last "
                        "five times longer."),
                annual_kg=carbon(saved_kwh), capex_inr=120 * count / divisor,
                annual_savings_inr=money(saved_kwh), lifetime_years=5,
                effort="Easy", sdgs=[7, 12, 13],
                co_benefit="Less heat in the room, so the fan works less too.",
            ))

    # --- Standby load: invisible, constant, and trivially fixable.
    standby = float(devices.get("Standby / phantom load", 0))
    if standby > 0:
        hours = float(hours_map.get("Standby / phantom load", 24.0))
        saved_kwh = 15 / 1000.0 * hours * 365.0 * standby * 0.8
        out.append(Action(
            id="standby", module="appliances",
            title="Put chargers and set-top boxes on a switched power strip",
            detail=(f"Phantom load runs {hours:g} hours a day whether you are there or not. "
                    f"Switching it off at the board saves about {saved_kwh:,.0f} kWh a year."),
            annual_kg=carbon(saved_kwh), capex_inr=400 / divisor,
            annual_savings_inr=money(saved_kwh), lifetime_years=5,
            effort="Easy", sdgs=[7, 12],
            co_benefit="Protects electronics from voltage spikes.",
        ))

    if float(inputs.get("dryer_cycles_week", 0.0)) > 0:
        cycles = float(inputs.get("dryer_cycles_week"))
        saved_kwh = F.DRYER_KWH_PER_CYCLE * cycles * 52.0
        out.append(Action(
            id="air_dry", module="appliances",
            title="Air-dry clothes instead of using the dryer",
            detail=(f"{cycles:g} dryer cycles a week is {saved_kwh:,.0f} kWh a year. "
                    "India has the sunshine to make this free."),
            annual_kg=carbon(saved_kwh), annual_savings_inr=money(saved_kwh),
            effort="Easy", sdgs=[7, 12],
            co_benefit="Clothes last noticeably longer.",
        ))

    geysers = float(devices.get("Geyser / water heater (15 L)", 0))
    if geysers > 0:
        hours = float(hours_map.get("Geyser / water heater (15 L)", 0.5))
        current = 2.0 * hours * 365.0 * geysers
        saved_kwh = current * 0.7
        out.append(Action(
            id="solar_geyser", module="appliances",
            title="Fit a solar water heater",
            detail=(f"A solar heater covers roughly 70% of the year in most of India, "
                    f"saving about {saved_kwh:,.0f} kWh - your geyser is the highest-watt "
                    "device you own."),
            annual_kg=carbon(saved_kwh), capex_inr=22_000 / divisor,
            annual_savings_inr=money(saved_kwh), lifetime_years=15,
            effort="Hard", sdgs=[6, 7, 13],
            co_benefit="Hot water even during a power cut.",
        ))
    return out


def _commute_actions(inputs: dict, profile: dict, res: Result) -> list[Action]:
    out: list[Action] = []
    HIGH_CARBON = {"Car (petrol)", "Car (diesel)", "Car (CNG)",
                   "Cab / ride-hail (Ola, Uber)", "Bike taxi (Rapido)",
                   "Auto rickshaw (CNG)", "Scooter (petrol)", "Motorcycle (petrol)"}

    for idx, leg in enumerate(inputs.get("legs", [])):
        mode = leg.get("mode", "")
        if mode not in HIGH_CARBON:
            continue
        spec = F.TRANSPORT_MODES[mode]
        distance = float(leg.get("distance_km", 0.0))
        days = max(0, int(leg.get("days_per_week", 0)))
        trips = 2 if leg.get("round_trip", True) else 1
        occupancy = max(1.0, float(leg.get("occupancy", 1)))
        ef = spec.get("ef", spec.get("kwh_per_km", 0) * grid_ef(profile))
        per_km = ef / (occupancy if spec["basis"] == "vehicle" else 1.0)
        cost_km = spec["cost_per_km"] / (occupancy if spec["basis"] == "vehicle" else 1.0)

        # Swap two days a week onto the metro, the cleanest motorised option.
        swap_days = min(2, days)
        if swap_days > 0 and distance > 0:
            metro = F.TRANSPORT_MODES["Metro / local train"]
            metro_ef = metro["kwh_per_km"] * grid_ef(profile)
            km = distance * trips * swap_days * 52.0
            saved_kg = km * (per_km - metro_ef)
            if saved_kg > 1:
                out.append(Action(
                    id=f"mode_shift_{idx}", module="commute",
                    title=f"Take the metro or bus {swap_days} day(s) a week instead of {mode.lower()}",
                    detail=(f"{km:,.0f} km a year moved off a {per_km * 1000:,.0f} g/km mode "
                            f"onto a {metro_ef * 1000:,.0f} g/km one."),
                    annual_kg=saved_kg,
                    annual_savings_inr=km * (cost_km - metro["cost_per_km"]),
                    effort="Medium", sdgs=[11, 13],
                    co_benefit="Reading or sleeping time instead of traffic time.",
                ))

        # Carpooling is the only change that cuts carbon without changing mode.
        if spec["basis"] == "vehicle" and occupancy < 3 and "Car" in mode:
            km = distance * trips * days * 52.0
            saved_kg = km * ef * (1 / occupancy - 1 / 3.0)
            if saved_kg > 1:
                out.append(Action(
                    id=f"carpool_{idx}", module="commute",
                    title="Carpool three-up on the car commute",
                    detail=(f"The same car trip split three ways cuts your share from "
                            f"{ef / occupancy * 1000:,.0f} to {ef / 3 * 1000:,.0f} g per km."),
                    annual_kg=saved_kg,
                    annual_savings_inr=km * spec["cost_per_km"] * (1 / occupancy - 1 / 3.0),
                    effort="Medium", sdgs=[11, 13],
                    co_benefit="Splits fuel and parking costs three ways too.",
                ))

        # Anything under 3 km is a cycle ride, not a drive.
        if distance <= 3.0 and days > 0:
            km = distance * trips * days * 52.0
            out.append(Action(
                id=f"cycle_{idx}", module="commute",
                title=f"Cycle or walk the {distance:g} km leg instead of taking {mode.lower()}",
                detail=(f"Under 3 km, a bicycle is usually as fast door-to-door once you "
                        f"count parking. {km:,.0f} km a year at zero emissions."),
                annual_kg=km * per_km,
                capex_inr=6_000, annual_savings_inr=km * cost_km, lifetime_years=8,
                effort="Medium", sdgs=[3, 11, 13],
                co_benefit="Roughly 30 minutes of daily exercise, free.",
            ))

    if int(inputs.get("wfh_days", 0)) == 0:
        commute_kg = sum(v for k, v in res.breakdown.items() if "/yr)" not in k)
        busiest = max((int(l.get("days_per_week", 0)) for l in inputs.get("legs", [])),
                      default=0)
        if commute_kg > 10 and busiest >= 5:
            out.append(Action(
                id="remote_day", module="commute",
                title="Make one day a week a no-travel day",
                detail=(f"One fewer commuting day in five cuts daily-travel carbon by 20% - "
                        f"about {commute_kg * 0.2:,.0f} kg CO₂e a year. For students this is "
                        "a library-or-hostel study day; for faculty, a remote day."),
                annual_kg=commute_kg * 0.2,
                annual_savings_inr=res.annual_cost * 0.2,
                effort="Medium", sdgs=[11, 13],
                co_benefit="Gives back a couple of hours of travel time every week.",
            ))

    for idx, trip in enumerate(inputs.get("intercity", [])):
        if trip.get("mode") == "Domestic flight (economy)":
            distance = float(trip.get("distance_km", 0.0))
            count = int(trip.get("trips_per_year", 0))
            km = distance * count * 2.0
            flight_ef = F.INTERCITY_MODES["Domestic flight (economy)"]["ef"]
            train_ef = F.INTERCITY_MODES["Train (AC coach)"]["ef"]
            if km > 0:
                out.append(Action(
                    id=f"train_not_plane_{idx}", module="commute",
                    title="Take an AC train instead of flying home",
                    detail=(f"{km:,.0f} km a year at {flight_ef * 1000:,.0f} g/km becomes "
                            f"{train_ef * 1000:,.0f} g/km. Flying is the single "
                            "highest-carbon thing most people do all year."),
                    annual_kg=km * (flight_ef - train_ef),
                    annual_savings_inr=km * (
                        F.INTERCITY_MODES["Domestic flight (economy)"]["cost_per_km"]
                        - F.INTERCITY_MODES["Train (AC coach)"]["cost_per_km"]),
                    effort="Easy", sdgs=[13],
                    co_benefit="Cheaper, and no airport queues.",
                ))
    return out


def _water_actions(inputs: dict, profile: dict, res: Result) -> list[Action]:
    out: list[Action] = []
    ef = grid_ef(profile)
    tariff = float(profile.get("tariff", F.DEFAULT_TARIFF))
    metrics = res.metrics
    quantities = inputs.get("quantities", {})

    leak = metrics.get("leak_litres_day", 0.0)
    if leak > 0:
        kl = leak * 365.0 / 1000.0
        source_kwh = F.WATER_SOURCE_KWH_PER_KL.get(inputs.get("source", ""), 0.55)
        out.append(Action(
            id="fix_leaks", module="water",
            title="Fix the dripping taps",
            detail=(f"{leak:,.0f} litres a day is {kl:,.1f} kilolitres a year going down "
                    "the drain, along with the energy used to pump and treat it. "
                    "A washer costs ₹10."),
            annual_kg=kl * (source_kwh + F.WASTEWATER_KWH_PER_KL) * ef,
            capex_inr=200,
            annual_savings_inr=kl * F.WATER_TARIFF_PER_KL + kl * source_kwh * tariff,
            lifetime_years=3, effort="Easy", sdgs=[6, 12],
            co_benefit="Stops the sound that keeps everyone awake.",
        ))

    shower_min = float(quantities.get("Shower", 0.0))
    if shower_min >= 5:
        saved_litres = (shower_min - 5) * 9.0
        hot_share = F.WATER_END_USES["Shower"]["hot_share"]
        heat_kwh = saved_litres * hot_share * 365.0 * F.HOT_WATER_KWH_PER_LITRE
        kl = saved_litres * 365.0 / 1000.0
        out.append(Action(
            id="short_shower", module="water",
            title=f"Cut the shower from {shower_min:g} to 5 minutes",
            detail=(f"At 9 litres a minute that saves {saved_litres:,.0f} litres a day, "
                    f"and about {heat_kwh:,.0f} kWh a year of water heating - which is "
                    "where the carbon actually is."),
            annual_kg=heat_kwh * ef + kl * 0.85 * ef,
            annual_savings_inr=heat_kwh * tariff + kl * F.WATER_TARIFF_PER_KL,
            effort="Easy", sdgs=[6, 7, 13],
            co_benefit="A 5-minute limit is easier with a song as a timer.",
        ))

    if shower_min > 0:
        out.append(Action(
            id="aerator", module="water",
            title="Fit a low-flow aerator on the shower and taps",
            detail=("An aerator mixes air into the stream: the same feel at 6 litres a "
                    "minute instead of 9. It is a ₹300 part and nobody notices it."),
            annual_kg=res.annual_kg * 0.12,
            capex_inr=600, annual_savings_inr=res.annual_cost * 0.12,
            lifetime_years=5, effort="Easy", sdgs=[6, 12],
            co_benefit="Works without anyone changing their habits.",
        ))

    ro_reject = metrics.get("ro_reject_litres_day", 0.0)
    if ro_reject > 0:
        out.append(Action(
            id="ro_reuse", module="water",
            title="Collect the RO reject water and use it",
            detail=(f"{ro_reject:,.0f} litres a day is clean enough for mopping, flushing, "
                    f"washing vehicles and watering plants - {ro_reject * 365 / 1000:,.1f} "
                    "kilolitres a year that you currently buy twice."),
            annual_kg=ro_reject * 365.0 / 1000.0 * 0.85 * ef,
            capex_inr=300,
            annual_savings_inr=ro_reject * 365.0 / 1000.0 * F.WATER_TARIFF_PER_KL,
            lifetime_years=5, effort="Easy", sdgs=[6, 12],
            co_benefit="A bucket under the outlet is the whole intervention.",
        ))

    bottled = float(inputs.get("bottled_litres_week", 0.0))
    if bottled > 0:
        out.append(Action(
            id="reusable_bottle", module="water",
            title="Carry a reusable bottle instead of buying water",
            detail=(f"{bottled:g} litres of bottled water a week is "
                    f"{bottled * 52 * F.BOTTLED_WATER_EF_PER_LITRE:,.0f} kg CO₂e a year in "
                    "packaging and transport alone, plus the PET that outlives you."),
            annual_kg=bottled * 52.0 * F.BOTTLED_WATER_EF_PER_LITRE,
            capex_inr=500, annual_savings_inr=bottled * 52.0 * 18.0,
            lifetime_years=4, effort="Easy", sdgs=[6, 12, 14],
            co_benefit="Pays for itself in about a month.",
        ))

    if inputs.get("heater_type") == "Electric geyser" and metrics.get("heating_kwh", 0) > 100:
        heating_kwh = metrics["heating_kwh"]
        out.append(Action(
            id="water_solar", module="water",
            title="Move hot water onto a solar heater",
            detail=(f"You spend about {heating_kwh:,.0f} kWh a year heating water. A solar "
                    "heater covers roughly 70% of that in this climate."),
            annual_kg=heating_kwh * 0.7 * ef,
            capex_inr=22_000, annual_savings_inr=heating_kwh * 0.7 * tariff,
            lifetime_years=15, effort="Hard", sdgs=[6, 7, 13],
            co_benefit="Hot water through power cuts.",
        ))

    harvest = metrics.get("rainwater_litres_year", 0.0)
    if harvest > 1000:
        out.append(Action(
            id="rainwater", module="water",
            title="Harvest rainwater from the roof",
            detail=(f"Your roof could capture {harvest / 1000:,.0f} kilolitres a year at "
                    f"{metrics.get('rainfall_mm', 0):,.0f} mm of rainfall - water that "
                    "needs no pumping and no treatment."),
            annual_kg=harvest / 1000.0 * 0.85 * ef,
            capex_inr=25_000,
            annual_savings_inr=harvest / 1000.0 * F.WATER_TARIFF_PER_KL,
            lifetime_years=20, effort="Hard", sdgs=[6, 11, 13],
            co_benefit="Recharges groundwater and cuts local flooding.",
        ))
    return out


def _waste_actions(inputs: dict, profile: dict, res: Result) -> list[Action]:
    out: list[Action] = []
    streams = inputs.get("streams", {})

    # Route changes are the whole game in waste: same mass, different outcome.
    BEST_ROUTE = {
        "Food & kitchen (wet)": "Composting",
        "Paper & cardboard": "Recycling",
        "Plastic": "Recycling",
        "Glass": "Recycling",
        "Metal (cans, scrap)": "Recycling",
        "E-waste": "Formal recycling",
        "Textiles": "Reuse / donation",
    }
    EFFORT = {
        "Food & kitchen (wet)": "Medium",
        "E-waste": "Easy",
        "Textiles": "Easy",
    }
    HOW = {
        "Food & kitchen (wet)": ("A two-bin compost setup on a balcony or a campus pit "
                                 "handles this. Landfilled food waste emits methane; "
                                 "composted food waste barely emits at all."),
        "Paper & cardboard": "Keep a dry-waste bag and hand it to the kabadiwala.",
        "Plastic": "Rinse, dry and segregate - wet plastic is what gets rejected.",
        "Glass": "Bottles go back through the same scrap channel.",
        "Metal (cans, scrap)": "The highest-value scrap stream per kilogram.",
        "E-waste": ("Use an authorised e-waste collector rather than a general scrap "
                    "dealer - formal recovery is where the avoided mining sits."),
        "Textiles": "Donation displaces a whole new garment, which beats recycling.",
    }

    for name, spec in F.WASTE_STREAMS.items():
        entry = streams.get(name, {})
        mass_week = float(entry.get("kg_week", 0.0))
        current_route = entry.get("route") or list(spec["routes"].keys())[0]
        best = BEST_ROUTE.get(name)
        if mass_week <= 0 or best is None or best not in spec["routes"]:
            continue
        if current_route == best:
            continue
        annual_mass = mass_week * 52.0
        current_ef = float(spec["routes"][current_route])
        best_ef = float(spec["routes"][best])
        saved = annual_mass * (current_ef - best_ef)
        if saved <= 0.5:
            continue
        value = annual_mass * float(spec["value_per_kg"])
        out.append(Action(
            id=f"route_{name[:6].lower().strip()}", module="waste",
            title=f"Send {name.lower()} to {best.lower()} instead of {current_route.lower()}",
            detail=(f"{annual_mass:,.0f} kg a year moving from {current_ef:+.2f} to "
                    f"{best_ef:+.2f} kg CO₂e per kg. {HOW.get(name, '')}"),
            annual_kg=saved,
            annual_savings_inr=value if best != "Composting" else annual_mass * 4.0,
            capex_inr=1_500 if name == "Food & kitchen (wet)" else 0.0,
            lifetime_years=5,
            effort=EFFORT.get(name, "Easy"), sdgs=[11, 12, 13],
            co_benefit=("Compost replaces bought fertiliser for plants."
                        if name == "Food & kitchen (wet)"
                        else "Keeps recoverable material in the economy."),
        ))
    return out


def _campus_actions(inputs: dict, profile: dict, res: Result) -> list[Action]:
    out: list[Action] = []
    meals = inputs.get("meals", {})

    # --- Diet shift: the biggest single lever in most students' footprints.
    high_carbon = {n: float(meals.get(n, 0.0))
                   for n in ("Mutton / goat meal", "Chicken meal", "Fish meal")
                   if float(meals.get(n, 0.0)) > 0}
    if high_carbon:
        swap = min(2.0, sum(high_carbon.values()))
        # Swap the worst meals first.
        remaining = swap
        saved = 0.0
        for name in sorted(high_carbon, key=lambda n: -F.MEALS[n]["ef"]):
            take = min(remaining, high_carbon[name])
            saved += take * 52.0 * (F.MEALS[name]["ef"] - F.MEALS["Vegetarian thali"]["ef"])
            remaining -= take
            if remaining <= 0:
                break
        if saved > 1:
            out.append(Action(
                id="diet_swap", module="campus",
                title=f"Swap {swap:g} meat meals a week for a veg thali",
                detail=(f"Mutton is {F.MEALS['Mutton / goat meal']['ef']:.1f} kg CO₂e a meal "
                        f"against {F.MEALS['Vegetarian thali']['ef']:.1f} for a veg thali. "
                        f"Two swaps a week is {saved:,.0f} kg CO₂e a year - no new "
                        "technology, no spending."),
                annual_kg=saved, annual_savings_inr=swap * 52.0 * 40.0,
                effort="Easy", sdgs=[12, 13],
                co_benefit="Usually cheaper and higher in fibre.",
            ))

    plate_g = float(inputs.get("plate_waste_g_day", 0.0))
    if plate_g > 40:
        saved = (plate_g - 40) / 1000.0 * 365.0 * F.PLATE_WASTE_EF
        out.append(Action(
            id="plate_waste", module="campus",
            title="Take smaller servings and go back for seconds",
            detail=(f"You leave about {plate_g:,.0f} g on the plate a day. Getting that to "
                    f"40 g saves {saved:,.0f} kg CO₂e a year - the carbon of growing, "
                    "moving and cooking food that nobody eats."),
            annual_kg=saved, annual_savings_inr=(plate_g - 40) / 1000.0 * 365.0 * 60.0,
            effort="Easy", sdgs=[2, 12, 13],
            co_benefit="A canteen-wide version of this cuts mess bills directly.",
        ))

    consumables = inputs.get("consumables", {})
    cups = float(consumables.get("Disposable cup", 0.0))
    if cups > 0:
        out.append(Action(
            id="reusable_cup", module="campus",
            title="Keep a steel cup in your bag",
            detail=(f"{cups:g} disposable cups a week is {cups * 52:,.0f} a year. Paper cups "
                    "are plastic-lined, so almost none of them are actually recycled."),
            annual_kg=cups * 52.0 * F.CONSUMABLES["Disposable cup"]["ef"],
            capex_inr=250, annual_savings_inr=cups * 52.0 * 2.0, lifetime_years=5,
            effort="Easy", sdgs=[12],
            co_benefit="Most campus cafes give a small discount for it.",
        ))

    pages = float(consumables.get("A4 page printed", 0.0))
    if pages > 10:
        out.append(Action(
            id="duplex", module="campus",
            title="Print double-sided by default",
            detail=(f"{pages:g} pages a week is {pages * 52:,.0f} sheets a year. Duplex "
                    "printing halves both the paper and the cost."),
            annual_kg=pages * 52.0 * F.CONSUMABLES["A4 page printed"]["ef"] * 0.5,
            annual_savings_inr=pages * 52.0 * 0.5 * 1.0,
            effort="Easy", sdgs=[12, 15],
            co_benefit="Lighter bag, and a one-time printer setting.",
        ))

    orders = float(consumables.get("Food delivery order", 0.0))
    if orders >= 1:
        cut = orders / 2.0
        out.append(Action(
            id="fewer_deliveries", module="campus",
            title=f"Halve food delivery orders (to {orders - cut:g} a week)",
            detail=(f"Each order carries about {F.CONSUMABLES['Food delivery order']['ef']:.2f} "
                    "kg CO₂e in packaging and a dedicated last-mile trip, on top of the food "
                    "itself."),
            annual_kg=cut * 52.0 * F.CONSUMABLES["Food delivery order"]["ef"],
            annual_savings_inr=cut * 52.0 * 250.0,
            effort="Medium", sdgs=[11, 12],
            co_benefit="Saves noticeably more money than carbon.",
        ))

    goods = inputs.get("goods", {})
    for name in ("Smartphone", "Laptop"):
        if float(goods.get(name, 0)) > 0:
            spec = F.GOODS[name]
            life = float(spec["life_years"])
            saved = float(spec["ef"]) / life - float(spec["ef"]) / (life + 1)
            out.append(Action(
                id=f"keep_{name.lower()}", module="campus",
                title=f"Keep your {name.lower()} one year longer",
                detail=(f"About 80% of a {name.lower()}'s lifetime carbon is manufacturing, "
                        f"not use. Stretching {life:.0f} years to {life + 1:.0f} avoids "
                        f"{saved:,.0f} kg CO₂e a year, and a battery replacement costs a "
                        "fraction of a new device."),
                annual_kg=saved * float(goods.get(name, 1)),
                annual_savings_inr=float(spec["ef"]) * 60.0 / life / 10,
                effort="Easy", sdgs=[12, 13],
                co_benefit="The cheapest 'new device' is the one you already own.",
            ))
    return out


GENERATORS = {
    "electricity": _electricity_actions,
    "appliances": _appliance_actions,
    "commute": _commute_actions,
    "water": _water_actions,
    "waste": _waste_actions,
    "campus": _campus_actions,
}


def generate(inputs: dict, profile: dict, results: dict[str, Result],
             skip_modules: set[str] | None = None) -> list[Action]:
    """
    Build the action list for this specific user.

    `skip_modules` excludes whichever electricity view is only a diagnostic,
    so the same saving is never offered twice under two different names.
    """
    skip = skip_modules or set()
    actions: list[Action] = []
    for module, generator in GENERATORS.items():
        if module in skip:
            continue
        actions.extend(generator(inputs.get(module, {}), profile, results[module]))
    return [a for a in actions if a.annual_kg > 0.5]


def rank(actions: list[Action], by: str = "impact") -> list[Action]:
    if by == "cost":
        return sorted(actions, key=lambda a: a.cost_per_tonne)
    if by == "effort":
        order = {"Easy": 0, "Medium": 1, "Hard": 2}
        return sorted(actions, key=lambda a: (order.get(a.effort, 3), -a.annual_kg))
    return sorted(actions, key=lambda a: -a.annual_kg)


def quick_wins(actions: list[Action], limit: int = 4) -> list[Action]:
    """Easy AND pays for itself -- the list to start with tomorrow."""
    wins = [a for a in actions if a.effort == "Easy" and a.annual_net_inr <= 0]
    return sorted(wins, key=lambda a: -a.annual_kg)[:limit]


# ---------------------------------------------------------------------------
# Applying a plan
# ---------------------------------------------------------------------------

# Savings from two actions on the same module overlap (raising the AC setpoint
# and replacing the AC both cut the same kWh). Rather than pretend they are
# additive, cumulative savings are capped per module. The cap is stated in the
# UI so nobody reads the plan as more than it is.
MODULE_SAVINGS_CAP = 0.85


def apply_plan(results: dict[str, Result], actions: list[Action],
               pledged: list[str], counted: dict[str, float]) -> dict[str, float]:
    """Return {module: remaining annual kg} after the pledged actions."""
    chosen = [a for a in actions if a.id in set(pledged)]
    remaining = dict(counted)
    by_module: dict[str, float] = {}
    for action in sorted(chosen, key=lambda a: -a.annual_kg):
        if action.module not in remaining:
            continue
        by_module[action.module] = by_module.get(action.module, 0.0) + action.annual_kg

    for module, saved in by_module.items():
        cap = counted[module] * MODULE_SAVINGS_CAP
        remaining[module] = counted[module] - min(saved, cap)
    return remaining


def plan_totals(actions: list[Action], pledged: list[str]) -> dict[str, float]:
    chosen = [a for a in actions if a.id in set(pledged)]
    return {
        "count": float(len(chosen)),
        "annual_kg": sum(a.annual_kg for a in chosen),
        "capex_inr": sum(a.capex_inr for a in chosen),
        "annual_savings_inr": sum(a.annual_savings_inr for a in chosen),
        "annual_net_inr": sum(a.annual_net_inr for a in chosen),
    }
