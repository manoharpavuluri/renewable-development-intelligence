# ADR-001: V1 Production Backlog (Deferred Intentionally)

**Status:** Accepted
**Date:** 2026-08-17
**Applies to:** `rdi-v1.0`

## Context

V1 of Renewable Development Intelligence is feature-complete for its
stated scope: a governed agentic screening system that takes a candidate
wind project through ten authoritative-source investigations, synthesizes
them into a gate-level assessment, and drafts a bounded, human-reviewed
recommendation. It runs against real public data, is checkpointed on a
local SQLite backend, and is covered by a 174-test offline evaluation
suite plus live-source and recommendation-stability checks.

Several capabilities that a production deployment would eventually need
were considered during V1 development and explicitly **not** built. This
ADR exists so that omission reads as a scoping decision, not an oversight
— and so a future implementer (including a future session of this same
project) has a concrete starting point rather than a blank page.

None of the items below are required to demonstrate the system's core
architectural claims: bounded LLM reasoning inside a deterministic policy
envelope, durable human-in-the-loop checkpointing, evidence-grounded
multi-domain screening, and a regression-tested recommendation pipeline.
Adding them now would broaden the technology surface without
strengthening that story.

## Decision

Defer the following from V1. Each entry states what exists today, what
production would need, and roughly how it would be built.

### 1. `WAITING_EXTERNAL_EVIDENCE` / asynchronous domain progression

**Today:** a domain investigation that hits a missing capability produces
a durable `interrupt()`; the *entire project turn* pauses until that
specific domain is resumed. In the V1 demo run this was never a practical
problem because every domain eventually got a real capability built for
it in the same session.

**Production need:** with many concurrent projects and capabilities that
depend on slow external processes (e.g. a human requesting an IPaC
official species list, which can take days), one stalled domain
shouldn't block the other nine from continuing.

**Approach:** add a `WAITING_EXTERNAL_EVIDENCE` project-domain-outcome
status distinct from `HUMAN_DILIGENCE_REQUIRED`, and change
`select_next_investigation` to route around domains in that state the
same way it already routes around exhausted domains — allowing the
project-root planner to keep working other domains while one waits.

### 2. PostgreSQL production LangGraph checkpointing

**Today:** `persistence/checkpointing.py` already supports a
`RDI_CHECKPOINT_BACKEND=postgres` path via `langgraph-checkpoint-postgres`,
gated behind `RDI_POSTGRES_URL`, with `RDI_POSTGRES_AUTO_SETUP` explicitly
opt-in. Nothing has been provisioned.

**Production need:** SQLite is single-writer and single-host; a
multi-tenant deployment needs concurrent-safe, durable checkpoint storage.

**Approach:** provision Azure Database for PostgreSQL, run
`checkpointer.setup()` once as a deliberate migration step (not
auto-run), point `RDI_POSTGRES_URL` at it. The abstraction is already
backend-agnostic; this is provisioning + migration testing, not new code.

### 3. Databricks / Delta persistent evidence ledger

**Today:** the evidence ledger lives inside the LangGraph checkpoint
state (a Python list, persisted as part of the thread).

**Production need:** cross-project evidence queries ("which projects
intersect this PAD-US unit"), long-term evidence retention independent
of any one investigation thread, and Databricks-side deterministic
batch/GIS processing at the volumes described in section 21 of
`CLAUDE_HANDOFF.md`.

**Approach:** mirror evidence-ledger writes to a Delta table keyed by
project ID / task ID / capability / artifact hash, alongside (not
instead of) the checkpoint-resident ledger the graph actually reasons
over.

### 4. Unity Catalog governance

**Today:** no catalog; artifacts are files on local disk (`data/`),
governed by path + SHA-256 hash checked at resume time.

**Production need:** access control, lineage, and discovery across many
projects' evidence artifacts.

**Approach:** register the Delta evidence table (#3) and raw artifact
locations in Unity Catalog once a Databricks workspace exists; the
hash-verification pattern already in every capability's evidence-loading
code carries over unchanged.

### 5. Azure Key Vault / managed identity hardening

**Today:** Foundry access uses `DefaultAzureCredential` (already
credential-source-agnostic); no secrets are hardcoded anywhere in the
codebase. Azure CLI login was sufficient for V1 development.

**Production need:** service-to-service auth without a human's `az login`
session — managed identity for compute, Key Vault for anything that
can't be a managed identity.

**Approach:** attach a system-assigned managed identity to whatever
compute runs the graph, grant it the Foundry project's Cognitive
Services User role; `DefaultAzureCredential` picks it up with no code
change.

### 6. Scheduled source-health monitoring

**Today:** `scripts/smoke_live_sources.py` exists and works — 11/11
sources UP as of last manual run — but nothing runs it on a schedule.

**Production need:** the whole reason this script is separate from the
offline test suite is that it *should* run periodically without gating
every commit; "periodically" isn't implemented yet.

**Approach:** a low-frequency scheduled job (e.g. daily) invoking the
existing script unchanged, alerting on non-zero exit rather than
blocking anything.

### 7. CI/CD deployment pipeline

**Today:** `.github/workflows/tests.yml` runs the 174-test offline suite
on every push/PR (fast, deterministic, no network or Foundry calls). This
is a test gate, not a deployment pipeline — there is no build, artifact,
or environment-promotion step, because there is no deployed environment
for V1 to promote to.

**Production need:** once this system runs as a deployed service rather
than a local CLI demo, it needs an actual build/deploy pipeline (image
build, environment promotion, rollback), plus the live smoke suite and
stability eval (#6, and this project's recommendation-stability eval)
wired to a scheduled job rather than the PR gate, since both depend on
external service/model availability.

**Approach:** extend the existing `tests.yml` job rather than replace
it; add environment-specific deploy jobs once there is a real deployment
target to promote to.

### 8. Multi-project tenancy

**Today:** one project (`RDI-WOK-250-001`), one checkpoint thread, no
concept of a project registry or per-project isolation.

**Production need:** many concurrent candidate projects, each with its
own thread, evidence, and recommendation lifecycle.

**Approach:** a thin project-registry layer above the existing
`thread_id`-keyed checkpointing (which already scopes cleanly per
project); the graph and synthesis code need no change, since they
already operate on one `project_id` at a time.

### 9. RBAC for human recommendation approval

**Today:** `human_review.finalize_recommendation()` requires a
freeform `--reviewer` name string; anyone who can run the script can
approve.

**Production need:** verify the named reviewer is actually authorized to
approve capital-allocation recommendations for this project.

**Approach:** the function signature already isolates "who is approving"
as a single parameter — swap the freeform name for an authenticated
identity (Entra ID) checked against a per-project approver list before
`finalize_recommendation()` is called; the approval logic itself
(the override/justification rules) doesn't change.

### 10. Production UI / API

**Today:** every interaction is a CLI script against a local checkpoint.

**Production need:** a developer or analyst who isn't comfortable running
Python scripts needs to submit a candidate, watch investigation progress,
and review/approve a draft.

**Approach:** a thin API wrapping the existing scripts
(`start_next_project_turn`, `synthesize_project_assessment`,
`finalize_recommendation`) — the business logic underneath is already
script-shaped and side-effect-isolated enough that this is closer to
"build a front door" than "restructure the system."

## Consequences

- V1 remains a single-project, single-host, CLI-driven demonstration.
  That is a known, deliberate limitation, not a discovered one.
- Every item above has an existing seam in the V1 codebase it would
  attach to (noted in each "Approach"), rather than requiring a rewrite.
- Re-opening any of these should start from this ADR, not from scratch.
