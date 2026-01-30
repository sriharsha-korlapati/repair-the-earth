from calculators.electricity.electricity_service import electricity_footprint
from rag_explanations.electricity_rag import explain_electricity_impact

# 1️⃣ Step 1: calculation
result = electricity_footprint(356)

print("Calculation Result:")
print(result)

# 2️⃣ Step 2: explanation (RAG)
explanation = explain_electricity_impact(
    bill_amount_rs=result["bill_amount_rs"],
    units_kwh=result["units_consumed_kwh"],
    co2_kg=result["co2_emissions_kg"]
)

print("\nElectricity Carbon Explanation:\n")
print(explanation)