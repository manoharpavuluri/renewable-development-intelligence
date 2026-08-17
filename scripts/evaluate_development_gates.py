#!/usr/bin/env python3

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from renewable_intelligence.domain.gates import (
    DevelopmentGate,
    DevelopmentGateAssessment,
    GateStatus,
    InvestigationPriority,
    InvestigationTask,
    Materiality,
)


RESULT_DIR = os.environ.get("RESULT_DIR")

if not RESULT_DIR:
    raise SystemExit(
        "RESULT_DIR is not set."
    )

RESULT_DIR = Path(RESULT_DIR)

SCREENING_PATH = (
    RESULT_DIR
    / "screening"
    / "candidate_site_screening.json"
)


def read_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(
            f"Required artifact missing: {path}"
        )

    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


screening = read_json(
    SCREENING_PATH
)

project_id = screening[
    "project_id"
]


# ============================================================
# G1 — RESOURCE AND PHYSICAL SITE
# ============================================================

g1 = DevelopmentGate(
    gate_id="G1",

    name=(
        "Resource and Physical "
        "Site Suitability"
    ),

    status=GateStatus.UNRESOLVED,

    materiality=Materiality.HIGH,

    rationale=(
        "One year of HRRR modeled resource data "
        "is available at one grid location, but "
        "candidate-wide long-term resource, terrain, "
        "slope, and land-cover suitability remain "
        "unresolved."
    ),

    supporting_domains=[
        "site",
        "wind_resource",
        "wetlands",
    ],

    missing_evidence=[
        "Multi-year wind-resource characterization.",
        "Spatial wind-resource variation across candidate.",
        "USGS 3DEP elevation and slope.",
        "NLCD land-cover composition.",
    ],

    next_actions=[
        "Acquire multi-year HRRR observations.",
        "Sample resource across candidate geography.",
        "Run deterministic terrain analysis.",
        "Run deterministic land-cover analysis.",
    ],
)


# ============================================================
# G2 — INTERCONNECTION
# ============================================================

g2 = DevelopmentGate(
    gate_id="G2",

    name=(
        "Transmission and Interconnection"
    ),

    status=GateStatus.UNRESOLVED,

    materiality=Materiality.CRITICAL,

    rationale=(
        "SPP queue and study sources have been proven "
        "accessible, but no candidate-specific POI, "
        "transmission proximity, hosting context, "
        "queue competition, or precedent-study analysis "
        "has yet been connected to this project."
    ),

    supporting_domains=[],

    missing_evidence=[
        "Candidate transmission context.",
        "Potential points of interconnection.",
        "Nearby relevant generator requests.",
        "Relevant SPP study precedents.",
        "Upgrade and schedule dependency evidence.",
    ],

    next_actions=[
        "Identify candidate-relevant transmission facilities.",
        "Identify plausible POI candidates.",
        "Analyze SPP queue around relevant electrical area.",
        "Retrieve and analyze precedent SPP studies.",
    ],
)


# ============================================================
# G3 — ENVIRONMENTAL / LAND
# ============================================================

wetland_overlap = (
    screening[
        "wetlands"
    ][
        "facts"
    ][
        "nwi_mapped_overlap_acres"
    ]
)

gap12 = (
    screening[
        "protected_lands"
    ][
        "facts"
    ][
        "biodiversity_protected_gap_1_2"
    ].get(
        "acres",
        0.0,
    )
)

g3 = DevelopmentGate(
    gate_id="G3",

    name=(
        "Environmental and Land Constraints"
    ),

    status=GateStatus.UNRESOLVED,

    materiality=Materiality.HIGH,

    rationale=(
        f"NWI maps {wetland_overlap:,.2f} acres of "
        f"wetland overlap and PAD-US identifies "
        f"{gap12:,.2f} acres of GAP 1/2 conservation "
        "context. However ESA/species, cultural "
        "resources, tribal/land status, flood exposure, "
        "and site-specific avoidance requirements remain "
        "unresolved."
    ),

    supporting_domains=[
        "wetlands",
        "flood",
        "protected_lands",
    ],

    missing_evidence=[
        "ESA / species screening.",
        "Historic and cultural resources.",
        "Tribal / trust / land-status diligence.",
        "State-land implications.",
        "Wildlife-management-area implications.",
        "Flood-risk evidence.",
    ],

    next_actions=[
        "Run USFWS species screening.",
        "Run historic-resource screening.",
        "Resolve tribal and state-land status.",
        "Investigate alternate flood evidence.",
    ],
)


