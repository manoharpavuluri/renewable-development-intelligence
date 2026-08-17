#!/usr/bin/env python3

from renewable_intelligence.agents.planner_policy import (
    build_admissible_actions,
    validate_planner_selection,
)


candidate_actions = [
    {
        "action_id": "INT-FU-002",
        "capability": (
            "spp.compare_model_cases"
        ),
        "priority": "HIGH",
        "domain": "interconnection",

        # Critical piece:
        "continues_blocking_investigation": True,
    },

    {
        "action_id": "INV-003",
        "capability": (
            "gis.analyze_terrain"
        ),
        "priority": "HIGH",
        "domain": "terrain",
        "continues_blocking_investigation": False,
    },

    {
        "action_id": "INV-002",
        "capability": (
            "wind.analyze_candidate_resource"
        ),
        "priority": "HIGH",
        "domain": "wind_resource",
        "continues_blocking_investigation": False,
    },
]


admissible = build_admissible_actions(
    candidate_actions
)


print(
    "=== DETERMINISTIC ADMISSIBLE ACTIONS ==="
)

for action in admissible:

    print(
        action["action_id"],
        "|",
        action["capability"],
        "|",
        action["effective_priority"],
    )


print()
print(
    "=== TEST MODEL'S ACTUAL DECISION ==="
)

decision = validate_planner_selection(
    selected_action_id="INV-003",
    selected_capability=(
        "gis.analyze_terrain"
    ),
    admissible_actions=admissible,
)

print(
    "Allowed:",
    decision.allowed,
)

print(
    "Reason:",
    decision.reason,
)


print()
print(
    "=== TEST EXPECTED INTERCONNECTION DECISION ==="
)

decision = validate_planner_selection(
    selected_action_id=(
        "INT-FU-002"
    ),
    selected_capability=(
        "spp.compare_model_cases"
    ),
    admissible_actions=admissible,
)

print(
    "Allowed:",
    decision.allowed,
)

print(
    "Reason:",
    decision.reason,
)
