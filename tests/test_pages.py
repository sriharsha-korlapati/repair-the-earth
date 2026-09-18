"""
UI tests: execute every page, then exercise the interactions that have
actually broken during development.

These use Streamlit's own AppTest harness, so they run the real script with
real widget state -- no browser required.

Run with:  python tests/test_pages.py
       or:  python -m pytest tests/test_pages.py -q
"""

from __future__ import annotations

import copy
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from streamlit.testing.v1 import AppTest  # noqa: E402

from core import engine, state  # noqa: E402

PAGES = ["dashboard", "electricity", "commute", "appliances", "water",
         "waste", "campus", "actions", "plan", "ask", "about"]

TIMEOUT = 180


def _app(page: str) -> AppTest:
    at = AppTest.from_file("app.py", default_timeout=TIMEOUT)
    at.session_state["page"] = page
    at.run()
    return at


def _errors(at: AppTest) -> str:
    return "; ".join(e.value for e in at.exception)


# ---------------------------------------------------------------------------
# Every page must render
# ---------------------------------------------------------------------------

def test_every_page_renders_without_exception():
    for page in PAGES:
        at = _app(page)
        assert not at.exception, f"{page}: {_errors(at)}"
        assert at.markdown, f"{page} rendered nothing"


# ---------------------------------------------------------------------------
# Interactions
# ---------------------------------------------------------------------------

def test_moving_a_slider_updates_the_page_on_the_same_run():
    """
    Regression: module pages used to receive a result computed BEFORE their
    widgets rendered, so every number lagged one interaction behind the slider
    the user had just moved.
    """
    at = _app("appliances")
    before = " ".join(m.value for m in at.markdown)
    ac_hours = [s for s in at.slider if "Hours a day" in (s.label or "")][0]
    ac_hours.set_value(12.0).run()

    assert not at.exception, _errors(at)
    assert at.session_state["inputs"]["appliances"]["ac_hours"] == 12.0
    assert " ".join(m.value for m in at.markdown) != before


def test_pledging_an_action_reaches_the_plan():
    at = _app("actions")
    boxes = [c for c in at.checkbox if c.key and c.key.startswith("pledge_")]
    assert len(boxes) > 5, f"only {len(boxes)} actions offered"

    boxes[0].set_value(True).run()
    pledged = at.session_state["inputs"]["plan"]["pledged"]
    assert len(pledged) == 1

    at.session_state["page"] = "plan"
    at.run()
    assert not at.exception, _errors(at)


def test_unpledging_removes_it():
    at = _app("actions")
    box = [c for c in at.checkbox if c.key and c.key.startswith("pledge_")][0]
    box.set_value(True).run()
    assert at.session_state["inputs"]["plan"]["pledged"]

    key = [c for c in at.checkbox if c.key and c.key.startswith("pledge_")][0].key
    [c for c in at.checkbox if c.key == key][0].set_value(False).run()
    assert at.session_state["inputs"]["plan"]["pledged"] == []


def test_a_pledge_survives_a_filter_that_hides_it():
    """
    Regression: the pledge list is rebuilt from the checkboxes that rendered,
    so filtering the list to one module must not silently drop commitments
    made against the others.
    """
    at = _app("actions")
    diet = [c for c in at.checkbox if c.key == "pledge_diet_swap"]
    assert len(diet) == 1, "the diet action should be offered for the defaults"
    diet[0].set_value(True).run()
    assert at.session_state["inputs"]["plan"]["pledged"] == ["diet_swap"]

    at.selectbox[0].set_value("Water").run()
    assert "diet_swap" in at.session_state["inputs"]["plan"]["pledged"]

    at.selectbox[0].set_value("All modules").run()
    assert "diet_swap" in at.session_state["inputs"]["plan"]["pledged"]


