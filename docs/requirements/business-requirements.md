# Renewable Development Intelligence
## Business Requirements

**Status:** Baseline V1  
**Initial market:** Western Oklahoma / Southwest Power Pool (SPP)  
**Initial technology:** Utility-scale onshore wind  
**Primary use case:** Early-stage renewable development screening

---

## 1. Business Problem

Renewable developers routinely identify candidate land areas before enough information exists to justify major development expenditure.

A candidate wind opportunity may initially be described by only:

- candidate land area;
- approximate project capacity;
- technology;
- target commercial operation date (COD);
- optionally, a preliminary point of interconnection or other developer assumptions.

Before committing significant development capital, the developer must investigate multiple interacting domains, including:

- wind resource;
- buildable land;
- transmission proximity;
- interconnection conditions;
- competing generation requests;
- environmental constraints;
- flood and terrain constraints;
- federal, state, and local requirements;
- aviation and military compatibility;
- schedule feasibility;
- material evidence gaps.

Today this investigation is fragmented across GIS systems, public datasets, regulatory documents, interconnection studies, spreadsheets, consultants, and subject-matter experts.

The purpose of Renewable Development Intelligence is to coordinate that investigation and produce an evidence-backed recommendation about whether additional development investment is warranted.

---

## 2. Business Objective

Given a candidate renewable-development opportunity, determine:

> Should the developer invest additional time and capital to advance this opportunity, and what diligence should occur next?

The system must provide one of four recommendations:

1. **ADVANCE**
2. **ADVANCE WITH CONDITIONS**
3. **HOLD**
4. **DO NOT ADVANCE**

The recommendation must be supported by traceable evidence and accompanied by:

- material positive factors;
- material risks;
- unresolved questions;
- confidence assessment;
- recommended next diligence;
- human-review requirements.

---

## 3. Primary User

### Renewable Development Lead

Representative titles include:

- Director of Development;
- VP of Development;
- Senior Development Manager;
- Project Development Manager.

The primary user is responsible for determining whether a candidate project warrants additional development expenditure.

---

## 4. Supporting Users

The primary user may rely on specialists including:

- interconnection engineers;
- transmission planners;
- GIS analysts;
- environmental specialists;
- permitting specialists;
- wind-resource engineers;
- land teams;
- legal counsel;
- project finance teams.

The system is not intended to replace these specialists.

It is intended to determine:

- when specialist review is needed;
- what evidence should be supplied to the specialist;
- what questions need to be answered.

---

## 5. Required Project Inputs

The minimum V1 project definition shall contain:

### BR-IN-001 Candidate Area

A geospatial polygon representing the candidate project area.

Accepted V1 formats may include:

- GeoJSON;
- GeoPackage;
- shapefile after ingestion/conversion.

### BR-IN-002 Technology

For V1:

`wind`

### BR-IN-003 Target Capacity

Proposed project capacity in MW.

Example:

`250 MW`

### BR-IN-004 Target COD

Target commercial operation date.

Example:

`2030-12-31`

### BR-IN-005 Project Identifier

Unique project name or identifier.

---

## 6. Optional Project Inputs

The system should support optional developer assumptions including:

- preliminary point of interconnection;
- target substation;
- turbine capacity;
- hub height;
- rotor diameter;
- preferred turbine model;
- known land-control boundaries;
- known exclusion areas;
- developer-defined setbacks;
- known environmental studies;
- previously completed interconnection analysis;
- project notes.

Absence of optional information must not prevent initial screening.

The system must identify where missing information materially limits its conclusion.

---

# 7. Required Analysis Domains

The V1 system shall investigate the following domains.

## BR-DOM-001 Wind Resource

Determine whether public wind-resource evidence supports continued development investigation.

The system may assess:

- wind-speed characteristics;
- temporal resource characteristics;
- directional characteristics where useful;
- screening-level generation potential;
- resource uncertainty.

The system must not represent public screening data as a bankable energy assessment.

---

## BR-DOM-002 Site and GIS Constraints

Determine the amount and distribution of potentially usable land after screening for material spatial constraints.

Potential considerations include:

- candidate acreage;
- wetlands;
- flood hazards;
- protected lands;
- terrain and slope;
- incompatible land cover;
- major infrastructure;
- known exclusion areas;
- configurable screening buffers.

