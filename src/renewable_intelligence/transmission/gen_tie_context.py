from __future__ import annotations

from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd


CAPABILITY_NAME = (
    "transmission.assess_gen_tie_context"
)

METERS_PER_MILE = 1609.344


def _resolve_inputs(
    *,
    state: dict[str, Any],
    task: dict[str, Any],
) -> dict[str, Any]:

    evidence = (
        task.get(
            "transmission_context_evidence"
        )
        or state.get(
            "transmission_context_evidence"
        )
    )

    if not evidence:

        raise RuntimeError(
            "transmission.assess_gen_tie_context "
            "requires transmission_context_evidence."
        )


    candidate_geometry = evidence.get(
        "candidate_geometry"
    )

    transmission_lines_artifact = evidence.get(
        "transmission_lines_artifact"
    )


    if not candidate_geometry:

        raise RuntimeError(
            "Candidate geometry evidence "
            "was not supplied."
        )


    if not transmission_lines_artifact:

        raise RuntimeError(
            "Transmission-line evidence "
            "was not supplied."
        )


    return {
        "candidate_geometry": (
            Path(
                candidate_geometry
            )
        ),

        "transmission_lines_artifact": (
            Path(
                transmission_lines_artifact
            )
        ),

        "target_name": (
            evidence.get(
                "target_name",
                "TATONGA",
            )
        ),

        "minimum_voltage_kv": (
            float(
                evidence.get(
                    "minimum_voltage_kv",
                    230,
                )
            )
        ),

        "target_voltage_kv": (
            float(
                evidence.get(
                    "target_voltage_kv",
                    345,
                )
            )
        ),
    }


def _utm_epsg(
    candidate: gpd.GeoDataFrame,
) -> int:

    candidate_wgs84 = (
        candidate.to_crs(
            4326
        )
    )

    centroid = (
        candidate_wgs84.geometry
        .union_all()
        .centroid
    )

    longitude = centroid.x
    latitude = centroid.y

    zone = int(
        (
            longitude
            + 180
        )
        // 6
    ) + 1

    if latitude >= 0:

        return (
            32600
            + zone
        )

    return (
        32700
        + zone
    )


def _contains_name(
    value: Any,
    target_name: str,
) -> bool:

    if value is None:
        return False

    return (
        target_name.upper()
        in str(value).upper()
    )


def _record(
    row,
) -> dict[str, Any]:

    return {
        "id": (
            row.get(
                "ID"
            )
        ),

        "owner": (
            row.get(
                "OWNER"
            )
        ),

        "voltage_kv": (
            row.get(
                "VOLTAGE"
            )
        ),

        "voltage_class": (
            row.get(
                "VOLT_CLASS"
            )
        ),

        "status": (
            row.get(
                "STATUS"
            )
        ),

        "substation_name_1": (
            row.get(
                "SUB_1"
            )
        ),

        "substation_name_2": (
            row.get(
                "SUB_2"
            )
        ),

        "distance_to_candidate_miles": (
            round(
                float(
                    row[
                        "distance_to_candidate_miles"
                    ]
                ),
                3,
            )
        ),

        "intersects_candidate": (
            bool(
                row[
                    "intersects_candidate"
                ]
            )
        ),

        "source": (
            row.get(
                "SOURCE"
            )
        ),

        "source_date": (
            row.get(
                "SOURCEDATE"
            )
        ),

        "validation_method": (
            row.get(
                "VAL_METHOD"
            )
        ),

        "voltage_inferred": (
            row.get(
                "INFERRED"
            )
        ),
    }


