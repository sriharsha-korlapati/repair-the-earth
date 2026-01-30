def appliance_impact_pipeline(ac_hours, ac_temp, wash_cycles, wash_load_type):
    # -----------------------------
    # Constants (explainable)
    # -----------------------------
    AC_CO2_PER_HOUR = 0.5          # kg CO2 per hour
    WASH_CO2_PER_CYCLE = 0.6       # kg CO2 per cycle
    TEMP_SAVING_FACTOR = 0.04      # 4% saving per °C above 24
    HALF_LOAD_FACTOR = 0.7

    COST_PER_KWH = 7               # ₹
    TREE_CO2_YEAR = 21.0           # kg
    PHONE_CHARGE_CO2 = 0.005       # kg

    # -----------------------------
    # AC impact
    # -----------------------------
    temp_adjustment = max(0, ac_temp - 24)
    ac_co2 = ac_hours * AC_CO2_PER_HOUR * (1 - temp_adjustment * TEMP_SAVING_FACTOR)

    # -----------------------------
    # Washing machine impact
    # -----------------------------
    wash_factor = HALF_LOAD_FACTOR if wash_load_type == "Half Load" else 1.0
    wash_co2 = wash_cycles * WASH_CO2_PER_CYCLE * wash_factor

    # -----------------------------
    # Monthly & yearly totals
    # -----------------------------
    monthly_co2 = (ac_co2 * 30) + (wash_co2 * 4)
    yearly_co2 = monthly_co2 * 12

    # -----------------------------
    # Approx electricity units & cost
    # -----------------------------
    units = monthly_co2 / 0.82   # reverse CO2 → kWh approximation
    monthly_cost = units * COST_PER_KWH
    yearly_cost = monthly_cost * 12

    # -----------------------------
    # FINAL STRUCTURE (UI EXPECTS THIS)
    # -----------------------------
    return {
        "impact": {
            "monthly_co2_kg": round(monthly_co2, 2),
            "annual_co2_kg": round(yearly_co2, 2)
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
