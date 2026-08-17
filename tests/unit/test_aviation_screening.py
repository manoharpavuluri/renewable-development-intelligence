"""
Layer 1 — deterministic unit tests for aviation-artifact field
mapping (nearest public-use airport, statutory-setback flag,
Special Use Airspace intersection count) and failure modes.
"""

from __future__ import annotations

import json

import pytest

from renewable_intelligence.aviation.aviation_screening import (
    screen_candidate,
)


def _write_artifact(
    tmp_path,
    *,
    nearest_public_use=None,
    sua_count=0,
    setback_violated=None,
):

    artifact = {
        "source": {"authority": "FAA"},
        "screening_radius_miles": 15,
        "statutory_airport_setback_nm": 1.5,
        "airports_within_screening_radius_count": 3,
        "public_use_airports_within_screening_radius_count": 1,
        "nearest_public_use_airport": nearest_public_use,
        "statutory_setback_appears_violated": setback_violated,
        "military_special_use_airspace_intersection_count": (
            sua_count
        ),
        "airports_within_screening_radius": [],
        "military_special_use_airspace_intersections": [],
    }

    path = tmp_path / "aviation.json"
    path.write_text(json.dumps(artifact), encoding="utf-8")

    return path


def _run(tmp_path, **kwargs):

    path = _write_artifact(tmp_path, **kwargs)

    return screen_candidate(
        state={
            "aviation_evidence": {
                "aviation_summary_artifact": str(path)
            }
        },
        task={},
    )


def test_missing_evidence_raises_runtime_error():

    with pytest.raises(RuntimeError):
        screen_candidate(state={}, task={})


def test_missing_artifact_file_raises_file_not_found(tmp_path):

    with pytest.raises(FileNotFoundError):
        screen_candidate(
            state={
                "aviation_evidence": {
                    "aviation_summary_artifact": str(
                        tmp_path / "missing.json"
                    )
                }
            },
            task={},
        )


def test_no_nearest_airport_fields_are_none(tmp_path):

    result = _run(tmp_path, nearest_public_use=None)

    finding = result["finding"]

    assert finding["nearest_public_use_airport_name"] is None
    assert (
        finding["nearest_public_use_airport_distance_nm"]
        is None
    )


def test_nearest_airport_fields_mapped_through(tmp_path):

    result = _run(
        tmp_path,
        nearest_public_use={
            "name": "Regional Field",
            "distance_to_candidate_nm": 4.2,
        },
    )

    finding = result["finding"]

    assert (
        finding["nearest_public_use_airport_name"]
        == "Regional Field"
    )
    assert (
        finding["nearest_public_use_airport_distance_nm"]
        == 4.2
    )


def test_setback_violation_flag_mapped_through(tmp_path):

    violated = _run(tmp_path, setback_violated=True)
    clear = _run(tmp_path, setback_violated=False)

    assert (
        violated["finding"]["statutory_setback_appears_violated"]
        is True
    )
    assert (
        clear["finding"]["statutory_setback_appears_violated"]
        is False
    )


def test_sua_intersection_count_mapped_through(tmp_path):

    result = _run(tmp_path, sua_count=2)

    assert (
        result["finding"][
            "military_special_use_airspace_intersection_count"
        ]
        == 2
    )


def test_sua_intersection_count_defaults_to_zero_when_absent(
    tmp_path,
):

    path = tmp_path / "aviation.json"
    path.write_text(
        json.dumps(
            {
                "source": {"authority": "FAA"},
            }
        ),
        encoding="utf-8",
    )

    result = screen_candidate(
        state={
            "aviation_evidence": {
                "aviation_summary_artifact": str(path)
            }
        },
        task={},
    )

    assert (
        result["finding"][
            "military_special_use_airspace_intersection_count"
        ]
        == 0
    )


def test_no_faa_determination_claimed_obtained(tmp_path):

    result = _run(tmp_path)

    finding = result["finding"]

    assert finding["faa_part77_notice_filed"] is False
    assert (
        finding["faa_airspace_determination_obtained"] is False
    )
