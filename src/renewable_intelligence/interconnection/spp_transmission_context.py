from __future__ import annotations

import csv
import json
import os
from collections import Counter
from pathlib import Path
from typing import Any


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
        return float(
            value.replace(",", "")
        )
    except ValueError:
        return None


def normalize_header(value):
    return " ".join(
        str(value or "").strip().split()
    )


def find_column(
    columns: list[str],
    required_terms: list[str],
):
    for column in columns:
        lowered = column.lower()

        if all(
            term.lower() in lowered
            for term in required_terms
        ):
            return column

    return None


def read_active_queue(
    path: Path,
) -> list[dict[str, str]]:

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:

        reader = csv.reader(f)

        # SPP row 1 contains metadata such as
        # "Last Updated On".
        next(reader)

        raw_header = next(reader)

        header = [
            normalize_header(value)
            for value in raw_header
        ]

        rows = []

        for values in reader:

            if not any(
                clean(value)
                for value in values
            ):
                continue

            # Pad short physical rows if needed.
            values = (
                values
                + [""] * (
                    len(header)
                    - len(values)
                )
            )

            rows.append(
                dict(
                    zip(
                        header,
                        values,
                    )
                )
            )

    return rows


def queue_text_context(
    rows: list[dict[str, str]],
    keyword: str,
) -> dict[str, Any]:

    if not rows:

        return {
            "keyword": keyword,
            "matched_record_count": 0,
        }

    columns = list(
        rows[0].keys()
    )

    poi_col = (
        find_column(
            columns,
            ["substation", "line"],
        )
        or find_column(
            columns,
            ["point", "interconnection"],
        )
    )

    town_col = find_column(
        columns,
        ["nearest", "town"],
    )

    status_col = find_column(
        columns,
        ["status"],
    )

    capacity_col = find_column(
        columns,
        ["capacity"],
    )

    generation_col = find_column(
        columns,
        ["generation", "type"],
    )

    fuel_col = find_column(
        columns,
        ["fuel", "type"],
    )

    state_col = find_column(
        columns,
        ["state"],
    )

    cluster_col = find_column(
        columns,
        ["cluster"],
    )


    keyword_lower = (
        keyword.lower()
    )

    matched = []

    for row in rows:

        poi_text = (
            clean(
                row.get(poi_col)
            )
            if poi_col
            else None
        )

        town_text = (
            clean(
                row.get(town_col)
            )
            if town_col
            else None
        )

        match_basis = []

        if (
            poi_text
            and keyword_lower
            in poi_text.lower()
        ):
            match_basis.append(
                "SUBSTATION_OR_LINE_TEXT"
            )

        if (
            town_text
            and keyword_lower
            in town_text.lower()
        ):
            match_basis.append(
                "NEAREST_TOWN_OR_COUNTY_TEXT"
            )

        if not match_basis:
            continue

        matched.append(
            {
                "match_basis": (
                    match_basis
                ),

                "substation_or_line": (
                    poi_text
                ),

                "nearest_town_or_county": (
                    town_text
                ),

                "state": (
                    clean(
                        row.get(
                            state_col
                        )
                    )
                    if state_col
                    else None
                ),

                "status": (
                    clean(
                        row.get(
                            status_col
                        )
                    )
                    if status_col
                    else None
                ),

                "capacity_raw_mw": (
                    number(
                        row.get(
                            capacity_col
                        )
                    )
                    if capacity_col
                    else None
                ),

                "generation_type": (
                    clean(
                        row.get(
                            generation_col
                        )
                    )
                    if generation_col
                    else None
                ),

                "fuel_type": (
                    clean(
                        row.get(
                            fuel_col
                        )
                    )
                    if fuel_col
                    else None
                ),

                "cluster": (
                    clean(
                        row.get(
                            cluster_col
                        )
                    )
                    if cluster_col
                    else None
                ),
            }
        )


    status_counts = Counter(
        item["status"] or "UNKNOWN"
        for item in matched
    )

    capacity_values = [
        item[
            "capacity_raw_mw"
        ]
        for item in matched
        if item[
            "capacity_raw_mw"
        ] is not None
    ]


    return {
        "keyword": keyword,

        "matched_record_count": (
            len(matched)
        ),

        "capacity_raw_sum_mw": (
            sum(capacity_values)
        ),

        "status_counts": dict(
            sorted(
                status_counts.items()
            )
        ),

        "records": matched,

        "interpretation_limit": (
            "This is deterministic text matching "
            "against SPP queue POI/town fields. "
            "It is not geographic proximity analysis "
            "and must not be described as projects "
            "'within X miles'."
        ),
    }


