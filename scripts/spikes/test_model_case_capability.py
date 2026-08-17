#!/usr/bin/env python3

import json
import os
from pathlib import Path

from renewable_intelligence.interconnection.spp_model_case_comparison import (
    compare_model_cases,
)


result_dir = Path(
    os.environ["RESULT_DIR"]
)


task = {
    "task_id": "INT-FU-002",

    "action_id": "INT-FU-002",

    "capability": (
        "spp.compare_model_cases"
    ),

    "model_cases": {
        "TC00": {
            "model": (
                "DIS231-TC00ALL-24SP3"
            ),

            "pois": {
                "TATONGA7": str(
                    result_dir
                    / "spp_hct"
                    / "tatonga_345_250mw"
                    / "grid-data.csv"
                ),

                "WWRDEHV7": str(
                    result_dir
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
                    result_dir
                    / "spp_hct"
                    / "model_cases"
                    / "DIS231-TC03ALL-24SP3"
                    / "tatonga_345_250mw"
                    / "grid-data.csv"
                ),

                "WWRDEHV7": str(
                    result_dir
                    / "spp_hct"
                    / "model_cases"
                    / "DIS231-TC03ALL-24SP3"
                    / "woodward_ehv_345_250mw"
                    / "grid-data.csv"
                ),
            },
        },
    },
}


result = compare_model_cases(
    state={},
    task=task,
)


print(
    "=== PRODUCTION MODEL-CASE CAPABILITY ==="
)

print(
    json.dumps(
        result,
        indent=2,
    )
)


assert result[
    "executed"
] is True


assert (
    result[
        "finding"
    ][
        "sensitivity_status"
    ]
    ==
    "ROBUST_ACROSS_TESTED_CASES"
)


assert (
    result[
        "finding"
    ][
        "screening_preferred_poi"
    ]
    ==
    "TATONGA7"
)


assert (
    result[
        "finding"
    ][
        "tested_model_count"
    ]
    == 2
)


assert (
    result[
        "finding"
    ][
        "tested_poi_count"
    ]
    == 2
)


print()
print(
    "Production capability validation: PASS"
)
