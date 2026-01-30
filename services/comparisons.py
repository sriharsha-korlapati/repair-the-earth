# services/comparisons.py

# Reference values (approximate, conservative, India-relevant)

CO2_PER_TREE_PER_YEAR_KG = 21       # One mature tree absorbs ~21 kg CO2/year
CO2_PER_LITER_PETROL_KG = 2.31      # Petrol combustion emissions
CO2_PER_DOMESTIC_FLIGHT_KG = 90     # Short domestic flight (one-way, economy)


def co2_to_trees(co2_kg_annual):
    return round(co2_kg_annual / CO2_PER_TREE_PER_YEAR_KG, 1)


def co2_to_petrol_liters(co2_kg_monthly):
    return round(co2_kg_monthly / CO2_PER_LITER_PETROL_KG, 1)


def co2_to_flights(co2_kg_annual):
    return round(co2_kg_annual / CO2_PER_DOMESTIC_FLIGHT_KG, 1)