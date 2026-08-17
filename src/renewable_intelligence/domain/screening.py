from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class KnowledgeStatus(StrEnum):
    OBSERVED = "OBSERVED"
    PARTIAL = "PARTIAL"
    UNKNOWN = "UNKNOWN"


class Confidence(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class EvidenceClass(StrEnum):
    SOURCE_FACT = "SOURCE_FACT"
    DERIVED_FACT = "DERIVED_FACT"
    AGENT_INTERPRETATION = "AGENT_INTERPRETATION"
    DEVELOPER_ASSUMPTION = "DEVELOPER_ASSUMPTION"
    UNRESOLVED = "UNRESOLVED"


@dataclass
class EvidenceReference:
    source_id: str
    artifact_path: str
    evidence_classes: list[EvidenceClass]
    description: str


@dataclass
class ScreeningDomain:
    status: KnowledgeStatus

    evidence_confidence: Confidence

    decision_confidence: Confidence

    facts: dict[str, Any]

    evidence: list[EvidenceReference] = field(
        default_factory=list
    )

    limitations: list[str] = field(
        default_factory=list
    )

    unresolved: list[str] = field(
        default_factory=list
    )


@dataclass
class CandidateSiteScreeningResult:
    project_id: str

    generated_utc: str

    project: dict[str, Any]

    site: ScreeningDomain

    wind_resource: ScreeningDomain

    wetlands: ScreeningDomain

    flood: ScreeningDomain

    protected_lands: ScreeningDomain

    unresolved_project_questions: list[str]

    recommendation: str | None = None

    recommendation_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
