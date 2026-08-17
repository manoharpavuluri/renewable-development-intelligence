#!/usr/bin/env python3

from __future__ import annotations

import csv
import hashlib
import json
import os
from pathlib import Path
from typing import Any


RESULT_DIR = Path(
    os.environ["RESULT_DIR"]
)


CASES = {
    "TC00": {
        "model": "DIS231-TC00ALL-24SP3",
        "tatonga": (
            RESULT_DIR
            / "spp_hct"
            / "tatonga_345_250mw"
            / "grid-data.csv"
        ),
        "woodward": (
            RESULT_DIR
            / "spp_hct"
            / "woodward_ehv_345_250mw"
            / "grid-data.csv"
        ),
    },

    "TC03": {
        "model": "DIS231-TC03ALL-24SP3",
        "tatonga": (
            RESULT_DIR
            / "spp_hct"
            / "model_cases"
            / "DIS231-TC03ALL-24SP3"
            / "tatonga_345_250mw"
            / "grid-data.csv"
        ),
        "woodward": (
            RESULT_DIR
            / "spp_hct"
            / "model_cases"
            / "DIS231-TC03ALL-24SP3"
            / "woodward_ehv_345_250mw"
            / "grid-data.csv"
        ),
    },
}


def sha256(path: Path) -> str:

    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def read_rows(
    path: Path,
) -> list[dict[str, str]]:

    with path.open(
        newline="",
        encoding="utf-8-sig",
    ) as f:

        return list(
            csv.DictReader(f)
        )


def to_float(
    value: str | None,
) -> float | None:

    if value is None:
        return None

    value = value.strip()

    if not value:
        return None

    return float(value)


def summarize(
    path: Path,
) -> dict[str, Any]:

    rows = read_rows(path)

    post = [
        value
        for row in rows
        if (
            value := to_float(
                row.get(
                    "postShiftLoading"
                )
            )
        )
        is not None
    ]

    pre = [
        value
        for row in rows
        if (
            value := to_float(
                row.get(
                    "preShiftLoading"
                )
            )
        )
        is not None
    ]

    available = [
        value
        for row in rows
        if (
            value := to_float(
                row.get(
                    "availableCapacity"
                )
            )
        )
        is not None
    ]

    shift_factors = [
        abs(value)
        for row in rows
        if (
            value := to_float(
                row.get(
                    "shiftFactor"
                )
            )
        )
        is not None
    ]

    impacts = [
        abs(value)
        for row in rows
        if (
            value := to_float(
                row.get(
                    "impact"
                )
            )
        )
        is not None
    ]

    return {
        "path": str(path),

        "sha256": sha256(
            path
        ),

        "row_count": len(
            rows
        ),

        "post_shift_overload_count": sum(
            value >= 1.0
            for value in post
        ),

        "pre_shift_overload_count": sum(
            value >= 1.0
            for value in pre
        ),

        "worst_post_shift_loading": (
            max(post)
            if post
            else None
        ),

        "worst_pre_shift_loading": (
            max(pre)
            if pre
            else None
        ),

        "minimum_available_capacity_raw": (
            min(available)
            if available
            else None
        ),

        "maximum_absolute_shift_factor": (
            max(shift_factors)
            if shift_factors
            else None
        ),

        "maximum_absolute_impact_mw": (
            max(impacts)
            if impacts
            else None
        ),
    }


def ranking_key(
    summary: dict[str, Any],
) -> tuple[Any, ...]:

    return (
        summary[
            "post_shift_overload_count"
        ],

        summary[
            "pre_shift_overload_count"
        ],

        (
            summary[
                "worst_post_shift_loading"
            ]
            if summary[
                "worst_post_shift_loading"
            ]
            is not None
            else float("inf")
        ),

        summary[
            "row_count"
        ],
    )


def preferred_poi(
    summaries: dict[
        str,
        dict[str, Any],
    ],
) -> str | None:

    ranked = sorted(
        summaries.items(),
        key=lambda item: (
            ranking_key(
                item[1]
            )
        ),
    )

    if len(ranked) < 2:
        return None

    if (
        ranking_key(
            ranked[0][1]
        )
        ==
        ranking_key(
            ranked[1][1]
        )
    ):
        return None

    return ranked[0][0]


model_results: dict[
    str,
    dict[str, Any],
] = {}