# ============================================================
# G4 — PERMITTING / REGULATORY
# ============================================================

g4 = DevelopmentGate(
    gate_id="G4",

    name=(
        "Permitting and Regulatory Path"
    ),

    status=GateStatus.UNRESOLVED,

    materiality=Materiality.HIGH,

    rationale=(
        "The project does not yet have a documented "
        "federal, state, county, tribal, and local "
        "permitting path or applicable wind-development "
        "setback requirements."
    ),

    supporting_domains=[
        "protected_lands",
    ],

    missing_evidence=[
        "Oklahoma state requirements.",
        "County/local wind requirements.",
        "Applicable setbacks.",
        "Tribal jurisdiction implications.",
        "Required environmental permits.",
    ],

    next_actions=[
        "Assemble applicable permitting authorities.",
        "Retrieve governing regulations and ordinances.",
        "Identify permit dependencies and lead times.",
    ],
)


# ============================================================
# G5 — AVIATION / MILITARY
# ============================================================

g5 = DevelopmentGate(
    gate_id="G5",

    name=(
        "Aviation and Military Compatibility"
    ),

    status=GateStatus.UNRESOLVED,

    materiality=Materiality.HIGH,

    rationale=(
        "No FAA obstruction, airport, radar, military "
        "airspace, or defense compatibility screening "
        "has yet been performed."
    ),

    supporting_domains=[],

    missing_evidence=[
        "FAA obstruction context.",
        "Nearby airports and aviation facilities.",
        "Military airspace / radar compatibility context.",
    ],

    next_actions=[
        "Run FAA screening.",
        "Identify aviation facilities.",
        "Investigate military compatibility sources.",
    ],
)


# ============================================================
# G6 — SCHEDULE / COD
# ============================================================

target_cod = screening[
    "project"
][
    "target_cod"
]

g6 = DevelopmentGate(
    gate_id="G6",

    name=(
        "Development Schedule and COD Feasibility"
    ),

    status=GateStatus.UNRESOLVED,

    materiality=Materiality.HIGH,

    rationale=(
        f"The project has a target COD of {target_cod}, "
        "but interconnection, permitting, environmental, "
        "land-control, equipment, and construction "
        "dependencies have not yet been assembled into "
        "a critical-path schedule."
    ),

    supporting_domains=[
        "site",
    ],

    missing_evidence=[
        "Interconnection timeline.",
        "Permit lead times.",
        "Environmental-study lead times.",
        "Land-control timeline.",
        "Procurement assumptions.",
        "Construction assumptions.",
    ],

    next_actions=[
        "Resolve major development dependencies.",
        "Build preliminary critical-path schedule.",
        "Compare required milestones with target COD.",
    ],
)


# ============================================================
# G7 — EVIDENCE SUFFICIENCY
# ============================================================

unresolved_count = len(
    screening.get(
        "unresolved_project_questions",
        []
    )
)

g7 = DevelopmentGate(
    gate_id="G7",

    name=(
        "Evidence Sufficiency for "
        "Investment Recommendation"
    ),

    status=GateStatus.UNRESOLVED,

    materiality=Materiality.CRITICAL,

    rationale=(
        f"The screening state still contains "
        f"{unresolved_count} material project questions. "
        "The available evidence is therefore insufficient "
        "for an investment recommendation."
    ),

    supporting_domains=[
        "site",
        "wind_resource",
        "wetlands",
        "flood",
        "protected_lands",
    ],

    missing_evidence=screening.get(
        "unresolved_project_questions",
        [],
    ),

    next_actions=[
        "Resolve material domain gaps.",
        "Re-evaluate G1-G6.",
        "Require human review before final recommendation.",
    ],

    human_review_required=True,
)


