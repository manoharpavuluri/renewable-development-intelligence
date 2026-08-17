# Renewable Development Intelligence — Project Specification & Claude Handoff

## 1. Purpose

Build a production-oriented **Agentic AI renewable-development screening system** for early-stage utility-scale renewable projects.

V1 scenario:

> “We are considering a 250-MW wind project in western Oklahoma. Should we spend more money advancing it, what are the material risks, and what diligence should happen next?”

The system should not behave like a fixed workflow with an LLM bolted on. It should act as a governed investigation agent that:

1. starts from a developer-supplied candidate area, capacity, technology, and target COD;
2. examines authoritative or high-quality public evidence;
3. chooses the next investigation based on unresolved material uncertainty;
4. uses deterministic tools for calculations and GIS;
5. uses the LLM for bounded planning, interpretation, and uncertainty reasoning;
6. pauses when authoritative evidence or a missing capability requires human/external work;
7. resumes the same persisted thread without replaying completed work;
8. maintains a traceable evidence/audit chain;
9. produces a final investment recommendation only after all material domains have been considered and a human approves the result.

Final recommendation categories:

- ADVANCE
- ADVANCE WITH CONDITIONS
- HOLD
- DO NOT ADVANCE

Do **not** create a fake 0–100 score.

---

## 2. Core Design Principles

### 2.1 Deterministic computation vs agent judgment

**Deterministic Python / Databricks owns:**
- GIS intersections
- acreage and distance calculations
- queue analytics
- HCT parsing and comparison
- wind-statistical calculations
- terrain/slope calculations
- land-cover statistics
- evidence hashing and provenance checks
- rule-based gates
- deterministic admissibility filtering
- planner validation

**Agent / LLM owns:**
- deciding what uncertainty is most valuable to investigate next;
- selecting among policy-approved investigations;
- interpreting documents and source material;
- synthesizing domain findings;
- explaining uncertainty;
- identifying next diligence;
- escalating to HITL;
- final recommendation drafting.

The LLM may never invent calculations or bypass deterministic policy.

---

## 3. Business Inputs

Required V1 inputs:

- `project_id`
- candidate polygon / site boundary
- technology (`onshore_wind`)
- target capacity MW
- target COD
- market / RTO-ISO

Current demo:

- Project ID: `RDI-WOK-250-001`
- Technology: onshore wind
- Capacity: 250 MW
- Target COD: 2031-12-31
- Market: SPP
- Candidate area: ~44,463 acres
- Centroid: approximately `(-99.0, 36.0)`

---

## 4. Business Outputs

The system should produce:

### Project-level
- recommendation
- recommendation rationale
- critical conditions
- unresolved risks
- next diligence
- confidence
- evidence quality
- human-review requirement

### Domain-level
For each domain:
- gate
- screening status
- decision confidence
- resolved uncertainty
- remaining uncertainty
- evidence references
- completed investigations
- next actions / human diligence boundary

---

## 5. Evidence Model

Evidence classes:

- `SOURCE_FACT`
- `DERIVED_FACT`
- `AGENT_INTERPRETATION`
- `DEVELOPER_ASSUMPTION`
- `UNRESOLVED`

Risk severity:
- LOW
- MEDIUM
- HIGH
- CRITICAL

Confidence:
- LOW
- MEDIUM
- HIGH

The system must keep **risk severity separate from confidence**.

Traceability chain:

`assumptions -> source evidence -> deterministic calculations -> interpretations -> domain risks -> gates -> human review -> final recommendation`

---

## 6. Development Gates

Current gate model:

- **G1** Resource and Physical Site Suitability
- **G2** Transmission and Interconnection
- **G3** Environmental and Land Constraints
- **G4** Permitting and Regulatory Path
- **G5** Aviation and Military Compatibility
- **G6** Development Schedule and COD Feasibility
- **G7** Evidence Sufficiency for Investment Recommendation

All currently begin as `UNRESOLVED`.

---

## 7. Initial Investigation Queue

Current `development_gate_assessment.json` queue:

