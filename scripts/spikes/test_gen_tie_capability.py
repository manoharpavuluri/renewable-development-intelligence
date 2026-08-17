#!/usr/bin/env python3

import json
import os
from pathlib import Path

from renewable_intelligence.transmission.gen_tie_context import (
    assess_gen_tie_context,
)


result_dir = Path(
    os.environ["RESULT_DIR"]
)


state = {
    "transmission_context_evidence": {
        "candidate_geometry": (
            "data/scenarios/"
            "western_ok_250mw/"
            "candidate_area.geojson"
        ),

        "transmission_lines_artifact": str(
            result_dir
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
}


task = {
    "task_id": (
        "INT-FU-004"
    ),

    "action_id": (
        "INT-FU-004"
    ),

    "capability": (
        "transmission.assess_gen_tie_context"
    ),
}


result = assess_gen_tie_context(
    state=state,
    task=task,
)


print(
    "=== PRODUCTION GEN-TIE CAPABILITY ==="
)

print(
    json.dumps(
        result,
        indent=2,
        default=str,
    )
)


finding = result[
    "finding"
]


assert result[
    "executed"
] is True

assert (
    finding[
        "public_line_context_status"
    ]
    ==
    "AVAILABLE"
)

assert (
    finding[
        "target_name_context_status"
    ]
    ==
    "FOUND"
)

assert (
    finding[
        "target_voltage_line_count"
    ]
    == 56
)

assert (
    finding[
        "candidate_intersection_count"
    ]
    == 0
)

assert (
    finding[
        "target_named_line_count"
    ]
    == 6
)

assert abs(
    finding[
        "nearest_target_named_line_miles"
    ]
    - 0.786
) < 0.001

assert (
    finding[
        "exact_target_bus_geometry_established"
    ]
    is False
)

assert (
    finding[
        "constructible_gen_tie_route_established"
    ]
    is False
)

assert (
    finding[
        "interconnection_feasibility_established"
    ]
    is False
)


print()
print(
    "Production gen-tie capability validation: PASS"
)
