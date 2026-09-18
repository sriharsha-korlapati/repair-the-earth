"""
Turn a photo into a carbon number.

THE ARCHITECTURE POINT, which is the same one the rest of this dashboard makes:
the model does NOT estimate carbon. It looks at the image and reports what it
can see -- units on a bill, the streams in a waste pile, what is left on a
plate -- as structured observations. Those observations are then fed through
the same deterministic factors in core/factors.py that every other module
uses.

So a photo of an electricity bill and a hand-typed bill produce the identical
number, and the arithmetic is auditable either way. The model is doing vision,
not physics.
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass, field

from core import factors as F

MODEL = "claude-opus-5"

# What the model is allowed to report back. `strict` makes the API validate the
# arguments against this schema, so the code below can trust the shape.
OBSERVATION_TOOL = {
    "name": "record_observation",
    "description": (
        "Record what is visible in the image as structured observations. Report "
        "only what you can actually see; leave a field out rather than guessing. "
        "Never estimate carbon or CO2 yourself - the application computes that "
        "from your observations using published emission factors."
    ),
    "strict": True,
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "kind": {
                "type": "string",
                "enum": ["electricity_bill", "waste", "food", "appliance", "other"],
                "description": "What the image mainly shows.",
            },
            "confidence": {
                "type": "string",
                "enum": ["high", "medium", "low"],
                "description": "How sure you are of the numbers you report.",
            },
            "summary": {
                "type": "string",
                "description": "One sentence on what is in the image.",
            },
            "electricity": {
                "type": "object",
                "additionalProperties": False,
                "description": "Only for an electricity bill.",
                "properties": {
                    "units_kwh": {"type": ["number", "null"],
                                  "description": "Units consumed, as printed."},
                    "amount_inr": {"type": ["number", "null"],
                                   "description": "Amount payable in rupees."},
                    "period_days": {"type": ["number", "null"],
                                    "description": "Days the bill covers, if shown."},
                },
                "required": ["units_kwh", "amount_inr", "period_days"],
            },
            "waste_items": {
                "type": "array",
                "description": "Only for a waste pile, bin or dump yard.",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "stream": {
                            "type": "string",
                            "enum": list(F.WASTE_STREAMS.keys()),
                        },
                        "estimated_kg": {
                            "type": "number",
                            "description": "Rough mass visible, in kilograms.",
                        },
                        "route": {
                            "type": "string",
                            "description": "Where it appears to be headed, if visible.",
                        },
                    },
                    "required": ["stream", "estimated_kg", "route"],
                },
            },
            "food": {
                "type": "object",
                "additionalProperties": False,
                "description": "Only for a plate, thali or meal.",
                "properties": {
                    "meal_type": {
                        "type": ["string", "null"],
                        "enum": list(F.MEALS.keys()) + [None],
                    },
                    "wasted_grams": {
                        "type": ["number", "null"],
                        "description": "Edible food left uneaten, in grams.",
                    },
                },
                "required": ["meal_type", "wasted_grams"],
            },
            "notes": {
                "type": "string",
                "description": "Anything that limits the reading: blur, cropping, "
                               "an angle that hides part of the pile.",
            },
        },
        "required": ["kind", "confidence", "summary", "notes"],
    },
}

SYSTEM = """You read images for an Indian carbon-footprint dashboard and report \
what is visible as structured observations.

You will be shown things like: an electricity bill, a pile of waste or a dump \
yard, a plate of food after a meal, or an appliance rating label.

