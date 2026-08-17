from __future__ import annotations

import csv
import hashlib
from pathlib import Path
from typing import Any


def to_float(
    value: str | None,
) -> float | None:

    if value is None:
        return None

    value = str(
        value
    ).strip()

    if not value:
        return None

    return float(
        value
    )


def sha256_file(
    path: Path,
) -> str:

    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def read_hct_rows(
    path: Path,
) -> list[dict[str, str]]:

    if not path.exists():

        raise FileNotFoundError(
            f"HCT artifact not found: {path}"
        )

    with path.open(
        newline="",
        encoding="utf-8-sig",
    ) as f:

        return list(
            csv.DictReader(
                f
            )
        )


def numeric_values(
    rows: list[dict[str, str]],
    field: str,
    *,
    absolute: bool = False,
) -> list[float]:

    result: list[float] = []

    for row in rows:

        value = to_float(
            row.get(
                field
            )
        )

        if value is None:
            continue

        if absolute:
            value = abs(
                value
            )

        result.append(
            value
        )

    return result


def summarize_hct_artifact(
    path: Path,
) -> dict[str, Any]:

    rows = read_hct_rows(
        path
    )

    post = numeric_values(
        rows,
        "postShiftLoading",
    )

    pre = numeric_values(
        rows,
        "preShiftLoading",
    )

    available = numeric_values(
        rows,
        "availableCapacity",
    )

    shift_factors = numeric_values(
        rows,
        "shiftFactor",
        absolute=True,
    )

    impacts = numeric_values(
        rows,
        "impact",
        absolute=True,
    )


    new_overload_crossings = 0

    existing_overloads_aggravated = 0


    for row in rows:

        pre_value = to_float(
            row.get(
                "preShiftLoading"
            )
        )

        post_value = to_float(
            row.get(
                "postShiftLoading"
            )
        )

        if (
            pre_value is None
            or post_value is None
        ):
            continue


        if (
            pre_value < 1.0
            and post_value >= 1.0
        ):

            new_overload_crossings += 1


        if (
            pre_value >= 1.0
            and post_value > pre_value
        ):

            existing_overloads_aggravated += 1


    return {
        "source_artifact": str(
            path
        ),

        "sha256": sha256_file(
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

        "new_overload_crossing_count": (
            new_overload_crossings
        ),

        "existing_overload_aggravation_count": (
            existing_overloads_aggravated
        ),

        "worst_post_shift_loading": (
            max(
                post
            )
            if post
            else None
        ),

        "worst_pre_shift_loading": (
            max(
                pre
            )
            if pre
            else None
        ),

        "minimum_available_capacity_raw": (
            min(
                available
            )
            if available
            else None
        ),

        "maximum_absolute_shift_factor": (
            max(
                shift_factors
            )
            if shift_factors
            else None
        ),

        "maximum_absolute_impact_mw": (
            max(
                impacts
            )
            if impacts
            else None
        ),
    }


def hct_screening_ranking_key(
    summary: dict[str, Any],
) -> tuple[Any, ...]:

    """
    Deterministic screening ordering only.

    Lower is preferred.

    This preserves the existing project ranking policy.
    It is NOT an interconnection viability score.
    """

    worst_post = summary.get(
        "worst_post_shift_loading"
    )

    return (
        summary[
            "post_shift_overload_count"
        ],

        summary[
            "pre_shift_overload_count"
        ],

        (
            worst_post
            if worst_post is not None
            else float(
                "inf"
            )
        ),

        summary[
            "row_count"
        ],
    )


def rank_pois(
    summaries: dict[
        str,
        dict[str, Any],
    ],
) -> list[str]:

    return [
        poi_name
        for poi_name, _
        in sorted(
            summaries.items(),
            key=lambda item: (
                hct_screening_ranking_key(
                    item[1]
                )
            ),
        )
    ]


def screening_preferred_poi(
    summaries: dict[
        str,
        dict[str, Any],
    ],
) -> str | None:

    if len(
        summaries
    ) < 2:

        return None


    ranked = sorted(
        summaries.items(),
        key=lambda item: (
            hct_screening_ranking_key(
                item[1]
            )
        ),
    )


    first_key = (
        hct_screening_ranking_key(
            ranked[0][1]
        )
    )

    second_key = (
        hct_screening_ranking_key(
            ranked[1][1]
        )
    )


    if (
        first_key
        == second_key
    ):

        return None


    return ranked[0][0]
