#!/usr/bin/env python3

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


RESULT_DIR = os.environ.get(
    "RESULT_DIR"
)

if not RESULT_DIR:
    raise SystemExit(
        "RESULT_DIR is not set."
    )

RESULT_DIR = Path(
    RESULT_DIR
)


screening_path = (
    RESULT_DIR
    / "screening"
    / "candidate_site_screening.json"
)

gate_path = (
    RESULT_DIR
    / "screening"
    / "development_gate_assessment.json"
)


screening = json.loads(
    screening_path.read_text(
        encoding="utf-8"
    )
)

gate_assessment = json.loads(
    gate_path.read_text(
        encoding="utf-8"
    )
)


# ============================================================
# Governed HCT evidence bundle
#
# Concrete artifact locations belong to the scenario/runtime,
# not to the reusable comparison capability.
# ============================================================

spp_hct_model_cases = {
    "TC00": {
        "model": (
            "DIS231-TC00ALL-24SP3"
        ),

        "pois": {
            "TATONGA7": str(
                RESULT_DIR
                / "spp_hct"
                / "tatonga_345_250mw"
                / "grid-data.csv"
            ),

            "WWRDEHV7": str(
                RESULT_DIR
                / "spp_hct"
                / "woodward_ehv_345_250mw"
                / "grid-data.csv"
            ),
        },
    },

    "TC03": {
        "model": (
            "DIS231-TC03ALL-24SP3"
        ),

        "pois": {
            "TATONGA7": str(
                RESULT_DIR
                / "spp_hct"
                / "model_cases"
                / "DIS231-TC03ALL-24SP3"
                / "tatonga_345_250mw"
                / "grid-data.csv"
            ),

            "WWRDEHV7": str(
                RESULT_DIR
                / "spp_hct"
                / "model_cases"
                / "DIS231-TC03ALL-24SP3"
                / "woodward_ehv_345_250mw"
                / "grid-data.csv"
            ),
        },
    },
}


# Fail early if provenance references are broken.
for case_id, case in (
    spp_hct_model_cases.items()
):

    for poi_name, artifact in (
        case["pois"].items()
    ):

        artifact_path = Path(
            artifact
        )

        if not artifact_path.exists():

            raise FileNotFoundError(
                "Missing governed HCT evidence: "
                f"{case_id} / {poi_name} / "
                f"{artifact_path}"
            )


# ============================================================
# Public transmission / gen-tie screening evidence
# ============================================================

transmission_context_evidence = {
    "candidate_geometry": (
        "data/scenarios/"
        "western_ok_250mw/"
        "candidate_area.geojson"
    ),

    "transmission_lines_artifact": str(
        RESULT_DIR
        / "transmission"
        / "gen_tie_context"
        / "hifld_transmission_lines.geojson"
    ),

    "target_name": (
        "TATONGA"
    ),

    "minimum_voltage_kv": (
        230
    ),

    "target_voltage_kv": (
        345
    ),
}


for required_path in [
    Path(
        transmission_context_evidence[
            "candidate_geometry"
        ]
    ),
    Path(
        transmission_context_evidence[
            "transmission_lines_artifact"
        ]
    ),
]:

    if not required_path.exists():

        raise FileNotFoundError(
            "Missing governed transmission "
            f"evidence: {required_path}"
        )


initial_state = {
    "project_id": (
        screening[
            "project_id"
        ]
    ),

    "screening": screening,

    "gate_assessment": (
        gate_assessment
    ),

    "spp_hct_model_cases": (
        spp_hct_model_cases
    ),

    "transmission_context_evidence": (
        transmission_context_evidence
    ),

    "current_investigation": None,

    "selected_task_id": None,

    "selected_capability": None,

    "capability_available": None,

    "investigation_status": (
        "INITIALIZED"
    ),

    "investigation_result": None,

    "evidence_sufficiency": None,

    "latest_evidence_assessment": None,

    "evidence_ledger": [],

    "recommended_follow_up": None,

    "investigation_history": [],

    "iteration": 0,

    "max_iterations": 25,

    "route_reason": None,

    "errors": [],

    "audit_events": [],
}


register_implemented_capabilities()


# ============================================================
# Durable LangGraph checkpoint
#
# The runner depends on the checkpoint abstraction rather
# than SQLite or PostgreSQL directly.
# ============================================================

thread_id = os.environ.get(
    "RDI_THREAD_ID",
    (
        f"{initial_state['project_id']}"
        ":screening:v1"
    ),
)


config = {
    "configurable": {
        "thread_id": (
            thread_id
        ),
    }
}


checkpoint_backend = (
    checkpoint_backend_description()
)


with open_checkpointer() as checkpointer:

    graph = build_investigation_graph(
        checkpointer=checkpointer
    )


    # Refuse to silently restart an existing thread.
    existing_state = graph.get_state(
        config
    )

    if existing_state.values:

        raise SystemExit(
            "Checkpoint thread already exists: "
            f"{thread_id}\n"
            "Backend: "
            f"{checkpoint_backend}\n"
            "Use the resume script instead of "
            "starting the investigation again."
        )


    result = graph.invoke(
        initial_state,
        config=config,
    )