The result shall be reproducible from deterministic GIS calculations.

---

## BR-DOM-003 Transmission Context

Determine the screening-level transmission context surrounding the candidate area.

Analysis may include:

- nearby transmission corridors;
- nominal voltage where available;
- distance to relevant infrastructure;
- nearby generation/interconnection activity;
- candidate interconnection areas.

Public transmission information must not be represented as an authoritative power-flow model.

---

## BR-DOM-004 SPP Interconnection

Investigate interconnection conditions that could materially affect project viability or schedule.

Analysis may include:

- relevant active generation requests;
- nearby or related points of interconnection;
- queue concentration;
- project status;
- historical or current studies;
- network constraints discussed in studies;
- identified network upgrades;
- competing development activity;
- relevant SPP process requirements.

The system must distinguish:

- observed public facts;
- derived analytics;
- agent interpretation;
- unknown interconnection outcomes.

The system must not claim a definitive interconnection cost or interconnection outcome without authoritative project-specific evidence.

---

## BR-DOM-005 Environmental Screening

Identify environmental conditions that may materially affect development.

V1 may include:

- wetlands;
- flood hazards;
- protected lands;
- federally listed species screening;
- habitat-related concerns where public data exists;
- known environmental review requirements.

The system shall distinguish desktop screening from formal environmental clearance.

---

## BR-DOM-006 Permitting and Regulatory

Determine what known federal, Oklahoma state, and relevant local requirements may affect the candidate project.

The system shall:

- identify applicable authorities;
- identify relevant requirements;
- retain source and effective-date evidence;
- distinguish binding requirements from guidance;
- identify uncertain or unavailable local requirements;
- escalate ambiguous regulatory interpretation when material.

The system must not provide legal advice.

---

## BR-DOM-007 Aviation and Military Compatibility

Identify screening-level aviation and military compatibility risks.

The system may identify:

- nearby airports;
- likely FAA review requirements;
- known military compatibility considerations;
- need for turbine-specific future review.

Desktop analysis must not be represented as an FAA determination.

---

## BR-DOM-008 Development Schedule

Assess whether known development activities and material uncertainties appear compatible with the target COD.

The schedule assessment may consider:

- current date;
- target COD;
- interconnection process stage;
- unresolved environmental work;
- permitting requirements;
- known development dependencies;
- major unresolved risks.

The system shall distinguish deterministic date calculations from probabilistic or judgment-based schedule conclusions.

---

# 8. Required System Behavior

## BR-FR-001 Investigation Planning

The system shall create an investigation plan based on:

- project attributes;
- geography;
- available evidence;
- unresolved questions.

The investigation plan must not be a permanently fixed workflow.

---

## BR-FR-002 Dynamic Investigation

During execution, the system shall be capable of deciding:

- what to investigate next;
- which approved tool to invoke;
- which source is appropriate;
- whether additional evidence is required;
- whether investigation can stop.

---

## BR-FR-003 Deterministic Computation

Numerical and geospatial calculations shall be performed by deterministic software rather than by the language model whenever practical.

Examples include:

- distance;
- acreage;
- spatial intersection;
- buffering;
- coordinate conversion;
- slope;
- queue aggregation;
- date arithmetic;
- percentages;
- counts.

---

## BR-FR-004 Evidence Collection

Every material conclusion shall be linked to evidence.

Evidence shall preserve, where applicable:

- source authority;
- source URL or identifier;
- retrieval timestamp;
- publication date;
- effective date;
- document/version identifier;
- source location such as page/section;
- source hash;
- transformation provenance.

---

## BR-FR-005 Evidence Classification

The system shall distinguish at least:

1. **Source fact**
2. **Deterministically derived fact**
3. **Agent interpretation**
4. **Developer assumption**
5. **Unresolved assertion**

These categories must not be silently mixed.

---

## BR-FR-006 Risk Identification

The system shall identify material risks by domain and assign a qualitative severity:

- LOW;
- MEDIUM;
- HIGH;
- CRITICAL.

Severity shall represent business materiality, not model confidence.

---

## BR-FR-007 Confidence

Material findings shall include a confidence assessment based on evidence quality and completeness.

Confidence shall be represented separately from risk severity.

A HIGH-risk finding may have LOW confidence.

