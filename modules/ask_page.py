"""
Ask anything: type it, say it, or photograph it.

Three ways in, one answer out:

  * TEXT  - a question in your own words
  * VOICE - the browser transcribes it into the same box, so you can check it
            before sending
  * IMAGE - a bill, a waste pile or a plate. The model reports what it can SEE
            and the deterministic engine turns that into carbon, using the same
            factors as every other module.

The split matters: the model never estimates emissions. Photograph a bill and
type the same bill, and you get the identical number.
"""

from __future__ import annotations

import streamlit as st

from core import ai, factors as F, recommend as R, vision
from core.engine import Footprint
from ui import charts, components as C, mic, theme as T

ACCEPTED = ["png", "jpg", "jpeg", "webp", "gif"]
MEDIA = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
         "webp": "image/webp", "gif": "image/gif"}

EXAMPLES = [
    "What should I do first?",
    "I have ₹5,000. Where does it cut the most?",
    "What looks bad but barely matters?",
]


def render(fp: Footprint, profile: dict, actions: list[R.Action], session_state) -> None:
    C.section("💬 Ask anything", "Type it, say it, or show it a photo.")

    usable, reason = ai.available()
    tab_ask, tab_photo = st.tabs(["Ask", "Photo"])

    with tab_ask:
        _ask(fp, profile, actions, session_state, usable, reason)
    with tab_photo:
        _photo(fp, profile, session_state, usable, reason)


# ---------------------------------------------------------------------------
# Ask: text + voice
# ---------------------------------------------------------------------------

def _ask(fp, profile, actions, session_state, usable: bool, reason: str) -> None:
    # Voice fills the text box rather than sending straight off, so a
    # misheard word can be fixed before it becomes a question.
    spoken = mic.speech_input(key="ask_mic")
    if spoken and spoken[1] != session_state.get("_last_heard_n"):
        session_state["_last_heard_n"] = spoken[1]
        session_state["ask_draft"] = (
            (session_state.get("ask_draft", "") + " " + spoken[0]).strip()
        )
        st.rerun()

    with st.form("ask_form", clear_on_submit=False):
        draft = st.text_area(
            "Your question", value=session_state.get("ask_draft", ""),
            placeholder="Why is my footprint so high?",
            height=96, label_visibility="collapsed",
        )
        sent = st.form_submit_button("Ask", type="primary", width="stretch")

    picked = None
    cols = st.columns(len(EXAMPLES))
    for col, example in zip(cols, EXAMPLES):
        if col.button(example, key=f"eg_{example[:14]}", width="stretch"):
            picked = example

    question = (draft.strip() if sent else None) or picked
    chat = session_state.setdefault("chat", [])

    if question:
        session_state["ask_draft"] = ""
        chat.append({"role": "user", "content": question})
        if usable:
            context = ai.build_context(fp, profile, actions)
            with st.chat_message("user"):
                st.markdown(question)
            with st.chat_message("assistant"):
                try:
                    answer = st.write_stream(ai.stream_reply(question, context, chat[:-1]))
                except Exception as error:  # noqa: BLE001
                    answer = f"Could not answer just now: `{error}`"
                    st.markdown(answer)
            chat.append({"role": "assistant", "content": answer})
        else:
            chat.append({"role": "assistant", "content": _offline_answer(fp, actions)})

    for turn in chat[-6:]:
        with st.chat_message(turn["role"]):
            st.markdown(turn["content"])

    if chat and st.button("Clear"):
        session_state["chat"] = []
        st.rerun()

    if not usable:
        C.insight(
            f"Conversation is offline: {reason} The ranked, costed answers below "
            "still come from the engine, which needs no key.", "info",
        )


def _offline_answer(fp: Footprint, actions: list[R.Action]) -> str:
    """The rule engine's answer, used whenever there is no API key."""
    if not actions:
        return "Fill in a module or two and I will have something to rank."
    lines = ["Here is what your own numbers say, ranked by impact:", ""]
    for index, action in enumerate(R.rank(actions, "impact")[:3], start=1):
        money = (f"pays back ₹{-action.annual_net_inr:,.0f}/yr"
                 if action.annual_net_inr < 0
                 else f"costs ₹{action.annual_net_inr:,.0f}/yr")
        lines.append(
            f"**{index}. {action.title}** — {action.annual_kg:,.0f} kg CO₂e a year "
            f"({action.annual_kg / fp.annual_kg:.0%} of your footprint), {money}."
        )
    return "\n\n".join(lines)


# ---------------------------------------------------------------------------
# Photo: image -> observation -> engine
# ---------------------------------------------------------------------------

def _photo(fp, profile, session_state, usable: bool, reason: str) -> None:
    st.caption(
        "An electricity bill, a waste pile, or a plate after a meal. "
        "The photo is read for what is in it; the carbon is computed here."
    )

    source = st.radio("Source", ["Upload", "Camera"], horizontal=True,
                      label_visibility="collapsed", key="photo_source")
    image = None
    if source == "Upload":
        image = st.file_uploader("Choose an image", type=ACCEPTED,
                                 label_visibility="collapsed")
    else:
        image = st.camera_input("Take a photo", label_visibility="collapsed")

    note = st.text_input(
        "Anything to add?", placeholder="e.g. this is one day's mess waste",
        key="photo_note",
    )

    if image is None:
        st.caption("Nothing loaded yet.")
        return

    st.image(image, width="stretch")

    if not usable:
        C.insight(
            f"Reading a photo needs the model: {reason} Everything else on this "
            "dashboard works without it.", "warn",
        )
        return

    if not st.button("Read this photo", type="primary", width="stretch"):
        return

    name = getattr(image, "name", "photo.jpg").lower()
    extension = name.rsplit(".", 1)[-1] if "." in name else "jpg"
    media_type = MEDIA.get(extension, "image/jpeg")

    with st.spinner("Reading the photo..."):
        try:
            observation = vision.analyse_image(image.getvalue(), media_type, note)
        except Exception as error:  # noqa: BLE001
            C.insight(f"Could not read that image: <b>{error}</b>", "critical")
            return

    result = vision.estimate(observation, profile)
    _show_estimate(result)


def _show_estimate(result: vision.Estimate) -> None:
    st.markdown("###### What it found")
    C.insight(f"<b>{result.headline}</b>", "good" if result.lines else "warn")

    if result.lines:
        tiles = []
        if result.once_kg:
            tiles.append({"label": "This one", "value": result.once_kg, "unit": "kg CO₂e"})
        if result.annual_kg:
            tiles.append({"label": "Per year at this rate", "value": result.annual_kg,
                          "unit": "kg CO₂e"})
            tiles.append({"label": "Trees to absorb that",
                          "value": result.annual_kg / F.TREE_CO2_PER_YEAR,
                          "unit": "trees"})
        if tiles:
            C.tile_row(tiles)

        st.markdown("###### The arithmetic")
        positive = {k: v for k, v in result.lines if v > 0}
        if len(positive) >= 2:
            fig, table = charts.item_breakdown(
                positive, unit="kg CO₂e", limit=8, color=T.SERIES[0]
            )
            charts.render(fig, table, key="photo_breakdown")
        else:
            for label, value in result.lines:
                st.markdown(f"- {label}: **{value:,.2f}**")

    if result.caveats:
        st.markdown("###### Read this before quoting the number")
        for caveat in result.caveats:
            C.insight(caveat, "warn")

    with st.expander("Exactly what the model reported"):
        st.json(result.observation)
        st.caption(
            "The model reports observations only. Every kilogram above was computed "
            "from these by core/factors.py - the same factors the rest of the app uses."
        )
