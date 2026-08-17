#!/usr/bin/env python3

from __future__ import annotations

import os

from renewable_intelligence.graph.investigation_graph import (
    select_next_investigation,
)
from renewable_intelligence.persistence.checkpointing import (
    open_checkpointer,
)
from renewable_intelligence.graph.investigation_graph import (
    build_investigation_graph,
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


# Bootstrap the interconnection domain outcome from the
# assessment already persisted in the checkpoint. This is a
# dry-run only; it does NOT mutate the checkpoint.
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
    }
}


result = select_next_investigation(
    state
)


print(
    "=== NEXT PROJECT INVESTIGATION DRY RUN ==="
)

print(
    "Selected:",
    result.get(
        "selected_task_id"
    ),
)

print(
    "Domain:",
    (
        result.get(
            "current_investigation"
        )
        or {}
    ).get(
        "domain"
    ),
)

print(
    "Capability:",
    result.get(
        "selected_capability"
    ),
)

print(
    "Status:",
    result.get(
        "investigation_status"
    ),
)

print(
    "Reason:",
    result.get(
        "route_reason"
    ),
)