| Task | Priority | Domain | Capability |
|---|---:|---|---|
| INV-001 | BLOCKING | interconnection | `spp.transmission_context` |
| INV-002 | HIGH | wind_resource | `wind.analyze_candidate_resource` |
| INV-003 | HIGH | terrain | `gis.analyze_terrain` |
| INV-004 | HIGH | land_cover | `gis.analyze_land_cover` |
| INV-005 | HIGH | species | `environment.screen_species` |
| INV-006 | HIGH | land_status | `land.resolve_status` |
| INV-007 | HIGH | aviation | `aviation.screen_candidate` |
| INV-008 | HIGH | regulatory | `regulatory.build_permit_matrix` |
| INV-009 | MEDIUM | cultural | `environment.screen_cultural_resources` |
| INV-010 | MEDIUM | flood | `gis.resolve_flood_evidence` |

Important requirement:

The agent should **not** simply execute tasks by task number.

Policy should first select the highest-priority admissible tier, then:
- if one action remains -> deterministic singleton;
- if multiple equal-priority actions remain -> Foundry planner chooses within the bounded set.

---

## 8. Current Public-Screening Evidence

### 8.1 Candidate site
- Gross area: ~44,463 acres
- Gross acres/MW: ~177.9
- No setbacks or exclusions yet
- Does not imply developable acreage or turbine layout

### 8.2 Wind
HRRR MET 2025 single modeled point:
- 8,760 hourly observations
- mean wind speed ~7.88 m/s at 120 m
- screening only
- not AEP
- not P50/P90
- not met-tower data
- multi-year and candidate-wide resource still unresolved

### 8.3 Wetlands
NWI:
- ~2,426.7 acres mapped overlap
- ~5.46% of candidate
- screening only
- not jurisdictional determination

### 8.4 Flood
FEMA NFHL:
- no digital NFHL/FIRM coverage found
- 100% treated as unknown
- must not interpret absence of mapping as no flood hazard

### 8.5 PAD-US / managed lands
Unique overlap:
- ~5,081.5 acres
- ~11.43%

Important mapped units include:
- Cheyenne and Arapaho Oklahoma Tribal Statistical Area
- CLO / State Land Board lands
- Dewey County Wildlife Management Area

Do not equate tribal statistical geography with trust/reservation/legal land status.

---

## 9. Interconnection Work Completed

The interconnection domain is the most developed domain so far.

### 9.1 SPP queue
Public queue:
- no lat/lon
- useful for text-based POI/county/TO/status analytics
- not valid for “within 25 miles” claims

### 9.2 SPP HCT / Pre-Screening
Model cases tested:
- `DIS231-TC00ALL-24SP3`
- `DIS231-TC03ALL-24SP3`

Tested POIs:
- `515407:TATONGA7`
- `515375:WWRDEHV7`
- `515497:MATHWSN7`

250-MW injection.

Deterministic shared HCT primitive:
`src/renewable_intelligence/interconnection/hct_screening.py`

Canonical screen:

#### Tatonga
- TC00 / TC03
- 0 pre-shift overloads
- 0 post-shift overloads
- worst post loading: 90.29%

#### Mathewson
TC00:
- rows 9
- pre overloads 3
- post overloads 4
- new crossings 2
- worst post 117.43%

TC03:
- rows 12
- pre overloads 2
- post overloads 5
- new crossings 3
- worst post 121.70%

#### Woodward
- 0 pre-shift overloads
- 17 post-shift overloads
- worst post loading 124.74%

Screening ranking in both model cases:

1. TATONGA7
2. MATHWSN7
3. WWRDEHV7

Conclusion:

`TATONGA7` is screening-preferred **among the tested POIs and tested model cases**.

Do **not** claim:
- globally optimal POI
- final POI
- GI feasibility
- final upgrade cost
- exact gen-tie route
- ROW availability

### 9.3 Additional POI capability
Implemented and independently validated:

`src/renewable_intelligence/interconnection/spp_additional_poi.py`

Capability:
`spp.evaluate_additional_poi`

Result:
- `PREFERENCE_ROBUST_ACROSS_TESTED_CASES`
- preferred `TATONGA7`
- 2 model cases
- 3 POIs
- additional Mathewson did not displace Tatonga

