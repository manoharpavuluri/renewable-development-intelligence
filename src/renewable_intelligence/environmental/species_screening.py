from __future__ import annotations

import json
from pathlib import Path
from typing import Any


CAPABILITY_NAME = "environment.screen_species"


def _resolve_inputs(
    *,
    state: dict[str, Any],
    task: dict[str, Any],
) -> dict[str, Any]:

    evidence = (
        task.get("species_evidence")
        or state.get("species_evidence")
    )

    if not evidence:

        raise RuntimeError(
            "environment.screen_species requires "
            "species_evidence."
        )

    artifact_path = evidence.get(
        "critical_habitat_summary_artifact"
    )

    if not artifact_path:

        raise RuntimeError(
            "species_evidence must supply "
            "critical_habitat_summary_artifact."
        )

    return {
        "artifact_path": Path(artifact_path),
    }


def screen_species(
    *,
    state,
    task,
) -> dict[str, Any]:

    inputs = _resolve_inputs(
        state=state,
        task=task,
    )

    artifact_path = inputs["artifact_path"]

    if not artifact_path.exists():

        raise FileNotFoundError(artifact_path)

    summary = json.loads(
        artifact_path.read_text(encoding="utf-8")
    )

    source = summary.get("source", {})
    species = summary.get("species", [])

    overlap_acres = summary.get(
        "critical_habitat_overlap_acres"
    )

    overlap_percent = summary.get(
        "critical_habitat_overlap_percent"
    )

    endangered_species_flagged = any(
        item.get("listing_status") == "Endangered"
        for item in species
    )

    threatened_species_flagged = any(
        item.get("listing_status") == "Threatened"
        for item in species
    )

    final_critical_habitat_flagged = any(
        item.get("critical_habitat_status") == "Final"
        for item in species
    )

    proposed_critical_habitat_flagged = any(
        item.get("critical_habitat_status") == "Proposed"
        for item in species
    )

    finding = {
        "source_authority": source.get("authority"),
        "source_dataset": source.get("dataset"),
        "source_retrieved_utc": source.get("retrieved_utc"),
        "candidate_area_acres": summary.get(
            "candidate_area_acres"
        ),
        "critical_habitat_overlap_acres": overlap_acres,
        "critical_habitat_overlap_percent": overlap_percent,
        "species_count": len(species),
        "endangered_species_flagged": endangered_species_flagged,
        "threatened_species_flagged": threatened_species_flagged,
        "final_critical_habitat_flagged": (
            final_critical_habitat_flagged
        ),
        "proposed_critical_habitat_flagged": (
            proposed_critical_habitat_flagged
        ),
        "official_ipac_species_list_obtained": False,
        "migratory_bird_screening_completed": False,
        "section_7_consultation_completed": False,
    }

    return {
        "task_id": (
            task.get("task_id")
            or task.get("action_id")
        ),

        "capability": CAPABILITY_NAME,

        "executed": True,

        "relationship": (
            task.get("relationship")
            or "CANDIDATE_SCREENING"
        ),

        "finding": finding,

        "species": species,

        "evidence_quality": "MEDIUM",

        "evidence_quality_reason": (
            "USFWS Critical Habitat is authoritative, "
            "Federal-Register-published federal data with real "
            "species, listing-status, and citation attributes for "
            "the candidate area, but designated critical habitat "
            "is only one component of a full ESA screening."
        ),

        "candidate_applicability": "HIGH",

        "interpretation_limits": [
            (
                "This screening covers only USFWS Final and "
                "Proposed designated critical habitat; it is not "
                "equivalent to a USFWS IPaC official species list, "
                "which also covers ESA-listed species without "
                "designated critical habitat, migratory birds, "
                "and bald/golden eagle concerns."
            ),
            (
                "This screening does not constitute or substitute "
                "for ESA Section 7 consultation."
            ),
            (
                "Critical habitat overlap does not by itself "
                "establish that wind development is prohibited; "
                "it establishes that federal consultation "
                "requirements are likely to apply."
            ),
            (
                "Federal Register publication and status fields "
                "should be reconciled against the current Federal "
                "Register record before relying on this screening "
                "for permitting timelines."
            ),
        ],
    }
