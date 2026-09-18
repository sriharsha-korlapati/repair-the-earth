"""
Browser-native speech input.

WHY THIS AND NOT A TRANSCRIPTION API: Claude has no audio input, so a voice
feature needs speech-to-text from somewhere. The obvious packages transcribe
server-side through an undocumented free Google endpoint, which is exactly the
sort of dependency that fails on stage. The browser already ships a speech
recogniser, so this uses that: no API key, no extra service, no audio leaving
the device, and it works on the Android and iOS browsers students actually use.

Firefox has no Web Speech API. The component says so and the text box still
works, which is the whole fallback.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

_DIR = Path(__file__).parent / "mic_component"
_component = None


def _get():
    global _component
    if _component is None:
        _component = components.declare_component("rte_mic", path=str(_DIR))
    return _component


def speech_input(key: str = "mic") -> tuple[str, int] | None:
    """
    Render the mic button.

    Returns (transcript, sequence) once speech ends. The sequence number rises
    with each utterance, so the caller can tell a fresh repeat of the same
    phrase from the component simply re-reporting its last value.
    """
    try:
        payload = _get()(key=key, default=None)
    except Exception:
        # A missing component build must never take the page down with it.
        st.caption("Voice input is unavailable in this browser. Type instead.")
        return None
    if not payload:
        return None
    if isinstance(payload, str):          # older component build
        return payload, 0
    text = str(payload.get("text", "")).strip()
    return (text, int(payload.get("n", 0))) if text else None
