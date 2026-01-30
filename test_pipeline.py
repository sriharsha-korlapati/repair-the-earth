from services.electricity_pipeline import electricity_impact_pipeline

result = electricity_impact_pipeline(356)

print("Calculation:")
print(result["calculation"])

print("\nExplanation:\n")
print(result["explanation"])