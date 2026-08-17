"""
Layer 1 — deterministic-policy evals for the investigation
planner's admissible-action policy. No LLM calls.
"""

from __future__ import annotations

from renewable_intelligence.agents.planner_policy import (
    build_admissible_actions,
    effective_priority,
    validate_planner_selection,
)


def test_effective_priority_defaults_to_action_priority():

    assert (
        effective_priority({"priority": "MEDIUM"}) == "MEDIUM"
    )


def test_continues_blocking_investigation_forces_blocking_priority():

    action = {
        "priority": "HIGH",
        "continues_blocking_investigation": True,
    }

    assert effective_priority(action) == "BLOCKING"


def test_admissible_actions_keep_only_best_priority_tier():

    actions = [
        {"action_id": "A", "priority": "MEDIUM"},
        {"action_id": "B", "priority": "HIGH"},
        {"action_id": "C", "priority": "HIGH"},
        {"action_id": "D", "priority": "LOW"},
    ]

    admissible = build_admissible_actions(actions)

    assert {a["action_id"] for a in admissible} == {"B", "C"}


def test_admissible_actions_empty_for_empty_input():

    assert build_admissible_actions([]) == []


def test_planner_selection_outside_admissible_set_is_rejected():

    admissible = [
        {
            "action_id": "INV-006",
            "capability": "land.resolve_status",
        }
    ]

    decision = validate_planner_selection(
        selected_action_id="INV-999",
        selected_capability="fabricated.capability",
        admissible_actions=admissible,
    )

    assert decision.allowed is False


def test_planner_selection_with_mismatched_capability_is_rejected():

    admissible = [
        {
            "action_id": "INV-006",
            "capability": "land.resolve_status",
        }
    ]

    decision = validate_planner_selection(
        selected_action_id="INV-006",
        selected_capability="a.different.capability",
        admissible_actions=admissible,
    )

    assert decision.allowed is False


def test_planner_selection_within_admissible_set_is_allowed():

    admissible = [
        {
            "action_id": "INV-006",
            "capability": "land.resolve_status",
        }
    ]

    decision = validate_planner_selection(
        selected_action_id="INV-006",
        selected_capability="land.resolve_status",
        admissible_actions=admissible,
    )

    assert decision.allowed is True
