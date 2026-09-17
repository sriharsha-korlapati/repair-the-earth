"""
Engine tests: the arithmetic, the accounting rules and the guard rails.

Run with:  python -m pytest tests -q
       or:  python tests/test_engine.py
"""

from __future__ import annotations

import copy
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import calculators as C, engine, factors as F, pathway as P  # noqa: E402
from core import recommend as R, report, state  # noqa: E402


def fresh() -> tuple[dict, dict]:
    return copy.deepcopy(state.DEFAULT_INPUTS), copy.deepcopy(state.DEFAULT_PROFILE)


# ---------------------------------------------------------------------------
# Accounting rules
# ---------------------------------------------------------------------------

def test_electricity_and_appliances_are_never_both_counted():
    """The double-count this dashboard exists to avoid."""
    inputs, profile = fresh()

    profile["electricity_source"] = "bill"
    by_bill = engine.build(inputs, profile)
    assert by_bill.diagnostic == ["appliances"]
    assert "appliances" not in by_bill.counted

    profile["electricity_source"] = "appliances"
    by_model = engine.build(inputs, profile)
    assert by_model.diagnostic == ["electricity"]
    assert "electricity" not in by_model.counted

    # The only difference between the two totals must be the swap of one
    # electricity view for the other -- nothing else may shift, and neither
    # total may contain both.
    elec = by_bill.results["electricity"].annual_kg
    appl = by_bill.results["appliances"].annual_kg
    assert abs((by_bill.annual_kg - by_model.annual_kg) - (elec - appl)) < 1e-6
    assert abs(by_bill.annual_kg - sum(by_bill.counted.values())) < 1e-6
    assert by_bill.annual_kg < sum(by_bill.counted.values()) + appl


def test_hot_water_is_not_charged_twice():
    inputs, profile = fresh()
    inputs["water"]["heater_type"] = "Electric geyser"
    owned_here = C.water(inputs["water"], profile)

    inputs["water"]["heater_type"] = "Electric geyser (already counted in Appliances)"
    owned_elsewhere = C.water(inputs["water"], profile)

    assert owned_here.breakdown.get("Water heating", 0) > 0
    assert "Water heating" not in owned_elsewhere.breakdown
    assert owned_elsewhere.annual_kg < owned_here.annual_kg


def test_shared_bills_are_divided_by_household():
    inputs, profile = fresh()
    inputs["electricity"]["share_with_household"] = True
    profile["household_size"] = 4
    shared = C.electricity(inputs["electricity"], profile)

    inputs["electricity"]["share_with_household"] = False
    alone = C.electricity(inputs["electricity"], profile)

    assert abs(alone.annual_kg - shared.annual_kg * 4) < 1.0


# ---------------------------------------------------------------------------
# Physical behaviour
# ---------------------------------------------------------------------------

def test_ac_setpoint_moves_consumption_the_right_way():
    inputs, profile = fresh()
    inputs["appliances"]["ac_temp"] = 18.0
    cold = C.appliances(inputs["appliances"], profile)
    inputs["appliances"]["ac_temp"] = 26.0
    warm = C.appliances(inputs["appliances"], profile)
    assert cold.annual_kg > warm.annual_kg


def test_electric_vehicles_track_the_grid_factor():
    """An EV is only as clean as the grid charging it -- never assumed zero."""
    inputs, profile = fresh()
    inputs["commute"]["legs"] = [
        {"mode": "Electric car", "distance_km": 10.0, "days_per_week": 5,
         "round_trip": True, "occupancy": 1},
    ]
    inputs["commute"]["intercity"] = []

    profile["grid_ef"] = 0.55
    clean = C.commute(inputs["commute"], profile)
    profile["grid_ef"] = 0.85
    dirty = C.commute(inputs["commute"], profile)

    assert dirty.annual_kg > clean.annual_kg > 0


def test_carpooling_divides_a_private_vehicle():
    inputs, profile = fresh()
    base = {"mode": "Car (petrol)", "distance_km": 10.0, "days_per_week": 5,
            "round_trip": True}
    inputs["commute"]["intercity"] = []

    inputs["commute"]["legs"] = [dict(base, occupancy=1)]
    alone = C.commute(inputs["commute"], profile)
    inputs["commute"]["legs"] = [dict(base, occupancy=4)]
    shared = C.commute(inputs["commute"], profile)

    assert abs(alone.annual_kg / 4 - shared.annual_kg) < 0.5