### 9.4 Model-case comparison capability
Implemented:
`spp.compare_model_cases`

The additional-POI capability now subsumes the narrower cross-model question for this case, so running a redundant `INT-FU-002` is not required if `INT-FU-003` already proves the same business uncertainty.

### 9.5 Public transmission / gen-tie context
Public line evidence:
- nearest public 345-kV line geometry to candidate ~0.786 miles
- OG&E Tatonga-Woodward line context
- do not call this “gen-tie distance”
- exact SPP bus geometry still unresolved
- route / ROW / cost unresolved

Capability:
`transmission.assess_gen_tie_context`

### 9.6 Precedent study
Implemented:
`spp.analyze_precedent_study`

Used SPP study precedent `GEN-2026-PR2`.

Important: study cost/system-upgrade totals must not be treated as candidate cost.

---

## 10. Agent Architecture Already Implemented

### 10.1 LangGraph state
Core:
`src/renewable_intelligence/graph/state.py`

### 10.2 Investigation graph
`src/renewable_intelligence/graph/investigation_graph.py`

### 10.3 Deterministic capability registry
`src/renewable_intelligence/tools/registry.py`
`src/renewable_intelligence/tools/bootstrap.py`

### 10.4 Planner policy
`src/renewable_intelligence/agents/planner_policy.py`

Already supports:
- deterministic effective priority
- admissible action filtering
- policy validation

### 10.5 Foundry planner
`src/renewable_intelligence/agents/foundry_planner.py`

Current planner:
- strict JSON schema
- can only choose enumerated action IDs and capabilities
- deterministic singleton bypass
- LLM call only when >1 equally admissible choices
- deterministic validation after LLM selection

Current Azure AI Foundry planner connectivity is proven.

---

## 11. Planner Policy We Want

Use **one governed planner**, not separate unrelated planners.

Planning scopes:

### PROJECT_ROOT
Choose which development domain to investigate next.

### FOLLOW_UP
Choose the next investigation inside the active domain.

Common policy:

1. deterministic application code builds candidate actions;
2. deterministic priority policy produces admissible actions;
3. if exactly one -> select deterministically;
4. if multiple -> Foundry reasons among only those actions;
5. strict structured output;
6. deterministic validator checks chosen action and capability;
7. agent cannot invent actions.

Project-level planner dry run already succeeded.

Candidate set:
- INV-002 through INV-010

Admissible HIGH set:
- INV-002 through INV-008

Foundry selected:
- `INV-006`
- `land.resolve_status`
- HIGH confidence

Reason was broadly sound: known State Land Board / WMA / tribal-geography intersections make land-status clarification potentially high value.

Planner prompt should avoid inventing false prerequisites between otherwise parallel investigations.

---

## 12. HITL / Persistence Architecture Already Working

### 12.1 Local checkpointing
Local:
- SQLite
- `data/runtime/investigation_checkpoints.sqlite`

Abstraction:
`src/renewable_intelligence/persistence/checkpointing.py`

Production target:
- PostgreSQL checkpointer
- Azure Database for PostgreSQL later

Do not provision Azure PostgreSQL yet.

### 12.2 Durable interrupt
Missing capability/evidence produces LangGraph interrupt:

`CAPABILITY_OR_EVIDENCE_REQUIRED`

The same thread can later resume after external/human evidence is supplied.

### 12.3 Resume behavior proven
Saved thread:

`RDI-WOK-250-001:screening:v1`

History successfully resumed without replay:

- INV-001 `spp.transmission_context`
- INT-FU-001 `spp.analyze_precedent_study`
- INT-FU-004 `transmission.assess_gen_tie_context`
- INT-FU-003 `spp.evaluate_additional_poi`

Evidence ledger:
4 entries.

INT-FU-003 assessment:
`HUMAN_DILIGENCE_REQUIRED`

This demonstrated:

agent decision -> missing evidence -> interrupt -> human acquires evidence -> same thread resumes -> deterministic capability executes -> evidence ledger updates -> redundant investigation skipped.

---

## 13. Evidence Ledger / Audit

Current concepts:

