"""
Optional AI coach, powered by Claude.

DESIGN PRINCIPLE: the dashboard is fully functional with no API key. Every
number, every recommendation and every insight is computed locally by
core/recommend.py and core/insights.py. The model is a conversation layer on
top of a deterministic engine -- it is handed the already-computed numbers as
grounding and asked to explain, prioritise and answer follow-ups. It is never
asked to do the arithmetic, because a language model guessing at emission
factors is exactly what this project exists to replace.

Set the key either as an environment variable:      ANTHROPIC_API_KEY
or in .streamlit/secrets.toml:                      ANTHROPIC_API_KEY = "sk-ant-..."
"""

from __future__ import annotations

import os
from typing import Iterator

MODEL = "claude-opus-5"

SYSTEM_PROMPT = """You are the sustainability coach inside "Repair the Earth", an \
Indian carbon-footprint dashboard used by students and faculty.

A deterministic calculation engine has already measured this user's footprint and \
ranked the actions available to them. Their numbers are given to you below. Your job \
is to interpret, prioritise and answer follow-up questions in conversation.

Rules:
- Treat the supplied numbers as authoritative. Never recompute or contradict them, \
and never invent an emission factor, a cost or a saving that is not in the data.
- If the user asks for something the data does not cover, say so plainly and tell \
them which module of the dashboard would capture it.
- Be specific and Indian in context: rupees, kWh, litres, kilograms, local modes of \
transport, hostel and campus realities, DISCOM tariffs, scrap dealers, compost pits.
- Lead with the action that has the largest effect for the least money and effort. \
Actions with a negative cost per tonne pay for themselves - say so.
- Be honest about scale. Do not tell a student their reusable bottle will fix the \
climate; do tell them which of their own actions actually moves the number, and \
where individual action runs out and institutional change has to take over.
- Keep answers short: a few sentences or a tight list. No preamble, no restating \
the question, no emoji.
"""


def available() -> tuple[bool, str]:
    """(usable, reason) -- reason explains what is missing when unusable."""
    try:
        import anthropic  # noqa: F401
    except ImportError:
        return False, "The `anthropic` package is not installed."
    if not _api_key():
        return False, "No ANTHROPIC_API_KEY found in the environment or Streamlit secrets."
    return True, ""


def _api_key() -> str | None:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key
    # st.secrets raises if no secrets file exists at all, so this stays guarded.
    try:
        import streamlit as st

        return st.secrets.get("ANTHROPIC_API_KEY")  # type: ignore[no-any-return]
    except Exception:
        return None


def build_context(fp, profile: dict, actions: list) -> str:
    """Serialise the computed footprint into grounding text for the model."""
    from core import factors as F

    lines: list[str] = []
    lines.append("## Who this is")
    lines.append(f"- Role: {profile.get('persona')}")
    lines.append(f"- Campus: {profile.get('campus')}, {profile.get('location')}")
    lines.append(f"- People sharing the bills: {profile.get('household_size')}")
    lines.append(f"- Grid factor in use: {profile.get('grid_ef')} kg CO2/kWh "
                 f"at {profile.get('tariff')} rupees/kWh")

    grade, grade_note = fp.grade
    lines.append("\n## Their measured footprint")
    lines.append(f"- Total: {fp.annual_kg:,.0f} kg CO2e/year "
                 f"({fp.tonnes:.2f} tonnes), grade {grade} ({grade_note})")
    lines.append(f"- Paris-aligned 2030 budget is {F.PARIS_2030_BUDGET:,.0f} kg/person/year; "
                 f"India average is {F.BENCHMARKS['India average']['value']:,.0f} kg")
    lines.append("- By module:")
    for module, value in fp.ranked():
        share = fp.share_of(module)
        lines.append(f"  - {F.MODULE_META[module]['label']}: {value:,.0f} kg/yr ({share:.0%})")
    if fp.diagnostic:
        excluded = ", ".join(F.MODULE_META[m]["label"] for m in fp.diagnostic)
        lines.append(f"- Excluded from the total to avoid double-counting: {excluded}")

    lines.append("\n## Biggest individual line items")
    items = sorted(fp.all_items().items(), key=lambda kv: kv[1], reverse=True)[:10]
    for name, value in items:
        lines.append(f"- {name}: {value:,.0f} kg/yr")

    lines.append("\n## Actions the engine found, with costed economics")
    for action in sorted(actions, key=lambda a: -a.annual_kg)[:16]:
        payback = (f", payback {action.payback_years:.1f} years"
                   if action.payback_years else "")
        lines.append(
            f"- {action.title}: saves {action.annual_kg:,.0f} kg CO2e/yr; "
            f"net {action.annual_net_inr:+,.0f} rupees/yr; "
            f"{action.cost_per_tonne:+,.0f} rupees per tonne avoided; "
            f"effort {action.effort}{payback}. {action.detail}"
        )

    lines.append("\n## Module notes from the engine")
    for module in fp.counted:
        for note in fp.results[module].notes[:2]:
            lines.append(f"- {F.MODULE_META[module]['label']}: {note}")
    return "\n".join(lines)


def stream_reply(question: str, context: str,
                 history: list[dict] | None = None) -> Iterator[str]:
    """
    Stream Claude's answer as text chunks.

    Streaming is used because it keeps the UI responsive and avoids HTTP
    timeouts on longer answers. Adaptive thinking is on so the model reasons
    about trade-offs between actions before answering; the reasoning itself is
    not surfaced, only the answer.
    """
    import anthropic

    client = anthropic.Anthropic(api_key=_api_key())
    messages: list[dict] = []
    for turn in (history or [])[-8:]:
        messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({"role": "user", "content": question})

    with client.messages.stream(
        model=MODEL,
        max_tokens=8000,
        system=[
            {"type": "text", "text": SYSTEM_PROMPT},
            # The footprint context is the stable, reusable prefix for this
            # session, so it is cached rather than re-billed on every question.
            {"type": "text", "text": f"# The user's data\n\n{context}",
             "cache_control": {"type": "ephemeral"}},
        ],
        messages=messages,
        thinking={"type": "adaptive"},
        output_config={"effort": "medium"},
    ) as stream:
        for chunk in stream.text_stream:
            yield chunk


SUGGESTED_QUESTIONS = [
    "What are the three things I should do first, and why those three?",
    "I have ₹5,000 to spend. Where does it cut the most carbon?",
    "Which of my habits looks bad but barely matters?",
    "Write a one-slide summary of my footprint for a presentation.",
    "What should my college change, as opposed to what I should change?",
]