interrupts = result.get(
    "__interrupt__",
    []
)


if interrupts:

    print(
        "=== GRAPH PAUSED FOR EXTERNAL WORK ==="
    )

    for item in interrupts:

        payload = getattr(
            item,
            "value",
            item,
        )

        print(
            json.dumps(
                payload,
                indent=2,
                default=str,
            )
        )

    print()


print(
    "=== INVESTIGATION GRAPH RESULT ==="
)

print(
    "Project:",
    result[
        "project_id"
    ],
)

print(
    "Selected task:",
    result.get(
        "selected_task_id"
    ),
)

print(
    "Capability:",
    result.get(
        "selected_capability"
    ),
)

print(
    "Capability available:",
    result.get(
        "capability_available"
    ),
)

runtime_status = (
    "WAITING_FOR_EXTERNAL_WORK"
    if interrupts
    else result.get(
        "investigation_status"
    )
)


print(
    "Status:",
    runtime_status,
)


if interrupts:

    first_interrupt = getattr(
        interrupts[0],
        "value",
        interrupts[0],
    )

    runtime_reason = (
        first_interrupt.get(
            "reason"
        )
        if isinstance(
            first_interrupt,
            dict,
        )
        else str(
            first_interrupt
        )
    )

else:

    runtime_reason = result.get(
        "route_reason"
    )


print(
    "Reason:",
    runtime_reason,
)


if interrupts:

    print(
        "Internal graph state:",
        result.get(
            "investigation_status"
        ),
    )


print()
print(
    "=== INVESTIGATION ==="
)

task = result.get(
    "current_investigation"
)

if task:

    print(
        "Priority:",
        task.get(
            "priority"
        ),
    )

    print(
        "Domain:",
        task.get(
            "domain"
        ),
    )

    print(
        "Question:",
        task.get(
            "question"
        ),
    )

    print(
        "Blocking gates:",
        ", ".join(
            task.get(
                "blocking_gate_ids",
                [],
            )
        ),
    )


print()
print(
    "=== RESULT ==="
)

print(
    json.dumps(
        result.get(
            "investigation_result"
        ),
        indent=2,
    )
)


print()
print(
    "=== CURRENT EVIDENCE SUFFICIENCY ==="
)

print(
    json.dumps(
        result.get(
            "evidence_sufficiency"
        ),
        indent=2,
    )
)


print()
print(
    "=== LATEST ASSESSED EVIDENCE ==="
)

print(
    json.dumps(
        result.get(
            "latest_evidence_assessment"
        ),
        indent=2,
    )
)


print()
print(
    "=== EVIDENCE LEDGER ==="
)

ledger = result.get(
    "evidence_ledger",
    [],
)

print(
    "Assessed investigations:",
    len(
        ledger
    ),
)


for entry in ledger:

    print(
        "-",
        entry.get(
            "task_id"
        ),
        "|",
        entry.get(
            "capability"
        ),
        "| gate:",
        entry.get(
            "gate_id"
        ),
        "|",
        entry.get(
            "gate_status"
        ),
        "| confidence:",
        entry.get(
            "decision_confidence"
        ),
    )


print()
print(
    "=== RECOMMENDED FOLLOW-UP ==="
)

print(
    json.dumps(
        result.get(
            "recommended_follow_up"
        ),
        indent=2,
    )
)


print()
print(
    "=== GOVERNED PLANNER ==="
)

print(
    "Selection mode:",
    result.get(
        "planner_selection_mode"
    ),
)

print(
    "Planner decision:"
)

print(
    json.dumps(
        result.get(
            "planner_decision"
        ),
        indent=2,
    )
)

print(
    "Admissible actions:"
)

print(
    json.dumps(
        result.get(
            "admissible_actions",
            [],
        ),
        indent=2,
    )
)


print()
print(
    "=== INVESTIGATION HISTORY ==="
)

history = result.get(
    "investigation_history",
    [],
)

print(
    "Completed investigations:",
    len(history),
)

for item in history:

    print(
        "-",
        item.get(
            "task_id"
        ),
        "|",
        item.get(
            "capability"
        ),
    )


print()
print(
    "=== AUDIT EVENTS ==="
)

for event in result.get(
    "audit_events",
    [],
):

    print(
        event[
            "event_type"
        ],
        "|",
        event.get(
            "task_id",
            "",
        ),
        event.get(
            "capability",
            "",
        ),
    )


output_path = (
    RESULT_DIR
    / "screening"
    / "investigation_graph_run.json"
)

output_path.write_text(
    json.dumps(
        result,
        indent=2,
        default=str,
    ),
    encoding="utf-8",
)


print()
print(
    "Output:",
    output_path,
)