for case_name, case in CASES.items():

    summaries = {
        "TATONGA7": summarize(
            case[
                "tatonga"
            ]
        ),

        "WWRDEHV7": summarize(
            case[
                "woodward"
            ]
        ),
    }

    model_results[
        case_name
    ] = {
        "model": case[
            "model"
        ],

        "poi_results": (
            summaries
        ),

        "screening_preferred_poi": (
            preferred_poi(
                summaries
            )
        ),
    }


tc00_preferred = (
    model_results[
        "TC00"
    ][
        "screening_preferred_poi"
    ]
)

tc03_preferred = (
    model_results[
        "TC03"
    ][
        "screening_preferred_poi"
    ]
)


tatonga_unchanged = (
    model_results[
        "TC00"
    ][
        "poi_results"
    ][
        "TATONGA7"
    ][
        "sha256"
    ]
    ==
    model_results[
        "TC03"
    ][
        "poi_results"
    ][
        "TATONGA7"
    ][
        "sha256"
    ]
)


woodward_unchanged = (
    model_results[
        "TC00"
    ][
        "poi_results"
    ][
        "WWRDEHV7"
    ][
        "sha256"
    ]
    ==
    model_results[
        "TC03"
    ][
        "poi_results"
    ][
        "WWRDEHV7"
    ][
        "sha256"
    ]
)


if (
    tc00_preferred
    and
    tc03_preferred
    and
    tc00_preferred
    ==
    tc03_preferred
):

    sensitivity_status = (
        "ROBUST_ACROSS_TESTED_CASES"
    )

elif (
    tc00_preferred
    !=
    tc03_preferred
):

    sensitivity_status = (
        "MODEL_SENSITIVE"
    )

else:

    sensitivity_status = (
        "INCONCLUSIVE"
    )


result = {
    "capability": (
        "spp.compare_model_cases"
    ),

    "candidate": {
        "project_id": (
            "RDI-WOK-250-001"
        ),

        "injection_mw": 250,

        "area": "OKGE",

        "kv": 345,
    },

    "model_cases": (
        model_results
    ),

    "cross_model": {
        "sensitivity_status": (
            sensitivity_status
        ),

        "screening_preferred_poi": (
            tc00_preferred
            if (
                sensitivity_status
                ==
                "ROBUST_ACROSS_TESTED_CASES"
            )
            else None
        ),

        "tatonga_export_unchanged": (
            tatonga_unchanged
        ),

        "woodward_export_unchanged": (
            woodward_unchanged
        ),

        "tested_model_count": 2,

        "tested_poi_count": 2,
    },

    "evidence_quality": (
        "HIGH"
    ),

    "candidate_decision_confidence": (
        "MEDIUM"
    ),

    "interpretation_limits": [
        (
            "Result applies only to the "
            "two tested SPP HCT model cases."
        ),

        (
            "Identical exported results do "
            "not establish that the underlying "
            "SPP network models are identical."
        ),

        (
            "HCT screening does not establish "
            "generator-interconnection feasibility."
        ),

        (
            "The result does not establish "
            "candidate-specific upgrade cost."
        ),

        (
            "The result does not establish "
            "that TATONGA7 is the globally "
            "optimal POI."
        ),

        (
            "availableCapacity is retained as "
            "a raw HCT field and is not treated "
            "as POI hosting capacity."
        ),
    ],
}


output_path = (
    RESULT_DIR
    / "spp_hct"
    / "model_cases"
    / "poi_model_case_comparison.json"
)

output_path.parent.mkdir(
    parents=True,
    exist_ok=True,
)

output_path.write_text(
    json.dumps(
        result,
        indent=2,
    )
    + "\n"
)


print(
    "=== SPP HCT MODEL-CASE COMPARISON ==="
)

print(
    json.dumps(
        result[
            "cross_model"
        ],
        indent=2,
    )
)

print()

for case_name in [
    "TC00",
    "TC03",
]:

    case = model_results[
        case_name
    ]

    print(
        case_name,
        case[
            "model"
        ]
    )

    print(
        "Preferred POI:",
        case[
            "screening_preferred_poi"
        ],
    )

    for poi_name, summary in (
        case[
            "poi_results"
        ].items()
    ):

        print(
            f"  {poi_name}: "
            f"rows={summary['row_count']}, "
            f"post_overloads="
            f"{summary['post_shift_overload_count']}, "
            f"worst_post="
            f"{summary['worst_post_shift_loading']}"
        )

    print()


print(
    "Output:",
    output_path
)
