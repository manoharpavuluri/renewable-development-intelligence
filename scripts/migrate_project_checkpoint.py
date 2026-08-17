#!/usr/bin/env python3

from __future__ import annotations

import os

from renewable_intelligence.graph.investigation_graph import (
    build_investigation_graph,
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


EXPECTED_LEGACY_TASKS = {
    "INV-001",
    "INT-FU-001",
    "INT-FU-003",
    "INT-FU-004",
}


with open_checkpointer() as checkpointer:

    graph = build_investigation_graph(
        checkpointer=checkpointer
    )

    snapshot = graph.get_state(
        config
    )


    if not snapshot.values:

        raise RuntimeError(
            "No saved thread state found."
        )


    if snapshot.next:

        raise RuntimeError(
            "Expected the legacy project thread "
            "to be completed before migration. "
            f"Pending nodes: {snapshot.next!r}"
        )


    existing_outcomes = dict(
        snapshot.values.get(
            "project_domain_outcomes",
            {},
        )
        or {}
    )


    if (
        "interconnection"
        in existing_outcomes
    ):

        print(
            "Interconnection domain outcome "
            "already migrated."
        )

    else:

        history = (
            snapshot.values.get(
                "investigation_history",
                []
            )
            or []
        )


        actual_task_ids = {
            item.get(
                "task_id"
            )
            for item in history
            if item.get(
                "task_id"
            )
        }


        if not actual_task_ids.issubset(
            EXPECTED_LEGACY_TASKS
        ):

            raise RuntimeError(
                "Legacy migration guard failed. "
                "Unexpected investigation task IDs: "
                f"{sorted(actual_task_ids)}"
            )


        latest = (
            snapshot.values.get(
                "latest_evidence_assessment"
            )
            or {}
        )


        if (
            latest.get(
                "gate_id"
            )
            != "G2"
        ):

            raise RuntimeError(
                "Expected latest legacy assessment "
                "to represent G2."
            )


        existing_outcomes[
            "interconnection"
        ] = {
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

            "resolved_uncertainty": (
                latest.get(
                    "resolved_uncertainty",
                    [],
                )
            ),

            "remaining_uncertainty": (
                latest.get(
                    "remaining_uncertainty",
                    [],
                )
            ),

            "latest_task_id": (
                "INT-FU-003"
            ),

            "latest_capability": (
                "spp.evaluate_additional_poi"
            ),

            "completed_task_ids": (
                sorted(
                    actual_task_ids
                )
            ),

            "migration_source": (
                "LEGACY_INTERCONNECTION_THREAD"
            ),
        }


        graph.update_state(
            config,
            values={
                "project_domain_outcomes": (
                    existing_outcomes
                )
            },
            as_node=(
                "record_domain_outcome"
            ),
        )


        print(
            "Migrated legacy G2 outcome into "
            "project_domain_outcomes."
        )


    after = graph.get_state(
        config
    )


    outcome = (
        after.values.get(
            "project_domain_outcomes",
            {}
        ).get(
            "interconnection"
        )
    )


    print()
    print(
        "=== MIGRATED DOMAIN OUTCOME ==="
    )

    print(
        "Domain:",
        outcome.get(
            "domain"
        ),
    )

    print(
        "Gate:",
        outcome.get(
            "gate_id"
        ),
    )

    print(
        "Screening status:",
        outcome.get(
            "screening_status"
        ),
    )

    print(
        "Confidence:",
        outcome.get(
            "decision_confidence"
        ),
    )

    print(
        "Completed tasks:",
        outcome.get(
            "completed_task_ids"
        ),
    )