### investigation_history
What capability executions actually happened.

### evidence_ledger
What each result meant for business uncertainty.

### audit_events
How the agent reached each step.

Examples already used:
- `PLANNER_POLICY_APPLIED`
- `PLANNER_BYPASSED_SINGLETON`
- `LLM_PLANNER_INVOKED`
- `LLM_PLANNER_DECISION`
- `PLANNER_DECISION_VALIDATED`
- `EVIDENCE_ASSESSED`
- `EVIDENCE_LEDGER_RECORDED`
- `CAPABILITY_WAIT_RESUMED`

---

## 14. Project-Level Lifecycle Change We Started

Problem discovered:

Interconnection reached:

`HUMAN_DILIGENCE_REQUIRED`

but the graph originally interpreted any non-follow-up result as **END**, which ended the entire project.

Desired architecture:

`domain automated screening exhausted -> record domain outcome -> end that project turn -> next project turn chooses another unresolved domain`

New intended state:

`project_domain_outcomes`

Example:

```json
{
  "interconnection": {
    "gate_id": "G2",
    "screening_status": "HUMAN_DILIGENCE_REQUIRED",
    "decision_confidence": "MEDIUM",
    "remaining_uncertainty": [],
    "completed_task_ids": []
  }
}
```

Also intended:
- `project_candidate_actions`
- `project_admissible_actions`
- `project_planner_decision`
- `project_planner_selection_mode`
- `run_iteration`

---

## 15. Why We Are Getting Errors Now

The overall architecture is not the problem.

The current failures are implementation consistency problems caused by **incrementally patching a live LangGraph while also evolving persisted checkpoint semantics**.

We changed several tightly coupled concerns in separate edits:

1. `route_after_assessment()` was changed so it can return:
   - `follow_up`
   - `domain_complete`
   - `end`

2. We intended to add a new node:
   - `record_domain_outcome`

3. We intended the graph edge:
   - `domain_complete -> record_domain_outcome`

4. We also added checkpoint migration logic.

Some edits landed while others did not, so the current source is internally inconsistent.

### Error 1

Earlier:

`KeyError: 'domain_complete'`

This happened because routing could return `domain_complete`, but the graph branch mapping being used during `update_state()` did not know that route.

### Error 2

Current:

`ValueError: At 'assess_investigation_result' node, 'route_after_assessment' branch found unknown target 'record_domain_outcome'`

This means the branch now references:

`record_domain_outcome`

but the compiled graph does **not** currently contain a node registered under that name.

This is a classic partial-topology update:

routing added -> node registration missing or patch did not land.

### Key lesson

We should stop applying more incremental string-replacement patches until the graph is reviewed as one state machine.

The current code should be treated as the source of truth and normalized in a single coherent patch.

---

## 16. Current Broken Area

Main file:

`src/renewable_intelligence/graph/investigation_graph.py`

Claude should verify together:

1. `record_domain_outcome()` function exists
2. `graph.add_node("record_domain_outcome", record_domain_outcome)` exists
3. `route_after_assessment()` returns only branch keys defined in the graph
4. branch map includes:
   - `follow_up -> plan_follow_up`
   - `domain_complete -> record_domain_outcome`
   - `end -> END`
5. `record_domain_outcome -> END`
6. `select_next_investigation` project-root behavior
7. project planner node registration
8. all route functions match every returned target
9. no stale edge from previous topology remains

---

## 17. Checkpoint-Migration Requirement

The existing SQLite thread predates `project_domain_outcomes`.

We need a controlled migration from the already completed interconnection result into the new project-level state.

Do not restart/replay interconnection.

Desired migration:

legacy thread
- has 4 completed investigations
- latest G2 assessment = `HUMAN_DILIGENCE_REQUIRED`

-> new checkpoint containing:

`project_domain_outcomes["interconnection"]`

The migration should be idempotent.

Because LangGraph graph topology has changed, Claude should confirm the safest version-specific strategy for the installed LangGraph version before using `update_state()`.

Do not assume `update_state()` behavior across versions without checking the installed API/version.

---

## 18. Next Domain

The project-level planner dry run already produced:

