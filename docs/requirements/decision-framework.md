# Renewable Development Intelligence
## V1 Development Decision Framework

---

# 1. Purpose

This framework defines how Renewable Development Intelligence converts evidence into a screening-stage development recommendation.

The framework is designed for:

- early-stage wind development;
- western Oklahoma;
- SPP;
- public-data-driven investigation.

It is not intended to replace investment committee approval, engineering studies, legal advice, environmental clearance, or formal interconnection processes.

---

# 2. Decision Question

The system shall answer:

> Based on currently available evidence, is additional development investment warranted for this opportunity?

The system shall also answer:

> What information or diligence would most improve the next development decision?

---

# 3. Recommendation States

Exactly one recommendation shall be produced.

## ADVANCE

Use when:

- no known fatal condition exists;
- no unresolved CRITICAL risk exists;
- HIGH risks have sufficient evidence and appear manageable;
- minimum evidence requirements are satisfied;
- target COD does not appear fundamentally incompatible with known conditions;
- remaining diligence is consistent with normal next-stage development activity.

ADVANCE does not mean the project is approved or economically viable.

It means additional development investment is justified.

---

## ADVANCE WITH CONDITIONS

Use when:

- no known fatal condition exists;
- the opportunity remains potentially attractive;
- one or more material risks require targeted diligence;
- identified issues do not currently justify stopping development;
- the next diligence actions are clear and bounded.

Conditions must be explicitly stated.

Example:

> Advance only after confirming candidate POI feasibility and obtaining the official species screening required for the site.

---

## HOLD

Use when:

- a material question prevents a rational advance/stop decision;
- evidence needed for a HIGH or CRITICAL issue is unavailable;
- authoritative sources conflict;
- human specialist interpretation is required before further significant spend;
- project schedule viability cannot reasonably be assessed;
- there is insufficient evidence to distinguish manageable risk from fatal risk.

HOLD is fundamentally an uncertainty state.

It must not be used merely because the project has risks.

---

## DO NOT ADVANCE

Use when sufficiently reliable evidence identifies a condition that makes continued development materially unattractive under current assumptions.

Potential examples include:

- severe site constraint leaving inadequate usable area;
- credible evidence of a prohibitive development constraint;
- schedule incompatibility that cannot reasonably be mitigated;
- a material regulatory or environmental restriction incompatible with the proposed project;
- other project-specific fatal or near-fatal conditions.

A DO NOT ADVANCE recommendation requires stronger evidence than a HOLD recommendation.

The agent shall not issue DO NOT ADVANCE solely because important evidence is missing.

---

# 4. No Overall Numeric Viability Score in V1

V1 shall not calculate a single weighted project viability score.

Reason:

No calibrated dataset currently demonstrates that arbitrary weights correctly represent renewable-development investment decisions.

Example:

`35% interconnection + 20% resource + 20% environmental + ...`

would create false precision.

V1 instead uses:

1. decision gates;
2. domain risk severity;
3. evidence confidence;
4. materiality;
5. explicit decision rules.

A quantitative score may be introduced later if historical project outcomes provide defensible calibration data.

---

# 5. Domain Assessment

Each required domain shall produce a domain assessment.

Required domains:

1. Wind Resource
2. Site / GIS
3. Transmission Context
4. SPP Interconnection
5. Environmental
6. Permitting / Regulatory
7. Aviation / Military
8. Development Schedule

Each domain assessment shall include:

- status;
- risk severity;
- confidence;
- material findings;
- supporting evidence;
- unresolved questions;
- recommended next diligence.

---

# 6. Risk Severity

Risk severity represents potential business impact.

It does not represent confidence.

## LOW

Issue is unlikely to materially affect the current development decision.

Typical response:

- record;
- monitor;
- no immediate escalation.

---

## MEDIUM

Issue may affect cost, schedule, design, or diligence but does not currently threaten the development thesis.

Typical response:

- targeted next-stage diligence.

---

## HIGH

Issue could materially affect viability, cost, schedule, or project configuration.

Typical response:

- focused diligence required before significant additional commitment.

A HIGH risk does not automatically require HOLD.

---

## CRITICAL

Issue could prevent the project from proceeding or invalidate the current development thesis.

Typical response:

- immediate escalation;
- block unconditional advancement.

---

# 7. Confidence

Confidence represents the reliability and completeness of evidence supporting a finding.

Allowed V1 values:

- LOW
- MEDIUM
- HIGH

---

## HIGH Confidence

Normally requires:

- authoritative or highly reliable source;
- current/relevant evidence;
- clear applicability;
- reproducible deterministic analysis where calculation is involved;
- no material unresolved contradiction.

---

## MEDIUM Confidence

May result from:

- authoritative evidence with applicability uncertainty;
- indirect but credible evidence;
- incomplete source coverage;
- aging evidence;
- screening-level public data.

---

## LOW Confidence

May result from:

- missing authoritative evidence;
- conflicting evidence;
- inference from indirect sources;
- material source limitations;
- uncertain applicability.

---

# 8. Risk and Confidence Must Remain Separate

Examples:

### Example A

Risk:

`HIGH`

Confidence:

`HIGH`

Meaning:

A material problem is well supported.

---

### Example B

Risk:

`HIGH`

Confidence:

`LOW`

Meaning:

A potentially material problem has been identified, but the evidence is insufficient.

This condition will often trigger additional investigation or HOLD.

---

### Example C

Risk:

`LOW`

Confidence:

`LOW`

Meaning:

No major problem has been found, but the evidence may be too weak to rely on.

Low apparent risk with poor evidence must not automatically be treated as good news.

---

# 9. Evidence Classes

Every material finding shall identify its evidence class.