def test_public_transport_is_not_divided_by_occupancy():
    """Bus and metro factors are already per passenger."""
    inputs, profile = fresh()
    inputs["commute"]["intercity"] = []
    base = {"mode": "City bus", "distance_km": 10.0, "days_per_week": 5,
            "round_trip": True}
    inputs["commute"]["legs"] = [dict(base, occupancy=1)]
    one = C.commute(inputs["commute"], profile)
    inputs["commute"]["legs"] = [dict(base, occupancy=4)]
    four = C.commute(inputs["commute"], profile)
    assert abs(one.annual_kg - four.annual_kg) < 0.001


def test_composting_beats_landfill_for_food_waste():
    inputs, profile = fresh()
    inputs["waste"]["streams"]["Food & kitchen (wet)"]["route"] = "Landfill / dump"
    dumped = C.waste(inputs["waste"], profile)
    inputs["waste"]["streams"]["Food & kitchen (wet)"]["route"] = "Composting"
    composted = C.waste(inputs["waste"], profile)

    assert composted.annual_kg < dumped.annual_kg
    assert composted.metrics["diversion_rate"] > dumped.metrics["diversion_rate"]


def test_recycling_produces_a_carbon_credit():
    inputs, profile = fresh()
    for name in inputs["waste"]["streams"]:
        inputs["waste"]["streams"][name]["kg_week"] = 0.0
    inputs["waste"]["streams"]["Metal (cans, scrap)"] = {
        "kg_week": 1.0, "route": "Recycling"}
    result = C.waste(inputs["waste"], profile)
    assert result.annual_kg < 0, "recycled metal should be a net credit"
    assert result.metrics["recoverable_value_inr"] > 0


def test_grid_losses_increase_the_consumer_factor():
    _, profile = fresh()
    profile["include_td_losses"] = False
    bare = C.grid_ef(profile)
    profile["include_td_losses"] = True
    with_losses = C.grid_ef(profile)
    assert with_losses > bare
    assert abs(with_losses - bare * (1 + F.TD_LOSS_FRACTION)) < 1e-9


# ---------------------------------------------------------------------------
# Guard rails
# ---------------------------------------------------------------------------

def test_zero_inputs_do_not_divide_by_zero():
    inputs, profile = fresh()
    inputs["electricity"]["monthly_bill"] = 0.0
    inputs["commute"]["legs"] = []
    inputs["commute"]["intercity"] = []
    inputs["appliances"]["has_ac"] = False
    inputs["appliances"]["devices"] = {k: 0 for k in inputs["appliances"]["devices"]}
    inputs["appliances"]["wash_cycles_week"] = 0.0
    inputs["water"]["quantities"] = {k: 0.0 for k in inputs["water"]["quantities"]}
    inputs["water"]["has_ro"] = False
    inputs["water"]["bottled_litres_week"] = 0.0
    inputs["water"]["leaking_taps"] = 0
    for name in inputs["waste"]["streams"]:
        inputs["waste"]["streams"][name]["kg_week"] = 0.0
    inputs["campus"] = {k: ({} if isinstance(v, dict) else 0.0)
                        for k, v in inputs["campus"].items()}

    fp = engine.build(inputs, profile)
    assert fp.annual_kg == 0.0
    assert fp.share_of("campus") == 0.0
    assert fp.grade[0] == "A+"
    # Everything downstream must survive a zero footprint too.
    assert R.generate(inputs, profile, fp.results, set(fp.diagnostic)) == []
    assert report.markdown_report(fp, profile, [], [])
    assert report.results_csv(fp)


def test_negative_and_silly_inputs_are_clamped():
    inputs, profile = fresh()
    inputs["electricity"]["monthly_bill"] = -500.0
    inputs["water"]["quantities"]["Bucket bath"] = -3.0
    inputs["appliances"]["ac_hours"] = -5.0
    fp = engine.build(inputs, profile)
    assert fp.annual_kg >= 0
    for result in fp.results.values():
        assert all(value == value for value in result.breakdown.values())  # no NaN


def test_unknown_transport_mode_does_not_crash():
    inputs, profile = fresh()
    inputs["commute"]["legs"] = [
        {"mode": "Teleportation", "distance_km": 5.0, "days_per_week": 5,
         "round_trip": True, "occupancy": 1}]
    result = C.commute(inputs["commute"], profile)
    assert result.annual_kg >= 0


# ---------------------------------------------------------------------------
# Recommendations & plan
# ---------------------------------------------------------------------------