def assess_gen_tie_context(
    *,
    state,
    task,
) -> dict[str, Any]:

    inputs = _resolve_inputs(
        state=state,
        task=task,
    )


    candidate_path = inputs[
        "candidate_geometry"
    ]

    lines_path = inputs[
        "transmission_lines_artifact"
    ]

    target_name = inputs[
        "target_name"
    ]

    minimum_voltage_kv = inputs[
        "minimum_voltage_kv"
    ]

    target_voltage_kv = inputs[
        "target_voltage_kv"
    ]


    if not candidate_path.exists():

        raise FileNotFoundError(
            candidate_path
        )


    if not lines_path.exists():

        raise FileNotFoundError(
            lines_path
        )


    candidate = gpd.read_file(
        candidate_path
    )

    lines = gpd.read_file(
        lines_path
    )


    if candidate.empty:

        raise RuntimeError(
            "Candidate geometry is empty."
        )


    if lines.empty:

        raise RuntimeError(
            "Transmission-line evidence is empty."
        )


    candidate = candidate.to_crs(
        4326
    )

    lines = lines.to_crs(
        4326
    )


    if "VOLTAGE" not in lines.columns:

        raise RuntimeError(
            "Transmission evidence is missing "
            "the VOLTAGE field."
        )


    lines[
        "VOLTAGE_NUMERIC"
    ] = pd.to_numeric(
        lines[
            "VOLTAGE"
        ],
        errors="coerce",
    )


    lines = lines[
        lines[
            "VOLTAGE_NUMERIC"
        ]
        >= minimum_voltage_kv
    ].copy()


    if lines.empty:

        raise RuntimeError(
            "No transmission lines met the "
            "minimum-voltage screening threshold."
        )


    epsg = _utm_epsg(
        candidate
    )


    candidate_m = (
        candidate.to_crs(
            epsg
        )
    )

    lines_m = (
        lines.to_crs(
            epsg
        )
    )


    candidate_union_m = (
        candidate_m.geometry
        .union_all()
    )


    lines[
        "distance_to_candidate_miles"
    ] = (
        lines_m.geometry.distance(
            candidate_union_m
        )
        / METERS_PER_MILE
    ).values


    candidate_union = (
        candidate.geometry
        .union_all()
    )


    lines[
        "intersects_candidate"
    ] = (
        lines.geometry.intersects(
            candidate_union
        )
    )


    target_voltage_lines = lines[
        lines[
            "VOLTAGE_NUMERIC"
        ]
        == target_voltage_kv
    ].copy()


    sub_1 = (
        lines[
            "SUB_1"
        ]
        if "SUB_1" in lines.columns
        else pd.Series(
            None,
            index=lines.index,
        )
    )

    sub_2 = (
        lines[
            "SUB_2"
        ]
        if "SUB_2" in lines.columns
        else pd.Series(
            None,
            index=lines.index,
        )
    )


    target_mask = (
        sub_1.map(
            lambda value: _contains_name(
                value,
                target_name,
            )
        )
        |
        sub_2.map(
            lambda value: _contains_name(
                value,
                target_name,
            )
        )
    )


    target_named_lines = (
        lines[
            target_mask
        ]
        .copy()
        .sort_values(
            "distance_to_candidate_miles"
        )
    )


    nearest_high_voltage = (
        lines.sort_values(
            "distance_to_candidate_miles"
        )
        .head(
            20
        )
    )


    nearest_target_voltage = (
        target_voltage_lines.sort_values(
            "distance_to_candidate_miles"
        )
        .head(
            20
        )
    )


    nearest_hv_distance = (
        float(
            nearest_high_voltage.iloc[
                0
            ][
                "distance_to_candidate_miles"
            ]
        )
        if not nearest_high_voltage.empty
        else None
    )


    nearest_target_voltage_distance = (
        float(
            nearest_target_voltage.iloc[
                0
            ][
                "distance_to_candidate_miles"
            ]
        )
        if not nearest_target_voltage.empty
        else None
    )


    nearest_target_named_distance = (
        float(
            target_named_lines.iloc[
                0
            ][
                "distance_to_candidate_miles"
            ]
        )
        if not target_named_lines.empty
        else None
    )


    finding = {
        "public_line_context_status": (
            "AVAILABLE"
        ),

        "target_name_context_status": (
            "FOUND"
            if not target_named_lines.empty
            else "NOT_FOUND"
        ),

        "minimum_voltage_kv": (
            minimum_voltage_kv
        ),

        "target_voltage_kv": (
            target_voltage_kv
        ),

        "high_voltage_line_count": (
            len(
                lines
            )
        ),

        "target_voltage_line_count": (
            len(
                target_voltage_lines
            )
        ),

        "candidate_intersection_count": (
            int(
                lines[
                    "intersects_candidate"
                ].sum()
            )
        ),

        "target_named_line_count": (
            len(
                target_named_lines
            )
        ),

        "nearest_high_voltage_line_miles": (
            round(
                nearest_hv_distance,
                3,
            )
            if nearest_hv_distance
            is not None
            else None
        ),

        "nearest_target_voltage_line_miles": (
            round(
                nearest_target_voltage_distance,
                3,
            )
            if nearest_target_voltage_distance
            is not None
            else None
        ),

        "nearest_target_named_line_miles": (
            round(
                nearest_target_named_distance,
                3,
            )
            if nearest_target_named_distance
            is not None
            else None
        ),

        "exact_target_bus_geometry_established": (
            False
        ),

        "constructible_gen_tie_route_established": (
            False
        ),

        "row_availability_established": (
            False
        ),

        "gen_tie_cost_established": (
            False
        ),

        "interconnection_feasibility_established": (
            False
        ),
    }


    return {
        "task_id": (
            task.get(
                "task_id"
            )
            or task.get(
                "action_id"
            )
        ),

        "capability": (
            CAPABILITY_NAME
        ),

        "executed": True,

        "relationship": (
            "CANDIDATE_SCREENING"
        ),

        "finding": (
            finding
        ),

        "nearest_high_voltage_lines": [
            _record(
                row
            )
            for _, row
            in nearest_high_voltage.iterrows()
        ],

        "nearest_target_voltage_lines": [
            _record(
                row
            )
            for _, row
            in nearest_target_voltage.iterrows()
        ],

        "target_named_lines": [
            _record(
                row
            )
            for _, row
            in target_named_lines.iterrows()
        ],

        "evidence_quality": (
            "MEDIUM"
        ),

        "evidence_quality_reason": (
            "Public transmission-line geometry provides "
            "useful screening context, but endpoint naming "
            "does not establish authoritative SPP bus "
            "geometry and some voltage/source attributes "
            "are inferred or imagery-derived."
        ),

        "candidate_applicability": (
            "MEDIUM"
        ),

        "interpretation_limits": [
            (
                "Distances are from the candidate "
                "polygon to public transmission-line "
                "geometry, not to an authoritative "
                "SPP bus coordinate."
            ),

            (
                "SUB_1 and SUB_2 are endpoint-name "
                "context and do not establish exact "
                "substation-point geometry."
            ),

            (
                "A target-named transmission line "
                "does not establish the exact "
                "location of the requested SPP bus."
            ),

            (
                "The nearest public transmission "
                "line is not automatically a viable "
                "gen-tie connection."
            ),

            (
                "This screening does not establish "
                "ROW availability or a constructible "
                "gen-tie route."
            ),

            (
                "This screening does not establish "
                "gen-tie cost or generator-"
                "interconnection feasibility."
            ),
        ],
    }
