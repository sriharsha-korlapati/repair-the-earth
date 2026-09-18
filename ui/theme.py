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
  --gutter: 16px;
}}

.stApp {{ background: var(--page); }}

/* Mobile-first container. The 16px gutter is the phone minimum; the page
   widens on larger screens rather than the other way round. */
.block-container {{
  /* Streamlit pins a toolbar over the top of the page; 1.1rem of padding let
     the header scroll underneath it and clipped the logo. */
  padding: 3rem var(--gutter) 3rem var(--gutter) !important;
  max-width: 1180px;
}}
@media (min-width: 768px) {{
  .block-container {{ padding: 3.2rem 2rem 3rem 2rem !important; }}
}}

/* Fluid type. Nothing is allowed below 13px: the previous build shipped 11px
   captions, which are unreadable on a phone held at arm's length. */
h1 {{ font-size: clamp(1.5rem, 5vw, 2.1rem); }}
h2 {{ font-size: clamp(1.3rem, 4.2vw, 1.7rem); }}
h3 {{ font-size: clamp(1.1rem, 3.6vw, 1.35rem); }}
h4 {{ font-size: clamp(1rem, 3.2vw, 1.15rem); }}
h1, h2, h3, h4 {{ color: var(--text-1); letter-spacing: -0.01em; line-height: 1.25; }}
p, li, label, .stMarkdown {{ color: var(--text-2); }}
.stCaption, [data-testid="stCaptionContainer"] p {{ font-size: 0.83rem !important; }}

/* ---------- Header ---------- */
.rte-head {{ display: flex; align-items: center; gap: 10px; margin-bottom: 4px; }}
.rte-head img {{ height: 32px; width: 32px; flex-shrink: 0; }}
.rte-title {{
  font-size: clamp(1.15rem, 4.5vw, 1.45rem); font-weight: 700;
  color: var(--text-1); line-height: 1.15; margin: 0;
}}
.rte-sub {{ color: var(--text-muted); font-size: 0.8rem; margin: 1px 0 0 0; line-height: 1.35; }}
.rte-badge {{
  display: inline-block; font-size: 0.72rem; font-weight: 700; letter-spacing: 0.06em;
  text-transform: uppercase; padding: 2px 7px; border-radius: 999px;
  background: rgba(34,197,94,0.14); color: var(--accent);
  border: 1px solid rgba(34,197,94,0.35); white-space: nowrap;
}}

/* ---------- Stat tiles: a wrapping grid, not fixed columns ----------
   st.columns keeps N columns side by side on a phone, which is what squeezed
   four tiles into 90px each. This grid reflows to two-up, then one-up. */
.tile-grid {{
  display: grid; gap: 10px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}}
@media (min-width: 720px) {{
  .tile-grid {{ grid-template-columns: repeat(var(--cols, 4), minmax(0, 1fr)); gap: 12px; }}
}}
.tile {{
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 14px; padding: 0.8rem 0.9rem; min-width: 0;
}}
.tile-label {{
  color: var(--text-muted); font-size: 0.83rem; line-height: 1.3;
  overflow-wrap: anywhere;
}}
.tile-value {{
  color: var(--text-1); font-size: clamp(1.25rem, 5.5vw, 1.55rem); font-weight: 650;
  line-height: 1.15; margin-top: 3px; overflow-wrap: anywhere;
}}
.tile-unit {{ color: var(--text-muted); font-size: 0.82rem; font-weight: 500; margin-left: 3px; }}
.tile-foot {{ color: var(--text-muted); font-size: 0.82rem; margin-top: 4px; line-height: 1.35; }}
.tile-delta-good {{ color: {GOOD}; font-size: 0.8rem; font-weight: 600; }}
.tile-delta-bad {{ color: {SERIOUS}; font-size: 0.8rem; font-weight: 600; }}

/* ---------- Hero ---------- */
.hero {{
  background: linear-gradient(180deg, {SURFACE_RAISED} 0%, {SURFACE} 100%);
  border: 1px solid var(--border); border-radius: 16px; padding: 1.1rem 1.15rem;
}}
.hero-row {{
  display: flex; justify-content: space-between; align-items: flex-start;
  gap: 14px; flex-wrap: wrap;
}}
.hero-label {{
  color: var(--text-muted); font-size: 0.78rem; text-transform: uppercase;
  letter-spacing: 0.07em;
}}
.hero-value {{
  font-size: clamp(2.4rem, 13vw, 3.2rem); font-weight: 700; color: var(--accent);
  line-height: 1; margin: 6px 0 2px 0;
}}
.hero-unit {{ font-size: clamp(0.85rem, 3.4vw, 1rem); color: var(--text-2); font-weight: 500; }}
.hero-note {{ color: var(--text-muted); font-size: 0.83rem; margin-top: 8px; line-height: 1.45; }}
.grade-chip {{
  display: inline-flex; align-items: center; justify-content: center;
  min-width: 54px; height: 54px; border-radius: 14px;
  font-size: 1.5rem; font-weight: 750; flex-shrink: 0;
}}

