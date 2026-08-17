from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class GateStatus(StrEnum):
    SATISFIED = "SATISFIED"
    CONDITIONALLY_SATISFIED = "CONDITIONALLY_SATISFIED"
    UNSATISFIED = "UNSATISFIED"
    UNRESOLVED = "UNRESOLVED"


class Materiality(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class InvestigationPriority(StrEnum):
    BLOCKING = "BLOCKING"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class InvestigationStatus(StrEnum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETE = "COMPLETE"
    BLOCKED = "BLOCKED"


@dataclass
class DevelopmentGate:
    gate_id: str
    name: str

    status: GateStatus

    materiality: Materiality

    rationale: str

    supporting_domains: list[str] = field(
        default_factory=list
    )

    missing_evidence: list[str] = field(
        default_factory=list
    )

    next_actions: list[str] = field(
        default_factory=list
    )

    human_review_required: bool = False


@dataclass
class InvestigationTask:
    task_id: str
    domain: str
    question: str

    priority: InvestigationPriority

    reason: str

    blocking_gate_ids: list[str]

    preferred_capability: str

    status: InvestigationStatus = (
        InvestigationStatus.PENDING
    )

    depends_on: list[str] = field(
        default_factory=list
    )


@dataclass
class DevelopmentGateAssessment:
    project_id: str

    generated_utc: str

    gates: list[DevelopmentGate]

    investigation_queue: list[InvestigationTask]

    overall_gate_state: str

    recommendation_allowed: bool

    recommendation_blockers: list[str]

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
