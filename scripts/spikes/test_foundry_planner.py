#!/usr/bin/env python3

import json
import os
from typing import Literal

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from pydantic import BaseModel, ConfigDict


class PlannerDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    selected_action_id: Literal[
        "INT-FU-002",
        "INV-003",
        "INV-002",
    ]

    selected_capability: Literal[
        "spp.compare_model_cases",
        "gis.analyze_terrain",
        "wind.analyze_candidate_resource",
    ]

    reason: str

    confidence: Literal[
        "LOW",
        "MEDIUM",
        "HIGH",
    ]


ADMISSIBLE_ACTIONS = {
    "INT-FU-002": "spp.compare_model_cases",
    "INV-003": "gis.analyze_terrain",
    "INV-002": "wind.analyze_candidate_resource",
}


planner_context = {
    "project": {
        "project_id": "RDI-WOK-250-001",
        "technology": "onshore_wind",
        "capacity_mw": 250,
        "market": "SPP",
        "target_cod": "2031-12-31",
    },

    "development_gates": [
        {
            "gate_id": "G2",
            "domain": "transmission_interconnection",
            "materiality": "CRITICAL",
            "status": "UNRESOLVED",
        },
        {
            "gate_id": "G1",
            "domain": "resource_physical_site",
            "materiality": "HIGH",
            "status": "UNRESOLVED",
        },
        {
            "gate_id": "G7",
            "domain": "evidence_sufficiency",
            "materiality": "CRITICAL",
            "status": "UNRESOLVED",
        },
    ],

    "completed_investigations": [
        {
            "task_id": "INV-001",
            "capability": "spp.transmission_context",
            "finding": (
                "TATONGA7 has lower HCT constraint "
                "exposure than WWRDEHV7 among the two "
                "tested POIs."
            ),
            "confidence": "MEDIUM",
        },
        {
            "task_id": "INT-FU-001",
            "capability": "spp.analyze_precedent_study",
            "finding": (
                "GEN-2026-PR2 provides Tatonga precedent "
                "evidence, but applicability to the "
                "250-MW candidate is LOW."
            ),
        },
    ],

    "unresolved_evidence": [
        "Only one SPP HCT model case has been evaluated.",
        "Candidate-specific interconnection feasibility has not been established.",
        "Candidate upgrade cost has not been established.",
        "Terrain analysis remains unresolved.",
        "Long-term candidate-wide wind resource analysis remains unresolved.",
    ],

    "admissible_actions": [
        {
            "action_id": "INT-FU-002",
            "capability": "spp.compare_model_cases",
            "domain": "interconnection",
            "purpose": (
                "Test whether TATONGA7 remains "
                "screening-preferred under another "
                "relevant SPP HCT model case."
            ),
        },
        {
            "action_id": "INV-003",
            "capability": "gis.analyze_terrain",
            "domain": "terrain",
            "purpose": (
                "Evaluate slope and terrain constraints "
                "for the candidate area."
            ),
        },
        {
            "action_id": "INV-002",
            "capability": "wind.analyze_candidate_resource",
            "domain": "wind_resource",
            "purpose": (
                "Assess candidate wind-resource evidence "
                "beyond the existing single-year point screen."
            ),
        },
    ],
}


instructions = """
You are the investigation planner for an early-stage
renewable-development screening system.

Select exactly one action from the supplied admissible actions.

Rules:
1. Never invent an action or capability.
2. Do not alter deterministic facts.
3. Do not declare a development gate satisfied.
4. Do not claim interconnection feasibility.
5. Do not invent upgrade cost.
6. Prefer resolving material blocking uncertainty.
7. Consider information gain and evidence already consumed.
8. The application decides whether a capability is executable.
""".strip()


schema = {
    "type": "object",
    "properties": {
        "selected_action_id": {
            "type": "string",
            "enum": [
                "INT-FU-002",
                "INV-003",
                "INV-002",
            ],
        },
        "selected_capability": {
            "type": "string",
            "enum": [
                "spp.compare_model_cases",
                "gis.analyze_terrain",
                "wind.analyze_candidate_resource",
            ],
        },
        "reason": {
            "type": "string",
        },
        "confidence": {
            "type": "string",
            "enum": [
                "LOW",
                "MEDIUM",
                "HIGH",
            ],
        },
    },
    "required": [
        "selected_action_id",
        "selected_capability",
        "reason",
        "confidence",
    ],
    "additionalProperties": False,
}


endpoint = os.environ["FOUNDRY_PROJECT_ENDPOINT"]
model = os.environ["FOUNDRY_MODEL_NAME"]


with (
    DefaultAzureCredential() as credential,
    AIProjectClient(
        endpoint=endpoint,
        credential=credential,
    ) as project,
):

    with project.get_openai_client() as client:

        response = client.responses.create(
            model=model,
            instructions=instructions,
            input=json.dumps(
                planner_context,
                indent=2,
            ),
            text={
                "format": {
                    "type": "json_schema",
                    "name": "investigation_planner_decision",
                    "schema": schema,
                    "strict": True,
                }
            },
        )


parsed = json.loads(
    response.output_text
)

decision = PlannerDecision.model_validate(
    parsed,
    strict=True,
)


expected_capability = ADMISSIBLE_ACTIONS.get(
    decision.selected_action_id
)

if expected_capability is None:
    raise RuntimeError(
        "POLICY REJECTED: unknown action."
    )

if (
    decision.selected_capability
    != expected_capability
):
    raise RuntimeError(
        "POLICY REJECTED: invalid action/capability mapping. "
        f"{decision.selected_action_id} must map to "
        f"{expected_capability}, not "
        f"{decision.selected_capability}."
    )


print(
    "=== FOUNDRY INVESTIGATION PLANNER ==="
)

print(
    "Response ID:",
    response.id,
)

print(
    "Model deployment:",
    model,
)

print()
print(
    "=== STRUCTURED OUTPUT ==="
)

print(
    json.dumps(
        parsed,
        indent=2,
    )
)

print()
print(
    "Pydantic validation: PASS"
)

print(
    "Policy validation: PASS"
)

print(
    "Mapping:",
    (
        f"{decision.selected_action_id}"
        f" -> "
        f"{decision.selected_capability}"
    ),
)