gates = [
    g1,
    g2,
    g3,
    g4,
    g5,
    g6,
    g7,
]


# ============================================================
# Investigation queue
# ============================================================

investigations = [
    InvestigationTask(
        task_id="INV-001",
        domain="interconnection",
        question=(
            "What transmission facilities and plausible "
            "points of interconnection are relevant to "
            "the candidate site?"
        ),
        priority=InvestigationPriority.BLOCKING,
        reason=(
            "Interconnection can materially affect project "
            "economics and schedule, and candidate-specific "
            "evidence is currently absent."
        ),
        blocking_gate_ids=[
            "G2",
            "G6",
            "G7",
        ],
        preferred_capability=(
            "spp.transmission_context"
        ),
    ),

    InvestigationTask(
        task_id="INV-002",
        domain="wind_resource",
        question=(
            "What is the multi-year modeled wind-resource "
            "profile across the candidate polygon?"
        ),
        priority=InvestigationPriority.HIGH,
        reason=(
            "Current resource evidence represents only "
            "one year and one grid location."
        ),
        blocking_gate_ids=[
            "G1",
            "G7",
        ],
        preferred_capability=(
            "wind.analyze_candidate_resource"
        ),
    ),

    InvestigationTask(
        task_id="INV-003",
        domain="terrain",
        question=(
            "What elevation and slope constraints occur "
            "inside the candidate polygon?"
        ),
        priority=InvestigationPriority.HIGH,
        reason=(
            "Terrain suitability has not yet been measured."
        ),
        blocking_gate_ids=[
            "G1",
            "G7",
        ],
        preferred_capability=(
            "gis.analyze_terrain"
        ),
    ),

    InvestigationTask(
        task_id="INV-004",
        domain="land_cover",
        question=(
            "What land-cover classes occur inside the "
            "candidate polygon?"
        ),
        priority=InvestigationPriority.HIGH,
        reason=(
            "Gross acreage cannot be treated as usable "
            "development acreage without land-cover context."
        ),
        blocking_gate_ids=[
            "G1",
            "G7",
        ],
        preferred_capability=(
            "gis.analyze_land_cover"
        ),
    ),

    InvestigationTask(
        task_id="INV-005",
        domain="species",
        question=(
            "What ESA-listed or sensitive species and "
            "habitat concerns apply to the candidate?"
        ),
        priority=InvestigationPriority.HIGH,
        reason=(
            "Species-related constraints can alter layout, "
            "study requirements, permitting, and schedule."
        ),
        blocking_gate_ids=[
            "G3",
            "G4",
            "G6",
            "G7",
        ],
        preferred_capability=(
            "environment.screen_species"
        ),
    ),

    InvestigationTask(
        task_id="INV-006",
        domain="land_status",
        question=(
            "What tribal, trust, state-land, wildlife-area, "
            "and other land-management implications apply "
            "to the intersecting PAD-US units?"
        ),
        priority=InvestigationPriority.HIGH,
        reason=(
            "PAD-US identifies tribal statistical geography, "
            "State Land Board land, and a wildlife management "
            "area, but those records do not by themselves "
            "establish development rights or prohibitions."
        ),
        blocking_gate_ids=[
            "G3",
            "G4",
            "G6",
            "G7",
        ],
        preferred_capability=(
            "land.resolve_status"
        ),
    ),

    InvestigationTask(
        task_id="INV-007",
        domain="aviation",
        question=(
            "What FAA, airport, radar, and military "
            "compatibility constraints may apply?"
        ),
        priority=InvestigationPriority.HIGH,
        reason=(
            "Wind-turbine height makes aviation and military "
            "compatibility a material development domain."
        ),
        blocking_gate_ids=[
            "G5",
            "G6",
            "G7",
        ],
        preferred_capability=(
            "aviation.screen_candidate"
        ),
    ),

    InvestigationTask(
        task_id="INV-008",
        domain="regulatory",
        question=(
            "What state, county, local, tribal, and federal "
            "permits and setback requirements apply?"
        ),
        priority=InvestigationPriority.HIGH,
        reason=(
            "The permitting path has not yet been established."
        ),
        blocking_gate_ids=[
            "G4",
            "G6",
            "G7",
        ],
        preferred_capability=(
            "regulatory.build_permit_matrix"
        ),
    ),

    InvestigationTask(
        task_id="INV-009",
        domain="cultural",
        question=(
            "What historic and cultural-resource screening "
            "concerns occur within or near the candidate?"
        ),
        priority=InvestigationPriority.MEDIUM,
        reason=(
            "Cultural-resource diligence remains unresolved."
        ),
        blocking_gate_ids=[
            "G3",
            "G4",
            "G7",
        ],
        preferred_capability=(
            "environment.screen_cultural_resources"
        ),
    ),

    InvestigationTask(
        task_id="INV-010",
        domain="flood",
        question=(
            "What alternate authoritative evidence can "
            "characterize flood exposure where digital "
            "NFHL coverage is unavailable?"
        ),
        priority=InvestigationPriority.MEDIUM,
        reason=(
            "FEMA NFHL/FIRM coverage is absent, so flood "
            "exposure remains unknown rather than low."
        ),
        blocking_gate_ids=[
            "G3",
            "G7",
        ],
        preferred_capability=(
            "gis.resolve_flood_evidence"
        ),
    ),
]


