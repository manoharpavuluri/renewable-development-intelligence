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

    legislative_status_path = evidence.get(
        "legislative_status_artifact"
    )

    if not legislative_status_path:

        raise RuntimeError(
            "regulatory_evidence must supply "
            "legislative_status_artifact. Bill status is "
            "temporally volatile evidence and must be loaded "
            "from a timestamped artifact, not hardcoded — see "
            "scripts/spikes/screen_legislative_status.py."
        )

    return {
        "artifact_path": Path(artifact_path),
        "legislative_status_path": Path(
            legislative_status_path
        ),
    }


def _build_legislative_requirement_entries(
    legislative_status: dict[str, Any],
) -> list[dict[str, Any]]:

    """
    Builds requirement-table entries from governed, timestamped
    legislative-status evidence rather than a hardcoded status
    string. Bill status changes between legislative sessions;
    treating it as application source code is exactly the kind
    of staleness this project's evidence model is meant to
    prevent elsewhere.
    """

    source = legislative_status.get("source", {})
    verified_utc = source.get("verified_utc")

    entries = []

    for bill in legislative_status.get("bills", []):

        entries.append(
            {
                "requirement_id": (
                    f"OK_LEGISLATION_{bill['bill']}"
                ),
                "authority_level": "STATE",
                "agency": "Oklahoma Legislature",
                "category": (
                    "Wind-energy setback/zoning legislation "
                    f"({bill['legislative_session']})"
                ),
                "trigger": bill.get("subject"),
                "citation": (
                    f"{bill['bill']}, "
                    f"{bill['legislative_session']}"
                ),
                "applies_to_this_project": (
                    f"{bill['status']} as of "
                    f"{verified_utc} — "
                    f"{bill['last_action']} "
                    f"({bill['last_action_date']}). Does not "
                    "currently change any statutory setback "
                    "requirement. Must be re-verified if a new "
                    "legislative session convenes."
                ),
                "process_note": None,
                "status": bill["status"],
                "verified_utc": verified_utc,
                "source_urls": bill.get("source_urls", []),
            }
        )

    return entries


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
    legislative_status_path = inputs["legislative_status_path"]

    if not artifact_path.exists():

        raise FileNotFoundError(artifact_path)

    if not legislative_status_path.exists():

        raise FileNotFoundError(legislative_status_path)

    jurisdiction = json.loads(
        artifact_path.read_text(encoding="utf-8")
    )

    legislative_status = json.loads(
        legislative_status_path.read_text(encoding="utf-8")
    )

    legislative_entries = (
        _build_legislative_requirement_entries(
            legislative_status
        )
    )

    requirement_categories = (
        KNOWN_REQUIREMENT_CATEGORIES + legislative_entries
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
                    "Section 7 applies to federal AGENCY "
                    "ACTIONS — a federal permit, license, or "
                    "funding decision that may affect a "
                    "listed species or designated critical "
                    "habitat. Designated critical habitat "
                    "overlap alone does not establish that "
                    "formal consultation is required; that "
                    "depends on whether a federal action is "
                    "involved and on the action agency's own "
                    "effects determination, which may instead "
                    "resolve through informal consultation or "
                    "concurrence."
                ),
                "citation": (
                    "16 U.S.C. Section 1536 (ESA Section 7); "
                    "50 CFR Part 402"
                ),
                "applies_to_this_project": (
                    "FLAGGED FOR REVIEW — this project's own "
                    "species screening found Final designated "
                    "critical habitat overlap, which is a "
                    "reason to evaluate Section 7 applicability "
                    "once a specific federal nexus (e.g. an "
                    "FAA determination) is identified, not a "
                    "confirmed consultation requirement by "
                    "itself; see the species domain outcome."
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
                    "If a federal undertaking triggers Section "
                    "106 (e.g. an FAA determination), the "
                    "responsible federal agency must identify "
                    "and consult tribes that may attach "
                    "religious and cultural significance to "
                    "affected historic properties — those "
                    "interests can exist on, or extend well "
                    "beyond, present tribal lands. PAD-US "
                    "tribal statistical geography is screening "
                    "context for which tribes to consider, not "
                    "the legal basis for the consultation "
                    "requirement itself."
                ),
                "citation": (
                    "National Historic Preservation Act "
                    "Section 106, 54 U.S.C. Section 306108; "
                    "36 CFR Part 800; ACHP tribal consultation "
                    "guidance"
                ),
                "applies_to_this_project": (
                    "FLAGGED FOR REVIEW — this project's own "
                    "land-status screening found PAD-US tribal "
                    "statistical area and State Land Board "
                    "overlap, which is a reason to identify "
                    "potentially interested tribes early, not "
                    "a confirmed Section 106 trigger by itself; "
                    "see the land_status domain outcome."
                ),
                "source_evidence": land_status_finding,
                "status": "FLAGGED_FROM_PROJECT_EVIDENCE",
            }
        )


    established_count = sum(
        1
        for item in requirement_categories
        if item["status"] == "ESTABLISHED_REQUIREMENT"
    )

    pending_count = sum(
        1
        for item in requirement_categories
        if item["status"] == "PENDING_NOT_ENACTED"
    )

    failed_legislation_count = sum(
        1
        for item in requirement_categories
        if item["status"] == "FAILED"
    )

    unverified_count = sum(
        1
        for item in requirement_categories
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
        "legislative_status_verified_utc": (
            legislative_status.get("source", {}).get(
                "verified_utc"
            )
        ),
        "established_requirement_count": (
            established_count
        ),
        "pending_not_enacted_count": pending_count,
        "failed_legislation_count": (
            failed_legislation_count
        ),
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
            requirement_categories
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
                "SB2 and HB2751, the two wind-setback bills "
                "tracked here, both FAILED in the 2025-2026 "
                "session (verified against the Oklahoma "
                "Legislature's own bill-status pages and the "
                "Senate's press release); neither currently "
                "changes any statutory setback figure. That "
                "status was manually verified, not fetched via "
                "API, and must be re-checked once a new "
                "legislative session convenes or before relying "
                "on it after this report ages."
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