def test_recommendations_are_personal_not_generic():
    inputs, profile = fresh()

    inputs["appliances"]["has_ac"] = True
    inputs["appliances"]["ac_temp"] = 19.0
    fp = engine.build(inputs, profile)
    profile["electricity_source"] = "appliances"
    fp = engine.build(inputs, profile)
    with_ac = R.generate(inputs, profile, fp.results, set(fp.diagnostic))
    assert any(a.id == "ac_setpoint" for a in with_ac)

    inputs["appliances"]["has_ac"] = False
    fp = engine.build(inputs, profile)
    without_ac = R.generate(inputs, profile, fp.results, set(fp.diagnostic))
    assert not any(a.id == "ac_setpoint" for a in without_ac)


def test_no_action_is_offered_for_a_diagnostic_module():
    inputs, profile = fresh()
    profile["electricity_source"] = "bill"
    fp = engine.build(inputs, profile)
    actions = R.generate(inputs, profile, fp.results, set(fp.diagnostic))
    assert not any(a.module == "appliances" for a in actions), (
        "appliance actions would double-count savings against a billed total"
    )


def test_marginal_abatement_cost_signs_are_right():
    inputs, profile = fresh()
    fp = engine.build(inputs, profile)
    for action in R.generate(inputs, profile, fp.results, set(fp.diagnostic)):
        if action.annual_savings_inr > action.annualised_capex:
            assert action.pays_for_itself
            assert action.cost_per_tonne < 0
        assert action.annual_kg > 0


def test_plan_savings_are_capped_per_module():
    """Two actions on one module overlap; the plan must not claim both in full."""
    inputs, profile = fresh()
    fp = engine.build(inputs, profile)
    actions = R.generate(inputs, profile, fp.results, set(fp.diagnostic))
    remaining = R.apply_plan(fp.results, actions, [a.id for a in actions], fp.counted)
    for module, value in remaining.items():
        floor = fp.counted[module] * (1 - R.MODULE_SAVINGS_CAP)
        assert value >= floor - 1e-6, f"{module} was reduced past its cap"
        assert value >= 0


def test_pathway_reaches_the_floor_and_reports_the_gap():
    path = P.build(current_kg=4000.0, planned_floor_kg=2000.0,
                   target_year=2030, target_reduction_pct=50, start_year=2026)
    assert path.planned[0] == 4000.0
    assert abs(path.planned[-1] - 2000.0) < 1e-6
    assert path.on_track  # 50% of 4000 is exactly 2000
    assert P.cumulative_avoided(path) > 0

    short = P.build(4000.0, 3500.0, 2030, 50, 2026)
    assert not short.on_track
    assert short.gap_kg > 0
    assert short.offset_trees > 0


def test_pathway_handles_a_target_year_in_the_past():
    path = P.build(1000.0, 500.0, 2020, 50, start_year=2026)
    assert path.target_year > 2026
    assert len(path.years) >= 2


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def test_report_marks_the_diagnostic_module():
    inputs, profile = fresh()
    fp = engine.build(inputs, profile)
    actions = R.generate(inputs, profile, fp.results, set(fp.diagnostic))
    text = report.markdown_report(fp, profile, actions, [actions[0].id])
    assert "Carbon Report Card" in text
    assert "cross-check" in text
    csv = report.results_csv(fp)
    assert "counted_in_total" in csv
    assert "False" in csv  # the diagnostic row is flagged


def test_factor_tables_are_internally_consistent():
    for name, spec in F.TRANSPORT_MODES.items():
        assert ("ef" in spec) ^ ("kwh_per_km" in spec), name
        assert spec["basis"] in ("vehicle", "passenger"), name
    for name, spec in F.WASTE_STREAMS.items():
        assert spec["routes"], name
        assert spec["value_per_kg"] >= 0, name
    for name, spec in F.GOODS.items():
        assert spec["life_years"] >= 1, name
    for module in F.MODULE_ORDER:
        assert module in F.MODULE_META
        assert module in C.CALCULATORS


if __name__ == "__main__":
    passed = failed = 0
    for key, value in sorted(list(globals().items())):
        if key.startswith("test_") and callable(value):
            try:
                value()
                print(f"ok   {key}")
                passed += 1
            except AssertionError as error:
                print(f"FAIL {key}: {error}")
                failed += 1
            except Exception as error:  # noqa: BLE001
                print(f"ERR  {key}: {type(error).__name__}: {error}")
                failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
