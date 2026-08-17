"""
Layer 1 — deterministic unit tests for PAD-US land-status
classification logic (tribal/state/conservation flags, GAP status
lookup, missing-evidence/missing-artifact failure modes).
"""

from __future__ import annotations

import json

import pytest

from renewable_intelligence.land.land_status_screening import (
    GAP_STATUS_SCREENING_MEANING,
    _unit_screening_flags,
    resolve_land_status,
)


# --- _unit_screening_flags -------------------------------------


def test_tribal_flag_from_unit_name():

    flags = _unit_screening_flags(
        {"unit_name": "Cheyenne-Arapaho Tribal Statistical Area"}
    )

    assert "POSSIBLE_TRIBAL_LAND_INTEREST" in flags


def test_tribal_flag_from_designation():

    flags = _unit_screening_flags(
        {"designation": "Native American Lands"}
    )

    assert "POSSIBLE_TRIBAL_LAND_INTEREST" in flags


def test_tribal_flag_from_manager_type():

    flags = _unit_screening_flags(
        {"manager_type": "American Indian Lands"}
    )

    assert "POSSIBLE_TRIBAL_LAND_INTEREST" in flags


def test_state_managed_flag_requires_exact_manager_type():

    flags = _unit_screening_flags({"manager_type": "State"})

    assert "STATE_MANAGED_LAND" in flags


def test_state_managed_flag_not_set_for_partial_match():

    # manager_type is compared with == "State", not substring
    # containment, unlike the tribal/conservation checks - a
    # value like "State Land Board" should NOT match.
    flags = _unit_screening_flags(
        {"manager_type": "State Land Board"}
    )

    assert "STATE_MANAGED_LAND" not in flags


def test_conservation_flag_from_wildlife_in_name():

    flags = _unit_screening_flags(
        {"unit_name": "Canton Wildlife Management Area"}
    )

    assert "CONSERVATION_MANAGEMENT_AREA" in flags


def test_conservation_flag_from_designation():

    flags = _unit_screening_flags(
        {"designation": "Conservation Easement"}
    )

    assert "CONSERVATION_MANAGEMENT_AREA" in flags


def test_no_flags_for_unremarkable_unit():

    flags = _unit_screening_flags(
        {
            "unit_name": "Some Private Easement",
            "designation": "Fee",
            "manager_type": "Private",
        }
    )

    assert flags == []


def test_unit_missing_all_fields_produces_no_flags():

    assert _unit_screening_flags({}) == []


def test_unit_can_carry_multiple_flags_at_once():

    flags = _unit_screening_flags(
        {
            "unit_name": "Tribal Wildlife Management Area",
            "manager_type": "State",
        }
    )

    assert set(flags) == {
        "POSSIBLE_TRIBAL_LAND_INTEREST",
        "STATE_MANAGED_LAND",
        "CONSERVATION_MANAGEMENT_AREA",
    }


# --- resolve_land_status: evidence resolution failure modes ----


def test_missing_evidence_raises_runtime_error():

    with pytest.raises(RuntimeError):
        resolve_land_status(state={}, task={})


def test_missing_artifact_path_raises_runtime_error():

    with pytest.raises(RuntimeError):
        resolve_land_status(
            state={"land_status_evidence": {}}, task={}
        )


def test_missing_artifact_file_raises_file_not_found(tmp_path):

    with pytest.raises(FileNotFoundError):
        resolve_land_status(
            state={
                "land_status_evidence": {
                    "padus_summary_artifact": str(
                        tmp_path / "missing.json"
                    )
                }
            },
            task={},
        )


# --- resolve_land_status: end-to-end classification ------------


def _write_padus_artifact(tmp_path, units):

    artifact = {
        "source": {"authority": "USGS", "dataset": "PAD-US"},
        "candidate_area_acres": 1000,
        "padus_unique_overlap": {
            "acres": 250,
            "percent_of_candidate": 25.0,
        },
        "units": units,
    }

    path = tmp_path / "padus.json"
    path.write_text(json.dumps(artifact), encoding="utf-8")

    return path


def test_gap_status_meaning_looked_up_for_known_code(tmp_path):

    path = _write_padus_artifact(
        tmp_path,
        [
            {
                "unit_name": "Some Unit",
                "gap_status": "2",
                "candidate_overlap_acres": 10,
            }
        ],
    )

    result = resolve_land_status(
        state={
            "land_status_evidence": {
                "padus_summary_artifact": str(path)
            }
        },
        task={},
    )

    assert (
        result["units"][0]["gap_status_screening_meaning"]
        == GAP_STATUS_SCREENING_MEANING["2"]
    )


def test_gap_status_meaning_falls_back_for_unknown_code(tmp_path):

    path = _write_padus_artifact(
        tmp_path,
        [
            {
                "unit_name": "Some Unit",
                "gap_status": "99",
                "candidate_overlap_acres": 10,
            }
        ],
    )

    result = resolve_land_status(
        state={
            "land_status_evidence": {
                "padus_summary_artifact": str(path)
            }
        },
        task={},
    )

    assert (
        result["units"][0]["gap_status_screening_meaning"]
        == "Unknown GAP status."
    )


def test_units_sorted_by_overlap_acres_descending(tmp_path):

    path = _write_padus_artifact(
        tmp_path,
        [
            {"unit_name": "Small", "candidate_overlap_acres": 5},
            {"unit_name": "Big", "candidate_overlap_acres": 500},
            {
                "unit_name": "Medium",
                "candidate_overlap_acres": 50,
            },
        ],
    )

    result = resolve_land_status(
        state={
            "land_status_evidence": {
                "padus_summary_artifact": str(path)
            }
        },
        task={},
    )

    names = [u["unit_name"] for u in result["units"]]

    assert names == ["Big", "Medium", "Small"]


def test_finding_flags_set_when_any_unit_matches(tmp_path):

    path = _write_padus_artifact(
        tmp_path,
        [
            {
                "unit_name": "Tribal Statistical Area",
                "candidate_overlap_acres": 100,
            },
            {
                "unit_name": "State Trust Parcel",
                "manager_type": "State",
                "candidate_overlap_acres": 50,
            },
        ],
    )

    result = resolve_land_status(
        state={
            "land_status_evidence": {
                "padus_summary_artifact": str(path)
            }
        },
        task={},
    )

    assert result["finding"]["tribal_interest_flagged"] is True
    assert (
        result["finding"]["state_managed_land_flagged"] is True
    )
    assert (
        result["finding"]["conservation_area_flagged"] is False
    )


def test_finding_flags_false_when_no_units(tmp_path):

    path = _write_padus_artifact(tmp_path, [])

    result = resolve_land_status(
        state={
            "land_status_evidence": {
                "padus_summary_artifact": str(path)
            }
        },
        task={},
    )

    assert result["finding"]["tribal_interest_flagged"] is False
    assert (
        result["finding"]["state_managed_land_flagged"] is False
    )
    assert (
        result["finding"]["conservation_area_flagged"] is False
    )
    assert result["finding"]["unit_count"] == 0
