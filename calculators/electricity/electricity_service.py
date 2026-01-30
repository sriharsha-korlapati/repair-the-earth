from pathlib import Path
from calculators.electricity.units_from_bill import calculate_units_from_bill
from calculators.electricity.emissions_from_units import calculate_emissions

BASE_DIR = Path(__file__).resolve().parents[2]

def electricity_footprint(bill_amount):
    units = calculate_units_from_bill(
        bill_amount,
        BASE_DIR / "knowledge_base" / "electricity" / "tariff_rules.yaml"
    )

    emissions = calculate_emissions(
        units,
        BASE_DIR / "knowledge_base" / "electricity" / "emission_factors.yaml"
    )

    return {
        "bill_amount_rs": bill_amount,
        "units_consumed_kwh": units,
        "co2_emissions_kg": emissions
    }