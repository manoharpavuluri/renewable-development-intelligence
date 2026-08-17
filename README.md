# Renewable Development Intelligence

An evidence-grounded agentic system for early-stage renewable-development
investment screening.

## Problem

> We are considering a 250-MW wind project in western Oklahoma. Should we
> spend more money advancing it, what are the material risks, and what
> diligence should happen next?

Answering that responsibly means touching interconnection, wind resource,
terrain, land cover, species, land status, aviation, flood, cultural
resources, and permitting — each governed by a different federal, state, or
utility authority, each with its own evidence quality, and none of them
individually sufficient to answer the business question alone.

## What the agent does

Given a candidate polygon, capacity, technology, and target COD, the system:

1. Chooses which unresolved domain to investigate next — governed by a
   deterministic priority policy, with an LLM reasoning only among options
   that policy has already deemed admissible.
2. Executes a deterministic capability against real authoritative public
   data (never simulated) to answer that domain's question.
3. Assesses whether the resulting evidence resolves the domain or still
   requires human diligence — and never converts "we don't have data" into
   "the answer is favorable."
4. Pauses durably (a LangGraph interrupt on the same checkpointed thread)
   whenever a capability or evidence source isn't available yet, and
   resumes later without replaying any completed work.
5. Once every domain has been screened, synthesizes the results into a
   gate-level rollup, a schedule-feasibility read, an evidence-sufficiency
   check, and a **draft** recommendation — bounded to only the categories a
   deterministic policy says the evidence can support.
6. Stops. The draft requires a named human reviewer before it can become
   final; nothing in the model-facing schema can set that flag itself.

## Example result

For the actual western-Oklahoma candidate (`RDI-WOK-250-001`):

```text
RECOMMENDATION: HOLD                    (status: DRAFT_PENDING_HUMAN_REVIEW)
COD FEASIBILITY: AT_RISK                (5.3 years to target COD 2031-12-31)
EVIDENCE SUFFICIENCY: MINIMUM_COVERAGE_FOR_SCREENING_RECOMMENDATION

G1 Resource/Physical .... SCREENED_WITH_CONDITIONS  (confidence: LOW)
G2 Interconnection ...... SCREENED_WITH_CONDITIONS  (confidence: MEDIUM)
G3 Environmental/Land ... UNRESOLVED               (confidence: MEDIUM)
G4 Regulatory ........... SCREENED_WITH_CONDITIONS  (confidence: LOW)
G5 Aviation/Military .... SCREENED_WITH_CONDITIONS  (confidence: MEDIUM)
```

## Why HOLD

The deterministic recommendation policy computed an admissible set of
`{ADVANCE_WITH_CONDITIONS, HOLD}` for this evidence profile — it ruled out
an unconditional `ADVANCE` (two HIGH-severity risks, one unresolved gate,
two LOW-confidence gates) and ruled out `DO_NOT_ADVANCE` (nothing
disqualifying was ever found). Within that admissible window, the model
chose HOLD because G3 remains genuinely unresolved: designated critical
habitat for a federally Endangered species overlaps the candidate, an
NRHP-listed historic building sits directly inside the polygon, and FEMA
flood coverage is 0% digital (unknown, not clear). None of that is a
"no" — it's a list of concrete, named diligence items with real evidence
behind each one.

## Architecture

Four layers — orchestration, business capabilities, evidence/data
platform, governance/observability — with deterministic computation and
LLM reasoning kept in strictly separate code paths. See
[`docs/architecture/overview.md`](docs/architecture/overview.md) for the
full diagram set, including where the "LLM never decides what it's allowed
to do" pattern shows up twice in this codebase (investigation planning and
recommendation drafting).

## Agentic behavior

- **Bounded planning**: the LLM selects only from a deterministically
  computed admissible set (`planner_policy.py`, `recommendation_policy.py`)
  — never invents an action, capability, or recommendation category.
- **Durable HITL**: missing capability or evidence produces a LangGraph
  `interrupt()`; the same thread resumes later with no replay of completed
  investigations (`persistence/checkpointing.py`).
- **Evidence discipline**: every capability reads a governed artifact by
  path *and* SHA-256 hash, verified at resume time.
- **Human finalization**: `human_review.finalize_recommendation()` is the
  only code path in the repository that can set `human_approved: true`. It
  requires a named reviewer, and overriding the deterministic admissible
  set requires an explicit written justification.

