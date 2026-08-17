#!/usr/bin/env python3

import json
import os
from pathlib import Path

from renewable_intelligence.interconnection.spp_precedent_study import (
    analyze_precedent_study,
)


result_dir = Path(
    os.environ["RESULT_DIR"]
)

artifact = (
    result_dir
    / "spp_study_chain"
    / "artifacts"
    / "GEN-2026-PR2_extracted.json"
)


state = {
    "project_id": (
        "RDI-WOK-250-001"
    ),
}


task = {
    "action_id": (
        "INT-FU-001"
    ),

    "domain": (
        "interconnection"
    ),

    "source_artifact": (
        str(artifact)
    ),
}


result = analyze_precedent_study(
    state=state,
    task=task,
)


print(
    "=== SPP PRECEDENT STUDY ANALYSIS ==="
)

print(
    "Study:",
    result["study"]["study_id"],
)

print(
    "Relationship:",
    result[
        "relationship_to_candidate"
    ],
)

print(
    "Study project:",
    (
        f"{result['study']['mw']} MW "
        f"{result['study']['fuel_type']}"
    ),
)

print(
    "POI:",
    result[
        "study"
    ][
        "poi"
    ],
)


print()
print(
    "=== CONSTRAINTS ==="
)

print(
    "Count:",
    result[
        "constraints"
    ][
        "count"
    ],
)

print(
    "Types:",
    result[
        "constraints"
    ][
        "type_counts"
    ],
)


print()
print(
    "=== COST CONTEXT ==="
)

cost = result[
    "cost_context"
]

print(
    "Known allocated upgrade cost:",
    cost[
        "known_allocated_upgrade_cost_total"
    ],
)

print(
    "Allocated cost contains TBD:",
    cost[
        "allocated_cost_contains_tbd"
    ],
)

print(
    "Known total upgrade cost represented:",
    cost[
        "known_total_upgrade_cost_represented"
    ],
)

print(
    "TBD upgrade rows:",
    cost[
        "tbd_cost_upgrade_count"
    ],
)


print()
print(
    "=== THERMAL ==="
)

print(
    "Result count:",
    result[
        "thermal"
    ][
        "result_count"
    ],
)

print(
    "Maximum transfer-case loading:",
)

print(
    json.dumps(
        result[
            "thermal"
        ][
            "max_transfer_case_loading"
        ],
        indent=2,
    )
)


print()
print(
    "=== SHORT CIRCUIT ==="
)

print(
    json.dumps(
        result[
            "short_circuit"
        ],
        indent=2,
    )
)


print()
print(
    "=== SCR / CCT ==="
)

print(
    json.dumps(
        result[
            "scrcct"
        ],
        indent=2,
    )
)


print()
print(
    "=== CONFIDENCE ==="
)

print(
    "Precedent evidence:",
    result[
        "precedent_evidence_confidence"
    ],
)

print(
    "Applicability to candidate:",
    result[
        "candidate_applicability_confidence"
    ],
)


output = (
    result_dir
    / "screening"
    / "precedent_study_analysis.json"
)

output.write_text(
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
    output,
)