def test_reset_clears_keyed_widget_state_too():
    """
    Regression: resetting the inputs dict alone did nothing visible, because
    Streamlit gives a keyed widget's stored state precedence over the value
    argument, so the old widget state overwrote the fresh defaults.
    """
    at = _app("campus")
    meals = at.session_state["inputs"]["campus"]["meals"]
    default = meals["Chicken meal"]

    [n for n in at.number_input if n.key == "meal_Chicken meal"][0].set_value(19.0).run()
    assert at.session_state["inputs"]["campus"]["meals"]["Chicken meal"] == 19.0

    [b for b in at.button if "Reset" in (b.label or "")][0].click().run()
    assert not at.exception, _errors(at)
    assert at.session_state["inputs"]["campus"]["meals"]["Chicken meal"] == default


def test_commute_legs_can_be_added_and_removed():
    at = _app("commute")
    start = len(at.session_state["inputs"]["commute"]["legs"])

    [b for b in at.button if "Add a leg" in (b.label or "")][0].click().run()
    assert len(at.session_state["inputs"]["commute"]["legs"]) == start + 1

    [b for b in at.button if b.label == "✕"][0].click().run()
    assert len(at.session_state["inputs"]["commute"]["legs"]) == start
    assert not at.exception, _errors(at)


def test_dashboard_survives_completely_empty_inputs():
    at = _app("dashboard")
    blank = copy.deepcopy(state.DEFAULT_INPUTS)
    blank["electricity"]["monthly_bill"] = 0.0
    blank["commute"]["legs"] = []
    blank["commute"]["intercity"] = []
    blank["appliances"]["has_ac"] = False
    blank["appliances"]["devices"] = {k: 0 for k in blank["appliances"]["devices"]}
    blank["appliances"]["wash_cycles_week"] = 0.0
    blank["water"]["quantities"] = {k: 0.0 for k in blank["water"]["quantities"]}
    blank["water"]["has_ro"] = False
    blank["water"]["bottled_litres_week"] = 0.0
    blank["water"]["leaking_taps"] = 0
    for name in blank["waste"]["streams"]:
        blank["waste"]["streams"][name]["kg_week"] = 0.0
    blank["campus"] = {k: ({} if isinstance(v, dict) else 0.0)
                       for k, v in blank["campus"].items()}

    at.session_state["inputs"] = blank
    at.run()
    assert not at.exception, _errors(at)
    assert engine.build(blank, at.session_state["profile"]).annual_kg == 0.0


def test_the_ask_page_works_without_an_api_key():
    """The dashboard must be fully usable with no model access at all."""
    saved = os.environ.pop("ANTHROPIC_API_KEY", None)
    try:
        at = _app("ask")
        assert not at.exception, _errors(at)
        body = " ".join(m.value for m in at.markdown)
        assert "offline" in body.lower()
    finally:
        if saved is not None:
            os.environ["ANTHROPIC_API_KEY"] = saved


def test_vision_estimates_are_computed_by_the_engine_not_the_model():
    """
    The model reports observations; core/factors.py turns them into carbon.
    A photographed bill and a typed bill must agree exactly.
    """
    from core import calculators, vision

    profile = copy.deepcopy(state.DEFAULT_PROFILE)
    observation = {"kind": "electricity_bill", "confidence": "high",
                   "summary": "bill", "notes": "",
                   "electricity": {"units_kwh": 257.0, "amount_inr": 1800.0,
                                   "period_days": 30}}
    from_photo = vision.estimate(observation, profile)
    expected = 257.0 * calculators.grid_ef(profile)
    assert abs(from_photo.once_kg - expected) < 0.01

    # An unreadable image must not invent a number.
    blank = vision.estimate({"kind": "other", "confidence": "low",
                             "summary": "", "notes": "too blurry"}, profile)
    assert blank.once_kg == 0.0 and blank.annual_kg == 0.0
    assert blank.caveats


if __name__ == "__main__":
    passed = failed = 0
    for name, fn in sorted(list(globals().items())):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"ok   {name}")
                passed += 1
            except AssertionError as error:
                print(f"FAIL {name}: {error}")
                failed += 1
            except Exception as error:  # noqa: BLE001
                print(f"ERR  {name}: {type(error).__name__}: {error}")
                failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
