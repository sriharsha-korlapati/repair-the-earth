# calculators/equivalents.py

ELECTRICITY_COST_PER_KWH = 6.0      # ₹
TREE_CO2_KG_PER_YEAR = 21           # kg
PHONE_CHARGE_KWH = 0.005            # kWh


def co2_to_trees(yearly_co2_kg: float) -> int:
    if yearly_co2_kg <= 0:
        return 0
    return max(1, round(yearly_co2_kg / TREE_CO2_KG_PER_YEAR))


def energy_to_phone_charges(kwh: float) -> int:
    if kwh <= 0:
        return 0
    return round(kwh / PHONE_CHARGE_KWH)


def energy_to_money(kwh: float) -> int:
    if kwh <= 0:
        return 0
    return round(kwh * ELECTRICITY_COST_PER_KWH)


def generate_comparisons(yearly_co2_kg: float, yearly_kwh: float) -> dict:
    return {
        "trees": co2_to_trees(yearly_co2_kg),
        "phone_charges": energy_to_phone_charges(yearly_kwh),
        "money_inr": energy_to_money(yearly_kwh)
    }