## Authoritative evidence sources

All real, all live-checked (`scripts/smoke_live_sources.py`, 10/10 UP as of
last run) — no simulated or placeholder data anywhere in the pipeline:

| Source | Authority | Used for |
|---|---|---|
| SPP HCT / Pre-Screening | Southwest Power Pool | Interconnection screening |
| PAD-US | USGS | Land status / tribal & state-land overlap |
| Critical Habitat | USFWS | Species / ESA screening |
| 3DEP | USGS | Terrain / elevation / slope |
| NLCD Annual | USGS / MRLC | Land cover composition |
| TIGERweb | U.S. Census Bureau | Jurisdiction (county/state) identification |
| US Airports + Special Use Airspace | FAA (+ NOAA mirror) | Aviation / military compatibility |
| NFHL | FEMA | Flood-hazard coverage |
| NRHP | National Park Service | Cultural/historic resources |
| HRRR MET | NOAA (via toolkit) | Wind resource |

## Guardrails

The system will not claim: bankable AEP, definitive interconnection
feasibility, a final POI, a constructible gen-tie route, legal land status
from statistical geography alone, environmental clearance, or an FAA
determination. See `CLAUDE_HANDOFF.md` §25 for the full non-negotiables
list this project was built against — and `tests/evaluation/` for the
pattern-based checks that enforce it against real model output.

## Evaluation

**174/174 offline tests pass in under a second** — no network or LLM calls in
the regression suite itself:

```bash
.venv/bin/python -m pytest tests/ -v
```

| Layer | Covers |
|---|---|
| Deterministic policy | Admissible-set correctness for both the investigation planner and the recommendation policy |
| Grounding / unsupported-claim | Pattern checker derived from the guardrails above, tested against labeled BAD/GOOD examples and the real draft |
| Recommendation-consistency | Named scenarios (unresolved-gate, clean-evidence, disqualifying-finding, insufficient-evidence, gap-retention) verifying the decision *envelope*, not exact wording |
| Agent/LangGraph regression | No-replay, missing-capability interrupt routing, evidence-ledger dedup, and one true end-to-end interrupt→resume test |
| Human finalization | `human_approved: true` is unreachable without a named reviewer; overrides outside policy require justification |

Separately, `scripts/smoke_live_sources.py` makes real network calls to
every external service above and checks both reachability and schema
stability — deliberately kept out of the offline suite since a flaky
government GIS endpoint shouldn't block a commit.

### Recommendation stability

`scripts/eval_recommendation_stability.py` runs the recommendation
drafter N times (default 20) against one **frozen** evidence packet and
asserts the deterministic layer (gate synthesis, G6, G7, admissible set)
is byte-identical every time it's recomputed, while the LLM's
recommendation is allowed to vary *within* the admissible set — and its
rationale is checked for grounding violations and for dropping any of
the frozen scenario's known HIGH risks or evidence gaps. This is the
project's answer to "the same evidence produced HOLD once and
ADVANCE_WITH_CONDITIONS on another call": that's not measured as a bug,
it's measured directly, with an explicit pass/fail bar.

```text
20 live Foundry runs against RDI-WOK-250-001's frozen evidence:

ADVANCE_WITH_CONDITIONS     12
HOLD                         8
determinism violations       0
policy violations            0
grounding violations         0
retention violations         0
```

*(From the run that validated this eval — see `scripts/eval_recommendation_stability.py`'s
own output for a fresh run. An earlier pass caught two real gaps in the
grounding checker itself: it was exempting "identify a constructible
gen-tie route" from overclaiming only when phrased as an imperative
sentence, so gerund phrasing and mid-sentence task framing slipped
through. Fixed by making the exemption field-aware — critical_conditions
and next_diligence are action-item fields by construction, so a target-
naming phrase there is never an overclaim regardless of grammar; the
same phrase in rationale or unresolved_risks still is.)*

## Demo walkthrough

