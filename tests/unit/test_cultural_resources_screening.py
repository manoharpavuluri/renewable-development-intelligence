"""
Layer 1 — deterministic unit tests for NRHP intersection /
National Historic Landmark flagging semantics.
"""

from __future__ import annotations

import json

import pytest

from renewable_intelligence.environmental.cultural_resources_screening import (
    screen_cultural_resources,
)


def _write_artifact(
    tmp_path, *, direct_intersections=None, nearby_sites=None
):

    artifact = {
        "source": {"authority": "NPS"},
        "screening_radius_miles": 5,
        "direct_intersection_count": len(
            direct_intersections or []
        ),
        "nearby_site_count_within_radius": len(
            nearby_sites or []
        ),
        "direct_intersections": direct_intersections or [],
        "nearby_sites_within_radius": nearby_sites or [],
    }

    path = tmp_path / "nrhp.json"
    path.write_text(json.dumps(artifact), encoding="utf-8")

    return path


def _run(tmp_path, **kwargs):

    path = _write_artifact(tmp_path, **kwargs)

    return screen_cultural_resources(
        state={
            "cultural_resources_evidence": {
                "nrhp_summary_artifact": str(path)
            }
        },
        task={},
    )


def test_missing_evidence_raises_runtime_error():

    with pytest.raises(RuntimeError):
        screen_cultural_resources(state={}, task={})


def test_missing_artifact_file_raises_file_not_found(tmp_path):

    with pytest.raises(FileNotFoundError):
        screen_cultural_resources(
            state={
                "cultural_resources_evidence": {
                    "nrhp_summary_artifact": str(
                        tmp_path / "missing.json"
                    )
                }
            },
            task={},
        )


def test_no_intersections_no_nhl_flag(tmp_path):

    result = _run(tmp_path)

    finding = result["finding"]

    assert finding["direct_intersection_count"] == 0
    assert (
        finding["national_historic_landmark_flagged"] is False
    )
    assert finding["direct_intersection_resource_names"] == []


def test_direct_intersection_without_nhl_status(tmp_path):

    result = _run(
        tmp_path,
        direct_intersections=[
            {"RESNAME": "Old Schoolhouse", "Is_NHL": False}
        ],
    )

    finding = result["finding"]

    assert finding["direct_intersection_count"] == 1
    assert (
        finding["national_historic_landmark_flagged"] is False
    )
    assert finding["direct_intersection_resource_names"] == [
        "Old Schoolhouse"
    ]


def test_nhl_flagged_from_direct_intersection(tmp_path):

    result = _run(
        tmp_path,
        direct_intersections=[
            {"RESNAME": "Fort Site", "Is_NHL": True}
        ],
    )

    assert (
        result["finding"][
            "national_historic_landmark_flagged"
        ]
        is True
    )


def test_nhl_flagged_from_nearby_site_even_without_direct_intersection(
    tmp_path,
):

    # NHL flag is an OR across BOTH lists - a landmark just
    # outside the candidate polygon still matters at screening
    # level, even with zero direct intersections.
    result = _run(
        tmp_path,
        direct_intersections=[],
        nearby_sites=[
            {
                "RESNAME": "Nearby Landmark",
                "is_national_historic_landmark": True,
            }
        ],
    )

    finding = result["finding"]

    assert finding["direct_intersection_count"] == 0
    assert (
        finding["national_historic_landmark_flagged"] is True
    )


def test_resource_names_list_preserves_order_and_missing_names(
    tmp_path,
):

    result = _run(
        tmp_path,
        direct_intersections=[
            {"RESNAME": "Site A"},
            {},
            {"RESNAME": "Site C"},
        ],
    )

    assert result["finding"][
        "direct_intersection_resource_names"
    ] == ["Site A", None, "Site C"]
