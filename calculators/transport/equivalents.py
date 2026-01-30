# calculators/transport/equivalents.py

def co2_to_trees(yearly_co2_kg: float) -> int:
    """
    Converts CO2 to tree equivalent.
    Assumption: 1 tree absorbs ~20 kg CO2 per year (India-average).
    """
    if yearly_co2_kg <= 0:
        return 0

    trees = yearly_co2_kg / 20
    return max(1, round(trees))


def co2_to_phone_charges(yearly_co2_kg: float) -> int:
    """
    Converts CO2 to smartphone charging equivalents.
    Assumption: ~0.005 kg CO2 per full charge.
    """
    if yearly_co2_kg <= 0:
        return 0

    charges = yearly_co2_kg / 0.005
    return round(charges)


def co2_to_short_flights(yearly_co2_kg: float) -> float:
    """
    Very rough awareness-only comparison.
    Assumption: 1 short domestic flight ≈ 90 kg CO2 per passenger.
    """
    if yearly_co2_kg <= 0:
        return 0.0

    return round(yearly_co2_kg / 90, 1)


def generate_equivalents(yearly_co2_kg: float) -> dict:
    """
    Returns equivalents in a UI-friendly structure.
    """

    return {
        "trees_per_year": co2_to_trees(yearly_co2_kg),
        "phone_charges": co2_to_phone_charges(yearly_co2_kg),
        "short_flights": co2_to_short_flights(yearly_co2_kg)
    }
