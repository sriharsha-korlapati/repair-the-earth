"""AI coach page. Works with or without an API key -- see core/ai.py."""

from __future__ import annotations

import streamlit as st

from core import ai, factors as F, insights, recommend as R
from core.engine import Footprint
from ui import components as C, theme as T


def render(fp: Footprint, profile: dict, actions: list[R.Action],
           session_state) -> None:
    C.section(
        "🤖 Ask the coach",
        "The numbers on this dashboard are computed by a deterministic engine, not "
        "guessed by a language model. The coach reads those finished numbers and "
        "helps you interpret and prioritise them.",
    )

    usable, reason = ai.available()

    if not usable:
        C.insight(
            f"The conversational coach is not connected: {reason} "
            "Everything below is the offline rule-based engine, which is what "
            "produces the recommendations and insights throughout this app - "
            "the dashboard is fully functional without a key.", "info",
        )
        st.markdown("##### Your briefing, generated offline")
        for kind, text in insights.build_all(fp, profile, actions):
            C.insight(text, kind)

        st.markdown("##### The offline answer to the question everyone asks first")
        st.markdown("**\"What are the three things I should do first?\"**")
        for index, action in enumerate(R.rank(actions, "impact")[:3], start=1):
            money = ("it pays back ₹%s a year" % f"{-action.annual_net_inr:,.0f}"
                     if action.annual_net_inr < 0
                     else "it costs ₹%s a year net" % f"{action.annual_net_inr:,.0f}")
            C.insight(
                f"<b>{index}. {action.title}</b> — saves "
                f"{action.annual_kg:,.0f} kg CO₂e a year "
                f"({action.annual_kg / fp.annual_kg:.0%} of your footprint) and "
                f"{money}. Effort: {action.effort.lower()}."
            )

        with st.expander("How to switch the conversational coach on"):
            st.markdown(
                """
Add your Anthropic API key and the coach appears on this page.

**Locally** — export it before running the app:
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
streamlit run app.py
```

**On Streamlit Community Cloud** — open *Settings → Secrets* for the app and add:
```toml
ANTHROPIC_API_KEY = "sk-ant-..."
```

The key is read from the environment or from Streamlit secrets and is never
written into the repository. `anthropic` is already in `requirements.txt`.
                """
            )
        return

    # ----- Connected: real conversation, grounded in the computed footprint ---
    context = ai.build_context(fp, profile, actions)

    with st.expander("Exactly what the coach is given (no hidden prompting)"):
        st.code(context, language="markdown")

    st.markdown("##### Try one of these")
    cols = st.columns(len(ai.SUGGESTED_QUESTIONS[:3]))
    asked: str | None = None
    for col, question in zip(cols, ai.SUGGESTED_QUESTIONS[:3]):
        if col.button(question, width="stretch", key=f"sugg_{question[:18]}"):
            asked = question
    cols = st.columns(len(ai.SUGGESTED_QUESTIONS[3:]))
    for col, question in zip(cols, ai.SUGGESTED_QUESTIONS[3:]):
        if col.button(question, width="stretch", key=f"sugg_{question[:18]}"):
            asked = question

    chat = session_state.setdefault("chat", [])
    for turn in chat:
        with st.chat_message(turn["role"]):
            st.markdown(turn["content"])

    typed = st.chat_input("Ask about your own footprint...")
    question = typed or asked

    if question:
        chat.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)
        with st.chat_message("assistant"):
            try:
                answer = st.write_stream(
                    ai.stream_reply(question, context, chat[:-1])
                )
            except Exception as error:  # noqa: BLE001 - surface, never crash the app
                answer = (
                    f"The coach could not answer just now: `{error}`. "
                    "The offline engine is unaffected - the recommendations page "
                    "still has the full costed action list."
                )
                st.markdown(answer)
        chat.append({"role": "assistant", "content": answer})

    if chat and st.button("Clear the conversation"):
        session_state["chat"] = []
        st.rerun()
