from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from renewable_intelligence.domain.gates import (
    GateStatus,
    Materiality,
)


# ------------------------------------------------------------
# Gate <-> domain grouping.
#
# This mirrors the blocking_gate_ids already assigned to each
# investigation task in development_gate_assessment.json.
# ------------------------------------------------------------

GATE_DOMAINS = {
    "G1": ["wind_resource", "terrain", "land_cover"],
    "G2": ["interconnection"],
    "G3": ["land_status", "species", "flood", "cultural"],
    "G4": ["regulatory"],
    "G5": ["aviation"],
}

GATE_NAMES = {
    "G1": "Resource and Physical Site Suitability",
    "G2": "Transmission and Interconnection",
    "G3": "Environmental and Land Constraints",
    "G4": "Permitting and Regulatory Path",
    "G5": "Aviation and Military Compatibility",
}

GATE_MATERIALITY = {
    "G1": Materiality.HIGH,
    "G2": Materiality.CRITICAL,
    "G3": Materiality.HIGH,
    "G4": Materiality.HIGH,
    "G5": Materiality.HIGH,
}


CONFIDENCE_RANK = {
    "LOW": 0,
    "MEDIUM": 1,
    "HIGH": 2,
}


# ------------------------------------------------------------
# Per-domain material-risk extraction.
#
# Each function reads the FINAL evidence_ledger assessment's
# "finding" dict for that domain (already produced by the
# deterministic capability + result_assessment.py, never
# re-interpreted here) and returns explicit, source-grounded
# risk records. This function set is the only place that
# decides what counts as a "material risk" for synthesis
# purposes; it does not invent new facts.
# ------------------------------------------------------------

def _risks_land_status(finding: dict[str, Any]) -> list[dict[str, Any]]:

    risks = []

    if finding.get("tribal_interest_flagged"):
        risks.append(
            {
                "severity": Materiality.MEDIUM,
                "description": (
                    "PAD-US tribal statistical area overlaps "
                    "the candidate; authoritative tribal legal/"
                    "trust status has not been established."
                ),
            }
        )

    if finding.get("state_managed_land_flagged"):
        risks.append(
            {
                "severity": Materiality.MEDIUM,
                "description": (
                    "State Land Board (CLO) lands overlap the "
                    "candidate; lease/sale eligibility has not "
                    "been established."
                ),
            }
        )

    if finding.get("conservation_area_flagged"):
        risks.append(
            {
                "severity": Materiality.LOW,
                "description": (
                    "A state wildlife management area overlaps "
                    "the candidate; access/use restrictions have "
                    "not been established."
                ),
            }
        )

    return risks


def _risks_species(finding: dict[str, Any]) -> list[dict[str, Any]]:

    risks = []

    if finding.get("endangered_species_flagged"):
        risks.append(
            {
                "severity": Materiality.HIGH,
                "description": (
                    "Final designated USFWS critical habitat "
                    "for a federally Endangered species overlaps "
                    "the candidate; ESA Section 7 consultation is "
                    "likely required where a federal nexus "
                    "exists."
                ),
            }
        )

    if (
        finding.get("threatened_species_flagged")
        and not finding.get("endangered_species_flagged")
    ):
        risks.append(
            {
                "severity": Materiality.MEDIUM,
                "description": (
                    "Critical habitat for a federally Threatened "
                    "species overlaps the candidate."
                ),
            }
        )

    return risks


def _risks_flood(finding: dict[str, Any]) -> list[dict[str, Any]]:

    if (
        finding.get("nfhl_coverage_status")
        == "NO_DIGITAL_COVERAGE"
    ):

        return [
            {
                "severity": Materiality.MEDIUM,
                "description": (
                    "FEMA NFHL has zero digital coverage for "
                    "the candidate; flood-hazard status is "
                    "genuinely UNKNOWN, not confirmed low-risk."
                ),
            }
        ]

    return []


