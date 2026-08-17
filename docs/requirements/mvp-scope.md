# Renewable Development Intelligence
## MVP Scope

**Version:** V1  
**Geography:** Western Oklahoma  
**Market:** SPP  
**Technology:** Onshore wind  
**Development stage:** Early-stage screening

---

# 1. MVP Scenario

The reference scenario is:

> A renewable developer has identified a candidate land area in western Oklahoma and is considering approximately a 250-MW wind project with a specified target COD. Determine whether the developer should invest additional development capital in the opportunity.

The candidate area is assumed to be sufficiently defined to provide a GIS polygon.

---

# 2. Required User Inputs

V1 requires:

- project identifier;
- candidate polygon;
- proposed capacity MW;
- technology = wind;
- target COD.

Optional:

- preliminary POI;
- candidate substation;
- turbine assumptions;
- known land constraints;
- developer notes;
- previously obtained diligence documents.

---

# 3. MVP Required Capabilities

## MVP-001 Project Intake

Create and persist a project definition.

---

## MVP-002 Investigation Planning

Create a project-specific investigation plan.

The agent must be able to add, remove, or reprioritize investigative tasks based on findings.

---

## MVP-003 Wind Resource Screening

Use public wind-resource data to generate screening-level resource metrics.

Required V1 outputs:

- representative wind-resource metrics;
- data coverage/quality;
- screening-level attractiveness;
- evidence references;
- limitations.

No bankable AEP claim.

---

## MVP-004 Candidate-Area GIS Analysis

Calculate:

- total candidate acreage;
- major excluded or constrained acreage;
- remaining screening-level usable acreage;
- percentage of candidate area affected by each major constraint.

Initial constraint classes should include, where data is available:

- wetlands;
- flood hazards;
- protected lands;
- slope/terrain;
- incompatible or material land-cover conditions.

All geometry calculations shall be deterministic.

---

## MVP-005 Transmission Proximity

Identify relevant public transmission corridors near the candidate area.

Required outputs:

- nearby transmission features;
- distance;
- nominal voltage where available;
- evidence quality.

Transmission proximity shall not be treated as proof of available interconnection capacity.

---

## MVP-006 SPP Queue Analytics

Retrieve and analyze relevant public SPP interconnection-request data.

V1 analytics should include:

- projects within a configurable geographic or POI relevance scope;
- active requested MW;
- technology mix;
- status;
- requested dates;
- project concentration;
- nearby wind competition;
- POI/substation patterns where available.

Deterministic calculations shall produce the queue metrics.

---

## MVP-007 SPP Study Investigation

The agent shall be able to investigate relevant SPP study documents when queue or POI findings justify additional investigation.

The agent may:

- identify relevant studies;
- retrieve documents;
- search within documents;
- extract evidence;
- interpret material constraints;
- follow references to related evidence.

This capability is intentionally agentic.

---

## MVP-008 Environmental Screening

Perform screening using authoritative public environmental data where realistically accessible.

Required initial topics:

- wetlands;
- flood hazard;
- protected lands;
- federally listed-species screening or available proxy evidence.

When an official process requires human interaction, the system shall request human input rather than automate around the process.

---

## MVP-009 Oklahoma Regulatory Screening

Identify material Oklahoma wind-development requirements relevant to the candidate project.

The system shall retain:

- authoritative source;
- requirement;
- applicability explanation;
- effective/version date where available;
- evidence citation.

---

## MVP-010 Local Requirement Investigation

Identify county or local requirements using authoritative public sources where available.

The system shall explicitly report when authoritative local information cannot be established.

---

## MVP-011 Aviation / Military Screening

Identify whether further aviation or military compatibility diligence appears necessary.

V1 shall not perform a final turbine-level FAA determination.

---

## MVP-012 Target-COD Assessment

Assess whether currently identified development conditions introduce material schedule risk relative to target COD.

The system shall identify the causes of schedule risk rather than produce unsupported precise schedule probabilities.

---

## MVP-013 Evidence Model

Persist evidence supporting material findings.

Evidence must support traceability from:

source
→ derived finding
→ risk
→ recommendation.

---

## MVP-014 Risk Register

Produce a project risk register covering at least:

- resource;
- site/GIS;
- interconnection;
- environmental;
- permitting/regulatory;
- aviation/military;
- schedule.

---

## MVP-015 Human Review

Support explicit human-review requests and human disposition.

The final recommendation shall require human review in V1.

---

## MVP-016 Development Recommendation

Generate exactly one current recommendation:

- ADVANCE;
- ADVANCE WITH CONDITIONS;
- HOLD;
- DO NOT ADVANCE.

