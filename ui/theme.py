"""
Design tokens and global CSS.

The palette is not a matter of taste here. The six categorical series colours
below were run through a contrast/colour-vision-deficiency validator against
this app's exact dark surface (#0f172a) and clear every gate: the lightness
band, the chroma floor, adjacent-pair CVD separation (worst pair ΔE 8.4),
the normal-vision floor (worst pair ΔE 19.3) and 3:1 contrast against the
surface. Do not swap a hex here without re-validating the whole set.

The app is pinned to dark mode, so every chart renders on the one surface the
palette was validated against.
"""

from __future__ import annotations

# --- Surfaces & ink --------------------------------------------------------
PAGE = "#0b1220"
SURFACE = "#0f172a"        # the validated chart surface
SURFACE_RAISED = "#16213a"
BORDER = "rgba(255,255,255,0.09)"

TEXT_1 = "#f1f5f9"         # primary ink
TEXT_2 = "#a8b4c6"         # secondary ink
TEXT_MUTED = "#7b8798"     # axis labels, captions
GRID = "#1e293b"           # hairline gridline, one step off surface
AXIS = "#2f3d54"

# --- Brand accent (hero figures and highlights only, never a series) -------
ACCENT = "#22c55e"
ACCENT_INK = "#052e16"

# --- Categorical series, in fixed slot order -------------------------------
SERIES = ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300"]

# Colour follows the entity, never its rank: a module keeps its hue in every
# chart, so filtering or re-sorting never repaints the survivors.
MODULE_COLORS = {
    "electricity": "#c98500",   # yellow
    "commute": "#3987e5",       # blue
    "appliances": "#d55181",    # magenta
    "water": "#199e70",         # aqua
    "waste": "#d95926",         # orange
    "campus": "#008300",        # green
}

# --- Status (reserved: never reused as a series colour) --------------------
GOOD = "#0ca30c"
WARNING = "#fab219"
SERIOUS = "#ec835a"
CRITICAL = "#d03b3b"

# --- Diverging pair for signed values (cost saved vs cost incurred) --------
DIVERGE_NEG = "#3987e5"    # cool: saves money
DIVERGE_POS = "#e66767"    # warm: costs money
DIVERGE_MID = "#2f3d54"

# --- Sequential ramp, one hue, light -> dark -------------------------------
SEQUENTIAL = ["#cde2fb", "#9ec5f4", "#86b6ef", "#6da7ec", "#3987e5",
              "#2a78d6", "#256abf", "#1c5cab", "#184f95"]

DEEMPHASIS = "#475569"     # the "everything else" grey in emphasis charts

FONT = 'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif'


def grade_color(letter: str) -> str:
    return {
        "A+": GOOD, "A": GOOD, "B": ACCENT,
        "C": WARNING, "D": SERIOUS, "E": CRITICAL,
    }.get(letter, TEXT_2)