def _risks_cultural(finding: dict[str, Any]) -> list[dict[str, Any]]:

    risks = []

    if finding.get("direct_intersection_count", 0) > 0:
        risks.append(
            {
                "severity": Materiality.MEDIUM,
                "description": (
                    "At least one NRHP-listed historic resource "
                    "directly intersects the candidate polygon; "
                    "Section 106 review has not been performed."
                ),
            }
        )

    if finding.get("national_historic_landmark_flagged"):
        risks.append(
            {
                "severity": Materiality.HIGH,
                "description": (
                    "A National Historic Landmark is flagged "
                    "within the screening radius."
                ),
            }
        )

    return risks


def _risks_terrain(finding: dict[str, Any]) -> list[dict[str, Any]]:

    pct = finding.get(
        "percent_of_area_over_15pct_slope"
    )

    if isinstance(pct, (int, float)) and pct > 10:
        return [
            {
                "severity": Materiality.LOW,
                "description": (
                    f"{pct:.1f}% of the sampled candidate area "
                    "exceeds 15% slope; no constructability "
                    "threshold has been applied."
                ),
            }
        ]

    return []


def _risks_land_cover(finding: dict[str, Any]) -> list[dict[str, Any]]:

    return []


def _risks_wind_resource(finding: dict[str, Any]) -> list[dict[str, Any]]:

    return [
        {
            "severity": Materiality.LOW,
            "description": (
                "Wind-resource evidence is a single modeled grid "
                "point over a single calendar year; candidate-"
                "wide, multi-year resource is unresolved."
            ),
        }
    ]


def _risks_aviation(finding: dict[str, Any]) -> list[dict[str, Any]]:

    risks = []

    if finding.get(
        "military_special_use_airspace_intersection_count",
        0,
    ) > 0:
        risks.append(
            {
                "severity": Materiality.MEDIUM,
                "description": (
                    "Military Special Use Airspace intersects "
                    "the candidate boundary."
                ),
            }
        )

    if finding.get("statutory_setback_appears_violated"):
        risks.append(
            {
                "severity": Materiality.HIGH,
                "description": (
                    "Nearest public-use airport appears closer "
                    "than the statutory 1.5 nm setback."
                ),
            }
        )

    return risks


def _risks_regulatory(finding: dict[str, Any]) -> list[dict[str, Any]]:

    risks = []

    # Both tracked wind-setback bills (SB2, HB2751) failed in the
    # 2025-2026 session (verified against official sources) and
    # do not currently pose a pending-legislation risk. That
    # status is manually verified, not API-fetched, and could go
    # stale if a new session convenes; the timestamp for when it
    # was last checked lives in finding.legislative_status_
    # verified_utc for anyone auditing this assessment's currency.

    if finding.get("not_yet_verified_count", 0) > 0:
        risks.append(
            {
                "severity": Materiality.MEDIUM,
                "description": (
                    "County/local zoning ordinance text has not "
                    "been retrieved or verified."
                ),
            }
        )

    return risks


def _risks_interconnection(finding: dict[str, Any]) -> list[dict[str, Any]]:

    return [
        {
            "severity": Materiality.HIGH,
            "description": (
                "Candidate-specific generator interconnection "
                "feasibility and network-upgrade cost have not "
                "been established; only screening-level HCT "
                "comparisons exist."
            ),
        }
    ]


DOMAIN_RISK_EXTRACTORS = {
    "land_status": _risks_land_status,
    "species": _risks_species,
    "flood": _risks_flood,
    "cultural": _risks_cultural,
    "terrain": _risks_terrain,
    "land_cover": _risks_land_cover,
    "wind_resource": _risks_wind_resource,
    "aviation": _risks_aviation,
    "regulatory": _risks_regulatory,
    "interconnection": _risks_interconnection,
}


@dataclass
class GateSynthesis:
    gate_id: str
    name: str
    materiality: Materiality
    status: GateStatus
    domains: list[str]
    observed_facts: list[str] = field(default_factory=list)
    material_risks: list[dict[str, Any]] = field(
        default_factory=list
    )
    confidence: str = "LOW"
    evidence_gaps: list[str] = field(default_factory=list)
    human_diligence_requirements: list[str] = field(
        default_factory=list
    )

    def to_dict(self) -> dict[str, Any]:

        return {
            "gate_id": self.gate_id,
            "name": self.name,
            "materiality": str(self.materiality),
            "status": str(self.status),
            "domains": self.domains,
            "observed_facts": self.observed_facts,
            "material_risks": [
                {
                    "severity": str(item["severity"]),
                    "description": item["description"],
                }
                for item in self.material_risks
            ],
            "confidence": self.confidence,
            "evidence_gaps": self.evidence_gaps,
            "human_diligence_requirements": (
                self.human_diligence_requirements
            ),
        }


