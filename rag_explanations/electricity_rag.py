"""
Electricity RAG Explanation Module (SAFE for Streamlit)

Key design principles:
- NO LLM initialization at import time
- Ollama is loaded lazily only on user action
- Cached responses for performance
- Structured output for UI rendering
"""

from functools import lru_cache
from langchain_core.prompts import ChatPromptTemplate


# ------------------------------------------------------------------
# Prompt Template (static, safe at import)
# ------------------------------------------------------------------

_PROMPT_TEMPLATE = ChatPromptTemplate.from_template(
    """
You are an environmental sustainability expert.

Explain the electricity-related carbon footprint for an Indian household
using simple, eye-opening language.

Context:
- Monthly electricity bill range: ₹{bill_bucket}
- Monthly electricity usage range: {unit_bucket} kWh
- Indian electricity grid is largely coal-based

Rules:
- Do NOT mention exact numbers
- Keep it short and impactful
- Avoid technical jargon
- Focus on why this matters to daily life
"""
)


# ------------------------------------------------------------------
# Bucketing logic (performance + cache efficiency)
# ------------------------------------------------------------------

def bucket_units(units_kwh: float) -> str:
    if units_kwh <= 50:
        return "0–50"
    elif units_kwh <= 100:
        return "51–100"
    elif units_kwh <= 200:
        return "101–200"
    elif units_kwh <= 300:
        return "201–300"
    else:
        return "300+"


def bucket_bill(bill_amount_rs: float) -> str:
    if bill_amount_rs <= 500:
        return "0–500"
    elif bill_amount_rs <= 1000:
        return "501–1000"
    elif bill_amount_rs <= 2000:
        return "1001–2000"
    else:
        return "2000+"


# ------------------------------------------------------------------
# Cached RAG call (LLM invoked ONLY here)
# ------------------------------------------------------------------

@lru_cache(maxsize=128)
def _explain_cached(bill_bucket: str, unit_bucket: str) -> dict:
    """
    Cached explanation generator.
    Same bucket combination = instant response.
    """

    # 🔥 Lazy import — THIS FIXES STREAMLIT FREEZE
    from langchain_ollama import ChatOllama

    llm = ChatOllama(
        model="phi3:mini",
        temperature=0.3
    )

    prompt = _PROMPT_TEMPLATE.format(
        bill_bucket=bill_bucket,
        unit_bucket=unit_bucket
    )

    response = llm.invoke(prompt)

    explanation_text = response.content.strip()

    # Structured response for UI
    return {
        "headline": "⚡ Your electricity has a hidden carbon cost",
        "insight": explanation_text,
        "why_it_matters": (
            "Most electricity in India comes from coal. "
            "Every unit you use releases invisible pollution into the air."
        ),
        "action_nudge": (
            "Saving electricity at home directly cuts carbon emissions "
            "and protects future generations."
        )
    }


# ------------------------------------------------------------------
# Public API (used by electricity_pipeline)
# ------------------------------------------------------------------

def explain_electricity_impact(
    bill_amount_rs: float,
    units_kwh: float,
    co2_kg: float
) -> dict:
    """
    Public function called by the pipeline.
    Returns a structured explanation dict.
    """

    bill_bucket = bucket_bill(bill_amount_rs)
    unit_bucket = bucket_units(units_kwh)

    return _explain_cached(bill_bucket, unit_bucket)
