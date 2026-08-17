from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Callable


class CapabilityKind(StrEnum):
    PYTHON = "PYTHON"
    DATABRICKS = "DATABRICKS"
    MCP = "MCP"
    API = "API"
    SUBGRAPH = "SUBGRAPH"


# ------------------------------------------------------------
# A capability having a HANDLER (implementation code exists) is
# a different fact from that handler having what it needs to run
# right now (governed evidence has been supplied). Conflating
# them is exactly the bug this project hit with
# gis.resolve_flood_evidence: the handler was enabled the moment
# its Python module was written, so check_capability reported it
# "available" and routed straight to execution before
# flood_evidence had ever been placed in state - crashing with an
# uncaught RuntimeError instead of pausing for evidence like every
# other missing-evidence case does.
#
# `readiness`, when set, is called as readiness(state, task) and
# must return True only when the handler has everything it needs
# to run without raising. It is checked independently of whether
# the handler itself exists.
# ------------------------------------------------------------

ReadinessCheck = Callable[[dict[str, Any], dict[str, Any]], bool]


def requires_evidence(*state_keys: str) -> ReadinessCheck:

    """
    Readiness-check factory for the common case: the handler
    needs one or more governed-evidence dicts to be present,
    either on the task (supplied by a resume payload merge) or
    on the graph state.
    """

    def _check(
        state: dict[str, Any],
        task: dict[str, Any],
    ) -> bool:

        return all(
            (task or {}).get(key) or (state or {}).get(key)
            for key in state_keys
        )

    return _check


@dataclass(frozen=True)
class Capability:
    name: str
    kind: CapabilityKind
    description: str
    available: bool
    handler: Callable | None = None
    readiness: ReadinessCheck | None = None


CAPABILITIES: dict[str, Capability] = {}


def register_capability(
    capability: Capability,
) -> None:

    if capability.name in CAPABILITIES:
        raise ValueError(
            f"Capability already registered: "
            f"{capability.name}"
        )

    CAPABILITIES[
        capability.name
    ] = capability


def get_capability(
    name: str,
) -> Capability | None:

    return CAPABILITIES.get(
        name
    )


def capability_exists(
    name: str,
) -> bool:

    capability = get_capability(
        name
    )

    return bool(
        capability
        and capability.available
        and capability.handler
    )


# ------------------------------------------------------------
# Planned business capabilities
#
# These deliberately exist before their implementations.
#
# The investigation graph can therefore distinguish:
#
#   "we know what capability is required"
#
# from:
#
#   "we currently have an executable implementation."
# ------------------------------------------------------------

PLANNED_CAPABILITIES = [
    Capability(
        name="spp.transmission_context",
        kind=CapabilityKind.PYTHON,
        description=(
            "Determine candidate-relevant transmission "
            "facilities, plausible POIs, queue context, "
            "and relevant SPP studies."
        ),
        available=False,
    ),

    Capability(
        name="spp.analyze_precedent_study",
        kind=CapabilityKind.PYTHON,
        description=(
            "Analyze an authoritative SPP precedent "
            "study while preserving the distinction "
            "between precedent evidence and the "
            "candidate project's own outcome."
        ),
        available=False,
    ),

    Capability(
        name="spp.compare_model_cases",
        kind=CapabilityKind.PYTHON,
        description=(
            "Compare candidate POI behavior across "
            "multiple relevant SPP HCT model cases."
        ),
        available=False,
    ),

    Capability(
        name="spp.evaluate_additional_poi",
        kind=CapabilityKind.PYTHON,
        description=(
            "Evaluate an additional plausible SPP "
            "point of interconnection for the candidate "
            "using governed screening evidence."
        ),
        available=False,
    ),

    Capability(
        name="transmission.assess_gen_tie_context",
        kind=CapabilityKind.PYTHON,
        description=(
            "Assess candidate-site to transmission "
            "gen-tie context without claiming a final "
            "route or engineering design."
        ),
        available=False,
    ),

    Capability(
        name="wind.analyze_candidate_resource",
        kind=CapabilityKind.PYTHON,
        description=(
            "Characterize multi-year modeled wind "
            "resource across the candidate polygon."
        ),
        available=False,
    ),

    Capability(
        name="gis.analyze_terrain",
        kind=CapabilityKind.PYTHON,
        description=(
            "Calculate elevation and slope "
            "statistics from authoritative terrain data."
        ),
        available=False,
    ),

    Capability(
        name="gis.analyze_land_cover",
        kind=CapabilityKind.PYTHON,
        description=(
            "Calculate candidate land-cover "
            "composition from authoritative raster data."
        ),
        available=False,
    ),

    Capability(
        name="environment.screen_species",
        kind=CapabilityKind.API,
        description=(
            "Screen candidate for species "
            "and habitat concerns."
        ),
        available=False,
    ),

    Capability(
        name="land.resolve_status",
        kind=CapabilityKind.SUBGRAPH,
        description=(
            "Resolve tribal, state, conservation, "
            "and other land-management status."
        ),
        available=False,
    ),

    Capability(
        name="aviation.screen_candidate",
        kind=CapabilityKind.API,
        description=(
            "Screen aviation and military "
            "compatibility concerns."
        ),
        available=False,
    ),

    Capability(
        name="regulatory.build_permit_matrix",
        kind=CapabilityKind.SUBGRAPH,
        description=(
            "Build evidence-backed permitting "
            "and regulatory matrix."
        ),
        available=False,
    ),

    Capability(
        name="environment.screen_cultural_resources",
        kind=CapabilityKind.API,
        description=(
            "Screen historic and cultural "
            "resource context."
        ),
        available=False,
    ),

    Capability(
        name="gis.resolve_flood_evidence",
        kind=CapabilityKind.SUBGRAPH,
        description=(
            "Find alternate authoritative flood "
            "evidence where NFHL coverage is absent."
        ),
        available=False,
    ),
]


for planned in PLANNED_CAPABILITIES:
    register_capability(
        planned
    )


def enable_capability(
    name: str,
    handler: Callable,
    readiness: ReadinessCheck | None = None,
) -> None:

    existing = CAPABILITIES.get(
        name
    )

    if existing is None:
        raise KeyError(
            f"Capability not registered: {name}"
        )

    CAPABILITIES[name] = Capability(
        name=existing.name,
        kind=existing.kind,
        description=existing.description,
        available=True,
        handler=handler,
        readiness=readiness,
    )