`INV-006 land_status -> land.resolve_status`

This is not yet executed.

Next expected cycle after graph normalization:

1. migrate legacy G2 outcome;
2. start next project turn on same `thread_id`;
3. project planner builds remaining root candidate set;
4. deterministic policy keeps HIGH tier;
5. Foundry chooses one;
6. registry checks capability;
7. if `land.resolve_status` unavailable -> durable interrupt;
8. build authoritative land-status capability/evidence;
9. resume same thread;
10. record domain result;
11. continue later project turns.

---

## 19. Remaining Domain Capabilities

Not yet implemented:

### G1 / Physical and Resource
- `wind.analyze_candidate_resource`
- `gis.analyze_terrain`
- `gis.analyze_land_cover`

### G3 / Environmental and Land
- `environment.screen_species`
- `land.resolve_status`
- `environment.screen_cultural_resources`
- likely wetland interpretation / exclusion synthesis later

### G4 / Permitting and Regulatory
- `regulatory.build_permit_matrix`

### G5 / Aviation / Military
- `aviation.screen_candidate`

### Flood
- `gis.resolve_flood_evidence`

### G6 / Schedule
Needs future synthesis of:
- interconnection timelines
- permitting
- environmental studies
- land control
- aviation
- target COD

### G7 / Investment Recommendation
Final synthesis only after material domains are investigated.

---

## 20. Likely Source Strategy for Remaining Domains

### Wind
- HRRR MET / WTK
- multiple years
- multiple candidate-area grid cells
- spatial variability
- screening only, no bankable AEP

### Terrain
- USGS 3DEP
- deterministic slope/elevation stats
- exclusions / constructability screen

### Land cover
- NLCD service
- deterministic polygon intersection
- screening compatibility

### Species
- USFWS ECOS / IPaC
- listed species / critical habitat / screening
- no biological clearance claim

### Land status
- PAD-US
- Oklahoma Commissioners of Land Office / State Land Board sources
- tribal land/status authoritative sources
- WMA ownership/management sources
- do not infer legal status from statistical geography

### Aviation
- FAA
- airports
- obstacle / radar / military screening
- no FAA determination claim

### Regulatory
- Oklahoma
- county/local
- federal
- tribal where applicable
- permit matrix with source evidence
- no legal opinion

### Cultural
- NRHP / NPS screening
- no Section 106 clearance claim

### Flood
- alternate authoritative flood-risk evidence
- site-specific hydrologic review if mapping unavailable

---

## 21. Production Platform Direction

Planned platform:

### Azure
- Azure AI Foundry / Azure OpenAI
- ADLS Gen2
- Databricks
- Delta Lake
- Unity Catalog
- Azure AI Search
- Key Vault
- Azure Monitor / OpenTelemetry
- PostgreSQL checkpointer in production later

### Databricks
- deterministic batch / GIS / data processing
- Delta evidence tables
- MLflow evaluation / tracing

### Agent
- LangGraph orchestration

### MCP
Use only for coarse, reusable business capabilities where it fits naturally.

Do not force every internal function behind MCP.

### A2A
Not required in V1.

### Fine tuning
Not justified until evaluation shows a real repeatable model gap.

---

## 22. Evaluation Requirements

We need tests before expanding much further.

### Unit tests
- priority policy
- admissible actions
- planner selection validation
- HCT thresholds
- overload crossing semantics
- evidence-hash mismatch
- domain-outcome filtering
- completed-task replay prevention

### Integration tests
- Foundry planner with bounded action set
- SQLite checkpoint resume
- interrupt -> evidence supply -> resume
- project turn -> domain outcome -> next project turn

### Graph-topology tests
Very important now:

At build time verify:
- every conditional route result has a registered target;
- every target node exists;
- no orphan routing labels;
- compile succeeds.

### Migration test
Given a legacy interconnection checkpoint:
- migration is idempotent
- G2 outcome appears
- history stays unchanged
- evidence ledger stays unchanged
- next project turn excludes INV-001

### Evals
Planner:
- never selects inadmissible action
- never invents capability
- rationale grounded in supplied state
- no false prerequisites
- no unsupported feasibility claims

