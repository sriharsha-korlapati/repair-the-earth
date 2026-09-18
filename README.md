# Repair the Earth — Carbon Intelligence v2

An interactive carbon-footprint dashboard for Indian students, faculty and campuses.
Measure six domains of everyday life, get **one honest total**, and receive a
**costed, ranked list of actions generated from your own numbers**.

Live v1 prototype: <https://rte-carbon.streamlit.app/>

```bash
pip install -r requirements.txt
streamlit run app.py
```

---

## What v2 changes

v1 was three isolated tabs. Each one computed a number and discarded it, so there
was no total footprint, no comparison and no advice.

| | v1 | v2 |
|---|---|---|
| Modules | 3 (electricity, commute, appliances) | **6** — adds water, waste and campus life |
| Total footprint | none — tabs never combined | one aggregated total, with double-counting resolved |
| Emission factors | hard-coded inside each tab | one audited `core/factors.py`, published in the UI |
| Advice | 2 fixed lines of generic text | **engine-generated, costed, ranked** per user |
| Economics | none | ₹ per tonne avoided, payback, marginal abatement curve |
| Planning | none | net-zero pathway, pledges, campus scale-up |
| AI | none | ask by text, voice or photo, over a deterministic engine |
| Tests | none | 31 tests covering arithmetic, accounting and UI |

v1 is preserved at `legacy/app_v1.py` so the two can be demonstrated side by side.

---

## The three new modules

**💧 Water** — the water-energy-carbon nexus. Water has no emissions of its own; it
carries carbon because we pump it, heat it, and treat it again as sewage. So the
biggest saving is rarely the biggest volume — it is whichever litres were *hot*.
Also covers RO reject water, dripping taps, and rainwater-harvesting potential
from local rainfall.

**♻️ Waste** — route matters more than mass. The same kilogram of food waste is
1.90 kg CO₂e in a landfill (anaerobic methane) and 0.18 kg in a compost pit, and
recycled metal is a carbon *credit* because it displaces smelting from ore. The
module also prices the diverted material at scrap rates — the "waste to wealth"
number.

**🎓 Campus life** — food, single-use plastic, printing, screen time and the
embodied carbon of what you own. Absent from v1 and from most carbon calculators,
and usually the **largest single slice** of a student's footprint.

---

## Architecture

```
app.py                 Shell: nav, sidebar profile, routing
core/
  factors.py           EVERY coefficient, with units and notes (single source of truth)
  state.py             Session schema; stores INPUTS only, never results
  calculators.py       Six pure functions: (inputs, profile) -> Result
  engine.py            Aggregation + the double-count resolution
  recommend.py         Action catalogue + marginal abatement costing
  insights.py          Rule-based narrative (deterministic, offline, auditable)
  pathway.py           Net-zero glide path, residual, offsets
  ai.py                Optional Claude conversation (degrades gracefully)
  vision.py            Photo -> structured observation -> the same engine
  report.py            Markdown / CSV export
modules/               One file per page, UI only
ui/
  theme.py             Mobile-first design tokens + CSS
  mic.py               Browser speech-to-text component (no key, no upload)
  components.py        Stat tiles, hero, meters, insight cards
  charts.py            Plotly builders, each with a table-view twin
tests/                 30 tests — python tests/test_engine.py && python tests/test_pages.py
```

**The key design rule:** session state holds *inputs*; every result is derived by a
pure function. That is what lets the dashboard, the recommendation engine, the
pathway and the report all read one consistent picture — no two pages can disagree
about the same number.

---

## The modelling decision that matters most

Your electricity bill and your appliance list describe **the same kilowatt-hours**
from two directions: one metered, one modelled. Adding them together roughly
doubles an energy footprint. It is the most common error in amateur carbon
calculators, and v1 had it.

v2 resolves it explicitly. Exactly **one** source is authoritative; the other
becomes a cross-check, and the app says which. The gap between them is itself
useful:

- **modelled ≫ billed** → listed hours are too generous, or the bill is shared more ways than you thought
- **billed ≫ modelled** → something real is missing from the list: a geyser, a fridge, a pump, a second AC

Hot water is handled the same way, via the heater setting in the Water module.
Other stated boundaries: digital emissions count network and data-centre energy
only (device charging lives in Appliances); goods are amortised over service life;
plan savings are capped at 85% per module because actions on one module overlap.

---

## The recommendation engine

Every action is generated from the user's own inputs — if you do not own an AC, no
AC advice appears; if your AC is already at 26 °C, the setpoint action is not
offered. Each carries:

- CO₂e avoided per year, computed from *your* numbers
- capital cost, annual saving, payback period
- **₹ per tonne avoided** — the honest way to rank climate actions against each other
- effort, co-benefit, and the SDG it serves

Actions with a **negative cost per tonne pay for themselves**. Most people have
several, and the marginal abatement cost curve shows them at a glance.

---

## Ask anything — text, voice or photo

One page, three ways in:

- **Text** — a question in your own words.
- **Voice** — the browser's own speech recogniser transcribes into the text box,
  so you can correct a misheard word before sending. No API key, no audio leaves
  the device. (Firefox has no Web Speech API; the page says so and the text box
  still works.)
- **Photo** — an electricity bill, a waste pile or a plate after a meal.

**The photo path is the important one architecturally.** The model reports only
what it can *see* — units on a bill, streams in a pile, grams left on a plate —
as structured observations. Those go through the same `core/factors.py`
coefficients as every other module. Photograph a bill and type the same bill, and
you get the identical number. The model does vision; the engine does physics.

The dashboard is **fully functional with no API key** — every number,
recommendation and insight is computed locally. Text and photo answers need a
key; set `ANTHROPIC_API_KEY` in the environment or in `.streamlit/secrets.toml`
(*Settings → Secrets* on Streamlit Community Cloud).

---

## Accuracy

Emission factors are India-relevant approximations compiled from public sources:
CEA grid emission data, BEE appliance ratings, and published waste, food and
transport factors. They are accurate enough to **rank actions against each other**,
which is what this tool is for. They are **not** an audited greenhouse-gas
inventory and will not survive a compliance review. Every coefficient is listed in
the app under *Method & export*, so anyone can audit the model and argue with it.

---

## Tests

```bash
python tests/test_engine.py    # 21 tests: arithmetic, accounting rules, guard rails
python tests/test_pages.py     # 10 tests: every page renders, interactions behave
```

The UI tests use Streamlit's own `AppTest` harness — real script, real widget
state, no browser needed.
