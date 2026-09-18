"""Methodology, assumptions and export. The page that answers 'how do you know?'."""

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from core import factors as F, recommend as R, report
from core.engine import Footprint
from ui import components as C


def render(fp: Footprint, profile: dict, actions: list[R.Action], plan: dict) -> None:
    C.section(
        "📖 Method, assumptions & export",
        "Every coefficient this dashboard uses is listed here. A carbon number "
        "nobody can audit is just an opinion with a decimal point.",
    )

    tab_export, tab_factors, tab_method = st.tabs(
        ["Download your report", "Every factor used", "How the model works"]
    )

    with tab_export:
        pledged = plan.get("pledged", [])
        markdown = report.markdown_report(fp, profile, actions, pledged)
        stamp = date.today().isoformat()

        cols = st.columns(3)
        cols[0].download_button(
            "⬇ Report card (Markdown)", markdown,
            file_name=f"carbon-report-{stamp}.md", mime="text/markdown",
            width="stretch",
        )
        cols[1].download_button(
            "⬇ Footprint data (CSV)", report.results_csv(fp),
            file_name=f"carbon-footprint-{stamp}.csv", mime="text/csv",
            width="stretch",
        )
        cols[2].download_button(
            "⬇ Action list (CSV)", report.actions_csv(actions, pledged),
            file_name=f"carbon-actions-{stamp}.csv", mime="text/csv",
            width="stretch",
        )
        st.markdown("###### Preview")
        st.markdown(markdown)

    with tab_factors:
        st.caption(
            "These are India-relevant approximations compiled from public sources: "
            "CEA grid emission data, BEE appliance ratings, and published waste, "
            "food and transport factors. They are accurate enough to rank actions "
            "against each other, which is what this tool is for. They are not an "
            "audited greenhouse-gas inventory."
        )

        st.markdown("###### Grid and tariff")
        st.dataframe(pd.DataFrame([
            {"Setting": "Grid emission factor (busbar)",
             "Value": f"{profile.get('grid_ef'):.3f} kg CO₂/kWh",
             "Note": profile.get("grid_preset", "")},
            {"Setting": "T&D losses applied",
             "Value": f"{F.TD_LOSS_FRACTION:.0%}" if profile.get("include_td_losses") else "off",
             "Note": "Losses between the power station and your meter"},
            {"Setting": "Tariff", "Value": f"₹{profile.get('tariff'):.2f}/kWh",
             "Note": profile.get("tariff_preset", "")},
        ]), width="stretch", hide_index=True)

        st.markdown("###### Transport (kg CO₂e per km)")
        rows = []
        for name, spec in F.TRANSPORT_MODES.items():
            if "kwh_per_km" in spec:
                value = f"{spec['kwh_per_km']:.3f} kWh/km × grid factor"
            else:
                value = f"{spec['ef']:.3f}"
            rows.append({"Mode": name, "Factor": value,
                         "Basis": spec["basis"], "₹/km": spec["cost_per_km"],
                         "Note": spec["note"]})
        for name, spec in F.INTERCITY_MODES.items():
            rows.append({"Mode": name, "Factor": f"{spec['ef']:.3f}",
                         "Basis": "passenger", "₹/km": spec["cost_per_km"],
                         "Note": spec["note"]})
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

        st.markdown("###### Appliances (rated watts)")
        st.dataframe(pd.DataFrame([
            {"Appliance": name, "Watts": spec["watts"],
             "Default hours/day": spec["hours"], "Note": spec["note"]}
            for name, spec in F.APPLIANCES.items()
        ]), width="stretch", hide_index=True)
        st.dataframe(pd.DataFrame([
            {"AC efficiency class": name, "Watts per ton": value}
            for name, value in F.AC_WATTS_PER_TON.items()
        ]), width="stretch", hide_index=True)

        st.markdown("###### Water")
        st.dataframe(pd.DataFrame(
            [{"End use": name, "Litres": spec["litres"], "Per": spec["unit"],
              "Hot share": f"{spec['hot_share']:.0%}", "Note": spec["note"]}
             for name, spec in F.WATER_END_USES.items()]
        ), width="stretch", hide_index=True)
        st.dataframe(pd.DataFrame(
            [{"Source": name, "kWh per kilolitre": value}
             for name, value in F.WATER_SOURCE_KWH_PER_KL.items()]
            + [{"Source": "Wastewater treatment",
                "kWh per kilolitre": F.WASTEWATER_KWH_PER_KL}]
        ), width="stretch", hide_index=True)

        st.markdown("###### Waste (kg CO₂e per kg, by route)")
        st.caption("Negative values are credits: recycling displaces virgin production.")
        rows = []
        for name, spec in F.WASTE_STREAMS.items():
            for route, value in spec["routes"].items():
                rows.append({"Stream": name, "Route": route,
                             "kg CO₂e per kg": value,
                             "₹ per kg recovered": spec["value_per_kg"]})
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

        st.markdown("###### Food, single-use, digital and goods")
        st.dataframe(pd.DataFrame(
            [{"Item": n, "kg CO₂e": s["ef"], "Unit": "per meal", "Note": s["note"]}
             for n, s in F.MEALS.items()]
            + [{"Item": n, "kg CO₂e": s["ef"], "Unit": "per serving", "Note": s["note"]}
               for n, s in F.BEVERAGES.items()]
            + [{"Item": n, "kg CO₂e": s["ef"], "Unit": "per item", "Note": s["note"]}
               for n, s in F.CONSUMABLES.items()]
            + [{"Item": n, "kg CO₂e": s["ef"],
                "Unit": "per month" if "per month" in n else "per hour",
                "Note": s["note"]}
               for n, s in F.DIGITAL.items()]
            + [{"Item": n, "kg CO₂e": s["ef"],
                "Unit": f"to manufacture, over {s['life_years']} yr",
                "Note": s["note"]}
               for n, s in F.GOODS.items()]
        ), width="stretch", hide_index=True)

        st.markdown("###### Equivalences and benchmarks")
        st.dataframe(pd.DataFrame([
            {"Anchor": "One mature tree absorbs",
             "Value": f"{F.TREE_CO2_PER_YEAR:g} kg CO₂/year"},
            {"Anchor": "Petrol", "Value": f"{F.PETROL_CO2_PER_LITRE:g} kg CO₂/litre"},
            {"Anchor": "LPG cylinder (14.2 kg)",
             "Value": f"{F.LPG_CYLINDER_CO2:g} kg CO₂"},
            {"Anchor": "1,000 km domestic flight, one way",
             "Value": f"{F.FLIGHT_1000KM_CO2:g} kg CO₂e"},
            {"Anchor": "Offset price used",
             "Value": f"₹{F.OFFSET_COST_PER_TONNE:,.0f} per tonne"},
        ] + [
            {"Anchor": name, "Value": f"{spec['value']:,.0f} kg CO₂e/person/year"}
            for name, spec in F.BENCHMARKS.items()
        ]), width="stretch", hide_index=True)

    with tab_method:
        st.markdown(
            f"""
###### The one modelling decision that matters most

Your electricity bill and your appliance list describe **the same kilowatt-hours**
from two directions: one metered, one modelled. Adding them together roughly
doubles an energy footprint, and it is the most common error in amateur carbon
calculators — v1 of this dashboard had it too.

So exactly one of them is authoritative and the other is a cross-check. You choose
which in the sidebar. Right now the authoritative source is
**{'your billed electricity' if profile.get('electricity_source') == 'bill'
   else 'your appliance model'}**, and
**{', '.join(F.MODULE_META[m]['label'] for m in fp.diagnostic) or 'nothing'}**
is excluded from the total.

The gap between the two is itself informative:

- **Modelled ≫ billed** — listed hours are too generous, or the bill is shared
  more ways than you thought.
- **Billed ≫ modelled** — something real is missing from the appliance list: a
  geyser, a fridge, a pump, a second AC.

Hot water is handled the same way. If you list a geyser under Appliances *and*
use hot water in the Water module, set the heater to "already counted in
Appliances" so one geyser is never charged twice.

###### Other boundaries, stated plainly

- **Digital emissions** cover network and data-centre energy only. Charging your
  laptop and phone is measured under Appliances. The boundary is deliberate, so
  the two modules can be added together safely.
- **Goods** are amortised over an assumed service life, so a five-year laptop
  contributes a fifth of its manufacturing carbon each year. That is what makes
  "keep it one more year" a quantifiable action rather than a slogan.
- **Shared bills** are divided by household size wherever you tick that box.
  Skipping this is how a family footprint gets counted four times over.
- **Plan savings** are capped at {R.MODULE_SAVINGS_CAP:.0%} of any single module,
  because actions on the same module overlap.
- **Benchmarks** come from national and global per-person statistics whose scopes
  differ slightly from this dashboard's. They are signposts for order of
  magnitude, not a precise score.

###### What this tool is not

It is not an audited inventory, it does not follow the GHG Protocol's corporate
accounting rules, and it will not survive a compliance review. It is a decision
tool: it tells you which lever in *your* life is worth pulling first, and shows
the arithmetic so you can argue with it.
            """
        )
