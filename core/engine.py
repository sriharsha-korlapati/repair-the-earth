"""
Aggregation: turn six module results into one honest footprint.

THE DOUBLE-COUNTING PROBLEM (and why this file exists)
------------------------------------------------------
The electricity bill and the appliance list describe the SAME kilowatt-hours
from two directions: one is metered, one is modelled. Adding them together
would roughly double a user's energy footprint, which is the most common error
in amateur carbon calculators -- v1 of this dashboard had it too.

v2 resolves it explicitly: exactly ONE of the two is authoritative
(profile["electricity_source"]) and the other becomes a diagnostic that
cross-checks it. The reconciliation gap between them is surfaced in the UI,
because a large gap is itself useful information -- it means either an
unlisted appliance or a wrongly shared bill.

Hot water is handled the same way, in the Water module's heater setting.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from core import factors as F
from core.calculators import Result, compute_all


@dataclass
class Footprint:
    """The aggregated picture every page reads from."""

    results: dict[str, Result]
    counted: dict[str, float] = field(default_factory=dict)   # module -> annual kg in total
    diagnostic: list[str] = field(default_factory=list)       # modules excluded from the total
    annual_kg: float = 0.0
    annual_cost: float = 0.0
    reconciliation: dict[str, float] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    # -- derived views ------------------------------------------------------
    @property
    def tonnes(self) -> float:
        return self.annual_kg / 1000.0

    @property
    def monthly_kg(self) -> float:
        return self.annual_kg / 12.0

    @property
    def grade(self) -> tuple[str, str]:
        return F.grade_for(self.annual_kg)

    def ranked(self) -> list[tuple[str, float]]:
        """Counted modules, largest first."""
        return sorted(self.counted.items(), key=lambda kv: kv[1], reverse=True)

    def share_of(self, module: str) -> float:
        return self.counted.get(module, 0.0) / self.annual_kg if self.annual_kg else 0.0

    def all_items(self) -> dict[str, float]:
        """Every line item across counted modules, for whole-footprint ranking."""
        items: dict[str, float] = {}
        for module in self.counted:
            for label, value in self.results[module].breakdown.items():
                items[f"{F.MODULE_META[module]['label']}: {label}"] = value
        return items

    def vs_benchmarks(self) -> list[tuple[str, float]]:
        rows = [("You", self.annual_kg)]
        rows += [(name, spec["value"]) for name, spec in F.BENCHMARKS.items()]
        return rows

    def equivalences(self) -> list[tuple[str, str, str]]:
        """(icon, value, label) -- concrete anchors for an abstract number."""
        kg = self.annual_kg
        return [
            ("🌳", f"{kg / F.TREE_CO2_PER_YEAR:,.0f}",
             "mature trees needed for a year to absorb this"),
            ("⛽", f"{kg / F.PETROL_CO2_PER_LITRE:,.0f}",
             "litres of petrol burnt, equivalent"),
            ("✈️", f"{kg / F.FLIGHT_1000KM_CO2:,.1f}",
             "one-way 1,000 km domestic flights"),
            ("🔥", f"{kg / F.LPG_CYLINDER_CO2:,.0f}",
             "LPG cylinders burnt"),
            ("❄️", f"{kg / F.AC_HOUR_CO2:,.0f}",
             "hours of running a 1.5-ton AC"),
            ("📱", f"{kg / F.PHONE_CHARGE_CO2:,.0f}",
             "full smartphone charges"),
        ]


def build(inputs: dict, profile: dict) -> Footprint:
    """Compute every module and assemble the non-double-counted total."""
    results = compute_all(inputs, profile)
    fp = Footprint(results=results)

    source = profile.get("electricity_source", "bill")
    if source == "appliances":
        excluded = "electricity"
    else:
        excluded = "appliances"

    for module in F.MODULE_ORDER:
        result = results[module]
        if module == excluded:
            fp.diagnostic.append(module)
            continue
        fp.counted[module] = result.annual_kg
        fp.annual_cost += result.annual_cost

    fp.annual_kg = sum(fp.counted.values())

    # --- Reconciliation: do the two views of electricity agree? -------------
    billed_kwh = results["electricity"].metrics.get("monthly_units_per_person", 0.0) * 12.0
    modelled_kwh = results["appliances"].metrics.get("kwh_per_person", 0.0)
    fp.reconciliation = {
        "billed_kwh_annual": billed_kwh,
        "modelled_kwh_annual": modelled_kwh,
        "gap_kwh": modelled_kwh - billed_kwh,
        "gap_pct": ((modelled_kwh - billed_kwh) / billed_kwh) if billed_kwh else 0.0,
    }

    gap_pct = fp.reconciliation["gap_pct"]
    if billed_kwh and modelled_kwh:
        if gap_pct > 0.30:
            fp.warnings.append(
                f"Your appliance list models {modelled_kwh:,.0f} kWh a year but your bill "
                f"implies {billed_kwh:,.0f} kWh - {gap_pct:+.0%}. Either some listed hours "
                "are too generous, or the bill is shared between more people than you think."
            )
        elif gap_pct < -0.30:
            fp.warnings.append(
                f"Your bill implies {billed_kwh:,.0f} kWh a year but your appliance list only "
                f"accounts for {modelled_kwh:,.0f} kWh ({gap_pct:+.0%}). Something real is "
                "missing from the list - a geyser, a fridge, a pump or a second AC."
            )
        else:
            fp.warnings.append(
                f"Metered and modelled electricity agree within {abs(gap_pct):.0%} "
                f"({billed_kwh:,.0f} vs {modelled_kwh:,.0f} kWh a year). "
                "That is a well-calibrated picture."
            )

    return fp


def campus_scale(fp: Footprint, population: int) -> dict[str, float]:
    """One person's footprint projected across a whole campus."""
    return {
        "population": float(population),
        "annual_tonnes": fp.annual_kg * population / 1000.0,
        "trees_equivalent": fp.annual_kg * population / F.TREE_CO2_PER_YEAR,
        "annual_cost_inr": fp.annual_cost * population,
    }
