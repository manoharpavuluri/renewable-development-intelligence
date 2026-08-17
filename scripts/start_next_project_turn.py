#!/usr/bin/env python3

"""
Start the next project-level turn on an existing, already-migrated
investigation thread.

Unlike run_investigation_graph.py (which bootstraps a brand-new
thread) this re-enters an existing thread at START. Nodes read
project_id / screening / gate_assessment / project_domain_outcomes /
investigation_history / evidence_ledger from the persisted
checkpoint; only the invocation-level run_iteration counter is
reset (by validate_state), preserving the full lifetime history.

This intentionally passes an empty input rather than replaying or
mutating any prior state.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from renewable_intelligence.graph.investigation_graph import (
    build_investigation_graph,
)
from renewable_intelligence.persistence.checkpointing import (
    checkpoint_backend_description,
    open_checkpointer,
)
from renewable_intelligence.tools.bootstrap import (
    register_implemented_capabilities,
)


THREAD_ID = os.environ.get(
    "RDI_THREAD_ID",
    "RDI-WOK-250-001:screening:v1",
)

RESULT_DIR_RAW = os.environ.get("RESULT_DIR")


config = {
    "configurable": {
        "thread_id": THREAD_ID,
    }
}


register_implemented_capabilities()


checkpoint_backend = checkpoint_backend_description()


with open_checkpointer() as checkpointer:

    graph = build_investigation_graph(checkpointer=checkpointer)

    before = graph.get_state(config)

    if not before.values:
        raise SystemExit(
            f"No saved state exists for thread {THREAD_ID!r} "
            f"using {checkpoint_backend}."
        )

    if before.next:
        raise SystemExit(
            "Thread is not at a clean project-turn boundary "
            f"(pending nodes: {before.next!r}). Resume it "
            "instead of starting a new turn."
        )

    if "interconnection" not in (
        before.values.get("project_domain_outcomes") or {}
    ):
        raise SystemExit(
            "project_domain_outcomes has not been migrated yet. "
            "Run migrate_project_checkpoint.py first."
        )

    print("=== STARTING NEXT PROJECT TURN ===")
    print("Backend:", checkpoint_backend)
    print("Thread:", THREAD_ID)
    print(
        "Domains already recorded:",
        sorted((before.values.get("project_domain_outcomes") or {}).keys()),
    )
    print(
        "Completed task IDs:",
        sorted(
            {
                item.get("task_id")
                for item in before.values.get("investigation_history", [])
                if item.get("task_id")
            }
        ),
    )
    print()

    result = graph.invoke({}, config=config)


interrupts = result.get("__interrupt__", [])


print("=== PROJECT TURN RESULT ===")
print("Status:", result.get("investigation_status"))
print("Selected task:", result.get("selected_task_id"))
print("Capability:", result.get("selected_capability"))
print(
    "Selection mode:",
    result.get("project_planner_selection_mode"),
)

decision = result.get("project_planner_decision") or {}

if decision:
    print("Planner reason:", decision.get("reason"))
    print("Planner confidence:", decision.get("confidence"))

print()
print("Project domain outcomes:")
print(
    json.dumps(
        result.get("project_domain_outcomes", {}),
        indent=2,
        default=str,
    )
)

if interrupts:

    print()
    print("=== GRAPH PAUSED FOR EXTERNAL WORK ===")

    for item in interrupts:

        payload = getattr(item, "value", item)

        print(json.dumps(payload, indent=2, default=str))


print()
print("=== AUDIT EVENTS (this turn) ===")

for event in result.get("audit_events", [])[-15:]:

    print(
        event["event_type"],
        "|",
        event.get("action_id", event.get("task_id", "")),
        event.get("capability", ""),
    )


if RESULT_DIR_RAW:

    output_path = (
        Path(RESULT_DIR_RAW) / "screening" / "project_turn_result.json"
    )

    output_path.write_text(
        json.dumps(result, indent=2, default=str),
        encoding="utf-8",
    )

    print()
    print("Output:", output_path)
