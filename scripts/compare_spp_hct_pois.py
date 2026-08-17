#!/usr/bin/env python3

import csv
import json
import math
import os
from pathlib import Path


RESULT_DIR = Path(
    os.environ["RESULT_DIR"]
)

HCT_DIR = (
    RESULT_DIR
    / "spp_hct"
)

POI_DIRS = [
    HCT_DIR / "tatonga_345_250mw",
    HCT_DIR / "woodward_ehv_345_250mw",
]


def clean(value):
    if value is None:
        return None

    value = str(value).strip()

    return value or None


def number(value):
    value = clean(value)

    if value is None:
        return None

    try:
        return float(value)
    except ValueError:
        return None


def is_base_case(value):
    value = (
        clean(value)
        or ""
    ).upper()

    return (
        not value
        or "BASE CASE" in value
        or value == "BASE"
    )


def load_poi(directory: Path):

    query_path = (
        directory
        / "query.json"
    )

    csv_path = (
        directory
        / "grid-data.csv"
    )

    query = json.loads(
        query_path.read_text(
            encoding="utf-8"
        )
    )

    with csv_path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:

        rows = list(
            csv.DictReader(f)
        )

    return {
        "directory": str(directory),
        "query": query["query"],
        "rows": rows,
    }


def summarize(poi):

    rows = poi["rows"]

    normalized = []

    for row in rows:

        pre = number(
            row.get(
                "preShiftLoading"
            )
        )

        post = number(
            row.get(
                "postShiftLoading"
            )
        )

        shift = number(
            row.get(
                "shiftFactor"
            )
        )

        impact = number(
            row.get(
                "impact"
            )
        )

        available = number(
            row.get(
                "availableCapacity"
            )
        )

        contingency = clean(
            row.get(
                "contingencyElement"
            )
        )

        base_case = (
            is_base_case(
                contingency
            )
        )

        overloaded = bool(
            post is not None
            and post >= 1.0
        )

        normalized.append(
            {
                "monitored_facility": clean(
                    row.get(
                        "monitoredFacility"
                    )
                ),

                "contingency_element": (
                    contingency
                ),

                "available_capacity_raw": (
                    available
                ),

                "shift_factor": (
                    shift
                ),

                "impact_mw": (
                    impact
                ),

                "pre_shift_loading_ratio": (
                    pre
                ),

                "pre_shift_loading_percent": (
                    pre * 100
                    if pre is not None
                    else None
                ),

                "post_shift_loading_ratio": (
                    post
                ),

                "post_shift_loading_percent": (
                    post * 100
                    if post is not None
                    else None
                ),

                "is_base_case": (
                    base_case
                ),

                "post_shift_overload": (
                    overloaded
                ),
            }
        )


    posts = [
        row[
            "post_shift_loading_percent"
        ]
        for row in normalized
        if row[
            "post_shift_loading_percent"
        ] is not None
    ]

    pres = [
        row[
            "pre_shift_loading_percent"
        ]
        for row in normalized
        if row[
            "pre_shift_loading_percent"
        ] is not None
    ]

    shifts = [
        abs(
            row[
                "shift_factor"
            ]
        )
        for row in normalized
        if row[
            "shift_factor"
        ] is not None
    ]

    impacts = [
        abs(
            row[
                "impact_mw"
            ]
        )
        for row in normalized
        if row[
            "impact_mw"
        ] is not None
    ]

    capacities = [
        row[
            "available_capacity_raw"
        ]
        for row in normalized
        if row[
            "available_capacity_raw"
        ] is not None
    ]


    overload_count = sum(
        1
        for row in normalized
        if row[
            "post_shift_overload"
        ]
    )

    base_case_rows = [
        row
        for row in normalized
        if row[
            "is_base_case"
        ]
    ]

    base_case_overloads = sum(
        1
        for row in base_case_rows
        if row[
            "post_shift_overload"
        ]
    )


    top_constraints = sorted(
        normalized,
        key=lambda row: (
            row[
                "post_shift_loading_percent"
            ]
            if row[
                "post_shift_loading_percent"
            ] is not None
            else -math.inf
        ),
        reverse=True,
    )[:5]


    return {
        "bus_id": (
            poi["query"][
                "bus_id"
            ]
        ),

        "bus_name": (
            poi["query"][
                "bus_name"
            ]
        ),

        "model": (
            poi["query"][
                "model"
            ]
        ),

        "area": (
            poi["query"][
                "area"
            ]
        ),

        "kv": (
            poi["query"][
                "kv"
            ]
        ),

        "injection_mw": (
            poi["query"][
                "injection_mw"
            ]
        ),

        "result_count": (
            len(normalized)
        ),

        "post_shift_overload_count": (
            overload_count
        ),

        "base_case_result_count": (
            len(base_case_rows)
        ),

        "base_case_overload_count": (
            base_case_overloads
        ),

        "maximum_pre_shift_loading_percent": (
            max(pres)
            if pres
            else None
        ),

        "maximum_post_shift_loading_percent": (
            max(posts)
            if posts
            else None
        ),

        "minimum_available_capacity_raw": (
            min(capacities)
            if capacities
            else None
        ),

        "maximum_absolute_shift_factor": (
            max(shifts)
            if shifts
            else None
        ),

        "maximum_absolute_impact_mw": (
            max(impacts)
            if impacts
            else None
        ),

        "top_constraints": (
            top_constraints
        ),
    }


