# calculators/transport/transport_service.py

import yaml
from pathlib import Path
from calculators.transport.impact_bands import get_impact_band
from calculators.transport.nudges import generate_nudges
from calculators.transport.equivalents import generate_equivalents



from calculators.transport.emissions_from_distance import (
    calculate_weekly_emissions,
    weekly_to_yearly
)
from calculators.transport.commute_patterns import (
    resolve_emission_key,
    carpool_modifier
)

KB_PATH = Path("knowledge_base/transport/emission_factors.yaml")


class TransportService:
    def __init__(self):
        self.emission_factors = self._load_emission_factors()

    def _load_emission_factors(self) -> dict:
        with open(KB_PATH, "r") as f:
            return yaml.safe_load(f)

    def calculate_commute_emissions(self, payload: dict) -> dict:
        """
        Entry point for commute emission calculation.
        """

        mode = payload.get("mode")
        distance_km = float(payload.get("distance_km", 0))
        frequency = int(payload.get("frequency_per_week", 0))
        fuel_type = payload.get("fuel_type")
        carpool = bool(payload.get("carpool", False))

        emission_key = resolve_emission_key(mode, fuel_type)

        factor = self.emission_factors.get(emission_key, {}).get(
            "co2_per_km", 0
        )

        modifier = carpool_modifier(carpool)

        weekly_co2 = calculate_weekly_emissions(
            distance_km=distance_km,
            trips_per_week=frequency,
            emission_factor_kg_per_km=factor,
            carpool_factor=modifier
        )

        yearly_co2 = weekly_to_yearly(weekly_co2)

        impact_band = get_impact_band(yearly_co2)
        nudges = generate_nudges(
            mode=mode,
            yearly_co2_kg=yearly_co2,
            carpool=carpool
        )

        equivalents = generate_equivalents(yearly_co2)

        return {
            "weekly_co2_kg": weekly_co2,
            "yearly_co2_kg": yearly_co2,
            "impact_band": impact_band,
            "equivalents": equivalents,
            "nudges": nudges,
            "mode": mode,
            "distance_km": distance_km,
            "frequency_per_week": frequency
        }
