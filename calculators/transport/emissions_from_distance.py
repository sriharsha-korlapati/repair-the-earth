# calculators/transport/emissions_from_distance.py

def calculate_weekly_emissions(
    distance_km: float,
    trips_per_week: int,
    emission_factor_kg_per_km: float,
    carpool_factor: float = 1.0
) -> float:
    """
    Calculate weekly CO2 emissions from commuting.

    Formula:
    weekly_co2 = distance * trips * emission_factor * carpool_factor
    """

    if distance_km <= 0 or trips_per_week <= 0:
        return 0.0

    weekly_co2 = (
        distance_km
        * trips_per_week
        * emission_factor_kg_per_km
        * carpool_factor
    )

    return round(weekly_co2, 2)


def weekly_to_yearly(weekly_co2: float) -> float:
    """
    Convert weekly emissions to yearly estimate.
    """
    return round(weekly_co2 * 52, 2)
