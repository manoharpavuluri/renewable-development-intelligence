#!/usr/bin/env python3

"""
Produces one complete MLflow trace for a project run:

  project request
    -> project planner decisions   (replayed from the real,
                                     already-recorded audit trail
                                     and evidence ledger - not
                                     re-executed)
    -> capability executions       (replayed, same reasoning)
    -> evidence assessments        (replayed, same reasoning)
    -> gate synthesis (G1-G5)      (live)
    -> G6 COD feasibility          (live)
    -> G7 evidence sufficiency     (live)
    -> recommendation policy       (live)
    -> Foundry draft                (live - calls the real
                                     Foundry endpoint)
    -> HITL boundary                (live)

The investigation history is REPLAYED as spans from the completed
checkpoint rather than re-executed, because re-running already-
completed investigations would violate the project's own no-
replay guardrail. The synthesis stage is genuinely live because
it is designed to be re-run any time new evidence is added.

Tracking uses a local SQLite backend (no server required):
  mlflow ui --backend-store-uri sqlite:///data/runtime/mlflow.db
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import mlflow
from mlflow.entities import SpanType

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
    "RDI_THREAD_ID", "RDI-WOK-250-001:screening:v1"
)

PROJECT_JSON_PATH = Path(
    "data/scenarios/western_ok_250mw/project.json"
)

MLFLOW_TRACKING_URI = os.environ.get(
    "MLFLOW_TRACKING_URI",
    "sqlite:///data/runtime/mlflow.db",
)

MLFLOW_EXPERIMENT = "renewable-development-intelligence"


mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
mlflow.set_experiment(MLFLOW_EXPERIMENT)


register_implemented_capabilities()

config = {"configurable": {"thread_id": THREAD_ID}}

with open_checkpointer() as checkpointer:
    graph = build_investigation_graph(checkpointer=checkpointer)
    snapshot = graph.get_state(config)

if not snapshot.values:
    raise SystemExit(f"No saved state for thread {THREAD_ID!r}.")

if snapshot.next:
    raise SystemExit(
        "Thread is not at a clean boundary "
        f"(pending nodes: {snapshot.next!r})."
    )

state = snapshot.values

project_id = state["project_id"]
investigation_history = state.get("investigation_history", [])
evidence_ledger = state.get("evidence_ledger", [])
audit_events = state.get("audit_events", [])
project_domain_outcomes = (
    state.get("project_domain_outcomes") or {}
)

ledger_by_task = {
    entry.get("task_id"): entry for entry in evidence_ledger
}

planner_events_by_action = {}

for event in audit_events:

    if event.get("event_type") in {
        "PROJECT_INVESTIGATION_SELECTED",
        "PLANNER_DECISION_VALIDATED",
    }:

        action_id = event.get("action_id")

        if action_id:
            planner_events_by_action.setdefault(
                action_id, []
            ).append(event)


target_cod = json.loads(
    PROJECT_JSON_PATH.read_text(encoding="utf-8")
)["target_cod"]


with mlflow.start_span(
    name="renewable_development_screening",
    span_type=SpanType.AGENT,
) as root_span:

    root_span.set_inputs(
        {
            "project_id": project_id,
            "thread_id": THREAD_ID,
            "target_cod": target_cod,
        }
    )

    mlflow.update_current_trace(
        tags={
            "project_id": project_id,
            "thread_id": THREAD_ID,
        }
    )


    # --------------------------------------------------------
    # Replay: project planner decisions + capability executions
    # + evidence assessments, one span group per investigation,
    # from the real recorded history.
    # --------------------------------------------------------

    with mlflow.start_span(
        name="investigation_history_replay",
        span_type=SpanType.CHAIN,
    ) as replay_span:

        replay_span.set_inputs(
            {"investigation_count": len(investigation_history)}
        )

        for item in investigation_history:

            task_id = item.get("task_id")
            capability = item.get("capability")
            domain = item.get("domain")

            planner_events = planner_events_by_action.get(
                task_id, []
            )

            selection_mode = None

            for event in planner_events:
                if "selection_mode" in event:
                    selection_mode = event["selection_mode"]

            with mlflow.start_span(
                name=f"plan:{task_id}",
                span_type=SpanType.AGENT,
            ) as plan_span:

                plan_span.set_inputs({"task_id": task_id})

                plan_span.set_outputs(
                    {
                        "selected_capability": capability,
                        "selection_mode": selection_mode,
                    }
                )

                plan_span.set_attribute("domain", domain)

            with mlflow.start_span(
                name=f"execute:{capability}",
                span_type=SpanType.TOOL,
            ) as exec_span:

                exec_span.set_inputs(
                    {"task_id": task_id, "capability": capability}
                )

                exec_span.set_attribute("domain", domain)

                result = item.get("result", {})

                exec_span.set_outputs(
                    {
                        "executed": result.get("executed"),
                        "evidence_quality": result.get(
                            "evidence_quality"
                        ),
                    }
                )

            ledger_entry = ledger_by_task.get(task_id)

            if ledger_entry:

                with mlflow.start_span(
                    name=f"assess:{task_id}",
                    span_type=SpanType.EVALUATOR,
                ) as assess_span:

                    assess_span.set_outputs(
                        {
                            "gate_id": ledger_entry.get(
                                "gate_id"
                            ),
                            "status": ledger_entry.get(
                                "status"
                            ),
                            "decision_confidence": (
                                ledger_entry.get(
                                    "decision_confidence"
                                )
                            ),
                        }
                    )

        replay_span.set_outputs(
            {
                "domains_recorded": sorted(
                    project_domain_outcomes.keys()
                )
            }
        )


    # --------------------------------------------------------
    # Live: gate synthesis (G1-G5)
    # --------------------------------------------------------

    with mlflow.start_span(
        name="gate_synthesis", span_type=SpanType.CHAIN
    ) as gate_span:

        gate_syntheses = [
            g.to_dict()
            for g in synthesize_all_gates(
                project_domain_outcomes=(
                    project_domain_outcomes
                ),
                evidence_ledger=evidence_ledger,
            )
        ]

        gate_span.set_outputs(
            {
                gate["gate_id"]: {
                    "status": gate["status"],
                    "confidence": gate["confidence"],
                    "material_risk_count": len(
                        gate["material_risks"]
                    ),
                }
                for gate in gate_syntheses
            }
        )


    # --------------------------------------------------------
    # Live: G6 COD feasibility
    # --------------------------------------------------------

    with mlflow.start_span(
        name="g6_cod_feasibility", span_type=SpanType.TASK
    ) as g6_span:

        cod_feasibility = assess_cod_feasibility(
            target_cod=target_cod,
            gate_syntheses=gate_syntheses,
        )

        g6_span.set_outputs(
            {
                "status": cod_feasibility["status"],
                "years_to_target_cod": cod_feasibility[
                    "years_to_target_cod"
                ],
            }
        )


    # --------------------------------------------------------
    # Live: G7 evidence sufficiency
    # --------------------------------------------------------

    with mlflow.start_span(
        name="g7_evidence_sufficiency",
        span_type=SpanType.EVALUATOR,
    ) as g7_span:

        evidence_sufficiency = assess_evidence_sufficiency(
            gate_syntheses=gate_syntheses
        )

        g7_span.set_outputs(
            {"status": evidence_sufficiency["status"]}
        )


    # --------------------------------------------------------
    # Live: recommendation policy (deterministic admissible set)
    # --------------------------------------------------------

    with mlflow.start_span(
        name="recommendation_policy",
        span_type=SpanType.GUARDRAIL,
    ) as policy_span:

        policy = determine_allowed_categories(
            evidence_sufficiency=evidence_sufficiency,
            gate_syntheses=gate_syntheses,
        )

        allowed_categories = policy["allowed_categories"]

        policy_span.set_outputs(
            {"allowed_categories": allowed_categories}
        )


    # --------------------------------------------------------
    # Live: Foundry-drafted recommendation
    # --------------------------------------------------------

    with mlflow.start_span(
        name="recommendation_draft", span_type=SpanType.LLM
    ) as draft_span:

        draft_span.set_inputs(
            {"allowed_categories": allowed_categories}
        )

        draft = draft_recommendation(
            project_id=project_id,
            gate_syntheses=gate_syntheses,
            cod_feasibility=cod_feasibility,
            evidence_sufficiency=evidence_sufficiency,
            allowed_categories=allowed_categories,
        )

        validate_recommendation(
            draft=draft, allowed_categories=allowed_categories
        )

        draft_span.set_outputs(
            {
                "recommendation": draft.recommendation,
                "confidence": draft.confidence,
                "evidence_quality": draft.evidence_quality,
            }
        )


    # --------------------------------------------------------
    # HITL boundary
    # --------------------------------------------------------

    with mlflow.start_span(
        name="hitl_boundary", span_type=SpanType.GUARDRAIL
    ) as hitl_span:

        hitl_span.set_outputs(
            {
                "status": "DRAFT_PENDING_HUMAN_REVIEW",
                "human_approved": False,
            }
        )

    root_span.set_outputs(
        {
            "recommendation": draft.recommendation,
            "cod_feasibility_status": cod_feasibility["status"],
            "evidence_sufficiency_status": (
                evidence_sufficiency["status"]
            ),
            "human_approved": False,
        }
    )

    mlflow.update_current_trace(
        tags={
            "recommendation": draft.recommendation,
            "cod_feasibility_status": (
                cod_feasibility["status"]
            ),
            "human_approved": "false",
        }
    )


trace_id = mlflow.get_last_active_trace_id()


print("=== TRACE LOGGED ===")
print("Tracking URI:", MLFLOW_TRACKING_URI)
print("Experiment:", MLFLOW_EXPERIMENT)
print("Trace ID:", trace_id)
print()
print("View with: mlflow ui --backend-store-uri", MLFLOW_TRACKING_URI)
