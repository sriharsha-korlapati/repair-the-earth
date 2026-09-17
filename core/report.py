"""Export the footprint as a shareable report card (Markdown or CSV)."""

from __future__ import annotations

import io
from datetime import date

import pandas as pd

from core import factors as F
from core.engine import Footprint
from core.recommend import Action


def markdown_report(fp: Footprint, profile: dict, actions: list[Action],
                    pledged: list[str]) -> str:
    grade, grade_note = fp.grade
    name = profile.get("name") or profile.get("persona", "This user")
    lines: list[str] = [
        "# Carbon Report Card",
        "",
        f"**{name}** · {profile.get('campus')} · {profile.get('location')}  ",
        f"Generated {date.today().isoformat()} by Repair the Earth - Carbon Intelligence v2",
        "",
        "## Headline",
        "",
        f"- **Annual footprint:** {fp.annual_kg:,.0f} kg CO₂e ({fp.tonnes:.2f} tonnes)",
        f"- **Grade:** {grade} - {grade_note}",
        f"- **Paris-aligned 2030 budget:** {F.PARIS_2030_BUDGET:,.0f} kg per person "
        f"({fp.annual_kg / F.PARIS_2030_BUDGET:.1f}x)",
        f"- **Annual running cost measured:** ₹{fp.annual_cost:,.0f}",
        "",
        "## Where it comes from",
        "",
        "| Module | kg CO₂e / year | Share |",
        "| --- | ---: | ---: |",
    ]
    for module, value in fp.ranked():
        lines.append(f"| {F.MODULE_META[module]['label']} | {value:,.0f} | "
                     f"{fp.share_of(module):.0%} |")

    if fp.diagnostic:
        excluded = ", ".join(F.MODULE_META[m]["label"] for m in fp.diagnostic)
        lines += ["", f"_{excluded} is measured as a cross-check and deliberately "
                      "excluded from the total, because it describes the same "
                      "kilowatt-hours as the billed figure._"]

    lines += ["", "## What this equals", ""]
    for _, value, label in fp.equivalences():
        lines.append(f"- {value} {label}")

    lines += ["", "## Recommended actions", "",
              "| Action | kg CO₂e saved / yr | Net ₹ / yr | ₹ / tonne | Effort |",
              "| --- | ---: | ---: | ---: | --- |"]
    for action in sorted(actions, key=lambda a: -a.annual_kg)[:15]:
        mark = " ✅" if action.id in set(pledged) else ""
        lines.append(
            f"| {action.title}{mark} | {action.annual_kg:,.0f} | "
            f"{action.annual_net_inr:+,.0f} | {action.cost_per_tonne:+,.0f} | "
            f"{action.effort} |"
        )

    chosen = [a for a in actions if a.id in set(pledged)]
    if chosen:
        saved = sum(a.annual_kg for a in chosen)
        money = -sum(a.annual_net_inr for a in chosen)
        lines += [
            "", "## My pledge", "",
            f"I have committed to **{len(chosen)} actions** worth "
            f"**{saved:,.0f} kg CO₂e a year** "
            f"({saved / fp.annual_kg:.0%} of my footprint)"
            + (f", with a net **₹{money:,.0f} a year** back in my pocket." if money > 0
               else f", at a net cost of ₹{-money:,.0f} a year."),
        ]
        for action in sorted(chosen, key=lambda a: -a.annual_kg):
            lines.append(f"- [ ] {action.title}")

    lines += [
        "", "---", "",
        "### How to read this",
        "",
        "Emission factors are India-relevant approximations compiled from public "
        "sources (CEA grid data, BEE appliance ratings, published waste and food "
        "factors). They are accurate enough to rank actions against each other, "
        "which is what this report is for. They are not an audited greenhouse-gas "
        "inventory, and the benchmark figures cover slightly different scopes than "
        "this dashboard, so treat them as signposts rather than scores.",
    ]
    return "\n".join(lines)


def results_csv(fp: Footprint) -> str:
    rows: list[dict] = []
    for module, value in fp.ranked():
        result = fp.results[module]
        rows.append({
            "module": F.MODULE_META[module]["label"],
            "line_item": "(module total)",
            "annual_kg_co2e": round(value, 1),
            "share_of_total": round(fp.share_of(module), 4),
            "counted_in_total": True,
        })
        for label, item_value in sorted(result.breakdown.items(),
                                        key=lambda kv: kv[1], reverse=True):
            rows.append({
                "module": F.MODULE_META[module]["label"],
                "line_item": label,
                "annual_kg_co2e": round(item_value, 2),
                "share_of_total": round(item_value / fp.annual_kg, 4) if fp.annual_kg else 0,
                "counted_in_total": True,
            })
    for module in fp.diagnostic:
        result = fp.results[module]
        rows.append({
            "module": F.MODULE_META[module]["label"],
            "line_item": "(diagnostic only - not added to total)",
            "annual_kg_co2e": round(result.annual_kg, 1),
            "share_of_total": 0.0,
            "counted_in_total": False,
        })
    buffer = io.StringIO()
    pd.DataFrame(rows).to_csv(buffer, index=False)
    return buffer.getvalue()


def actions_csv(actions: list[Action], pledged: list[str]) -> str:
    chosen = set(pledged)
    rows = [{
        "action": a.title,
        "module": F.MODULE_META[a.module]["label"],
        "annual_kg_co2e_saved": round(a.annual_kg, 1),
        "capex_inr": round(a.capex_inr),
        "annual_savings_inr": round(a.annual_savings_inr),
        "annual_net_inr": round(a.annual_net_inr),
        "inr_per_tonne_avoided": round(a.cost_per_tonne),
        "payback_years": round(a.payback_years, 1) if a.payback_years else "",
        "effort": a.effort,
        "pledged": a.id in chosen,
    } for a in sorted(actions, key=lambda a: -a.annual_kg)]
    buffer = io.StringIO()
    pd.DataFrame(rows).to_csv(buffer, index=False)
    return buffer.getvalue()