The recommendation shall include:

- rationale;
- evidence;
- confidence;
- risks;
- unresolved questions;
- next diligence.

---

# 4. MVP Technical Scope

V1 architecture may use:

- Python;
- GeoPandas;
- Shapely;
- Rasterio;
- PyProj;
- Databricks;
- Delta Lake;
- Unity Catalog;
- ADLS Gen2;
- Azure OpenAI / Microsoft Foundry model deployments;
- LangGraph;
- Azure AI Search;
- MCP;
- MLflow;
- FastAPI;
- Terraform;
- GitHub Actions.

Technology inclusion is conditional on solving a demonstrated requirement.

---

# 5. MCP Scope

MCP is included in V1.

MCP shall expose coarse-grained business capabilities rather than every internal function.

Initial candidate capabilities:

- `wind.get_resource_summary`
- `gis.run_site_screen`
- `gis.find_transmission`
- `spp.search_queue`
- `spp.get_queue_context`
- `spp.search_studies`
- `spp.get_study_evidence`
- `environment.get_site_screen`
- `regulatory.search_requirements`

The final MCP tool contract shall be defined only after deterministic domain services exist.

---

# 6. A2A Scope

A2A is **not required for V1**.

V1 specialist behavior shall initially be implemented as:

- LangGraph nodes;
- LangGraph subgraphs;
- domain services.

A2A may be introduced only when a specialist becomes independently deployable and operationally independent.

Examples of possible future specialists:

- Interconnection Intelligence Agent;
- Environmental Diligence Agent;
- Permitting Intelligence Agent.

---

# 7. Model Routing Scope

V1 shall support simple explicit task-based model selection if multiple models are justified.

Examples:

- lower-cost model for structured extraction;
- stronger reasoning model for complex regulatory interpretation;
- stronger reasoning model for final synthesis.

V1 shall not implement an autonomous learned routing system.

Routing sophistication must be driven by measured evaluation results.

---

# 8. Evaluation Scope

Evaluation is mandatory in V1.

The evaluation harness shall eventually measure:

## Deterministic correctness

- geometry;
- spatial intersection;
- acreage;
- distance;
- queue aggregation;
- dates.

## Retrieval

- source selection;
- document recall;
- citation relevance;
- effective-document selection.

## Agent behavior

- investigation planning;
- tool selection;
- unnecessary tool use;
- missed material investigation;
- premature stopping;
- escalation correctness.

## Final recommendation

- factual correctness;
- evidence coverage;
- unsupported claims;
- identified risks;
- recommendation consistency;
- next-diligence quality.

---

# 9. Fine-Tuning Scope

Fine-tuning is excluded from V1.

Fine-tuning may be considered only when:

1. a repeatable failure is observed;
2. a representative evaluation dataset exists;
3. retrieval/prompting/tool improvements do not resolve it;
4. model substitution does not adequately resolve it;
5. the expected quality improvement justifies added lifecycle complexity.

---

# 10. Explicitly Out of Scope

The following are outside the MVP:

- solar development;
- battery storage;
- ERCOT;
- MISO;
- PJM;
- full United States coverage;
- proprietary ISO power-flow models;
- final transmission study;
- final interconnection cost;
- production-cost modeling;
- nodal-price forecasting;
- merchant revenue forecasting;
- PPA valuation;
- project finance model;
- IRR/NPV;
- detailed CAPEX;
- turbine micrositing;
- wake optimization;
- bankable energy yield;
- final permitting approval;
- legal opinions;
- land-title analysis;
- lease negotiation;
- construction engineering;
- procurement;
- operations.

Some may be future roadmap items, but none are required to call V1 complete.

---

# 11. V1 Demonstration Standard

The reference demonstration shall use a realistic candidate polygon in western Oklahoma and public industry data wherever possible.

The demonstration should visibly show the agent:

1. accepting the project definition;
2. forming an investigation plan;
3. invoking deterministic tools;
4. examining intermediate results;
5. deciding additional investigation is required;
6. retrieving documentary evidence;
7. revising risk conclusions;
8. detecting missing evidence;
9. escalating when necessary;
10. producing an evidence-backed recommendation.

A predetermined sequence of fixed API calls followed by LLM summarization does not satisfy the MVP.

---

# 12. Definition of Done

V1 is complete when:

- all required MVP domains have working data paths;
- deterministic analytics are tested;
- material claims are traceable;
- the agent dynamically investigates at least one domain based on intermediate evidence;
- HITL works;
- evaluation/regression tests exist;
- the final recommendation obeys the decision framework;
- infrastructure is reproducible;
- CI validates code and tests;
- historical investigation runs remain reproducible.

