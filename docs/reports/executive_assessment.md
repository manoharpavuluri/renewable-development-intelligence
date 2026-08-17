# Executive Assessment — RDI-WOK-250-001

**Status: DRAFT — PENDING HUMAN REVIEW.** This is a system-generated
screening output, not an approved investment decision. It requires review
and sign-off by a named human reviewer (`scripts/finalize_recommendation.py`)
before any recommendation here is final.

---

## Executive recommendation

## HOLD

Admissible category set for this evidence profile: `ADVANCE_WITH_CONDITIONS`,
`HOLD`. An unconditional `ADVANCE` was ruled out by two HIGH-severity
material risks, one unresolved gate, and two low-confidence gates.
`DO_NOT_ADVANCE` was ruled out because no disqualifying finding was
identified anywhere in screening. Between the two admissible options, HOLD
reflects that the environmental/land gate (G3) remains genuinely unresolved
rather than merely conditioned.

---

## Decision context

| | |
|---|---|
| Project | RDI-WOK-250-001 — 250 MW onshore wind |
| Location | Western Oklahoma (Dewey County), centroid ≈ (-99.0, 36.0) |
| Candidate area | ~44,463 gross acres |
| Target COD | 2031-12-31 (5.3 years from assessment date) |
| Market | SPP |
| Land control | None — candidate area is not owned, leased, or under option |
| Development stage | Early-stage screening (demonstration scenario) |

---

## Gate summary

| Gate | Domain(s) | Status | Confidence | Material risks |
|---|---|---|---|---|
| G1 — Resource / Physical | wind_resource, terrain, land_cover | CONDITIONALLY_SATISFIED | LOW | 2 (both LOW severity) |
| G2 — Interconnection | interconnection | CONDITIONALLY_SATISFIED | MEDIUM | 1 HIGH |
| G3 — Environmental / Land | land_status, species, flood, cultural | **UNRESOLVED** | MEDIUM | 6 (1 HIGH, 4 MEDIUM, 1 LOW) |
| G4 — Regulatory | regulatory | CONDITIONALLY_SATISFIED | LOW | 2 (1 MEDIUM, 1 LOW) |
| G5 — Aviation / Military | aviation | CONDITIONALLY_SATISFIED | MEDIUM | 0 |

G6 (COD feasibility) and G7 (evidence sufficiency) are assessed separately
below — they synthesize across G1–G5 rather than covering their own domain.

---

## Key findings

- **Interconnection** — TATONGA7 is screening-preferred among tested POIs,
  robust across 2 SPP HCT model cases and 3 tested points of
  interconnection. Candidate-specific feasibility and network-upgrade cost
  remain unestablished (screening-level only).
- **Critical habitat overlap** — USFWS Final designated critical habitat
  for the Peppered chub (*Macrhybopsis tetranema*, federally Endangered)
  overlaps 509.7 acres (1.15%) of the candidate. ESA Section 7 consultation
  is likely required wherever a federal nexus exists (e.g. the FAA filing
  itself creates one).
- **Land-management complexity** — PAD-US identifies 5,081.5 acres (11.4%)
  of overlapping land-management units: a Cheyenne and Arapaho Oklahoma
  Tribal Statistical Area, Oklahoma State Land Board (CLO) lands, and a
  state Wildlife Management Area. None of this establishes legal title,
  trust status, or a development restriction by itself.
- **Cultural-resource intersection** — the Dewey County Courthouse (NRHP,
  ref. 85000680, Taloga) sits **directly inside** the candidate polygon;
  two more NRHP-listed sites fall within 10 miles. Section 106 review has
  not been performed.
- **Flood evidence gap** — FEMA NFHL has **zero digital coverage** for this
  area. That is an absence of data, not a finding of low risk, and is
  treated as such throughout.
- **Aviation** — nearest public-use airport (Seiling Municipal) is 5.71 nm
  away, clear of Oklahoma's 1.5 nm statutory setback; zero Military Special
  Use Airspace intersections. No FAA Form 7460-1 has been filed.
