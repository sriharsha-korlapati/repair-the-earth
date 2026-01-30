def electricity_impact_pipeline(monthly_bill_inr: float):
    COST_PER_UNIT = 8          # ₹ per kWh
    CO2_PER_UNIT = 0.82        # kg CO2 per kWh
    TREE_ABSORPTION_YEAR = 21  # kg CO2 / tree / year

    units = monthly_bill_inr / COST_PER_UNIT
    monthly_co2 = units * CO2_PER_UNIT
    yearly_co2 = monthly_co2 * 12

    return {
        "calculation": {
            "monthly_co2_kg": round(monthly_co2, 2),
            "yearly_co2_kg": round(yearly_co2, 2)
        },
        "cost_inr": {
            "monthly": round(monthly_bill_inr, 0),
            "yearly": round(monthly_bill_inr * 12, 0)
        },
        "comparisons": {
            "trees": int(yearly_co2 / TREE_ABSORPTION_YEAR),
            "phone_charges": int(units * 70),   # ~70 phone charges / kWh
            "money_inr": int(monthly_bill_inr * 12)
        },
        "action_nudge": "Switching to LEDs and energy-efficient appliances can cut this by 15–25%."
    }