# ============================================================
# Recommendation control
# ============================================================

recommendation_blockers = [
    gate.gate_id
    for gate in gates
    if gate.status in {
        GateStatus.UNRESOLVED,
        GateStatus.UNSATISFIED,
    }
]


recommendation_allowed = (
    len(
        recommendation_blockers
    )
    == 0
)


assessment = DevelopmentGateAssessment(
    project_id=project_id,

    generated_utc=(
        datetime.now(
            timezone.utc
        ).isoformat()
    ),

    gates=gates,

    investigation_queue=investigations,

    overall_gate_state=(
        "INVESTIGATION_REQUIRED"
        if recommendation_blockers
        else "READY_FOR_HUMAN_REVIEW"
    ),

    recommendation_allowed=(
        recommendation_allowed
    ),

    recommendation_blockers=(
        recommendation_blockers
    ),

    metadata={
        "policy_version": (
            "development-gates-v0.1"
        ),

        "principle": (
            "Unknown evidence is not interpreted "
            "as low risk."
        ),
    },
)


output_path = (
    RESULT_DIR
    / "screening"
    / "development_gate_assessment.json"
)

output_path.write_text(
    json.dumps(
        assessment.to_dict(),
        indent=2,
    ),
    encoding="utf-8",
)


# ============================================================
# Report
# ============================================================

print(
    "=== DEVELOPMENT GATE ASSESSMENT ==="
)

print(
    "Project:",
    project_id,
)

print(
    "Overall state:",
    assessment.overall_gate_state,
)

print(
    "Recommendation allowed:",
    recommendation_allowed,
)


print()
print(
    "=== GATES ==="
)

for gate in gates:

    print(
        f"{gate.gate_id} | "
        f"{gate.status:<12} | "
        f"{gate.materiality:<8} | "
        f"{gate.name}"
    )

    print(
        "   ",
        gate.rationale,
    )


print()
print(
    "=== INVESTIGATION QUEUE ==="
)

for task in investigations:

    print(
        f"{task.task_id} | "
        f"{task.priority:<8} | "
        f"{task.domain}"
    )

    print(
        "   ",
        task.question,
    )

    print(
        "    capability:",
        task.preferred_capability,
    )

    print(
        "    gates:",
        ", ".join(
            task.blocking_gate_ids
        ),
    )


print()
print(
    "=== RECOMMENDATION BLOCKERS ==="
)

for gate_id in (
    recommendation_blockers
):
    print(
        "-",
        gate_id,
    )


print()
print(
    "Output:",
    output_path,
)
