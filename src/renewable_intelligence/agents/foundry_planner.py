from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Literal

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from pydantic import BaseModel, ConfigDict

from renewable_intelligence.agents.planner_policy import (
    build_admissible_actions,
    validate_planner_selection,
)


def _audit_event(
    event_type: str,
    **details: Any,
) -> dict[str, Any]:

    return {
        "timestamp_utc": (
            datetime.now(
                timezone.utc
            ).isoformat()
        ),
        "event_type": event_type,
        **details,
    }


class PlannerDecision(BaseModel):

    model_config = ConfigDict(
        extra="forbid"
    )

    selected_action_id: str
    selected_capability: str
    reason: str

    confidence: Literal[
        "LOW",
        "MEDIUM",
        "HIGH",
    ]


def _completed_investigation_summary(
    state: dict[str, Any],
) -> list[dict[str, Any]]:

    result = []

    for item in state.get(
        "investigation_history",
        [],
    ):

        result.append(
            {
                "task_id": (
                    item.get(
                        "task_id"
                    )
                ),

                "capability": (
                    item.get(
                        "capability"
                    )
                ),
            }
        )

    return result


def _call_foundry_planner(
    *,
    state: dict[str, Any],
    admissible_actions: list[
        dict[str, Any]
    ],
) -> PlannerDecision:

    endpoint = os.environ[
        "FOUNDRY_PROJECT_ENDPOINT"
    ]

    model = os.environ[
        "FOUNDRY_MODEL_NAME"
    ]


    action_ids = [
        action["action_id"]
        for action in admissible_actions
    ]

    capabilities = sorted(
        {
            action["capability"]
            for action in admissible_actions
        }
    )


    schema = {
        "type": "object",

        "properties": {
            "selected_action_id": {
                "type": "string",
                "enum": action_ids,
            },

            "selected_capability": {
                "type": "string",
                "enum": capabilities,
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


    context = {
        "project_id": (
            state.get(
                "project_id"
            )
        ),

        "planning_scope": (
            state.get(
                "planning_scope",
                "FOLLOW_UP",
            )
        ),

        "screening_context": (
            state.get(
                "screening"
            )
        ),

        "project_domain_outcomes": (
            state.get(
                "project_domain_outcomes",
                {},
            )
        ),

        "latest_evidence_assessment": (
            state.get(
                "latest_evidence_assessment"
            )
        ),

        "evidence_sufficiency": (
            state.get(
                "evidence_sufficiency"
            )
        ),

        "completed_investigations": (
            _completed_investigation_summary(
                state
            )
        ),

        "admissible_actions": (
            admissible_actions
        ),
    }


    instructions = """
You are the governed investigation planner for an
early-stage renewable-development screening system.

The application has already determined which actions are
admissible under deterministic business policy.

You may select ONLY from the supplied admissible actions.

The input contains a planning_scope.

If planning_scope is PROJECT_ROOT:

- Choose the development investigation that provides the
  highest-value next reduction in material project
  uncertainty.

- Consider the evidence already available, remaining
  uncertainty, potential development impact, dependencies,
  and likely information gain.

- Prefer investigating a materially uncertain issue over
  repeating an area that already has useful screening
  evidence.

- Do NOT choose based on task-id ordering.

If planning_scope is FOLLOW_UP:

- Choose the action that provides the best next information
  gain for the active investigation.

Rules:

1. Select exactly one supplied action.
2. Never invent an action or capability.
3. Never select outside the admissible action set.
4. Do not change deterministic facts.
5. Do not declare a development gate satisfied.
6. Do not claim interconnection feasibility.
7. Do not invent upgrade cost.
8. Do not convert screening evidence into a bankable
   technical conclusion.
9. Do not bypass application policy.
10. Explain why the selected action is preferable to the
    other admissible choices.
11. Do not claim that one investigation is a prerequisite
    or dependency of another unless that dependency is
    explicitly present in the supplied deterministic state
    or action metadata.
""".strip()


    with (
        DefaultAzureCredential()
        as credential,

        AIProjectClient(
            endpoint=endpoint,
            credential=credential,
        )
        as project,
    ):

        with project.get_openai_client() as client:

            response = client.responses.create(
                model=model,

                instructions=instructions,

                input=json.dumps(
                    context,
                    indent=2,
                    default=str,
                ),

                text={
                    "format": {
                        "type": (
                            "json_schema"
                        ),

                        "name": (
                            "investigation_planner_decision"
                        ),

                        "schema": (
                            schema
                        ),

                        "strict": True,
                    }
                },
            )


    parsed = json.loads(
        response.output_text
    )

    return PlannerDecision.model_validate(
        parsed,
        strict=True,
    )


def plan_follow_up(
    state: dict[str, Any],
) -> dict[str, Any]:

    candidates = (
        state.get(
            "candidate_actions"
        )
        or []
    )


    admissible = build_admissible_actions(
        candidates
    )


    # ========================================================
    # No permissible action
    # ========================================================

    if not admissible:

        return {
            "admissible_actions": [],

            "planner_decision": None,

            "planner_selection_mode": (
                "NO_ADMISSIBLE_ACTION"
            ),

            "recommended_follow_up": (
                None
            ),

            "route_reason": (
                "No admissible follow-up "
                "action remains."
            ),
        }


    # ========================================================
    # Exactly one permitted action:
    # DO NOT waste an LLM call.
    # ========================================================

    if len(admissible) == 1:

        selected = dict(
            admissible[0]
        )

        capability = selected[
            "capability"
        ]

        selected[
            "preferred_capability"
        ] = capability


        return {
            "admissible_actions": (
                admissible
            ),

            "planner_decision": {
                "selected_action_id": (
                    selected[
                        "action_id"
                    ]
                ),

                "selected_capability": (
                    capability
                ),

                "reason": (
                    "Only one action remained "
                    "after deterministic business-"
                    "policy filtering."
                ),

                "confidence": (
                    "HIGH"
                ),
            },

            "planner_selection_mode": (
                "DETERMINISTIC_SINGLETON"
            ),

            "recommended_follow_up": (
                selected
            ),

            "route_reason": (
                "Single admissible action "
                "selected without invoking "
                "the LLM."
            ),

            "audit_events": (
                state.get(
                    "audit_events",
                    []
                )
                + [
                    _audit_event(
                        "PLANNER_POLICY_APPLIED",
                        candidate_count=len(candidates),
                        admissible_count=len(admissible),
                    ),

                    _audit_event(
                        "PLANNER_BYPASSED_SINGLETON",
                        action_id=(
                            selected[
                                "action_id"
                            ]
                        ),
                        capability=capability,
                    ),

                    _audit_event(
                        "PLANNER_DECISION_VALIDATED",
                        action_id=(
                            selected[
                                "action_id"
                            ]
                        ),
                        capability=capability,
                        allowed=True,
                    ),
                ]
            ),
        }


    # ========================================================
    # Multiple equally permissible actions:
    # genuine reasoning decision.
    # ========================================================

    decision = _call_foundry_planner(
        state=state,
        admissible_actions=admissible,
    )


    policy = validate_planner_selection(
        selected_action_id=(
            decision.selected_action_id
        ),

        selected_capability=(
            decision.selected_capability
        ),

        admissible_actions=(
            admissible
        ),
    )


    if not policy.allowed:

        raise RuntimeError(
            "PLANNER POLICY REJECTED: "
            f"{policy.reason}"
        )


    selected = next(
        action
        for action in admissible
        if action[
            "action_id"
        ]
        == decision.selected_action_id
    )

    selected = dict(
        selected
    )

    selected[
        "preferred_capability"
    ] = (
        decision.selected_capability
    )


    return {
        "admissible_actions": (
            admissible
        ),

        "planner_decision": (
            decision.model_dump()
        ),

        "planner_selection_mode": (
            "FOUNDRY_LLM"
        ),

        "recommended_follow_up": (
            selected
        ),

        "route_reason": (
            "Foundry planner selected "
            "one action from the governed "
            "admissible action set."
        ),

        "audit_events": (
            state.get(
                "audit_events",
                []
            )
            + [
                _audit_event(
                    "PLANNER_POLICY_APPLIED",
                    candidate_count=len(candidates),
                    admissible_count=len(admissible),
                ),

                _audit_event(
                    "LLM_PLANNER_INVOKED",
                    model=os.environ.get(
                        "FOUNDRY_MODEL_NAME"
                    ),
                ),

                _audit_event(
                    "LLM_PLANNER_DECISION",
                    action_id=(
                        decision.selected_action_id
                    ),
                    capability=(
                        decision.selected_capability
                    ),
                    confidence=(
                        decision.confidence
                    ),
                ),

                _audit_event(
                    "PLANNER_DECISION_VALIDATED",
                    action_id=(
                        decision.selected_action_id
                    ),
                    capability=(
                        decision.selected_capability
                    ),
                    allowed=True,
                ),
            ]
        ),
    }


def plan_project_investigation(
    state: dict[str, Any],
) -> dict[str, Any]:

    project_candidates = (
        state.get(
            "project_candidate_actions"
        )
        or []
    )


    # Reuse the same governed planning engine.
    #
    # candidate_actions is supplied only in this temporary
    # planner-state copy; the persisted follow-up state is
    # not mutated.
    planner_state = dict(
        state
    )

    planner_state[
        "candidate_actions"
    ] = project_candidates

    planner_state[
        "planning_scope"
    ] = "PROJECT_ROOT"


    planned = plan_follow_up(
        planner_state
    )


    selected = planned.get(
        "recommended_follow_up"
    )


    if not selected:

        return {
            "project_admissible_actions": (
                planned.get(
                    "admissible_actions",
                    [],
                )
            ),

            "project_planner_decision": (
                planned.get(
                    "planner_decision"
                )
            ),

            "project_planner_selection_mode": (
                planned.get(
                    "planner_selection_mode"
                )
            ),

            "current_investigation": (
                None
            ),

            "selected_task_id": (
                None
            ),

            "selected_capability": (
                None
            ),

            "investigation_status": (
                "NO_PROJECT_ACTION_SELECTED"
            ),

            "route_reason": (
                "Governed project planning produced "
                "no admissible root investigation."
            ),

            "audit_events": (
                planned.get(
                    "audit_events"
                )
                or state.get(
                    "audit_events",
                    [],
                )
            ),
        }


    selected = dict(
        selected
    )


    action_id = selected[
        "action_id"
    ]

    capability = selected[
        "capability"
    ]


    selected[
        "task_id"
    ] = action_id

    selected[
        "preferred_capability"
    ] = capability

    selected[
        "status"
    ] = "PENDING"


    audit_events = list(
        planned.get(
            "audit_events"
        )
        or state.get(
            "audit_events",
            [],
        )
    )


    audit_events.append(
        _audit_event(
            "PROJECT_INVESTIGATION_SELECTED",
            action_id=action_id,
            domain=selected.get(
                "domain"
            ),
            capability=capability,
            selection_mode=(
                planned.get(
                    "planner_selection_mode"
                )
            ),
        )
    )


    return {
        "project_admissible_actions": (
            planned.get(
                "admissible_actions",
                [],
            )
        ),

        "project_planner_decision": (
            planned.get(
                "planner_decision"
            )
        ),

        "project_planner_selection_mode": (
            planned.get(
                "planner_selection_mode"
            )
        ),

        "current_investigation": (
            selected
        ),

        "selected_task_id": (
            action_id
        ),

        "selected_capability": (
            capability
        ),

        "capability_available": (
            None
        ),

        "investigation_status": (
            "INVESTIGATION_SELECTED"
        ),

        "iteration": (
            state.get(
                "iteration",
                0,
            )
            + 1
        ),

        "run_iteration": (
            state.get(
                "run_iteration",
                0,
            )
            + 1
        ),

        "route_reason": (
            "Governed project planner selected "
            f"{action_id} using {capability}."
        ),

        "audit_events": (
            audit_events
        ),
    }