CSS = f"""
<style>
:root {{
  --page: {PAGE};
  --surface: {SURFACE};
  --surface-raised: {SURFACE_RAISED};
  --border: {BORDER};
  --text-1: {TEXT_1};
  --text-2: {TEXT_2};
  --text-muted: {TEXT_MUTED};
  --accent: {ACCENT};
}}

.stApp {{ background: var(--page); }}
.block-container {{ padding-top: 3.2rem !important; padding-bottom: 3rem !important; max-width: 1180px; }}

h1, h2, h3, h4 {{ color: var(--text-1); letter-spacing: -0.01em; }}
p, li, label, .stMarkdown {{ color: var(--text-2); }}

/* ---------- Header ---------- */
.rte-head {{ display: flex; align-items: center; gap: 12px; margin-bottom: 2px; }}
.rte-head img {{ height: 38px; width: 38px; }}
.rte-title {{ font-size: 1.55rem; font-weight: 700; color: var(--text-1); line-height: 1.1; margin: 0; }}
.rte-sub {{ color: var(--text-muted); font-size: 0.87rem; margin: 2px 0 0 0; }}
.rte-badge {{
  display: inline-block; font-size: 0.68rem; font-weight: 700; letter-spacing: 0.06em;
  text-transform: uppercase; padding: 3px 9px; border-radius: 999px;
  background: rgba(34,197,94,0.14); color: var(--accent);
  border: 1px solid rgba(34,197,94,0.35);
}}

/* ---------- Cards & tiles ---------- */
.rte-card {{
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 14px; padding: 1rem 1.1rem;
}}
.tile {{
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 14px; padding: 0.85rem 0.95rem; height: 100%;
}}
.tile-label {{ color: var(--text-muted); font-size: 0.76rem; line-height: 1.3; }}
.tile-value {{
  color: var(--text-1); font-size: 1.6rem; font-weight: 650;
  line-height: 1.15; margin-top: 3px;
}}
.tile-unit {{ color: var(--text-muted); font-size: 0.78rem; font-weight: 500; margin-left: 3px; }}
.tile-foot {{ color: var(--text-muted); font-size: 0.72rem; margin-top: 4px; }}
.tile-delta-good {{ color: {GOOD}; font-size: 0.75rem; font-weight: 600; }}
.tile-delta-bad {{ color: {SERIOUS}; font-size: 0.75rem; font-weight: 600; }}

/* ---------- Hero figure: exactly one per view ---------- */
.hero {{
  background: linear-gradient(180deg, {SURFACE_RAISED} 0%, {SURFACE} 100%);
  border: 1px solid var(--border); border-radius: 18px; padding: 1.3rem 1.5rem;
}}
.hero-label {{ color: var(--text-muted); font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.07em; }}
.hero-value {{ font-size: 3.2rem; font-weight: 700; color: var(--accent); line-height: 1; margin: 6px 0 2px 0; }}
.hero-unit {{ font-size: 1rem; color: var(--text-2); font-weight: 500; }}
.hero-note {{ color: var(--text-muted); font-size: 0.82rem; margin-top: 8px; }}
.grade-chip {{
  display: inline-flex; align-items: center; justify-content: center;
  min-width: 62px; height: 62px; border-radius: 16px;
  font-size: 1.7rem; font-weight: 750;
}}

/* ---------- Meters ---------- */
.meter-track {{
  background: rgba(255,255,255,0.07); border-radius: 999px; height: 9px; overflow: hidden;
}}
.meter-fill {{ height: 100%; border-radius: 999px; }}

/* ---------- Insight & note blocks ---------- */
.insight {{
  background: var(--surface); border-left: 3px solid var(--accent);
  border-radius: 10px; padding: 0.7rem 0.9rem; margin-bottom: 0.5rem;
  color: var(--text-2); font-size: 0.88rem; line-height: 1.5;
}}
.insight-warn {{ border-left-color: {WARNING}; }}
.insight-crit {{ border-left-color: {CRITICAL}; }}
.insight-good {{ border-left-color: {GOOD}; }}
.insight b {{ color: var(--text-1); }}

.assump {{
  color: var(--text-muted); font-size: 0.78rem; line-height: 1.5;
  border-top: 1px solid var(--border); padding-top: 0.6rem; margin-top: 0.8rem;
}}

/* ---------- Action / recommendation rows ---------- */
.action {{
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 12px; padding: 0.8rem 0.95rem; margin-bottom: 0.55rem;
}}
.action-title {{ color: var(--text-1); font-weight: 620; font-size: 0.95rem; }}
.action-body {{ color: var(--text-2); font-size: 0.84rem; line-height: 1.5; margin-top: 3px; }}
.chip {{
  display: inline-block; font-size: 0.7rem; padding: 2px 8px; border-radius: 999px;
  border: 1px solid var(--border); color: var(--text-muted); margin-right: 5px;
}}
.chip-save {{ color: {GOOD}; border-color: rgba(12,163,12,0.4); }}
.chip-cost {{ color: {SERIOUS}; border-color: rgba(236,131,90,0.4); }}
.chip-easy {{ color: {GOOD}; border-color: rgba(12,163,12,0.4); }}
.chip-medium {{ color: {WARNING}; border-color: rgba(250,178,25,0.4); }}
.chip-hard {{ color: {SERIOUS}; border-color: rgba(236,131,90,0.4); }}

/* ---------- Streamlit widget polish ---------- */
section[data-testid="stSidebar"] {{ background: {SURFACE}; border-right: 1px solid var(--border); }}
div[data-testid="stMetricValue"] {{ color: var(--text-1); }}
.stTabs [data-baseweb="tab-list"] {{ gap: 2px; border-bottom: 1px solid var(--border); }}
.stTabs [data-baseweb="tab"] {{ color: var(--text-muted); font-size: 0.87rem; }}
.stTabs [aria-selected="true"] {{ color: var(--accent) !important; }}
div[data-testid="stExpander"] details {{
  border: 1px solid var(--border); border-radius: 10px; background: var(--surface);
}}
.stButton button {{ border-radius: 10px; border: 1px solid var(--border); }}
hr {{ border-color: var(--border); }}

/* Phone width: no horizontal scroll, 16px gutter */
@media (max-width: 640px) {{
  .block-container {{ padding-left: 16px !important; padding-right: 16px !important; }}
  .hero-value {{ font-size: 2.4rem; }}
  .tile-value {{ font-size: 1.3rem; }}
}}
</style>
"""
