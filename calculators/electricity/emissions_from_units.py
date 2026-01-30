import yaml

def calculate_emissions(units, emission_file):
    with open(emission_file, "r") as f:
        factors = yaml.safe_load(f)

    factor = factors["india"]["electricity"]["kg_co2_per_kwh"]
    emissions = units * factor

    return round(emissions, 2)