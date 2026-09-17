"""Net-zero plan page: glide path, residual, offsets, campus scale-up."""

from __future__ import annotations

import streamlit as st

from core import factors as F, insights, pathway as P, recommend as R
from core.engine import Footprint, campus_scale
from ui import charts, components as C, theme as T


def render(fp: Footprint, profile: dict, actions: list[R.Action], plan: dict) -> None:
    C.section(
        "📉 Your net-zero pathway",
        "A footprint is a measurement. A pathway is a commitment: a target, the "
        "actions that get you there, and the residual that no behaviour change "
        "can remove.",
    )

    pledged = plan.get("pledged", [])
    cols = st.columns([1, 1, 1])
    plan["target_year"] = cols[0].slider(
        "Target year", 2027, 2040, int(plan.get("target_year", 2030)),
        help="2030 is the horizon most national and institutional climate "
             "commitments are written against.",
    )
    plan["target_reduction_pct"] = cols[1].slider(
        "Reduction target (%)", 10, 90, int(plan.get("target_reduction_pct", 50)), step=5
    )
    cols[2].metric("Actions pledged", f"{len(pledged)} of {len(actions)}")

    remaining = R.apply_plan(fp.results, actions, pledged, fp.counted)
    floor = sum(remaining.values())
    path = P.build(fp.annual_kg, floor, plan["target_year"],
                   plan["target_reduction_pct"])
    totals = R.plan_totals(actions, pledged)

    C.tile_row([
        {"label": "Footprint today", "value": fp.annual_kg, "unit": "kg CO₂e/yr"},
        {"label": f"With your plan, by {path.target_year}", "value": floor,
         "unit": "kg CO₂e/yr",
         "foot": f"−{(1 - floor / fp.annual_kg):.0%}" if fp.annual_kg else ""},
        {"label": "Your target", "value": path.target_value, "unit": "kg CO₂e/yr"},
        {"label": "Cumulative CO₂e avoided", "value": P.cumulative_avoided(path),
         "unit": "kg", "foot": "over the whole plan, not just the final year"},
    ])

    if not pledged:
        C.insight(
            "Nothing is pledged yet, so the plan line sits on top of the baseline. "
            "Go to <b>What to do about it</b> and tick the actions you will actually "
            "commit to - the chart below updates immediately.", "warn",
        )
    elif path.on_track:
        C.insight(
            f"Your pledged actions <b>meet your target</b>: "
            f"{floor:,.0f} kg against a target of {path.target_value:,.0f} kg by "
            f"{path.target_year}.", "good",
        )
    else:
        C.insight(
            f"Your pledged actions get you to <b>{floor:,.0f} kg</b>, which is "
            f"<b>{path.gap_kg:,.0f} kg short</b> of your {path.target_year} target. "
            "Either pledge more actions, or be honest and move the target - an "
            "unmet target is worse than a realistic one.", "warn",
        )

    st.markdown("##### The glide path")
    st.caption(
        "Pledged actions are phased in linearly between now and your target year, "
        "which is how behaviour change actually lands. The dashed line is the "
        "1.5 °C per-person budget."
    )
    fig, table = charts.pathway_chart(
        path.years, path.baseline, path.planned,
        F.PARIS_2030_BUDGET, "1.5 °C budget (2,300 kg/person)",
    )
    charts.render(fig, table, table_label="Year by year", key="pathway")

    st.caption(
        f"Savings are capped at {R.MODULE_SAVINGS_CAP:.0%} of each module's total, "
        "because two actions on the same module overlap - raising the AC setpoint "
        "and replacing the AC cut the same kilowatt-hours, and pretending they add "
        "up would overstate the plan."
    )

    st.divider()
    left, right = st.columns([1, 1], gap="large")

    with left:
        st.markdown("##### Before and after, by module")
        rows = [
            (F.MODULE_META[m]["label"], fp.counted[m], remaining[m])
            for m in fp.counted
        ]
        fig, table = charts.dumbbell(rows)
        charts.render(fig, table, key="plan_dumbbell")

    with right:
        st.markdown("##### The residual, and what it costs to offset")
        st.caption(
            "Whatever is left after every action you will actually take. Offsetting "
            "is the last step, never the first - you cannot buy your way out of a "
            "footprint you have not tried to cut."
        )
        C.tile_row([
            {"label": "Residual", "value": path.residual_kg, "unit": "kg CO₂e/yr"},
            {"label": "Trees to absorb it", "value": path.offset_trees, "unit": "trees",
             "foot": "mature trees, every year"},
        ])
        st.write("")
        C.tile_row([
            {"label": "Offset cost", "value": path.offset_cost_inr, "unit": "₹/yr",
             "foot": f"at ₹{F.OFFSET_COST_PER_TONNE:,.0f} per tonne"},
            {"label": "Net money from your plan",
             "value": abs(totals["annual_net_inr"]),
             "unit": "₹/yr",
             "foot": ("back in your pocket" if totals["annual_net_inr"] <= 0
                      else "out of your pocket")},
        ])
        if totals["capex_inr"] > 0:
            st.caption(
                f"Your pledged plan needs ₹{totals['capex_inr']:,.0f} of up-front "
                f"spending and returns ₹{totals['annual_savings_inr']:,.0f} a year."
            )

    st.divider()
    st.markdown("##### Scale it to the whole campus")
    st.caption(
        "The real argument for doing this at a college: one policy moves thousands "
        "of footprints at once. This is your own numbers multiplied by the people "
        "around you."
    )
    profile["campus_population"] = st.slider(
        "People on campus", 500, 40_000, int(profile.get("campus_population", 8000)),
        step=500,
    )
    population = int(profile["campus_population"])
    now = campus_scale(fp, population)
    after_fp_kg = floor
    after_tonnes = after_fp_kg * population / 1000.0

    C.tile_row([
        {"label": "Campus footprint today", "value": now["annual_tonnes"],
         "unit": "tCO₂e/yr"},
        {"label": "If everyone adopted your plan", "value": after_tonnes,
         "unit": "tCO₂e/yr"},
        {"label": "Avoided at campus scale",
         "value": now["annual_tonnes"] - after_tonnes, "unit": "tCO₂e/yr"},
        {"label": "Equivalent trees",
         "value": (now["annual_tonnes"] - after_tonnes) * 1000 / F.TREE_CO2_PER_YEAR,
         "unit": "trees", "foot": "to absorb the same amount"},
    ])
    st.write("")
    C.insight(insights.campus_scale_insight(fp, population))
    if totals["annual_net_inr"] < 0:
        C.insight(
            f"Across {population:,} people, the money saved by this plan comes to "
            f"about <b>₹{-totals['annual_net_inr'] * population / 100000:,.1f} lakh a "
            "year</b>. At campus scale the climate case and the finance case are the "
            "same case - which is the argument that actually gets a proposal "
            "approved.", "good",
        )
