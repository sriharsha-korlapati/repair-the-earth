# calculators/transport/nudges.py

def generate_nudges(
    mode: str,
    yearly_co2_kg: float,
    carpool: bool = False
) -> list[str]:
    """
    Awareness nudges.
    Max 2–3 nudges.
    No shaming. No commands.
    """

    nudges = []

    if mode == "car":
        nudges.append(
            "Using public transport once a week could save about 1 tree every year."
        )

        if not carpool:
            nudges.append(
                "Carpooling with one person can nearly halve your commute footprint."
            )

    if mode in ["bike", "car"]:
        nudges.append(
            "One work-from-home day a week can significantly reduce yearly emissions."
        )

    if mode in ["bus", "metro"]:
        nudges.append(
            "You are already choosing a lower-impact commute compared to private vehicles."
        )

    if mode in ["walk", "cycle"]:
        nudges.append(
            "This is one of the greenest ways to commute. Thank you for choosing it."
        )

    # Awareness guardrail
    if yearly_co2_kg > 300:
        nudges.append(
            "Even small changes, repeated weekly, make a meaningful difference over a year."
        )

    # Return max 3 nudges
    return nudges[:3]
