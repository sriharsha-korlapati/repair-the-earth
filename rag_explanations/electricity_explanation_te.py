"""
Telugu Electricity Explanation Module (Structured Output)

Purpose:
- Provide short, impactful Telugu explanations
- Match English RAG output structure exactly
- Simple Andhra-style Telugu
- UI-ready (cards, icons, highlights)
"""

def explain_electricity_telugu(
    bill_amount_rs: float,
    units_kwh: float,
    co2_kg: float
) -> dict:
    """
    Structured Telugu explanation for electricity carbon footprint.
    """

    return {
        "headline": "⚡ విద్యుత్ కనిపించదు, కాలుష్యం మాత్రం నిజం",
        
        "insight": (
            "మీ ఇంట్లో వినియోగించే విద్యుత్ ఎక్కువగా బొగ్గుతో తయారవుతుంది. "
            f"దీని వల్ల నెలకు సుమారు {round(co2_kg, 1)} కిలోల కార్బన్ వాయువు వాతావరణంలోకి వెళ్తోంది."
        ),

        "why_it_matters": (
            "ఈ కార్బన్ వాయువు భూమి వేడెక్కడానికి, వాతావరణ మార్పులకు కారణమవుతుంది."
        ),

        "action_nudge": (
            "🌱 అవసరం లేని లైట్లు, ఫ్యాన్లు ఆపివేయండి — చిన్న అలవాటు, పెద్ద మార్పు."
        )
    }
