service = TransportService()

payload = {
    "mode": "car",
    "distance_km": 10,
    "frequency_per_week": 5,
    "fuel_type": "petrol",
    "carpool": False
}

result = service.calculate_commute_emissions(payload)
print(result)
