#!/usr/bin/env python3

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from renewable_intelligence.domain.screening import (
    CandidateSiteScreeningResult,
    Confidence,
    EvidenceClass,
    EvidenceReference,
    KnowledgeStatus,
    ScreeningDomain,
)


RESULT_DIR = os.environ.get("RESULT_DIR")

if not RESULT_DIR:
    raise SystemExit(
        "RESULT_DIR is not set."
    )


RESULT_DIR = Path(RESULT_DIR)

SCENARIO_DIR = Path(
    "data/scenarios/western_ok_250mw"
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


project_path = (
    SCENARIO_DIR
    / "project.json"
)

site_path = (
    RESULT_DIR
    / "gis"
    / "candidate_area_profile.json"
)

wind_path = (
    RESULT_DIR
    / "wind_resource"
    / "hrrr_met_2025_test_point_summary.json"
)

nwi_path = (
    RESULT_DIR
    / "gis"
    / "nwi"
    / "nwi_summary.json"
)

fema_path = (
    RESULT_DIR
    / "gis"
    / "fema_nfhl"
    / "fema_nfhl_summary.json"
)

padus_path = (
    RESULT_DIR
    / "gis"
    / "padus"
    / "padus_summary.json"
)


project = read_json(project_path)
site = read_json(site_path)
wind = read_json(wind_path)
nwi = read_json(nwi_path)
fema = read_json(fema_path)
padus = read_json(padus_path)


# ---------------------------------------------------------
# Site
# ---------------------------------------------------------

site_domain = ScreeningDomain(
    status=KnowledgeStatus.OBSERVED,

    evidence_confidence=Confidence.HIGH,

    decision_confidence=Confidence.HIGH,

    facts={
        "gross_area_acres": (
            site[
                "gross_site_metrics"
            ][
                "area_acres"
            ]
        ),

        "gross_area_square_km": (
            site[
                "gross_site_metrics"
            ][
                "area_square_km"
            ]
        ),

        "gross_acres_per_target_mw": (
            site[
                "gross_site_metrics"
            ][
                "gross_acres_per_target_mw"
            ]
        ),

        "centroid_wgs84": (
            site[
                "geometry"
            ][
                "centroid_wgs84"
            ]
        ),

        "analysis_crs": (
            site[
                "geometry"
            ][
                "analysis_crs"
            ]
        ),
    },

    evidence=[
        EvidenceReference(
            source_id="DEV-001",

            artifact_path=str(
                site_path
            ),

            evidence_classes=[
                EvidenceClass.DEVELOPER_ASSUMPTION,
                EvidenceClass.DERIVED_FACT,
            ],

            description=(
                "Developer-supplied candidate polygon "
                "with deterministic geometry metrics."
            ),
        )
    ],

    limitations=site.get(
        "limitations",
        [],
    ),
)


# ---------------------------------------------------------
# Wind resource
# ---------------------------------------------------------

wind_domain = ScreeningDomain(
    status=KnowledgeStatus.PARTIAL,

    evidence_confidence=Confidence.HIGH,

    decision_confidence=Confidence.MEDIUM,

    facts={
        "data_year": 2025,

        "returned_grid_point": (
            wind[
                "source"
            ][
                "returned_grid_point"
            ]
        ),

        "hourly_observations": (
            wind[
                "time_series_quality"
            ][
                "rows"
            ]
        ),

        "missing_hourly_slots": (
            wind[
                "time_series_quality"
            ][
                "missing_hourly_slot_count"
            ]
        ),

        "mean_wind_speed_mps": {
            height: values[
                "mean_mps"
            ]

            for height, values
            in wind[
                "wind_speed"
            ].items()
        },

        "median_hourly_wind_speed_mps": {
            height: values[
                "p50_mps"
            ]

            for height, values
            in wind[
                "wind_speed"
            ].items()
        },

        "hourly_wind_speed_p90_mps": {
            height: values[
                "p90_mps"
            ]

            for height, values
            in wind[
                "wind_speed"
            ].items()
        },

        "wind_shear_alpha_median": (
            wind[
                "wind_shear_100m_160m"
            ][
                "median_alpha"
            ]
        ),
    },

    evidence=[
        EvidenceReference(
            source_id="WIND-001",

            artifact_path=str(
                wind_path
            ),

            evidence_classes=[
                EvidenceClass.SOURCE_FACT,
                EvidenceClass.DERIVED_FACT,
            ],

            description=(
                "2025 HRRR MET Toolkit modeled "
                "hourly meteorological screening data."
            ),
        )
    ],

    limitations=wind.get(
        "limitations",
        [],
    ),

    unresolved=[
        (
            "Obtain multi-year resource history "
            "for candidate-area grid cells."
        ),

        (
            "Characterize spatial variability "
            "across the candidate polygon."
        ),

        (
            "Do not calculate project AEP or "
            "P50/P90 until turbine assumptions "
            "and appropriate resource methodology "
            "are established."
        ),
    ],
)


# ---------------------------------------------------------
# Wetlands
# ---------------------------------------------------------

wetlands_domain = ScreeningDomain(
    status=KnowledgeStatus.OBSERVED,

    evidence_confidence=Confidence.HIGH,

    decision_confidence=Confidence.MEDIUM,

    facts={
        "nwi_mapped_overlap_acres": (
            nwi[
                "nwi_overlap_acres"
            ]
        ),

        "nwi_mapped_overlap_percent": (
            nwi[
                "nwi_overlap_percent"
            ]
        ),

        "wetland_types": (
            nwi[
                "wetland_types"
            ]
        ),
    },

    evidence=[
        EvidenceReference(
            source_id="ENV-WET-001",

            artifact_path=str(
                nwi_path
            ),

            evidence_classes=[
                EvidenceClass.SOURCE_FACT,
                EvidenceClass.DERIVED_FACT,
            ],

            description=(
                "USFWS National Wetlands Inventory "
                "mapped polygons intersecting the "
                "candidate area."
            ),
        )
    ],

    limitations=nwi.get(
        "limitations",
        [],
    ),

    unresolved=[
        (
            "Mapped NWI overlap is not a "
            "jurisdictional wetland determination."
        ),

        (
            "Determine project-specific wetland "
            "avoidance, buffer, permitting, and "
            "field-delineation requirements."
        ),
    ],
)


# ---------------------------------------------------------
# FEMA flood
# ---------------------------------------------------------

flood_domain = ScreeningDomain(
    status=KnowledgeStatus.UNKNOWN,

    evidence_confidence=Confidence.HIGH,

    decision_confidence=Confidence.LOW,

    facts={
        "nfhl_mapped_coverage_acres": (
            fema[
                "nfhl_mapped_coverage"
            ][
                "acres"
            ]
        ),

        "nfhl_mapped_coverage_percent": (
            fema[
                "nfhl_mapped_coverage"
            ][
                "percent"
            ]
        ),

        "unmapped_or_unknown_acres": (
            fema[
                "nfhl_unmapped_or_unknown"
            ][
                "acres"
            ]
        ),

        "unmapped_or_unknown_percent": (
            fema[
                "nfhl_unmapped_or_unknown"
            ][
                "percent"
            ]
        ),

        "sfha_overlap_acres": (
            fema[
                "special_flood_hazard_area"
            ][
                "acres"
            ]
        ),

        "coverage_reason": (
            "NO_DIGITAL_NFHL_OR_FIRM_PANEL_COVERAGE"
        ),
    },

    evidence=[
        EvidenceReference(
            source_id="ENV-FLOOD-001",

            artifact_path=str(
                fema_path
            ),

            evidence_classes=[
                EvidenceClass.SOURCE_FACT,
                EvidenceClass.DERIVED_FACT,
                EvidenceClass.UNRESOLVED,
            ],

            description=(
                "FEMA NFHL query returned no "
                "digital Flood Hazard Zone or "
                "FIRM panel coverage for the "
                "candidate area."
            ),
        )
    ],

    limitations=fema.get(
        "limitations",
        [],
    ),

    unresolved=[
        (
            "Flood exposure remains unknown "
            "because FEMA digital NFHL/FIRM "
            "coverage is unavailable."
        ),

        (
            "Identify alternate authoritative "
            "flood-risk evidence or require "
            "site-specific hydrologic review."
        ),
    ],
)


# ---------------------------------------------------------
# PAD-US
# ---------------------------------------------------------

protection_views = (
    padus.get(
        "protection_views",
        {}
    )
)

protected_domain = ScreeningDomain(
    status=KnowledgeStatus.OBSERVED,

    evidence_confidence=Confidence.HIGH,

    decision_confidence=Confidence.MEDIUM,

    facts={
        "padus_unique_overlap_acres": (
            padus[
                "padus_unique_overlap"
            ][
                "acres"
            ]
        ),

        "padus_unique_overlap_percent": (
            padus[
                "padus_unique_overlap"
            ][
                "percent_of_candidate"
            ]
        ),

        "biodiversity_protected_gap_1_2": (
            protection_views.get(
                "BIODIVERSITY_PROTECTED_GAP_1_2",
                {},
            )
        ),

        "multiple_use_gap_3": (
            protection_views.get(
                "MULTIPLE_USE_GAP_3",
                {},
            )
        ),

        "gap_4_management_context": (
            protection_views.get(
                "NO_KNOWN_BIODIVERSITY_PROTECTION_MANDATE_GAP_4",
                {},
            )
        ),

        "cross_gap_overlap_acres": (
            padus[
                "cross_gap_overlap_acres"
            ]
        ),

        "units": (
            padus[
                "units"
            ]
        ),
    },

    evidence=[
        EvidenceReference(
            source_id="ENV-PAD-001",

            artifact_path=str(
                padus_path
            ),

            evidence_classes=[
                EvidenceClass.SOURCE_FACT,
                EvidenceClass.DERIVED_FACT,
            ],

            description=(
                "PAD-US protected-area, management, "
                "designation, and GAP-status "
                "intersections."
            ),
        )
    ],

    limitations=padus.get(
        "limitations",
        [],
    ),

    unresolved=[
        (
            "Review Dewey County Wildlife "
            "Management Area development implications."
        ),

        (
            "Determine actual tribal, trust, "
            "reservation, or other land status "
            "where tribal statistical geography "
            "intersects the candidate."
        ),

        (
            "Determine State Land Board land-control "
            "and leasing implications."
        ),
    ],
)


# ---------------------------------------------------------
# Consolidated object
# ---------------------------------------------------------

result = CandidateSiteScreeningResult(
    project_id=project[
        "project_id"
    ],

    generated_utc=(
        datetime.now(
            timezone.utc
        ).isoformat()
    ),

    project={
        "name": (
            project[
                "project_name"
            ]
        ),

        "technology": (
            project[
                "technology"
            ]
        ),

        "target_capacity_mw": (
            project[
                "target_capacity_mw"
            ]
        ),

        "target_cod": (
            project[
                "target_cod"
            ]
        ),

        "development_stage": (
            project[
                "development_stage"
            ]
        ),

        "market": (
            project[
                "market"
            ]
        ),
    },

    site=site_domain,

    wind_resource=wind_domain,

    wetlands=wetlands_domain,

    flood=flood_domain,

    protected_lands=protected_domain,

    unresolved_project_questions=[
        "Long-term candidate-wide wind resource characterization.",
        "Terrain, elevation, and slope screening.",
        "Land-cover compatibility screening.",
        "Flood exposure due to FEMA coverage gap.",
        "Tribal and land-status diligence.",
        "State land-control / leasing diligence.",
        "Wildlife-management-area implications.",
        "SPP transmission and interconnection context for this candidate.",
        "ESA / species screening.",
        "Historic and cultural resource screening.",
        "FAA / aviation screening.",
        "Local permitting and setback requirements.",
    ],

    recommendation=None,

    recommendation_reason=(
        "No investment recommendation is produced "
        "at this stage because material development "
        "domains remain unresolved."
    ),
)


# ---------------------------------------------------------
# Write result
# ---------------------------------------------------------

output_dir = (
    RESULT_DIR
    / "screening"
)

output_dir.mkdir(
    parents=True,
    exist_ok=True,
)

output_path = (
    output_dir
    / "candidate_site_screening.json"
)

output_path.write_text(
    json.dumps(
        result.to_dict(),
        indent=2,
    ),
    encoding="utf-8",
)


# ---------------------------------------------------------
# Human-readable report
# ---------------------------------------------------------

print(
    "=== CANDIDATE SITE SCREENING RESULT ==="
)

print(
    "Project:",
    result.project_id,
)

print(
    "Target:",
    f"{result.project['target_capacity_mw']} MW",
    result.project["technology"],
)

print(
    "COD:",
    result.project["target_cod"],
)


print()
print(
    "=== SITE ==="
)

print(
    "Gross area:",
    f"{site_domain.facts['gross_area_acres']:,.1f} acres",
)


print()
print(
    "=== WIND RESOURCE ==="
)

print(
    "Status:",
    wind_domain.status,
)

print(
    "Decision confidence:",
    wind_domain.decision_confidence,
)

print(
    "2025 mean @ 120m:",
    f"{wind_domain.facts['mean_wind_speed_mps']['120m']:.3f} m/s",
)


print()
print(
    "=== WETLANDS ==="
)

print(
    "Status:",
    wetlands_domain.status,
)

print(
    "NWI mapped overlap:",
    (
        f"{wetlands_domain.facts['nwi_mapped_overlap_acres']:,.2f} "
        f"acres "
        f"({wetlands_domain.facts['nwi_mapped_overlap_percent']:.3f}%)"
    ),
)


print()
print(
    "=== FLOOD ==="
)

print(
    "Status:",
    flood_domain.status,
)

print(
    "Decision confidence:",
    flood_domain.decision_confidence,
)

print(
    "Reason:",
    flood_domain.facts[
        "coverage_reason"
    ],
)


print()
print(
    "=== PAD-US / LAND MANAGEMENT ==="
)

protected = (
    protected_domain.facts[
        "biodiversity_protected_gap_1_2"
    ]
)

print(
    "GAP 1/2 conservation signal:",
    (
        f"{protected.get('acres', 0):,.2f} acres "
        f"({protected.get('percent_of_candidate', 0):.3f}%)"
    ),
)

gap4 = (
    protected_domain.facts[
        "gap_4_management_context"
    ]
)

print(
    "GAP 4 management context:",
    (
        f"{gap4.get('acres', 0):,.2f} acres "
        f"({gap4.get('percent_of_candidate', 0):.3f}%)"
    ),
)


print()
print(
    "=== RECOMMENDATION ==="
)

print(
    result.recommendation
    or "NOT YET DETERMINED"
)

print(
    result.recommendation_reason
)


print()
print(
    "=== UNRESOLVED PROJECT QUESTIONS ==="
)

for question in (
    result.unresolved_project_questions
):
    print(
        "-",
        question,
    )


print()
print(
    "Output:",
    output_path,
)
