# calculators/transport/impact_bands.py

def get_impact_band(yearly_co2_kg: float) -> str:
    """
    Awareness-first impact banding.
    Intentionally broad, not precise.
    """

    if yearly_co2_kg <= 50:
        return "low"

    if yearly_co2_kg <= 200:
        return "medium"

    return "high"