---

## 23. Recommended Immediate Recovery Plan

Do **not** keep applying one-off patches.

Claude should:

### Phase A — Code audit
Read current:
- `graph/state.py`
- `graph/investigation_graph.py`
- `graph/result_assessment.py`
- `agents/planner_policy.py`
- `agents/foundry_planner.py`
- `tools/registry.py`
- `tools/bootstrap.py`
- `persistence/checkpointing.py`
- `scripts/run_investigation_graph.py`
- `scripts/resume_investigation_graph.py`
- `scripts/start_next_project_turn.py`
- `scripts/migrate_project_checkpoint.py`
- `scripts/test_project_planner.py`

Produce:
1. current state-machine diagram;
2. all node names;
3. all route labels;
4. all edges;
5. missing/inconsistent topology;
6. checkpoint-version assumptions.

### Phase B — Define canonical graph before patching
Expected conceptual graph:

```text
START
  -> validate_state
  -> prepare_project_candidates
  -> plan_project_investigation
  -> check_capability
      -> execute_capability
      -> assess_and_record_evidence

assessment:
  FOLLOW_UP_REQUIRED + candidates
      -> plan_follow_up
      -> prepare_follow_up
      -> check_capability

  DOMAIN_AUTOMATION_EXHAUSTED
      -> record_domain_outcome
      -> END project turn

capability unavailable:
  -> interrupt
  -> resume same thread
  -> check_capability
```

### Phase C — Normalize implementation
Make one coherent patch.

### Phase D — Compile/tests
Do not touch the real checkpoint until:
- `py_compile` passes
- graph compile passes
- topology unit test passes
- project planner dry run passes

### Phase E — Migration
Migrate legacy G2 thread once.

### Phase F — Start next project turn
Only then let the project planner select the next domain.

---

## 24. Questions for Claude

Please review the repository and answer:

1. What is the actual current LangGraph state machine?
2. Which topology edits are partially applied?
3. Why is `record_domain_outcome` referenced but not registered?
4. Should project turns end at domain boundaries, or should a single invocation continue through multiple domains?
5. What is the safest migration strategy for this installed LangGraph version?
6. Should root planning and follow-up planning reuse one planner function or share a lower-level common planner engine?
7. Should `project_domain_outcomes` be a dict in state, a reducer-backed list, or persisted separately?
8. Should task/domain lifecycle be explicit enums rather than inferred from history?
9. How should we prevent stale `PENDING` source-queue entries from causing replay?
10. How should checkpoint/schema versioning be implemented?
11. What tests should be added before implementing the remaining domains?
12. What is the smallest coherent patch that gets the project back to a stable state without rewriting working interconnection code?

---

## 25. Guardrails / Non-Negotiables

Do not:
- replay already-completed interconnection work;
- delete the SQLite checkpoint;
- create a new thread just to avoid migration;
- provision Azure PostgreSQL yet;
- claim bankable AEP;
- claim definitive GI feasibility;
- claim candidate network-upgrade cost;
- claim final POI;
- claim constructible gen-tie route;
- claim legal land status from PAD-US/statistical geography alone;
- claim environmental clearance;
- claim FAA determination;
- let the LLM invent actions or tools;
- turn the project back into a fixed pipeline.

Preserve:
- deterministic calculations;
- evidence provenance;
- shared HCT parser;
- evidence ledger;
- audit log;
- checkpoint/resume behavior;
- bounded Foundry planner;
- HITL boundary;
- human final recommendation review.

---

## 26. Current Status in One Paragraph

The project already has a strong, working interconnection investigation slice, deterministic HCT analysis, real SPP evidence, Foundry-based bounded planning, a capability registry, evidence ledger, durable SQLite checkpointing, HITL interrupts, and a demonstrated resume-without-replay workflow. The current instability is localized to the **new project-level orchestration refactor**: we started adding domain outcomes, project-root planning, and graph-topology changes incrementally, leaving `route_after_assessment`, node registration, edges, and legacy-checkpoint migration temporarily inconsistent. The next task should be to normalize the graph and migration strategy as one coherent change before adding any new domain capability.
