from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Any


CAPABILITY_NAME = "schedule.assess_cod_feasibility"


class CODFeasibilityStatus(StrEnum):
    PLAUSIBLE = "PLAUSIBLE"
    PLAUSIBLE_WITH_CONDITIONS = "PLAUSIBLE_WITH_CONDITIONS"
    AT_RISK = "AT_RISK"
    NOT_ASSESSABLE = "NOT_ASSESSABLE"


# ------------------------------------------------------------
# Known, citable regulatory durations. These are the ONLY
# specific duration figures this module uses; every other
# lead time is explicitly labeled unresolved rather than
# estimated, per project guardrails against inventing
# permitting timelines.
# ------------------------------------------------------------

KNOWN_DURATIONS = [
    {
        "item": "FAA Form 7460-1 pre-filing window",
        "duration_days": 45,
        "duration_type": "MINIMUM_LEAD_TIME",
        "citation": "14 CFR Part 77; FAA Form 7460-1",
        "note": (
            "Minimum notice before construction start or "
            "permit application, not a total review duration."
        ),
    },
    {
        "item": "ESA Section 7 formal consultation",
        "duration_days": 135,
        "duration_type": "STATUTORY_MAXIMUM",
        "citation": "50 CFR 402.14 (90 days consultation + "
        "45 days for Biological Opinion)",
        "note": (
            "Runs from initiation (i.e. once USFWS has a "
            "complete Biological Assessment), not from project "
            "start; assembling that assessment is itself an "
            "unresolved-duration workstream. Extendable by up "
            "to 60 days without applicant consent."
        ),
    },
]


UNRESOLVED_DURATION_WORKSTREAMS = [
    {
        "workstream": "SPP generator interconnection study process",
        "gate_id": "G2",
        "reason": (
            "No candidate-specific System Impact Study or "
            "Facility Study has been initiated; SPP GI study "
            "cycle duration depends on queue position and is "
            "not established for this project."
        ),
    },
    {
        "workstream": "Land status / tribal and state-land resolution",
        "gate_id": "G3",
        "reason": (
            "Tribal trust status and State Land Board lease/"
            "sale eligibility require authoritative agency "
            "engagement with no established timeline."
        ),
    },
    {
        "workstream": "ESA Biological Assessment preparation",
        "gate_id": "G3",
        "reason": (
            "Field surveys and BA drafting must occur before "
            "the 135-day Section 7 clock even starts; duration "
            "not established."
        ),
    },
    {
        "workstream": "County/local zoning and permitting",
        "gate_id": "G4",
        "reason": (
            "Dewey County ordinance text and approval process "
            "have not been retrieved."
        ),
    },
    {
        "workstream": "Section 106 / SHPO-THPO review",
        "gate_id": "G3",
        "reason": (
            "Required given the direct NRHP intersection; "
            "duration depends on SHPO/THPO response time, not "
            "established."
        ),
    },
    {
        "workstream": "Land control (lease/option execution)",
        "gate_id": None,
        "reason": (
            "The project explicitly does not represent the "
            "candidate area as owned, leased, or under option."
        ),
    },
]


def _parse_date(value: str) -> date:

    return datetime.strptime(
        value, "%Y-%m-%d"
    ).date()


def assess_cod_feasibility(
    *,
    target_cod: str,
    gate_syntheses: list[dict[str, Any]],
    as_of: date | None = None,
) -> dict[str, Any]:

    as_of = as_of or date.today()

    cod_date = _parse_date(target_cod)

    months_to_cod = (
        (cod_date.year - as_of.year) * 12
        + (cod_date.month - as_of.month)
    )

    years_to_cod = round(months_to_cod / 12, 1)


    blocking_gate_ids = [
        gate["gate_id"]
        for gate in gate_syntheses
        if gate["status"] == "UNRESOLVED"
        and gate["materiality"]
        in {"HIGH", "CRITICAL"}
    ]

    high_or_critical_risks = [
        risk
        for gate in gate_syntheses
        for risk in gate.get("material_risks", [])
        if risk["severity"] in {"HIGH", "CRITICAL"}
    ]


    parallelizable_workstreams = [
        "Environmental screening/consultation (species, "
        "cultural, land status)",
        "Regulatory/permitting diligence",
        "Aviation obstruction filing (once turbine layout and "
        "heights are set)",
        "Land control negotiation",
    ]

    critical_path_candidates = [
        (
            "SPP generator interconnection study process is "
            "typically the longest-lead workstream for a "
            "project of this size and is usually on the "
            "critical path; duration for this project is not "
            "yet established."
        ),
        (
            "Land control (lease/option) must be secured before "
            "most other workstreams can be finalized, and is "
            "currently unresolved for this candidate."
        ),
    ]


    if months_to_cod <= 0:

        status = CODFeasibilityStatus.NOT_ASSESSABLE

        reason = (
            f"Target COD {target_cod} is not in the future "
            f"relative to the assessment date ({as_of.isoformat()})."
        )

    elif blocking_gate_ids and high_or_critical_risks:

        status = CODFeasibilityStatus.AT_RISK

        reason = (
            f"{len(blocking_gate_ids)} HIGH/CRITICAL-materiality "
            f"gate(s) remain UNRESOLVED "
            f"({', '.join(blocking_gate_ids)}) alongside "
            f"{len(high_or_critical_risks)} HIGH/CRITICAL "
            "material risk(s); several long-lead workstreams "
            "(interconnection study, land control) have no "
            "established duration."
        )

    elif months_to_cod < 24:

        status = CODFeasibilityStatus.AT_RISK

        reason = (
            f"Only {years_to_cod} years remain to target COD, "
            "which is short relative to typical interconnection-"
            "study and permitting lead times for a project this "
            "size."
        )

    else:

        status = (
            CODFeasibilityStatus.PLAUSIBLE_WITH_CONDITIONS
        )

        reason = (
            f"{years_to_cod} years remain to target COD "
            f"({target_cod}), and no domain screening has "
            "identified a clearly disqualifying finding, but "
            f"{len(UNRESOLVED_DURATION_WORKSTREAMS)} material "
            "workstreams (interconnection study, land control, "
            "ESA consultation prep, county permitting, Section "
            "106 review) currently have no established duration "
            "and could threaten the target COD if any proves "
            "long-lead."
        )


    return {
        "capability": CAPABILITY_NAME,

        "target_cod": target_cod,

        "assessment_date": as_of.isoformat(),

        "months_to_target_cod": months_to_cod,

        "years_to_target_cod": years_to_cod,

        "status": str(status),

        "reason": reason,

        "known_durations": KNOWN_DURATIONS,

        "unresolved_duration_workstreams": (
            UNRESOLVED_DURATION_WORKSTREAMS
        ),

        "parallelizable_workstreams": (
            parallelizable_workstreams
        ),

        "critical_path_candidates": (
            critical_path_candidates
        ),

        "blocking_gate_ids": blocking_gate_ids,

        "high_or_critical_material_risks": (
            high_or_critical_risks
        ),

        "interpretation_limits": [
            (
                "No exact permit, study, or consultation "
                "duration is estimated beyond the two statutory/"
                "regulatory figures explicitly cited above; all "
                "other workstream durations are labeled "
                "unresolved rather than guessed."
            ),
            (
                "This does not constitute a project schedule or "
                "critical-path analysis; it identifies which "
                "workstreams currently lack duration evidence."
            ),
        ],
    }