- **Regulatory** — jurisdiction confirmed as Dewey County, OK. Applicable
  requirement categories identified: FAA Part 77 notice, Oklahoma Wind
  Energy Development Act registration (17 O.S. §160.11 et seq.), and
  SPP/FERC interconnection process. Pending 2026 state legislation (SB2,
  HB2751) could change setback requirements before this project reaches
  permitting — flagged, not yet enacted.

---

## COD assessment: AT_RISK

5.3 years remain to the 2031-12-31 target. One HIGH-materiality gate (G3)
is unresolved, alongside 2 HIGH-severity material risks. Two workstreams
have genuinely long, uncertain lead times with no established duration for
this project: the SPP generator interconnection study process and land
control (lease/option execution) — both typically sit on the critical path.

Two durations are cited from real statutory/regulatory sources, and are the
*only* specific figures used anywhere in this assessment:

| Item | Duration | Source |
|---|---|---|
| FAA Form 7460-1 pre-filing window | ≥45 days before construction/permit filing | 14 CFR Part 77 |
| ESA Section 7 formal consultation | up to 135 days from initiation (90 + 45), extendable | 50 CFR 402.14 |

Every other workstream duration (SPP GI study, land control, county
permitting, Section 106 review) is explicitly labeled **unresolved**
rather than estimated.

---

## Critical conditions

1. Obtain a full USFWS IPaC official species list and complete ESA review
2. Complete ESA Section 7 consultation if a federal nexus is confirmed
3. Conduct Section 106 review (SHPO + THPO consultation) for the Dewey
   County Courthouse intersection
4. Resolve actual land ownership, lease, option, and easement status
5. Establish authoritative status for the overlapping tribal/state-land
   areas and confirm any development restrictions
6. Initiate candidate-specific SPP interconnection study work
7. Identify a constructible gen-tie route and confirm ROW availability
8. Retrieve and verify Dewey County zoning/permitting ordinance text
9. Complete FAA Form 7460-1 / OE-AAA process once turbine layout/heights
   are defined
10. Replace screening-grade wind/terrain evidence with field-based surveys

## Unresolved risks

- HIGH-severity critical-habitat overlap; siting impact not yet assessed
- Direct NRHP intersection creates unresolved Section 106 risk
- Interconnection cost/feasibility not yet candidate-specific
- Land control unsecured, compounded by tribal/state-land overlap
- Flood hazard status unknown (not low — unknown)
- Resource/terrain evidence is single-point, single-year, screening-grade
- Regulatory path incomplete (county ordinances, pending legislation)
- Aviation screening incomplete (no FAA determination obtained)

## Next diligence

- Request an authoritative IPaC official species list
- Commission SHPO desktop search, THPO coordination, field archaeological
  assessment
- Obtain title/lease/easement package; confirm state/tribal land interests
- Open candidate-specific SPP interconnection diligence
- Map a preliminary turbine layout against critical habitat, the NRHP
  resource, and land-control boundaries
- Verify Dewey County wind-siting/zoning requirements directly
- Prepare FAA filing once layout/heights are set
- Commission met-tower or equivalent site-measured wind data

---

## Evidence provenance

Every finding above traces to a real, live-queried authoritative source,
hash-verified at the point the deterministic capability consumed it: SPP
HCT/Pre-Screening, USGS PAD-US, USFWS Critical Habitat, USGS 3DEP, NLCD
Annual, U.S. Census TIGERweb, FAA Airports + Special Use Airspace, FEMA
NFHL, and NPS NRHP. See [`docs/data/source-catalog.md`](../data/source-catalog.md)
for source details and [`docs/architecture/overview.md`](../architecture/overview.md)
for how evidence flows from source to recommendation.

## Important limitations

This is an early-stage **screening** output. It does not and must not be
read as: bankable AEP, established interconnection feasibility, a final
POI, a constructible gen-tie route, legal land title, ESA/Section 106
clearance, or an FAA determination. Nothing in this report substitutes for
review by qualified permitting counsel, environmental consultants, or an
interconnection engineer.

## Human approval

**PENDING.** Finalization requires a named reviewer via
`scripts/finalize_recommendation.py` — the only code path in this
repository capable of setting `human_approved: true`.