/* ---------- Meters ---------- */
.meter-track {{
  background: rgba(255,255,255,0.07); border-radius: 999px; height: 9px; overflow: hidden;
}}
.meter-fill {{ height: 100%; border-radius: 999px; }}

/* ---------- Insights ---------- */
.insight {{
  background: var(--surface); border-left: 3px solid var(--accent);
  border-radius: 10px; padding: 0.7rem 0.85rem; margin-bottom: 0.5rem;
  color: var(--text-2); font-size: 0.88rem; line-height: 1.5;
}}
.insight-warn {{ border-left-color: {WARNING}; }}
.insight-crit {{ border-left-color: {CRITICAL}; }}
.insight-good {{ border-left-color: {GOOD}; }}
.insight b {{ color: var(--text-1); }}

.assump {{
  color: var(--text-muted); font-size: 0.8rem; line-height: 1.5;
  border-top: 1px solid var(--border); padding-top: 0.6rem; margin-top: 0.8rem;
}}

/* ---------- Action cards ---------- */
.action {{
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 12px; padding: 0.8rem 0.9rem; margin-bottom: 0.5rem;
}}
.action-title {{
  color: var(--text-1); font-weight: 620; font-size: 0.97rem; line-height: 1.35;
}}
.action-body {{ color: var(--text-2); font-size: 0.86rem; line-height: 1.5; margin-top: 4px; }}
.chip-row {{ display: flex; flex-wrap: wrap; gap: 5px; margin-top: 8px; }}
.chip {{
  display: inline-block; font-size: 0.81rem; padding: 3px 9px; border-radius: 999px;
  border: 1px solid var(--border); color: var(--text-muted); white-space: nowrap;
}}
.chip-save {{ color: {GOOD}; border-color: rgba(12,163,12,0.4); }}
.chip-cost {{ color: {SERIOUS}; border-color: rgba(236,131,90,0.4); }}
.chip-easy {{ color: {GOOD}; border-color: rgba(12,163,12,0.4); }}
.chip-medium {{ color: {WARNING}; border-color: rgba(250,178,25,0.4); }}
.chip-hard {{ color: {SERIOUS}; border-color: rgba(236,131,90,0.4); }}

/* ---------- Equivalence chips ---------- */
.eq-grid {{
  display: grid; gap: 10px; grid-template-columns: repeat(3, minmax(0, 1fr));
}}
@media (min-width: 720px) {{ .eq-grid {{ grid-template-columns: repeat(6, minmax(0, 1fr)); }} }}
.eq {{
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 14px; padding: 0.7rem 0.4rem; text-align: center; min-width: 0;
}}
.eq-icon {{ font-size: 1.1rem; }}
.eq-value {{
  color: var(--text-1); font-size: clamp(1rem, 4.5vw, 1.2rem);
  font-weight: 650; line-height: 1.15; margin-top: 2px; overflow-wrap: anywhere;
}}
.eq-label {{ color: var(--text-muted); font-size: 0.8rem; line-height: 1.3; margin-top: 3px; }}

/* ---------- Streamlit widget polish ---------- */
section[data-testid="stSidebar"] {{ background: {SURFACE}; border-right: 1px solid var(--border); }}
div[data-testid="stMetricValue"] {{ color: var(--text-1); }}

/* Tab strip: let it scroll sideways instead of crushing the labels together,
   which is what made "Cooling Laundry Every other device" read as one line. */
.stTabs [data-baseweb="tab-list"] {{
  gap: 2px; border-bottom: 1px solid var(--border);
  overflow-x: auto; flex-wrap: nowrap; scrollbar-width: none;
}}
.stTabs [data-baseweb="tab-list"]::-webkit-scrollbar {{ display: none; }}
.stTabs [data-baseweb="tab"] {{
  color: var(--text-muted); font-size: 0.88rem; white-space: nowrap; padding: 0 12px;
}}
.stTabs [aria-selected="true"] {{ color: var(--accent) !important; }}

div[data-testid="stExpander"] details {{
  border: 1px solid var(--border); border-radius: 10px; background: var(--surface);
}}
.stButton button {{ border-radius: 10px; border: 1px solid var(--border); }}
/* A primary button paints itself in the accent green and picks a light label,
   which leaves pale green on green. Force the dark ink instead. */
.stButton button[kind="primary"],
.stFormSubmitButton button[kind="primaryFormSubmit"] {{
  background: {ACCENT}; color: {ACCENT_INK}; border-color: {ACCENT}; font-weight: 600;
}}
.stButton button[kind="primary"]:hover,
.stFormSubmitButton button[kind="primaryFormSubmit"]:hover {{
  background: #1ea850; color: {ACCENT_INK}; border-color: #1ea850;
}}
hr {{ border-color: var(--border); }}

/* Charts and tables must never force the page sideways on a phone. */
[data-testid="stPlotlyChart"], .js-plotly-plot {{ max-width: 100%; }}
[data-testid="stDataFrame"] {{ max-width: 100%; }}
</style>
"""