pois = [
    load_poi(path)
    for path in POI_DIRS
]


# ------------------------------------------------------------
# Verify this is truly a controlled comparison
# ------------------------------------------------------------

comparison_fields = [
    "model",
    "area",
    "kv",
    "injection_mw",
]

reference = (
    pois[0][
        "query"
    ]
)

for poi in pois[1:]:

    for field in comparison_fields:

        if (
            poi[
                "query"
            ][field]
            != reference[field]
        ):
            raise RuntimeError(
                "Cannot compare POIs: "
                f"{field} differs. "
                f"{reference[field]!r} vs "
                f"{poi['query'][field]!r}"
            )


summaries = [
    summarize(poi)
    for poi in pois
]


# ------------------------------------------------------------
# Deterministic comparison
#
# Do NOT use availableCapacity as a POI hosting-limit score.
#
# Lower is better, in this order:
#
# 1. post-shift overload count
# 2. base-case overload count
# 3. worst post-shift loading
# 4. number of returned constraint rows
# ------------------------------------------------------------

def comparison_key(summary):

    return (
        summary[
            "post_shift_overload_count"
        ],

        summary[
            "base_case_overload_count"
        ],

        (
            summary[
                "maximum_post_shift_loading_percent"
            ]
            if summary[
                "maximum_post_shift_loading_percent"
            ] is not None
            else float("inf")
        ),

        summary[
            "result_count"
        ],
    )


ranked = sorted(
    summaries,
    key=comparison_key,
)


preferred = ranked[0]


result = {
    "comparison_type": (
        "SPP_HCT_CONTROLLED_POI_COMPARISON"
    ),

    "scenario": (
        "RDI-WOK-250-001"
    ),

    "common_assumptions": {
        field: reference[field]
        for field in comparison_fields
    },

    "pois": summaries,

    "screening_preferred_among_tested": {
        "bus_id": (
            preferred[
                "bus_id"
            ]
        ),

        "bus_name": (
            preferred[
                "bus_name"
            ]
        ),

        "basis": [
            (
                "Fewer post-shift overload "
                "conditions is preferred."
            ),

            (
                "Fewer base-case overload "
                "conditions is preferred."
            ),

            (
                "Lower worst post-shift loading "
                "is preferred."
            ),

            (
                "Returned HCT constraint count "
                "is used only after overload and "
                "loading measures."
            ),
        ],
    },

    "confidence": "MEDIUM",

    "confidence_basis": [
        (
            "Only two candidate POIs have "
            "been compared."
        ),

        (
            "Only one SPP HCT model case "
            "has been evaluated."
        ),

        (
            "HCT is an early-stage "
            "pre-screening tool rather than "
            "a generator interconnection study."
        ),
    ],

    "limitations": [
        (
            "This comparison does not establish "
            "interconnection feasibility."
        ),

        (
            "This comparison does not estimate "
            "network-upgrade cost."
        ),

        (
            "This comparison does not establish "
            "the physically shortest or lowest-cost "
            "gen-tie route from the candidate site."
        ),

        (
            "availableCapacity is retained as "
            "an HCT source field and is not "
            "interpreted as POI hosting capacity."
        ),
    ],
}


output_path = (
    HCT_DIR
    / "poi_comparison.json"
)

output_path.write_text(
    json.dumps(
        result,
        indent=2,
    ),
    encoding="utf-8",
)


print(
    "=== SPP HCT POI COMPARISON ==="
)

print(
    "Model:",
    reference[
        "model"
    ],
)

print(
    "Area:",
    reference[
        "area"
    ],
)

print(
    "Voltage:",
    reference[
        "kv"
    ],
    "kV",
)

print(
    "Injection:",
    reference[
        "injection_mw"
    ],
    "MW",
)


for summary in summaries:

    print()
    print(
        "=== ",
        summary[
            "bus_name"
        ],
        " ===",
        sep="",
    )

    print(
        "Result rows:",
        summary[
            "result_count"
        ],
    )

    print(
        "Post-shift overloads:",
        summary[
            "post_shift_overload_count"
        ],
    )

    print(
        "Base-case rows:",
        summary[
            "base_case_result_count"
        ],
    )

    print(
        "Base-case overloads:",
        summary[
            "base_case_overload_count"
        ],
    )

    print(
        "Worst post-shift loading:",
        (
            f"{summary['maximum_post_shift_loading_percent']:.2f}%"
            if summary[
                "maximum_post_shift_loading_percent"
            ] is not None
            else "N/A"
        ),
    )

    print(
        "Min availableCapacity (raw):",
        summary[
            "minimum_available_capacity_raw"
        ],
    )

    print(
        "Max |shift factor|:",
        summary[
            "maximum_absolute_shift_factor"
        ],
    )

    print(
        "Max |impact|:",
        summary[
            "maximum_absolute_impact_mw"
        ],
        "MW",
    )


print()
print(
    "=== SCREENING PREFERENCE ==="
)

print(
    preferred[
        "bus_name"
    ],
)

print(
    "Confidence:",
    result[
        "confidence"
    ],
)

print()
print(
    "This means preferred among tested HCT "
    "cases, NOT approved for interconnection."
)

print()
print(
    "Output:",
    output_path,
)
