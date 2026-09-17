# NetZero Navigators × Repair the Earth — v2 walkthrough

Brief for the call with the Aditya University team ahead of
**TerraThon 2026: Sustainability Sprint**, SRM University-AP, 25 September 2026.

---

## 1. Where the idea stands

The registration form promises a concept that will "track carbon emissions,
identify major sources of environmental impact, and suggest practical solutions",
help users "set achievable sustainability goals, monitor their progress", and
scale to "schools, communities, and organizations".

That is a good pitch. Presented as slides, it is also a pitch that a dozen other
teams will make. **The gap between your abstract and a winning entry is that
every verb in it is now a working screen.**

| The registration promise | Where it now lives |
|---|---|
| "track carbon emissions" | Six measurement modules → one aggregated total |
| "identify major sources" | Ranked module chart + biggest-line-items across all modules |
| "suggest practical solutions" | Recommendation engine: costed, ranked, personal |
| "set achievable goals, monitor progress" | Net-zero pathway with pledges and a glide path |
| "scalable for schools, communities" | Campus scale-up slider: one policy × 8,000 people |
| "data-driven insights" | Marginal abatement cost curve; every factor published |

## 2. Tracks you can now enter against

The form lists five tracks. The prototype speaks to four of them **with running code**:

- **AI for Earth** — deterministic engine + optional Claude coach grounded in it
- **Water Reimagined** — the water module, framed as the water-energy-carbon nexus
- **Net-Zero Future** — pathway, residual, offsets, campus scale-up
- **Waste to Wealth** — route-based waste module that prices recovered material

The flyer's SDG strip (6, 7, 9, 11, 12, 13) is mirrored in the action cards: every
recommendation is tagged with the goal it serves.

The form also asks for a **mode of presentation**. Pick **Prototype / Working
Model**. That is the whole point of this change.

## 3. Demo script — seven minutes

1. **Open on the dashboard.** One number: 3.77 tonnes, grade D, 1.6× the 1.5 °C
   budget. *"This is a real student profile, not a slide."*
2. **Point at the split chart.** Campus life is 61% of it. *"Food is the biggest
   lever in a student's life and it is missing from every calculator we found."*
3. **Open Waste.** Change food waste from *Landfill* to *Composting* and let the
   number move on screen. *"Same kilogram, same bin, different route — 90% less
   carbon, because landfilled food emits methane."*
4. **Open Water.** Show that 77% of water carbon is *heating*, not volume.
   *"Water is an energy problem wearing a water costume."*
5. **Open What to do.** Twenty-one actions, generated from those inputs. Nineteen
   pay for themselves. Show the marginal abatement curve: *"Everything below the
   line pays you to do it."*
6. **Pledge four actions → Net-zero plan.** Watch the glide path bend under the
   Paris line.
7. **Campus scale-up.** Drag to 8,000 people. *"Individually this is a nudge.
   At campus scale it is thousands of tonnes and lakhs of rupees — and that is the
   argument that actually gets a proposal approved."*

Close on **Method & export**: every coefficient on screen. *"A carbon number nobody
can audit is just an opinion with a decimal point."*

## 4. What to say when a judge pushes back

**"Are these numbers accurate?"** They are India-relevant public estimates — CEA
grid data, BEE ratings, published food and waste factors — accurate enough to rank
actions against each other, which is what a decision tool needs. Every one is
listed in the app, and the user can override the grid factor and tariff. It is not
an audited inventory and we say so in the app.

**"Isn't this just another carbon calculator?"** Three differences. It resolves
double-counting explicitly instead of silently — the bill and the appliance list
measure the same kWh, and we pick one and show the reconciliation gap. It costs
every action in rupees per tonne, so advice is ranked by leverage rather than by
vibe. And it scales one person's answer to an institution.

**"What does the AI actually do?"** Not the arithmetic. The engine is
deterministic, offline and auditable; the model reads the finished numbers and
helps interpret them. The dashboard works with no API key at all — demo it that
way if the venue Wi-Fi is bad.

**"What's the impact?"** On the default profile, the actions the engine finds come
to 55% of the footprint, and 19 of 21 are cash-positive. That is the finding worth
presenting: for most students the climate-optimal choice is also the cheap one.

## 5. Division of work for the team

Five members, five ownable pieces — everyone should be able to answer questions
about their own area on stage:

1. **Water module + rainwater** — refine end-use volumes for hostel life; get real
   rainfall and roof areas for the Aditya campus.
2. **Waste module + campus audit** — weigh a hostel bin for a week; replace our
   defaults with measured data. This single step turns a prototype into research.
3. **Campus life + canteen data** — get the real mess menu and meal mix; plate-waste
   measurement is a one-afternoon experiment with a weighing scale.
4. **Recommendations + economics** — verify local prices: solar capex, scrap rates,
   bus fares, tariff slabs. Numbers a judge can check are numbers a judge trusts.
5. **Presentation + methodology** — own the Method page and the pushback answers
   above. Whoever owns this should be the one fielding technical questions.

## 6. Highest-value work before 25 September

In priority order:

1. **Replace defaults with measured campus data** for at least one module. A
   prototype with real local data beats a prettier prototype with invented data,
   every time.
2. **Run it on 20–30 classmates** and screenshot the distribution. "We measured 30
   students and the median was X" is a finding, not a demo.
3. **Write one institutional recommendation** costed with the engine — e.g. campus
   composting, or rooftop solar on one hostel block — with tonnes avoided, capex
   and payback. That is the slide that wins the room.
4. **Rehearse the seven-minute script until it needs no notes.** A working demo
   that stalls is worse than slides.

## 7. Known limits — own them before a judge finds them

- Factors are public estimates, not measured; scope differs slightly from the
  national benchmarks we display, and the app says so.
- Water pumping electricity may overlap slightly with a home meter reading; hot
  water, the large term, is handled explicitly.
- Flights exclude high-altitude radiative forcing, which would roughly double them.
- No multi-user accounts or persistence yet: everything lives in one browser
  session. Fine for a demo, and honest about being a prototype.
- The campus scale-up multiplies one profile across a population. Say "if everyone
  lived like this", never "the campus emits this".
