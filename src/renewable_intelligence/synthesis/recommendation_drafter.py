from __future__ import annotations

import json
import os
from typing import Any, Literal

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from pydantic import BaseModel, ConfigDict


CAPABILITY_NAME = "recommendation.draft"


class RecommendationDraft(BaseModel):

    model_config = ConfigDict(extra="forbid")

    recommendation: Literal[
        "ADVANCE",
        "ADVANCE_WITH_CONDITIONS",
        "HOLD",
        "DO_NOT_ADVANCE",
    ]

    rationale: str

    critical_conditions: list[str]

    unresolved_risks: list[str]

    next_diligence: list[str]

    confidence: Literal["LOW", "MEDIUM", "HIGH"]

    evidence_quality: Literal["LOW", "MEDIUM", "HIGH"]


INSTRUCTIONS = """
You are drafting an EARLY-STAGE SCREENING recommendation for a
renewable-development investment-diligence system. This draft
requires human review and approval before it is final; you are
not authorizing capital, only synthesizing the evidence already
assembled by deterministic screening capabilities.

You may select `recommendation` ONLY from the supplied
allowed_categories. You may never select a category outside that
list, and the deterministic policy that produced that list is
not open to your interpretation.

Rules:
1. Ground every statement in the supplied gate_syntheses,
   cod_feasibility, and evidence_sufficiency data. Do not invent
   facts, figures, acreages, distances, species, statutes, or
   dates not present in the input.
2. Do not claim regulatory, legal, environmental, or FAA
   clearance. Every domain in this project resolved to
   HUMAN_DILIGENCE_REQUIRED; treat that as a hard constraint on
   your language, not a formality to smooth over.
3. Do not state or imply a specific permit fee, approval
   timeline, or probability of approval beyond what is already
   present in cod_feasibility's known_durations.
4. critical_conditions should be the specific, concrete items
   that must be resolved before capital commitment increases
   (e.g. "obtain IPaC official species list", "confirm land
   control via lease or option", "complete Section 106 review
   for the intersecting NRHP resource").
5. unresolved_risks should summarize the HIGH/CRITICAL material
   risks and evidence gaps already identified, in your own
   words, without softening them.
6. next_diligence should be concrete, actionable next steps, not
   vague restatements of "more diligence needed".
7. confidence and evidence_quality describe YOUR assessment of
   the underlying evidence base as a whole, using the same
   LOW/MEDIUM/HIGH vocabulary already used throughout this
   project; they are not a claim about the project's investment
   merit.
""".strip()


SCHEMA = {
    "type": "object",
    "properties": {
        "recommendation": {
            "type": "string",
        },
        "rationale": {"type": "string"},
        "critical_conditions": {
            "type": "array",
            "items": {"type": "string"},
        },
        "unresolved_risks": {
            "type": "array",
            "items": {"type": "string"},
        },
        "next_diligence": {
            "type": "array",
            "items": {"type": "string"},
        },
        "confidence": {"type": "string"},
        "evidence_quality": {"type": "string"},
    },
    "required": [
        "recommendation",
        "rationale",
        "critical_conditions",
        "unresolved_risks",
        "next_diligence",
        "confidence",
        "evidence_quality",
    ],
    "additionalProperties": False,
}


def draft_recommendation(
    *,
    project_id: str,
    gate_syntheses: list[dict[str, Any]],
    cod_feasibility: dict[str, Any],
    evidence_sufficiency: dict[str, Any],
    allowed_categories: list[str],
) -> RecommendationDraft:

    endpoint = os.environ["FOUNDRY_PROJECT_ENDPOINT"]
    model = os.environ["FOUNDRY_MODEL_NAME"]

    schema = dict(SCHEMA)
    schema["properties"] = dict(SCHEMA["properties"])
    schema["properties"]["recommendation"] = {
        "type": "string",
        "enum": allowed_categories,
    }
    schema["properties"]["confidence"] = {
        "type": "string",
        "enum": ["LOW", "MEDIUM", "HIGH"],
    }
    schema["properties"]["evidence_quality"] = {
        "type": "string",
        "enum": ["LOW", "MEDIUM", "HIGH"],
    }

    context = {
        "project_id": project_id,
        "allowed_categories": allowed_categories,
        "gate_syntheses": gate_syntheses,
        "cod_feasibility": cod_feasibility,
        "evidence_sufficiency": evidence_sufficiency,
    }

    with (
        DefaultAzureCredential() as credential,
        AIProjectClient(
            endpoint=endpoint, credential=credential
        ) as project,
    ):

        with project.get_openai_client() as client:

            response = client.responses.create(
                model=model,
                instructions=INSTRUCTIONS,
                input=json.dumps(
                    context, indent=2, default=str
                ),
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "recommendation_draft",
                        "schema": schema,
                        "strict": True,
                    }
                },
            )

    parsed = json.loads(response.output_text)

    return RecommendationDraft.model_validate(
        parsed, strict=True
    )


def validate_recommendation(
    *,
    draft: RecommendationDraft,
    allowed_categories: list[str],
) -> None:

    if draft.recommendation not in allowed_categories:

        raise RuntimeError(
            "RECOMMENDATION POLICY REJECTED: selected "
            f"category {draft.recommendation!r} is not in "
            f"the deterministically allowed set "
            f"{allowed_categories!r}."
        )
