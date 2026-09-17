"""
Net-zero pathway: from "here is your number" to "here is your plan".

The registration brief for this project promised users would "set achievable
sustainability goals, monitor their progress, and work together". This module
is that promise in arithmetic: a glide path from today's footprint to a target,
the residual that no behaviour change can remove, and what it costs to offset
what is left.
"""

from __future__ import annotations

from dataclasses import dataclass

from core import factors as F


@dataclass
class Pathway:
    years: list[int]
    baseline: list[float]      # nothing changes
    planned: list[float]       # pledged actions phased in
    target_year: int
    target_value: float        # kg CO2e/yr at the target year
    plan_floor: float          # best achievable with the pledged actions
    residual_kg: float         # what still remains at the target year
    offset_trees: float
    offset_cost_inr: float
    gap_kg: float              # how far the plan falls short of the target
    on_track: bool


def build(current_kg: float, planned_floor_kg: float, target_year: int,
          target_reduction_pct: float, start_year: int = 2026) -> Pathway:
    """
    `planned_floor_kg` is the footprint once every pledged action is in effect.
    Actions are phased in linearly between now and the target year, which is
    how behaviour change actually lands -- not all at once in January.
    """
    target_year = max(start_year + 1, int(target_year))
    years = list(range(start_year, target_year + 1))
    span = len(years) - 1 or 1

    target_value = current_kg * (1.0 - target_reduction_pct / 100.0)
    baseline = [current_kg for _ in years]
    planned = [
        current_kg + (planned_floor_kg - current_kg) * (index / span)
        for index, _ in enumerate(years)
    ]

    residual = max(0.0, planned[-1])
    gap = max(0.0, planned[-1] - target_value)

    return Pathway(
        years=years,
        baseline=baseline,
        planned=planned,
        target_year=target_year,
        target_value=target_value,
        plan_floor=planned_floor_kg,
        residual_kg=residual,
        offset_trees=residual / F.TREE_CO2_PER_YEAR,
        offset_cost_inr=residual / 1000.0 * F.OFFSET_COST_PER_TONNE,
        gap_kg=gap,
        on_track=planned[-1] <= target_value + 1e-6,
    )


def cumulative_avoided(pathway: Pathway) -> float:
    """Total CO2e avoided over the whole plan, not just in the final year.

    The area between the two lines -- the number that actually matters for the
    atmosphere, since a tonne avoided in 2027 counts as much as one in 2030.
    """
    return sum(b - p for b, p in zip(pathway.baseline, pathway.planned))


def milestones(pathway: Pathway) -> list[tuple[int, float, float]]:
    """(year, kg that year, cumulative avoided by then)."""
    rows: list[tuple[int, float, float]] = []
    running = 0.0
    for year, base, plan in zip(pathway.years, pathway.baseline, pathway.planned):
        running += base - plan
        rows.append((year, plan, running))
    return rows