def run_transmission_context(
    *,
    state,
    task,
) -> dict[str, Any]:

    result_dir_value = (
        os.environ.get(
            "RESULT_DIR"
        )
    )

    if not result_dir_value:
        raise RuntimeError(
            "RESULT_DIR is not set."
        )

    result_dir = Path(
        result_dir_value
    )


    # --------------------------------------------------------
    # HCT comparison
    # --------------------------------------------------------

    comparison_path = (
        result_dir
        / "spp_hct"
        / "poi_comparison.json"
    )

    if not comparison_path.exists():
        raise FileNotFoundError(
            comparison_path
        )

    comparison = json.loads(
        comparison_path.read_text(
            encoding="utf-8"
        )
    )


    # --------------------------------------------------------
    # SPP active queue
    # --------------------------------------------------------

    queue_path = (
        result_dir
        / "spp_active_queue.csv"
    )

    if not queue_path.exists():
        raise FileNotFoundError(
            queue_path
        )

    queue_rows = read_active_queue(
        queue_path
    )


    queue_context = {
        "TATONGA": (
            queue_text_context(
                queue_rows,
                "Tatonga",
            )
        ),

        "WOODWARD": (
            queue_text_context(
                queue_rows,
                "Woodward",
            )
        ),
    }


    # --------------------------------------------------------
    # Known SPP precedent study
    # --------------------------------------------------------

    study_path = (
        result_dir
        / "spp_study_chain"
        / "artifacts"
        / "GEN-2026-PR2_extracted.json"
    )

    study_available = (
        study_path.exists()
    )


    preferred = comparison[
        "screening_preferred_among_tested"
    ]


    poi_by_name = {
        poi["bus_name"]: poi
        for poi in comparison[
            "pois"
        ]
    }


    preferred_detail = (
        poi_by_name.get(
            preferred[
                "bus_name"
            ]
        )
    )


    # --------------------------------------------------------
    # Deterministic interpretation
    # --------------------------------------------------------

    findings = []

    if preferred_detail:

        findings.append(
            {
                "finding_type": (
                    "POI_SCREENING_PREFERENCE"
                ),

                "poi": (
                    preferred_detail[
                        "bus_name"
                    ]
                ),

                "statement": (
                    f"{preferred_detail['bus_name']} "
                    "has lower modeled HCT constraint "
                    "exposure than the other tested POI "
                    "under the controlled comparison."
                ),

                "basis": {
                    "post_shift_overload_count": (
                        preferred_detail[
                            "post_shift_overload_count"
                        ]
                    ),

                    "base_case_overload_count": (
                        preferred_detail[
                            "base_case_overload_count"
                        ]
                    ),

                    "maximum_post_shift_loading_percent": (
                        preferred_detail[
                            "maximum_post_shift_loading_percent"
                        ]
                    ),
                },

                "evidence_class": (
                    "DERIVED_FACT"
                ),
            }
        )


    findings.append(
        {
            "finding_type": (
                "INTERCONNECTION_FEASIBILITY"
            ),

            "statement": (
                "HCT pre-screening does not establish "
                "generator interconnection feasibility, "
                "upgrade cost, or final POI selection."
            ),

            "evidence_class": (
                "UNRESOLVED"
            ),
        }
    )


    return {
        "task_id": (
            task.get(
                "task_id"
            )
        ),

        "domain": (
            "interconnection"
        ),

        "capability": (
            "spp.transmission_context"
        ),

        "executed": True,

        "project_id": (
            state.get(
                "project_id"
            )
        ),

        "hct": {
            "comparison_artifact": (
                str(
                    comparison_path
                )
            ),

            "common_assumptions": (
                comparison[
                    "common_assumptions"
                ]
            ),

            "pois": (
                comparison[
                    "pois"
                ]
            ),

            "preferred_among_tested": (
                preferred
            ),

            "confidence": (
                comparison[
                    "confidence"
                ]
            ),
        },

        "queue_context": (
            queue_context
        ),

        "study_precedent": {
            "study_id": (
                "GEN-2026-PR2"
            ),

            "artifact_available": (
                study_available
            ),

            "artifact_path": (
                str(study_path)
                if study_available
                else None
            ),

            "relationship": (
                "Known public wind-generation "
                "study precedent at Tatonga 345 kV."
            ),
        },

        "findings": findings,

        "evidence_status": (
            "PARTIAL"
        ),

        "decision_confidence": (
            "MEDIUM"
        ),

        "unresolved": [
            (
                "Only two HCT POI candidates "
                "have been compared."
            ),

            (
                "Only one HCT model case "
                "has been evaluated."
            ),

            (
                "Queue text matching does not "
                "establish geographic proximity."
            ),

            (
                "No final gen-tie route or "
                "distance has been established."
            ),

            (
                "No definitive network-upgrade "
                "cost has been established."
            ),

            (
                "Generator interconnection "
                "feasibility requires the "
                "applicable SPP study process."
            ),
        ],
    }
