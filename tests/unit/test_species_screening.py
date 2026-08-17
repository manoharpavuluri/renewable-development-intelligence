"""
Layer 1 — deterministic unit tests for USFWS critical-habitat
screening semantics (endangered/threatened, final/proposed
habitat flags).
"""

from __future__ import annotations

import json

import pytest

from renewable_intelligence.environmental.species_screening import (
    screen_species,
)


def _write_artifact(tmp_path, species):

    artifact = {
        "source": {"authority": "USFWS"},
        "candidate_area_acres": 1000,
        "critical_habitat_overlap_acres": 50,
        "critical_habitat_overlap_percent": 5.0,
        "species": species,
    }

    path = tmp_path / "critical_habitat.json"
    path.write_text(json.dumps(artifact), encoding="utf-8")

    return path


def _run(tmp_path, species):

    path = _write_artifact(tmp_path, species)

    return screen_species(
        state={
            "species_evidence": {
                "critical_habitat_summary_artifact": str(path)
            }
        },
        task={},
    )


def test_missing_evidence_raises_runtime_error():

    with pytest.raises(RuntimeError):
        screen_species(state={}, task={})


def test_missing_artifact_file_raises_file_not_found(tmp_path):

    with pytest.raises(FileNotFoundError):
        screen_species(
            state={
                "species_evidence": {
                    "critical_habitat_summary_artifact": str(
                        tmp_path / "missing.json"
                    )
                }
            },
            task={},
        )


def test_no_species_flags_nothing(tmp_path):

    result = _run(tmp_path, [])

    finding = result["finding"]

    assert finding["endangered_species_flagged"] is False
    assert finding["threatened_species_flagged"] is False
    assert finding["final_critical_habitat_flagged"] is False
    assert (
        finding["proposed_critical_habitat_flagged"] is False
    )
    assert finding["species_count"] == 0


def test_endangered_species_flagged(tmp_path):

    result = _run(
        tmp_path,
        [{"listing_status": "Endangered"}],
    )

    finding = result["finding"]

    assert finding["endangered_species_flagged"] is True
    assert finding["threatened_species_flagged"] is False


def test_threatened_species_flagged(tmp_path):

    result = _run(
        tmp_path,
        [{"listing_status": "Threatened"}],
    )

    finding = result["finding"]

    assert finding["threatened_species_flagged"] is True
    assert finding["endangered_species_flagged"] is False


def test_mixed_species_flags_both(tmp_path):

    result = _run(
        tmp_path,
        [
            {"listing_status": "Endangered"},
            {"listing_status": "Threatened"},
        ],
    )

    finding = result["finding"]

    assert finding["endangered_species_flagged"] is True
    assert finding["threatened_species_flagged"] is True
    assert finding["species_count"] == 2


def test_final_critical_habitat_flagged(tmp_path):

    result = _run(
        tmp_path,
        [{"critical_habitat_status": "Final"}],
    )

    finding = result["finding"]

    assert finding["final_critical_habitat_flagged"] is True
    assert (
        finding["proposed_critical_habitat_flagged"] is False
    )


def test_proposed_critical_habitat_flagged(tmp_path):

    result = _run(
        tmp_path,
        [{"critical_habitat_status": "Proposed"}],
    )

    finding = result["finding"]

    assert (
        finding["proposed_critical_habitat_flagged"] is True
    )
    assert finding["final_critical_habitat_flagged"] is False


def test_species_missing_listing_status_key_does_not_crash(
    tmp_path,
):

    result = _run(tmp_path, [{"common_name": "Unlisted species"}])

    finding = result["finding"]

    assert finding["endangered_species_flagged"] is False
    assert finding["threatened_species_flagged"] is False
    assert finding["species_count"] == 1