## SOURCE_FACT

Direct statement or value obtained from a source.

Example:

An SPP record lists a project with a specified MW and POI.

---

## DERIVED_FACT

Result produced deterministically from source data.

Example:

There are 1,420 MW of active requests within the defined analysis scope.

---

## AGENT_INTERPRETATION

A reasoned interpretation of evidence.

Example:

Queue concentration and repeated study constraints indicate elevated screening-level interconnection risk.

---

## DEVELOPER_ASSUMPTION

Information supplied by the project developer but not independently established.

Example:

The developer assumes a specific substation will be the POI.

---

## UNRESOLVED

A material assertion that cannot yet be established.

Example:

County-level permit applicability could not be confirmed.

---

# 10. Source Authority

Sources shall be ranked by relevance and authority rather than by retrieval convenience.

Preferred order:

1. legally controlling or official authoritative source;
2. official agency/ISO publication;
3. official structured dataset;
4. official guidance;
5. credible secondary source;
6. indirect evidence.

A secondary source shall not silently override an applicable authoritative source.

---

# 11. Temporal Validity

Regulations, interconnection procedures, queue status, studies, and other changing sources must be evaluated as of the investigation date.

Where relevant, evidence shall retain:

- publication date;
- effective date;
- superseded date;
- retrieval date;
- version.

The system must avoid applying superseded regulatory/process information as current policy.

---

# 12. Decision Gates

Before recommendation synthesis, the following gates shall be evaluated.

---

## Gate G1 — Project Definition

Required:

- valid candidate polygon;
- capacity;
- technology;
- target COD.

Failure:

`HOLD / INVALID INPUT`

The system should request correction rather than continue unsupported analysis.

---

## Gate G2 — Minimum Domain Coverage

Minimum required domain investigations:

- resource;
- site/GIS;
- transmission/interconnection;
- environmental;
- permitting/regulatory;
- schedule.

If one or more material domains cannot be investigated:

evaluate whether the missing domain creates decision-critical uncertainty.

If yes:

`HOLD`

---

## Gate G3 — Fatal Condition

Question:

> Does sufficiently reliable evidence identify a condition incompatible with continued development under current assumptions?

If yes:

candidate for `DO NOT ADVANCE`.

CRITICAL findings with LOW confidence shall normally result in additional investigation or HOLD rather than DO NOT ADVANCE.

---

## Gate G4 — Critical Uncertainty

Question:

> Is a potentially fatal or highly material issue unresolved because evidence is insufficient?

If yes:

`HOLD`

unless bounded next-stage diligence can reasonably resolve the issue without disproportionate development exposure.

---

## Gate G5 — Manageable Material Risk

Question:

> Are identified HIGH risks real but manageable through clearly defined next diligence?

If yes:

candidate for:

`ADVANCE WITH CONDITIONS`

---

## Gate G6 — Evidence Sufficiency

Question:

> Is there enough reliable evidence to justify additional development spend?

If no:

`HOLD`

If yes:

continue recommendation synthesis.

---

## Gate G7 — Target COD

Question:

> Do currently known requirements, risks, and unresolved dependencies appear compatible with the target COD?

Possible outcomes:

- compatible;
- at risk;
- currently indeterminate;
- incompatible.

`Incompatible` may support DO NOT ADVANCE if strongly evidenced and the COD is a hard business constraint.

`Indeterminate` may support HOLD.

`At risk` may support ADVANCE WITH CONDITIONS.

---

# 13. Recommendation Logic

The following rules form the initial V1 recommendation policy.

They are deterministic guardrails around agent synthesis.

---

## Rule R1

If a confirmed fatal condition exists with sufficient evidence:

`DO NOT ADVANCE`

---

## Rule R2

If a potentially fatal or CRITICAL condition exists but evidence is insufficient:

`HOLD`

---

## Rule R3

If a decision-critical domain lacks sufficient evidence:

`HOLD`

---

## Rule R4

If no fatal condition exists and one or more HIGH risks require clearly defined diligence before major commitment:

`ADVANCE WITH CONDITIONS`

---

## Rule R5

If no fatal condition exists, evidence coverage is sufficient, material risks are manageable, and remaining work represents normal development diligence:

`ADVANCE`

---

# 14. Human Review Triggers

Human review is mandatory when any of the following occurs.

## HITL-001

Final V1 investment recommendation.

---

## HITL-002

CRITICAL risk.

---

## HITL-003

HIGH-risk conclusion with LOW confidence.

---

## HITL-004

Conflicting authoritative regulatory sources.

---

## HITL-005

Ambiguous legal or regulatory applicability that could materially affect the decision.

---

## HITL-006

Required official process cannot be completed programmatically.

Example:

official project-specific submission or authenticated regulatory workflow.

---

## HITL-007

Agent proposes DO NOT ADVANCE.

A human must review supporting evidence.

---

## HITL-008

Material conclusion depends primarily on indirect evidence.

---

# 15. Investigation Loop

The agent shall repeatedly evaluate:

1. What do I currently know?
2. What material uncertainties remain?
3. Could those uncertainties change the recommendation?
4. Is an approved tool available to reduce the uncertainty?
5. Is the expected evidence value worth another investigation?
6. Should a human be involved instead?
7. Can investigation stop?

Conceptually:

```text
PLAN
  ↓
INVESTIGATE
  ↓
ASSESS EVIDENCE
  ↓
ASSESS MATERIAL UNCERTAINTY
  ↓
 ┌─────────────────────────────┐
 │ Need more evidence?         │
 └─────────────────────────────┘
       │ yes              │ no
       ▼                  ▼
INVESTIGATE NEXT      SYNTHESIZE
       │                  │
       └────── loop ──────┘

