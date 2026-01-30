def transport_impact_pipeline(mode: str, distance_km: float, days_per_week: int):
    # -----------------------------
    # Emission factors (kg CO2 / km)
    # Indian averages (incl. grid mix for EVs)
    # -----------------------------
    EMISSION_FACTORS = {
        "Walk / Cycle": 0.0,
        "Bike (Petrol)": 0.103,
        "EV Bike": 0.022,
        "Bus": 0.027,
        "Metro": 0.014,
        "Car (Petrol)": 0.192,
        "Car (Diesel)": 0.171,
        "EV Car": 0.045,
        "Ride-sharing Auto (Ola / Rapido)": 0.068
    }

    # -----------------------------
    # Approx cost per km (₹)
    # Indian real-world averages
    # -----------------------------
    COST_PER_KM = {
        "Walk / Cycle": 0,
        "Bike (Petrol)": 3,
        "EV Bike": 1,
        "Bus": 1.5,
        "Metro": 2,
        "Car (Petrol)": 10,
        "Car (Diesel)": 9,
        "EV Car": 2,
        "Ride-sharing Auto (Ola / Rapido)": 7
    }

    TREE_CO2_YEAR = 21.0       # kg
    PHONE_CHARGE_CO2 = 0.005   # kg

    mode = mode.strip()

    if mode not in EMISSION_FACTORS:
        raise ValueError(f"Unknown transport mode: {mode}")

    factor = EMISSION_FACTORS[mode]
    cost_per_km = COST_PER_KM[mode]
    
    # Monthly assumptions
    trips_per_day = 2
    days_per_month = days_per_week * 4

    monthly_km = distance_km * trips_per_day * days_per_month
    monthly_co2 = monthly_km * factor
    yearly_co2 = monthly_co2 * 12

    monthly_cost = monthly_km * cost_per_km
    yearly_cost = monthly_cost * 12

    return {
        "co2": {
            "monthly_kg": round(monthly_co2, 2),
            "yearly_kg": round(yearly_co2, 2)
        },
        "comparisons": {
            "trees": round(yearly_co2 / TREE_CO2_YEAR, 1),
            "phone_charges": round(monthly_co2 / PHONE_CHARGE_CO2, 0),
            "money_inr": round(yearly_cost, 0)
        },
        "cost_inr": {
            "monthly": round(monthly_cost, 0),
            "yearly": round(yearly_cost, 0)
        }
    }
