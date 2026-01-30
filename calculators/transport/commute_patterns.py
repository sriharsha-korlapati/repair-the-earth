# calculators/transport/commute_patterns.py

def resolve_emission_key(mode: str, fuel_type: str | None = None) -> str:
    """
    Maps UI input to emission factor key.
    """

    if mode in ["walk", "cycle", "wfh"]:
        return mode

    if mode == "bike":
        return "bike"

    if mode == "bus":
        return "bus"

    if mode == "metro":
        return "metro"

    if mode == "car":
        if fuel_type == "diesel":
            return "car_diesel"
        if fuel_type == "cng":
            return "car_cng"
        if fuel_type == "ev":
            return "car_ev"
        return "car_petrol"

    raise ValueError(f"Unsupported commute mode: {mode}")


def carpool_modifier(carpool: bool) -> float:
    """
    Simple awareness-first carpool modifier.
    """
    return 0.5 if carpool else 1.0