---

## BR-FR-008 Evidence Gaps

The system shall explicitly identify missing evidence when the absence could materially affect the recommendation.

The system shall not fill missing evidence with unsupported assumptions.

---

## BR-FR-009 Human Escalation

The system shall pause or request human review when predefined escalation conditions occur.

Examples include:

- high materiality with insufficient evidence;
- conflicting authoritative sources;
- unavailable required regulatory evidence;
- ambiguous legal/regulatory interpretation;
- official filing or portal action requiring a person;
- major recommendation based primarily on indirect evidence.

---

## BR-FR-010 Development Recommendation

The system shall produce:

- recommendation;
- recommendation rationale;
- positive factors;
- material risks;
- unresolved questions;
- evidence references;
- confidence;
- required human review;
- recommended next diligence;
- recommended actions not yet justified.

---

## BR-FR-011 Reproducibility

A completed investigation shall retain sufficient information to answer:

> Why did the system make this recommendation using the information available at that time?

---

## BR-FR-012 Re-evaluation

The architecture shall support re-running a project when:

- source data changes;
- regulations change;
- target COD changes;
- project capacity changes;
- candidate area changes;
- new diligence becomes available.

New runs must not silently overwrite historical conclusions.

---

# 9. Agentic AI Requirements

## BR-AG-001

The language model shall not merely summarize outputs from a predetermined pipeline.

---

## BR-AG-002

The agent shall determine which investigations are necessary for the specific project.

---

## BR-AG-003

The agent shall be able to change its investigation plan based on intermediate findings.

Example:

SPP queue analysis identifies a potentially relevant POI.

The agent may then decide to:

1. locate studies associated with the area;
2. retrieve relevant study documents;
3. examine network constraints;
4. investigate related studies;
5. update interconnection risk.

---

## BR-AG-004

The agent shall select from explicitly approved tools.

It shall not have unrestricted access to arbitrary execution capabilities.

---

## BR-AG-005

The agent shall evaluate whether gathered evidence is sufficient for a material conclusion.

---

## BR-AG-006

The agent shall distinguish uncertainty from absence of evidence.

---

## BR-AG-007

The agent shall cite evidence for material claims.

---

## BR-AG-008

The agent shall escalate rather than fabricate conclusions when authoritative information is unavailable.

---

## BR-AG-009

The final investment recommendation shall require human review in V1.

---

# 10. Explicit Non-Goals

V1 shall not claim to produce:

- bankable annual energy production;
- final turbine layout;
- micrositing;
- final wake-loss modeling;
- final electrical design;
- detailed collector-system design;
- definitive interconnection cost;
- power-flow or stability study results;
- formal SPP interconnection approval;
- environmental clearance;
- legal opinion;
- title opinion;
- executed land control;
- FAA determination;
- final project economics;
- financing recommendation.

These capabilities require data, models, processes, or professional expertise outside the V1 public-data screening use case.

---

# 11. Key Business Assumptions

## BR-ASM-001

The project begins before substantial development capital has been committed.

## BR-ASM-002

The user has identified a candidate land area.

## BR-ASM-003

Public data is sufficient for a meaningful screening recommendation but not final development approval.

## BR-ASM-004

Unknown information is itself a meaningful development risk when it prevents a decision.

## BR-ASM-005

The value of the system is not only identifying risks.

It must identify the **next economically rational diligence action**.

---

# 12. V1 Success Criteria

A V1 implementation is successful when, for a western Oklahoma wind candidate, it can:

1. ingest a candidate polygon, capacity, and target COD;
2. generate a project-specific investigation plan;
3. execute deterministic wind, GIS, and queue analysis;
4. retrieve and interpret relevant authoritative documents;
5. adapt its investigation based on intermediate results;
6. identify material risks;
7. identify evidence gaps;
8. distinguish facts, calculations, assumptions, and interpretations;
9. trigger human review when required;
10. produce an evidence-backed development recommendation;
11. reproduce the evidence and reasoning inputs for the recommendation;
12. pass a defined regression/evaluation suite.

---

# 13. Business Success Measure

The primary success criterion is not:

> Did the model produce an impressive report?

It is:

> Did the system correctly identify whether further development investment is warranted, identify the material reasons why, and identify the next diligence necessary to improve the decision?