```bash
# 0. Zero-setup: show the frozen, committed example output - no
#    credentials, no live checkpoint, no network calls. This is
#    what `make demo` runs by default from a fresh clone.
make demo

# Steps 1-7 below re-run the pipeline live and require the
# original data/spikes/ evidence tree and checkpoint (gitignored,
# not committed - see "Reproducibility" below) plus Foundry
# credentials; they are not needed to see the demo output.

# 1. Inspect the completed investigation thread (read-only)
export RDI_THREAD_ID="RDI-WOK-250-001:screening:v1"
.venv/bin/python scripts/start_next_project_turn.py   # reports NO_PENDING_INVESTIGATIONS

# 2. Re-run the synthesis + draft-recommendation pipeline
export RESULT_DIR="data/spikes/public_sources_20260815T173207Z"
export FOUNDRY_PROJECT_ENDPOINT="<your Foundry project endpoint>"
export FOUNDRY_MODEL_NAME="<your deployed model>"
.venv/bin/python scripts/synthesize_project_assessment.py

# 3. Log a full pipeline trace to MLflow
.venv/bin/python scripts/trace_project_run.py
mlflow ui --backend-store-uri sqlite:///data/runtime/mlflow.db

# 4. Run the offline evaluation harness
.venv/bin/python -m pytest tests/ -v

# 5. Check every live external source is still up
.venv/bin/python scripts/smoke_live_sources.py

# 6. Measure recommendation stability across N live Foundry calls
.venv/bin/python scripts/eval_recommendation_stability.py

# 7. (A human, not this script) review and finalize the draft
.venv/bin/python scripts/finalize_recommendation.py \
  --decision approve --reviewer "<your name>"
```

## Local setup

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Azure AI Foundry connectivity (`azure-identity` `DefaultAzureCredential`)
and `FOUNDRY_PROJECT_ENDPOINT` / `FOUNDRY_MODEL_NAME` are required for any
script that invokes the bounded planner or recommendation drafter. Every
other capability only needs outbound HTTPS to the public sources above.

## Reproducibility

`data/spikes/` is where a live run's fetched evidence artifacts and
LangGraph checkpoint land; it's gitignored because it's regenerated
output, not source, and some of it is timestamped per-run. That means a
fresh clone has no completed investigation to inspect out of the box.

`data/examples/rdi-wok-250-001/` is the fix: a small, committed, frozen
snapshot of one completed synthesis result (gate rollup, G6/G7, and the
draft recommendation) for the same western-Oklahoma candidate used
throughout this README. `make demo` reads from it by default, so the
walkthrough above works immediately after cloning, with no credentials
and no network calls. Point `RESULT_DIR` at a live `data/spikes/<run>/`
directory (see the Demo walkthrough steps 1-7) to see a real,
uncommitted re-run instead.

## Repository structure

```text
src/renewable_intelligence/
  graph/            LangGraph state machine + evidence assessment
  agents/           Planner policy + bounded Foundry planner
  synthesis/         Gate synthesis, G6/G7, recommendation policy +
                     drafter, human finalization
  {land,environmental,gis,regulatory,aviation,resource,
   transmission,interconnection}/
                     Deterministic capabilities, one per domain
  persistence/       Checkpointing (SQLite/Postgres)
  evaluation/         Grounding/overclaiming checker
  tools/              Capability registry

scripts/
  spikes/             One-off authoritative-source fetch scripts
                       (produce hash-verified governed artifacts)
  run_investigation_graph.py, resume_investigation_graph.py,
  start_next_project_turn.py
                     Investigation lifecycle
  synthesize_project_assessment.py, finalize_recommendation.py
                     Post-investigation synthesis + HITL
  trace_project_run.py, smoke_live_sources.py
                     Observability

tests/
  unit/, integration/, evaluation/
                     174-test offline regression + eval suite

data/
  examples/           Frozen, committed synthesis snapshot (`make demo`)
  spikes/             Gitignored - live-run evidence + checkpoint

docs/
  architecture/       Diagrams and design rationale
  requirements/       Original business requirements / MVP scope
  data/               Public-source catalog
  adr/                Architecture decision records

.github/workflows/
  tests.yml           CI: runs the offline suite on push/PR
```

## Limitations

This is a **screening** system, not a bankable diligence package. It does
not and should not claim: final interconnection feasibility, bankable AEP,
legal land title, FAA obstruction clearance, ESA Section 7 clearance, or
Section 106 clearance. Every domain in the current run resolved to
`HUMAN_DILIGENCE_REQUIRED` — the honest state for an early-stage screen,
not a gap to be smoothed over before the next round of diligence actually
happens.