def _latest_ledger_assessment(
    *,
    domain: str,
    domain_outcome: dict[str, Any],
    evidence_ledger: list[dict[str, Any]],
) -> dict[str, Any]:

    latest_task_id = domain_outcome.get("latest_task_id")
    latest_capability = domain_outcome.get(
        "latest_capability"
    )

    for entry in reversed(evidence_ledger):

        if (
            entry.get("task_id") == latest_task_id
            and entry.get("capability") == latest_capability
        ):

            return entry.get("assessment", {})

    return {}


def synthesize_gate(
    *,
    gate_id: str,
    project_domain_outcomes: dict[str, dict[str, Any]],
    evidence_ledger: list[dict[str, Any]],
) -> GateSynthesis:

    domains = GATE_DOMAINS[gate_id]

    observed_facts: list[str] = []
    material_risks: list[dict[str, Any]] = []
    evidence_gaps: list[str] = []
    human_diligence_requirements: list[str] = []

    present_domains = []

    worst_confidence_rank = 2

    has_evidence_gap = False

    for domain in domains:

        outcome = project_domain_outcomes.get(domain)

        if not outcome:
            continue

        present_domains.append(domain)

        observed_facts.extend(
            outcome.get("resolved_uncertainty", [])
        )

        evidence_gaps.extend(
            outcome.get("remaining_uncertainty", [])
        )

        human_diligence_requirements.append(
            f"{domain}: {outcome.get('screening_status')}"
        )

        confidence = outcome.get(
            "decision_confidence", "LOW"
        )

        worst_confidence_rank = min(
            worst_confidence_rank,
            CONFIDENCE_RANK.get(confidence, 0),
        )

        assessment = _latest_ledger_assessment(
            domain=domain,
            domain_outcome=outcome,
            evidence_ledger=evidence_ledger,
        )

        finding = assessment.get("finding", {})

        extractor = DOMAIN_RISK_EXTRACTORS.get(domain)

        if extractor:
            material_risks.extend(extractor(finding))

        if (
            domain == "flood"
            and finding.get("nfhl_coverage_status")
            == "NO_DIGITAL_COVERAGE"
        ):
            has_evidence_gap = True

    confidence_label = {
        v: k for k, v in CONFIDENCE_RANK.items()
    }[worst_confidence_rank]

    missing_domains = [
        domain
        for domain in domains
        if domain not in present_domains
    ]

    has_high_or_critical_risk = any(
        item["severity"]
        in {Materiality.HIGH, Materiality.CRITICAL}
        for item in material_risks
    )

    if missing_domains:
        status = GateStatus.UNRESOLVED

    elif has_evidence_gap:
        status = GateStatus.UNRESOLVED

    elif has_high_or_critical_risk:
        status = GateStatus.CONDITIONALLY_SATISFIED

    else:
        status = GateStatus.CONDITIONALLY_SATISFIED

    return GateSynthesis(
        gate_id=gate_id,
        name=GATE_NAMES[gate_id],
        materiality=GATE_MATERIALITY[gate_id],
        status=status,
        domains=domains,
        observed_facts=observed_facts,
        material_risks=material_risks,
        confidence=confidence_label,
        evidence_gaps=evidence_gaps,
        human_diligence_requirements=(
            human_diligence_requirements
        ),
    )


def synthesize_all_gates(
    *,
    project_domain_outcomes: dict[str, dict[str, Any]],
    evidence_ledger: list[dict[str, Any]],
) -> list[GateSynthesis]:

    return [
        synthesize_gate(
            gate_id=gate_id,
            project_domain_outcomes=(
                project_domain_outcomes
            ),
            evidence_ledger=evidence_ledger,
        )
        for gate_id in GATE_DOMAINS
    ]
