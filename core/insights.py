"""
Narrative generation: turn the numbers into sentences a person can act on.

This is deliberately RULE-BASED, not a language model. It runs offline, costs
nothing, is identical every time it runs, and can be audited line by line --
all of which matter when a judge asks "how does it know that?". The optional
Claude coach in core/ai.py sits on top of this for open-ended conversation;
it never replaces it.
"""

from __future__ import annotations

from core import factors as F
from core.engine import Footprint
from core.recommend import Action

# HTML fragments are allowed in these strings (rendered through the insight
# component); <b> is used for the number that carries the point.


def headline(fp: Footprint, profile: dict) -> str:
    grade, _ = fp.grade
    paris = fp.annual_kg / F.PARIS_2030_BUDGET
    if paris <= 1.0:
        return (f"Your footprint is <b>{fp.tonnes:.2f} tonnes CO₂e a year</b>, which is "
                f"<b>{(1 - paris):.0%} inside</b> the per-person budget for holding warming "
                f"to 1.5 °C. Grade {grade}.")
    return (f"Your footprint is <b>{fp.tonnes:.2f} tonnes CO₂e a year</b>, about "
            f"<b>{paris:.1f}x</b> the per-person budget for holding warming to 1.5 °C "
            f"({F.PARIS_2030_BUDGET / 1000:.1f} t). Grade {grade}.")


def driver(fp: Footprint) -> str | None:
    ranked = fp.ranked()
    if not ranked:
        return None
    module, value = ranked[0]
    label = F.MODULE_META[module]["label"].lower()
    items = fp.results[module].top_items(1)
    tail = ""
    if items:
        name, item_value = items[0]
        if value:
            tail = (f" Inside that, <b>{name.lower()}</b> alone is "
                    f"{item_value / value:.0%} of it.")
    return (f"<b>{label.capitalize()}</b> is your biggest source at "
            f"<b>{value:,.0f} kg CO₂e a year</b> - {fp.share_of(module):.0%} of the total."
            + tail)


def concentration(fp: Footprint) -> str | None:
    """How few line items carry most of the footprint. The 80/20 finding."""
    items = sorted(fp.all_items().items(), key=lambda kv: kv[1], reverse=True)
    items = [(k, v) for k, v in items if v > 0]
    if len(items) < 4 or not fp.annual_kg:
        return None
    running = 0.0
    for index, (_, value) in enumerate(items, start=1):
        running += value
        if running >= 0.6 * fp.annual_kg:
            names = ", ".join(k.split(": ")[-1].lower() for k, _ in items[:index])
            return (f"Just <b>{index} of {len(items)} line items</b> make up 60% of your "
                    f"footprint: {names}. That is where all the leverage is - the rest is "
                    "rounding error by comparison.")
    return None


def savings_available(actions: list[Action], fp: Footprint) -> str | None:
    if not actions:
        return None
    total_kg = sum(a.annual_kg for a in actions)
    free = [a for a in actions if a.annual_net_inr <= 0]
    free_kg = sum(a.annual_kg for a in free)
    free_money = -sum(a.annual_net_inr for a in free)
    if fp.annual_kg <= 0:
        return None
    return (f"The {len(actions)} actions this dashboard found for you add up to "
            f"<b>{total_kg:,.0f} kg CO₂e a year</b> - {total_kg / fp.annual_kg:.0%} of your "
            f"footprint. <b>{len(free)} of them pay for themselves</b>, together worth "
            f"{free_kg:,.0f} kg and about <b>₹{free_money:,.0f} a year back in your pocket</b>.")


def cheapest_first(actions: list[Action]) -> str | None:
    paying = [a for a in actions if a.pays_for_itself and a.annual_kg > 0]
    if not paying:
        return None
    # "Start with" has to mean something someone can start with. An easy action
    # that pays for itself beats a bigger one that needs capital and a landlord.
    easy = [a for a in paying if a.effort == "Easy"]
    best = max(easy or paying, key=lambda a: a.annual_kg)
    return (f"Start with <b>{best.title.lower()}</b>: {best.annual_kg:,.0f} kg CO₂e a year "
            f"at a net gain of ₹{-best.annual_net_inr:,.0f}. "
            "A negative cost per tonne means the climate benefit is free - you are "
            "being paid to take it.")


def water_energy_link(fp: Footprint) -> str | None:
    water = fp.results.get("water")
    if not water or not water.annual_kg:
        return None
    heating = water.breakdown.get("Water heating", 0.0)
    if heating <= 0:
        return None
    return (f"Water looks like a water problem until you look at the energy: "
            f"<b>{heating / water.annual_kg:.0%}</b> of your water carbon is just "
            f"<b>heating</b> it. Saving hot water saves electricity, and saving "
            "electricity saves carbon - the same litre counts twice.")


def waste_route_link(fp: Footprint) -> str | None:
    waste = fp.results.get("waste")
    if not waste:
        return None
    avoided = waste.metrics.get("avoided_vs_landfill_kg", 0.0)
    diversion = waste.metrics.get("diversion_rate", 0.0)
    value = waste.metrics.get("recoverable_value_inr", 0.0)
    if waste.metrics.get("kg_per_week", 0) <= 0:
        return None
    if diversion < 0.3:
        return (f"You divert only <b>{diversion:.0%}</b> of your waste from landfill. The mass "
                "does not change when you segregate - the emissions do. Routing the same "
                f"waste properly would cut this module by most of its "
                f"{waste.annual_kg:,.0f} kg.")
    return (f"Your segregation already avoids <b>{avoided:,.0f} kg CO₂e a year</b> versus "
            f"dumping everything, and the diverted material is worth about "
            f"<b>₹{value:,.0f} a year</b>.")


def campus_scale_insight(fp: Footprint, population: int) -> str:
    tonnes = fp.annual_kg * population / 1000.0
    trees = fp.annual_kg * population / F.TREE_CO2_PER_YEAR
    return (f"If all <b>{population:,}</b> people on your campus lived like this, that is "
            f"<b>{tonnes:,.0f} tonnes CO₂e a year</b> - it would take about "
            f"<b>{trees:,.0f} mature trees</b> to absorb it. This is why a campus is the "
            "right unit to intervene on: one policy moves thousands of footprints at once.")


def reconciliation_note(fp: Footprint) -> str | None:
    return fp.warnings[0] if fp.warnings else None


def build_all(fp: Footprint, profile: dict, actions: list[Action]) -> list[tuple[str, str]]:
    """Return [(kind, html)] ready to render, in priority order."""
    grade, _ = fp.grade
    out: list[tuple[str, str]] = [
        ("good" if grade in ("A+", "A", "B") else "warn", headline(fp, profile)),
    ]
    candidates: list[tuple[str, str | None]] = [
        ("info", driver(fp)),
        ("info", concentration(fp)),
        ("good", savings_available(actions, fp)),
        ("good", cheapest_first(actions)),
        ("info", water_energy_link(fp)),
        ("info", waste_route_link(fp)),
    ]
    out.extend((tone, text) for tone, text in candidates if text)
    return out
