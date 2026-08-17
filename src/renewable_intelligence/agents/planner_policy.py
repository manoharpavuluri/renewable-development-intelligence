from __future__ import annotations

from dataclasses import dataclass
from typing import Any


PRIORITY_RANK = {
    "BLOCKING": 0,
    "HIGH": 1,
    "MEDIUM": 2,
    "LOW": 3,
}


@dataclass(frozen=True)
class PlannerPolicyDecision:
    allowed: bool
    reason: str
    selected_action_id: str
    selected_capability: str


def effective_priority(
    action: dict[str, Any],
) -> str:

    """
    Determine the business priority of an action.

    A follow-up that is required to resolve an active
    BLOCKING investigation inherits BLOCKING priority,
    even if the follow-up task itself was originally
    labeled HIGH.
    """

    if action.get(
        "continues_blocking_investigation"
    ):
        return "BLOCKING"

    return action.get(
        "priority",
        "MEDIUM",
    )


def build_admissible_actions(
    actions: list[dict[str, Any]],
) -> list[dict[str, Any]]:

    if not actions:
        return []

    enriched = []

    for action in actions:

        item = dict(action)

        item[
            "effective_priority"
        ] = effective_priority(
            action
        )

        enriched.append(
            item
        )


    best_rank = min(
        PRIORITY_RANK[
            action[
                "effective_priority"
            ]
        ]
        for action in enriched
    )


    return [
        action
        for action in enriched
        if PRIORITY_RANK[
            action[
                "effective_priority"
            ]
        ]
        == best_rank
    ]


def validate_planner_selection(
    *,
    selected_action_id: str,
    selected_capability: str,
    admissible_actions: list[
        dict[str, Any]
    ],
) -> PlannerPolicyDecision:

    by_id = {
        action[
            "action_id"
        ]: action
        for action in admissible_actions
    }


    action = by_id.get(
        selected_action_id
    )


    if action is None:

        return PlannerPolicyDecision(
            allowed=False,
            reason=(
                "Selected action is outside "
                "the deterministic admissible "
                "action set."
            ),
            selected_action_id=(
                selected_action_id
            ),
            selected_capability=(
                selected_capability
            ),
        )


    expected_capability = action.get(
        "capability"
    )


    if (
        selected_capability
        != expected_capability
    ):

        return PlannerPolicyDecision(
            allowed=False,
            reason=(
                "Selected capability does not "
                "match the capability assigned "
                "to the selected action."
            ),
            selected_action_id=(
                selected_action_id
            ),
            selected_capability=(
                selected_capability
            ),
        )


    return PlannerPolicyDecision(
        allowed=True,
        reason=(
            "Selection is within the "
            "deterministically admissible "
            "business-policy envelope."
        ),
        selected_action_id=(
            selected_action_id
        ),
        selected_capability=(
            selected_capability
        ),
    )
