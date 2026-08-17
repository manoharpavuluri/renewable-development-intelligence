#!/usr/bin/env python3

from __future__ import annotations

import os

from renewable_intelligence.agents.foundry_planner import (
    plan_project_investigation,
)
from renewable_intelligence.graph.investigation_graph import (
    build_investigation_graph,
    select_next_investigation,
)
from renewable_intelligence.persistence.checkpointing import (
    open_checkpointer,
)


THREAD_ID = os.environ.get(
    "RDI_THREAD_ID",
    "RDI-WOK-250-001:screening:v1",
)


config = {
    "configurable": {
        "thread_id": THREAD_ID,
    }
}


with open_checkpointer() as checkpointer:

    graph = build_investigation_graph(
        checkpointer=checkpointer
    )

    snapshot = graph.get_state(
        config
    )


state = dict(
    snapshot.values
)


# ------------------------------------------------------------
# The saved thread predates project_domain_outcomes.
#
# Bootstrap the already-established interconnection outcome
# only in this dry-run state.
#
# This DOES NOT mutate the checkpoint.
# ------------------------------------------------------------

latest = (
    state.get(
        "latest_evidence_assessment"
    )
    or {}
)


state[
    "project_domain_outcomes"
] = {
    "interconnection": {
        "domain": (
            "interconnection"
        ),

        "gate_id": (
            latest.get(
                "gate_id"
            )
        ),

        "screening_status": (
            latest.get(
                "status"
            )
        ),

        "gate_status": (
            latest.get(
                "gate_status"
            )
        ),

        "decision_confidence": (
            latest.get(
                "decision_confidence"
            )
        ),

        "remaining_uncertainty": (
            latest.get(
                "remaining_uncertainty",
                [],
            )
        ),
    }
}


selection_update = (
    select_next_investigation(
        state
    )
)


state.update(
    selection_update
)


print(
    "=== PROJECT CANDIDATE SET ==="
)


for action in state.get(
    "project_candidate_actions",
    [],
):

    print(
        action.get(
            "action_id"
        ),
        "|",
        action.get(
            "priority"
        ),
        "|",
        action.get(
            "domain"
        ),
        "|",
        action.get(
            "capability"
        ),
    )


print()
print(
    "Calling governed Foundry planner..."
)


planned = plan_project_investigation(
    state
)


print()
print(
    "=== PROJECT PLANNER RESULT ==="
)

print(
    "Selection mode:",
    planned.get(
        "project_planner_selection_mode"
    ),
)


print(
    "Admissible IDs:",
    [
        action.get(
            "action_id"
        )
        for action
        in planned.get(
            "project_admissible_actions",
            [],
        )
    ],
)


decision = (
    planned.get(
        "project_planner_decision"
    )
    or {}
)


print(
    "Selected:",
    decision.get(
        "selected_action_id"
    ),
)


print(
    "Capability:",
    decision.get(
        "selected_capability"
    ),
)


print(
    "Confidence:",
    decision.get(
        "confidence"
    ),
)


print(
    "Reason:",
    decision.get(
        "reason"
    ),
)


print()
print(
    "Current investigation:",
    (
        planned.get(
            "current_investigation"
        )
        or {}
    ).get(
        "domain"
    ),
)


print()
print(
    "CHECKPOINT MUTATED: NO"
)