Rules:
- Report only what you can see. If the units on a bill are illegible, say so in \
notes and leave the field null rather than inventing a plausible number.
- Estimate masses conservatively and say in notes what you based them on.
- Never compute or state carbon, CO2 or emissions. The application does that \
from published factors. Your job is observation only.
- Always call the record_observation tool."""


@dataclass
class Estimate:
    """What the engine computed from one observation."""

    kind: str
    headline: str
    annual_kg: float = 0.0
    once_kg: float = 0.0
    lines: list[tuple[str, float]] = field(default_factory=list)
    caveats: list[str] = field(default_factory=list)
    observation: dict = field(default_factory=dict)


def available() -> tuple[bool, str]:
    from core.ai import available as ai_available

    return ai_available()


def analyse_image(image_bytes: bytes, media_type: str, question: str | None = None) -> dict:
    """Send one image to the model and get structured observations back."""
    import anthropic

    from core.ai import _api_key

    client = anthropic.Anthropic(api_key=_api_key())
    prompt = (question or "").strip() or "What is in this image?"

    response = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        system=SYSTEM,
        tools=[OBSERVATION_TOOL],
        tool_choice={"type": "tool", "name": "record_observation"},
        thinking={"type": "adaptive"},
        output_config={"effort": "medium"},
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {
                    "type": "base64", "media_type": media_type,
                    "data": base64.standard_b64encode(image_bytes).decode(),
                }},
                {"type": "text", "text": prompt},
            ],
        }],
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "record_observation":
            # Tool inputs come back as parsed objects, but escaping varies by
            # model, so never string-match them -- round-trip through json.
            return json.loads(json.dumps(block.input))
    raise RuntimeError("The model returned no observation.")


# ---------------------------------------------------------------------------
# Observation -> carbon, using the SAME factors as every other module
# ---------------------------------------------------------------------------

def estimate(observation: dict, profile: dict) -> Estimate:
    kind = observation.get("kind", "other")
    summary = observation.get("summary", "")
    est = Estimate(kind=kind, headline=summary, observation=observation)

    if observation.get("notes"):
        est.caveats.append(observation["notes"])
    if observation.get("confidence") in ("medium", "low"):
        est.caveats.append(
            f"The model rated its own reading {observation['confidence']} confidence. "
            "Check the numbers before you use them."
        )

    if kind == "electricity_bill":
        _electricity(observation, profile, est)
    elif kind == "waste":
        _waste(observation, profile, est)
    elif kind == "food":
        _food(observation, profile, est)
    else:
        est.caveats.append(
            "No carbon computed: this image does not carry the numbers any module "
            "needs. Try a bill, a waste pile or a plate of food."
        )
    return est


def _electricity(obs: dict, profile: dict, est: Estimate) -> None:
    from core.calculators import grid_ef

    data = obs.get("electricity") or {}
    ef = grid_ef(profile)
    tariff = max(0.5, float(profile.get("tariff", F.DEFAULT_TARIFF)))

    units = data.get("units_kwh")
    amount = data.get("amount_inr")
    if units is None and amount is None:
        est.caveats.append("Neither the units nor the amount were readable.")
        return

    if units is None:
        units = float(amount) / tariff
        est.caveats.append(
            f"Units were not readable, so they are inferred from ₹{amount:,.0f} "
            f"at ₹{tariff:.2f}/kWh."
        )
    units = float(units)

    # Normalise to a month if the bill states its period.
    days = data.get("period_days")
    monthly_units = units * 30.0 / float(days) if days else units
    if days and abs(float(days) - 30) > 3:
        est.caveats.append(
            f"The bill covers {float(days):.0f} days, so it has been scaled to 30."
        )

    est.once_kg = units * ef
    est.annual_kg = monthly_units * 12.0 * ef
    est.lines = [
        ("Units on this bill (kWh)", units),
        ("Grid factor (kg CO₂ per kWh)", ef),
        ("This bill (kg CO₂e)", est.once_kg),
        ("A year at this rate (kg CO₂e)", est.annual_kg),
    ]
    est.headline = f"{units:,.0f} kWh on this bill → {est.once_kg:,.0f} kg CO₂e"


def _waste(obs: dict, profile: dict, est: Estimate) -> None:
    items = obs.get("waste_items") or []
    if not items:
        est.caveats.append("No identifiable waste streams were reported.")
        return

    total_now = total_best = 0.0
    for item in items:
        stream = item.get("stream")
        spec = F.WASTE_STREAMS.get(stream)
        if not spec:
            continue
        mass = max(0.0, float(item.get("estimated_kg", 0.0)))
        # A photographed pile is, by default, on its way to landfill: that is
        # what a dump yard IS. The comparison against the best route is the
        # actionable half of this estimate.
        landfill_ef = spec["routes"].get("Landfill / dump", max(spec["routes"].values()))
        best_ef = min(spec["routes"].values())
        total_now += mass * landfill_ef
        total_best += mass * best_ef
        est.lines.append((f"{stream} ({mass:g} kg, dumped)", mass * landfill_ef))

    est.once_kg = total_now
    est.lines.append(("If every stream were routed properly", total_best))
    # Best-case routing can be NEGATIVE, because recycling is a credit. So the
    # swing is bigger than the dumped figure, and saying "X of it avoidable"
    # against a smaller dumped number reads as a contradiction. State the swing.
    swing = total_now - total_best
    est.lines.append(("Swing from dumping to best routing", swing))
    total_mass = sum(float(i.get("estimated_kg", 0)) for i in items)
    est.headline = (
        f"{total_mass:,.1f} kg of waste → {total_now:,.1f} kg CO₂e if it is dumped. "
        f"Routing it properly moves that by {swing:,.1f} kg, to {total_best:,.1f} kg."
    )
    est.caveats.append(
        "Mass from a photograph is a rough visual estimate. Weigh a bin for a week "
        "if you need a number to present."
    )


def _food(obs: dict, profile: dict, est: Estimate) -> None:
    data = obs.get("food") or {}
    meal = data.get("meal_type")
    wasted = data.get("wasted_grams")

    if meal and meal in F.MEALS:
        meal_kg = float(F.MEALS[meal]["ef"])
        est.lines.append((f"{meal} (per meal)", meal_kg))
        est.once_kg += meal_kg

    if wasted:
        waste_kg = float(wasted) / 1000.0 * F.PLATE_WASTE_EF
        est.lines.append((f"Food left uneaten ({float(wasted):,.0f} g)", waste_kg))
        est.once_kg += waste_kg
        est.annual_kg = float(wasted) / 1000.0 * 365.0 * F.PLATE_WASTE_EF
        est.lines.append(("Every day for a year", est.annual_kg))

    if not est.lines:
        est.caveats.append("Neither the meal type nor the leftovers were clear.")
        return
    est.headline = f"{est.once_kg:,.2f} kg CO₂e for this plate"
