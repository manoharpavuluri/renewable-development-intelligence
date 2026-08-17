from __future__ import annotations

import json
from pathlib import Path
from typing import Any


CAPABILITY_NAME = "regulatory.build_permit_matrix"


# ------------------------------------------------------------
# Governed regulatory reference table.
#
# These are fixed, well-established, citable federal/state
# requirement CATEGORIES that are essentially universal for a
# utility-scale onshore wind project in Oklahoma. This is NOT
# legal advice, NOT a complete permitting matrix, and does NOT
# establish specific fees, timelines, or approval likelihood.
# Every entry lists its source citation as of the retrieval
# date below; verify against current statute/regulation text
# before relying on it for actual permitting decisions.
# ------------------------------------------------------------

REFERENCE_TABLE_AS_OF = "2026-08-17"

KNOWN_REQUIREMENT_CATEGORIES = [
    {
        "requirement_id": "FAA_PART77_NOTICE",
        "authority_level": "FEDERAL",
        "agency": "Federal Aviation Administration",
        "category": "Airspace / obstruction notice",
        "trigger": (
            "Any structure exceeding 200 ft above ground "
            "level, or penetrating the Part 77 imaginary "
            "surfaces, requires notice."
        ),
        "citation": "14 CFR Part 77; FAA Form 7460-1",
        "applies_to_this_project": (
            "LIKELY — utility-scale wind turbines are "
            "essentially always taller than 200 ft AGL to "
            "blade tip."
        ),
        "process_note": (
            "Form 7460-1 must be filed at least 45 days "
            "before the earlier of construction start or "
            "permit application."
        ),
        "status": "ESTABLISHED_REQUIREMENT",
    },
    {
        "requirement_id": "OK_WIND_ENERGY_DEVELOPMENT_ACT",
        "authority_level": "STATE",
        "agency": (
            "Oklahoma Corporation Commission, "
            "Public Utility Division"
        ),
        "category": "State wind-facility registration",
        "trigger": (
            "Building, constructing, owning, operating, "
            "controlling, managing, or maintaining a wind "
            "energy facility in Oklahoma."
        ),
        "citation": (
            "Oklahoma Wind Energy Development Act, "
            "17 O.S. Section 160.11 et seq.; "
            "OAC 165:35-45"
        ),
        "applies_to_this_project": "LIKELY",
        "process_note": (
            "Annual information submission to PUD required "
            "on or before March 1."
        ),
        "status": "ESTABLISHED_REQUIREMENT",
    },
    {
        "requirement_id": "OK_WIND_SETBACK_AIRPORT_SCHOOL_HOSPITAL",
        "authority_level": "STATE",
        "agency": "Oklahoma Corporation Commission",
        "category": "Statutory setback distances",
        "trigger": (
            "Wind energy facility siting near public-use or "
            "municipally owned airports, public schools, or "
            "hospitals."
        ),
        "citation": (
            "Oklahoma Wind Energy Development Act "
            "implementing rules"
        ),
        "applies_to_this_project": (
            "REQUIRES_SITE_SPECIFIC_VERIFICATION — the "
            "current statutory setback is 1.5 nautical "
            "miles from a public-use or municipally owned "
            "airport, public school, or hospital; whether "
            "any such facility exists within that distance "
            "of the actual turbine layout has not been "
            "checked."
        ),
        "process_note": None,
        "status": "ESTABLISHED_REQUIREMENT",
    },
    {
        "requirement_id": "OK_PENDING_WIND_LEGISLATION",
        "authority_level": "STATE",
        "agency": "Oklahoma Legislature",
        "category": "Pending/emerging setback and zoning legislation",
        "trigger": (
            "Legislative session activity as of the "
            f"reference date ({REFERENCE_TABLE_AS_OF})."
        ),
        "citation": (
            "e.g. Oklahoma SB2 (county-level setback "
            "provisions) and HB2751 (residential setbacks) "
            "as introduced/advanced in the 2026 session"
        ),
        "applies_to_this_project": (
            "NOT YET LAW — must be re-checked against "
            "current legislative status before relying on "
            "any specific setback figure."
        ),
        "process_note": None,
        "status": "PENDING_NOT_ENACTED",
    },
    {
        "requirement_id": "COUNTY_LOCAL_ZONING",
        "authority_level": "COUNTY",
        "agency": "County zoning/planning authority",
        "category": "Local zoning, permitting, and/or road-use agreements",
        "trigger": "Construction within county jurisdiction.",
        "citation": (
            "County-specific ordinances; not retrieved by "
            "this screening"
        ),
        "applies_to_this_project": (
            "REQUIRES_DIRECT_COUNTY_CONTACT — specific "
            "county ordinance text was not retrieved."
        ),
        "process_note": None,
        "status": "NOT_YET_VERIFIED",
    },
    {
        "requirement_id": "SPP_FERC_INTERCONNECTION",
        "authority_level": "FEDERAL_RTO",
        "agency": "Southwest Power Pool / FERC",
        "category": "Generator interconnection study process",
        "trigger": "Interconnecting generation to the SPP transmission system.",
        "citation": "SPP Open Access Transmission Tariff, generator interconnection procedures",
        "applies_to_this_project": (
            "CONFIRMED APPLICABLE — already the subject of "
            "this project's interconnection-domain "
            "screening work."
        ),
        "process_note": None,
        "status": "ESTABLISHED_REQUIREMENT",
    },
]


