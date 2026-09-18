"""Reusable presentation pieces. No calculation happens in this file."""

from __future__ import annotations

import base64
import html
from pathlib import Path

import streamlit as st

from ui import theme as T


def inject_css() -> None:
    st.markdown(T.CSS, unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def _logo_b64(path: str) -> str:
    try:
        return base64.b64encode(Path(path).read_bytes()).decode()
    except Exception:
        return ""


def header(title: str, subtitle: str, badge: str | None = None,
           logo_path: str = "assets/logo.png") -> None:
    logo = _logo_b64(logo_path)
    img = (f'<img src="data:image/png;base64,{logo}" alt="Repair the Earth logo" />'
           if logo else "")
    badge_html = f'<span class="rte-badge">{html.escape(badge)}</span>' if badge else ""
    st.markdown(
        f"""
        <div class="rte-head">
          {img}
          <div>
            <p class="rte-title">{html.escape(title)}</p>
            <p class="rte-sub">{html.escape(subtitle)} {badge_html}</p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section(title: str, caption: str | None = None) -> None:
    st.markdown(f"#### {title}")
    if caption:
        st.markdown(
            f'<p style="color:{T.TEXT_MUTED};font-size:0.83rem;margin:-8px 0 10px 0;">'
            f"{html.escape(caption)}</p>",
            unsafe_allow_html=True,
        )


def _compact(value: float) -> str:
    """
    Auto-compact a stat-tile value: 21 / 3,766 / 194K / 1.24M.

    Decimals are only shown where they carry information. A count of 21 actions
    must never render as "21.0", and a rupee figure below six digits reads
    better in full than abbreviated.
    """
    a = abs(value)
    whole = float(value).is_integer()
    if a >= 1_000_000:
        return f"{value / 1_000_000:,.2f}M"
    if a >= 100_000:
        return f"{value / 1_000:,.0f}K"
    if a >= 10:
        return f"{value:,.0f}"
    if whole:
        return f"{value:,.0f}"
    if a >= 1:
        return f"{value:,.1f}"
    return f"{value:,.2f}"


def tile(label: str, value: float | str, unit: str = "", foot: str = "",
         delta: str | None = None, delta_good: bool = True) -> None:
    """A stat tile. The number IS the chart -- never a one-bar bar chart."""
    shown = _compact(value) if isinstance(value, (int, float)) else str(value)
    delta_html = ""
    if delta:
        cls = "tile-delta-good" if delta_good else "tile-delta-bad"
        delta_html = f'<div class="{cls}">{html.escape(delta)}</div>'
    st.markdown(
        f"""
        <div class="tile">
          <div class="tile-label">{html.escape(label)}</div>
          <div class="tile-value">{shown}<span class="tile-unit">{html.escape(unit)}</span></div>
          {delta_html}
          {'<div class="tile-foot">' + html.escape(foot) + '</div>' if foot else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _tile_html(label: str, value: float | str, unit: str = "", foot: str = "",
               delta: str | None = None, delta_good: bool = True) -> str:
    shown = _compact(value) if isinstance(value, (int, float)) else str(value)
    delta_html = ""
    if delta:
        cls = "tile-delta-good" if delta_good else "tile-delta-bad"
        delta_html = f'<div class="{cls}">{html.escape(delta)}</div>'
    return (
        f'<div class="tile">'
        f'<div class="tile-label">{html.escape(label)}</div>'
        f'<div class="tile-value">{shown}'
        f'<span class="tile-unit">{html.escape(unit)}</span></div>'
        f'{delta_html}'
        + (f'<div class="tile-foot">{html.escape(foot)}</div>' if foot else "")
        + '</div>'
    )


def tile_row(tiles: list[dict]) -> None:
    """
    A row of stat tiles that reflows: two-up on a phone, N-up on a wide screen.

    st.columns would keep all N side by side at any width, which is what
    squeezed four tiles into 90px each and made the labels collide.
    """
    cells = "".join(_tile_html(**spec) for spec in tiles)
    st.markdown(
        f'<div class="tile-grid" style="--cols:{len(tiles)}">{cells}</div>',
        unsafe_allow_html=True,
    )


def hero(label: str, value: str, unit: str, note: str,
         grade: tuple[str, str] | None = None) -> None:
    """The one number a view leads with. Exactly one per page."""
    grade_block = ""
    if grade:
        letter, desc = grade
        color = T.grade_color(letter)
        grade_block = f"""
          <div style="text-align:right;">
            <div class="grade-chip" style="background:{color}22;color:{color};
                 border:1px solid {color}55;">{html.escape(letter)}</div>
            <div style="color:{T.TEXT_MUTED};font-size:0.82rem;max-width:210px;
                 margin-top:6px;line-height:1.35;">{html.escape(desc)}</div>
          </div>"""
    st.markdown(
        f"""
        <div class="hero">
          <div class="hero-row">
            <div>
              <div class="hero-label">{html.escape(label)}</div>
              <div class="hero-value">{html.escape(value)}
                <span class="hero-unit">{html.escape(unit)}</span></div>
              <div class="hero-note">{html.escape(note)}</div>
            </div>
            {grade_block}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def meter(label: str, fraction: float, color: str | None = None,
          right_text: str = "") -> None:
    """A single ratio against a limit. Never a two-slice pie."""
    pct = max(0.0, min(1.0, fraction))
    fill = color or T.ACCENT
    st.markdown(
        f"""
        <div style="margin-bottom:0.7rem;">
          <div style="display:flex;justify-content:space-between;font-size:0.78rem;
               color:{T.TEXT_MUTED};margin-bottom:4px;">
            <span>{html.escape(label)}</span><span>{html.escape(right_text)}</span>
          </div>
          <div class="meter-track"><div class="meter-fill"
               style="width:{pct * 100:.1f}%;background:{fill};"></div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def insight(text: str, kind: str = "info") -> None:
    """A finding in plain language. `text` may contain <b> tags."""
    cls = {"info": "insight", "warn": "insight insight-warn",
           "critical": "insight insight-crit", "good": "insight insight-good"}[kind]
    st.markdown(f'<div class="{cls}">{text}</div>', unsafe_allow_html=True)


def equivalence_chips(rows: list[tuple[str, str, str]]) -> None:
    """Three-up on a phone, six-up on a wide screen."""
    cells = "".join(
        f'<div class="eq"><div class="eq-icon">{icon}</div>'
        f'<div class="eq-value">{html.escape(value)}</div>'
        f'<div class="eq-label">{html.escape(label)}</div></div>'
        for icon, value, label in rows
    )
    st.markdown(f'<div class="eq-grid">{cells}</div>', unsafe_allow_html=True)


def assumptions(lines: list[str]) -> None:
    if not lines:
        return
    body = "<br/>".join(html.escape(line) for line in lines)
    st.markdown(f'<div class="assump">{body}</div>', unsafe_allow_html=True)


def action_card(title: str, body: str, chips: list[tuple[str, str]]) -> None:
    """chips are (css_class_suffix, text) pairs, e.g. ('save', 'Saves ₹4,200/yr')."""
    chip_html = "".join(
        f'<span class="chip chip-{cls}">{html.escape(text)}</span>' for cls, text in chips
    )
    chip_html = f'<div class="chip-row">{chip_html}</div>'
    st.markdown(
        f"""
        <div class="action">
          <div class="action-title">{html.escape(title)}</div>
          <div class="action-body">{html.escape(body)}</div>
          {chip_html}
        </div>
        """,
        unsafe_allow_html=True,
    )
