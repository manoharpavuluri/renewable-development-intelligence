#!/usr/bin/env python3

"""
Post-investigation synthesis: aggregates the completed
per-domain investigation results into a gate-level rollup
(G1-G5), a G6 COD-feasibility assessment, a G7 evidence-
sufficiency assessment, and a DRAFT investment recommendation.

This does NOT finalize a recommendation. Per the project design,
the draft always carries human_review_required=True and must be
approved, modified, or rejected by a human before it is final.

Reads the completed investigation-graph checkpoint; does not
mutate it and does not execute any further investigations.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from renewable_intelligence.graph.investigation_graph import (
    build_investigation_graph,
)
from renewable_intelligence.persistence.checkpointing import (
    open_checkpointer,
)
from renewable_intelligence.tools.bootstrap import (
    register_implemented_capabilities,
)
from renewable_intelligence.synthesis.gate_synthesis import (
    synthesize_all_gates,
)
from renewable_intelligence.synthesis.schedule_feasibility import (
    assess_cod_feasibility,
)
from renewable_intelligence.synthesis.evidence_sufficiency import (
    assess_evidence_sufficiency,
)
from renewable_intelligence.synthesis.recommendation_policy import (
    determine_allowed_categories,
)
from renewable_intelligence.synthesis.recommendation_drafter import (
    draft_recommendation,
    validate_recommendation,
)


THREAD_ID = os.environ.get(
    "RDI_THREAD_ID",
    "RDI-WOK-250-001:screening:v1",
)

PROJECT_JSON_PATH = Path(
    "data/scenarios/western_ok_250mw/project.json"
)

RESULT_DIR = os.environ.get("RESULT_DIR")


register_implemented_capabilities()

config = {"configurable": {"thread_id": THREAD_ID}}


with open_checkpointer() as checkpointer:

    graph = build_investigation_graph(
        checkpointer=checkpointer
    )

    snapshot = graph.get_state(config)


if not snapshot.values:
    raise SystemExit(f"No saved state for thread {THREAD_ID!r}.")

if snapshot.next:
    raise SystemExit(
        "Thread is not at a clean boundary "
        f"(pending nodes: {snapshot.next!r}). Resume or "
        "complete the investigation graph first."
    )


project_domain_outcomes = (
    snapshot.values.get("project_domain_outcomes") or {}
)

evidence_ledger = snapshot.values.get("evidence_ledger", [])

project_id = snapshot.values.get("project_id")


if not project_domain_outcomes:
    raise SystemExit(
        "project_domain_outcomes is empty; nothing to "
        "synthesize."
    )


project_config = json.loads(
    PROJECT_JSON_PATH.read_text(encoding="utf-8")
)

target_cod = project_config["target_cod"]


# ============================================================
# Gate synthesis (G1-G5)
# ============================================================

gate_syntheses = [
    gate.to_dict()
    for gate in synthesize_all_gates(
        project_domain_outcomes=project_domain_outcomes,
        evidence_ledger=evidence_ledger,
    )
]


# ============================================================
# G6 — COD feasibility
# ============================================================

cod_feasibility = assess_cod_feasibility(
    target_cod=target_cod,
    gate_syntheses=gate_syntheses,
)


# ============================================================
# G7 — Evidence sufficiency
# ============================================================

evidence_sufficiency = assess_evidence_sufficiency(
    gate_syntheses=gate_syntheses,
)


# ============================================================
# Recommendation policy + draft
# ============================================================

policy = determine_allowed_categories(
    evidence_sufficiency=evidence_sufficiency,
    gate_syntheses=gate_syntheses,
)

allowed_categories = policy["allowed_categories"]


draft = draft_recommendation(
    project_id=project_id,
    gate_syntheses=gate_syntheses,
    cod_feasibility=cod_feasibility,
    evidence_sufficiency=evidence_sufficiency,
    allowed_categories=allowed_categories,
)

validate_recommendation(
    draft=draft,
    allowed_categories=allowed_categories,
)


# ============================================================
# Assemble output
# ============================================================

output = {
    "project_id": project_id,
    "target_cod": target_cod,
    "gate_synthesis": gate_syntheses,
    "cod_feasibility": cod_feasibility,
    "evidence_sufficiency": evidence_sufficiency,
    "recommendation_policy": policy,
    "recommendation_draft": {
        **draft.model_dump(),
        "status": "DRAFT_PENDING_HUMAN_REVIEW",
        "human_review_required": True,
        "human_approved": False,
    },
}


print("=== GATE SYNTHESIS ===")
for gate in gate_syntheses:
    print(
        f"{gate['gate_id']} | {gate['status']:<24} | "
        f"{gate['materiality']:<8} | confidence={gate['confidence']:<6} | "
        f"{gate['name']}"
    )
    for risk in gate["material_risks"]:
        print(f"    [{risk['severity']}] {risk['description']}")

print()
print("=== G6: COD FEASIBILITY ===")
print("Status:", cod_feasibility["status"])
print("Years to target COD:", cod_feasibility["years_to_target_cod"])
print("Reason:", cod_feasibility["reason"])

print()
print("=== G7: EVIDENCE SUFFICIENCY ===")
print("Status:", evidence_sufficiency["status"])
print("Reason:", evidence_sufficiency["reason"])

print()
print("=== RECOMMENDATION POLICY ===")
print("Allowed categories:", allowed_categories)
print("Reason:", policy["reason"])

print()
print("=== DRAFT RECOMMENDATION (requires human review) ===")
print("Recommendation:", draft.recommendation)
print("Confidence:", draft.confidence)
print("Evidence quality:", draft.evidence_quality)
print()
print("Rationale:")
print(draft.rationale)
print()
print("Critical conditions:")
for item in draft.critical_conditions:
    print("-", item)
print()
print("Unresolved risks:")
for item in draft.unresolved_risks:
    print("-", item)
print()
print("Next diligence:")
for item in draft.next_diligence:
    print("-", item)


if RESULT_DIR:

    output_path = (
        Path(RESULT_DIR)
        / "screening"
        / "project_assessment_draft.json"
    )

    output_path.write_text(
        json.dumps(output, indent=2, default=str),
        encoding="utf-8",
    )

    print()
    print("Output:", output_path)