def _resolve_inputs(
    *,
    state: dict[str, Any],
    task: dict[str, Any],
) -> dict[str, Any]:

    evidence = (
        task.get("regulatory_evidence")
        or state.get("regulatory_evidence")
    )

    if not evidence:

        raise RuntimeError(
            "regulatory.build_permit_matrix requires "
            "regulatory_evidence."
        )

    artifact_path = evidence.get(
        "jurisdiction_summary_artifact"
    )

    if not artifact_path:

        raise RuntimeError(
            "regulatory_evidence must supply "
            "jurisdiction_summary_artifact."
        )

    return {
        "artifact_path": Path(artifact_path),
    }


def build_permit_matrix(
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

    jurisdiction = json.loads(
        artifact_path.read_text(encoding="utf-8")
    )

    domain_outcomes = (
        state.get("project_domain_outcomes")
        or {}
    )


    conditional_triggers = []

    if "species" in domain_outcomes:

        species_finding = (
            domain_outcomes["species"].get(
                "resolved_uncertainty",
                [],
            )
        )

        conditional_triggers.append(
            {
                "requirement_id": (
                    "ESA_SECTION_7_CONSULTATION_FLAGGED"
                ),
                "authority_level": "FEDERAL",
                "agency": "U.S. Fish and Wildlife Service",
                "category": (
                    "Endangered Species Act consultation"
                ),
                "trigger": (
                    "A federal nexus (e.g. FAA Part 77 "
                    "notice) combined with designated "
                    "critical habitat or listed species "
                    "presence typically triggers ESA "
                    "Section 7 interagency consultation."
                ),
                "citation": "16 U.S.C. Section 1536 (ESA Section 7)",
                "applies_to_this_project": (
                    "FLAGGED — this project's own species "
                    "screening already found Final "
                    "designated critical habitat overlap; "
                    "see the species domain outcome."
                ),
                "source_evidence": species_finding,
                "status": "FLAGGED_FROM_PROJECT_EVIDENCE",
            }
        )

    if "land_status" in domain_outcomes:

        land_status_finding = (
            domain_outcomes["land_status"].get(
                "resolved_uncertainty",
                [],
            )
        )

        conditional_triggers.append(
            {
                "requirement_id": (
                    "TRIBAL_NHPA_CONSULTATION_FLAGGED"
                ),
                "authority_level": "FEDERAL",
                "agency": (
                    "State Historic Preservation Office / "
                    "affected Tribal Historic Preservation "
                    "Office(s)"
                ),
                "category": (
                    "Tribal consultation / Section 106 review"
                ),
                "trigger": (
                    "A federal nexus combined with proximity "
                    "to tribal statistical geography commonly "
                    "warrants tribal outreach and NHPA "
                    "Section 106 review, even where legal "
                    "trust status has not been established."
                ),
                "citation": (
                    "National Historic Preservation Act "
                    "Section 106, 54 U.S.C. Section 306108"
                ),
                "applies_to_this_project": (
                    "FLAGGED — this project's own land-status "
                    "screening already found PAD-US tribal "
                    "statistical area and State Land Board "
                    "overlap; see the land_status domain "
                    "outcome."
                ),
                "source_evidence": land_status_finding,
                "status": "FLAGGED_FROM_PROJECT_EVIDENCE",
            }
        )


    established_count = sum(
        1
        for item in KNOWN_REQUIREMENT_CATEGORIES
        if item["status"] == "ESTABLISHED_REQUIREMENT"
    )

    pending_count = sum(
        1
        for item in KNOWN_REQUIREMENT_CATEGORIES
        if item["status"] == "PENDING_NOT_ENACTED"
    )

    unverified_count = sum(
        1
        for item in KNOWN_REQUIREMENT_CATEGORIES
        if item["status"] == "NOT_YET_VERIFIED"
    )


    finding = {
        "jurisdiction_county": jurisdiction.get(
            "county_name"
        ),
        "jurisdiction_state": jurisdiction.get(
            "state_name"
        ),
        "reference_table_as_of": (
            REFERENCE_TABLE_AS_OF
        ),
        "established_requirement_count": (
            established_count
        ),
        "pending_not_enacted_count": pending_count,
        "not_yet_verified_count": unverified_count,
        "conditional_trigger_count": (
            len(conditional_triggers)
        ),
        "complete_permit_matrix_established": (
            False
        ),
        "specific_fees_or_timelines_established": (
            False
        ),
        "legal_review_completed": (
            False
        ),
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
            or "PROJECT_SCREENING"
        ),

        "finding": finding,

        "jurisdiction": jurisdiction,

        "known_requirement_categories": (
            KNOWN_REQUIREMENT_CATEGORIES
        ),

        "conditional_triggers": (
            conditional_triggers
        ),

        "evidence_quality": "LOW",

        "evidence_quality_reason": (
            "This is a screening-level list of well-"
            "established requirement CATEGORIES with "
            "citations, combined with real county/state "
            "jurisdiction identification and conditions "
            "flagged from this project's own prior evidence. "
            "It is not a complete permit matrix, not legal "
            "advice, and has not been reviewed by permitting "
            "counsel."
        ),

        "candidate_applicability": "MEDIUM",

        "interpretation_limits": [
            (
                "This does not establish a complete, "
                "authoritative permit matrix; county/local "
                "ordinance text was not retrieved."
            ),
            (
                "Pending Oklahoma legislation (as of "
                f"{REFERENCE_TABLE_AS_OF}) could change "
                "setback requirements and must be re-checked "
                "before relying on any current setback figure."
            ),
            (
                "No permit fees, approval timelines (beyond "
                "the FAA's documented 45-day pre-filing "
                "window), or approval likelihood are "
                "established by this screening."
            ),
            (
                "This is not legal advice and does not "
                "substitute for review by qualified "
                "permitting counsel or a permitting "
                "consultant."
            ),
        ],
    }
