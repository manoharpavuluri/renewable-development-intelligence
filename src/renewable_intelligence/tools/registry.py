from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Callable


class CapabilityKind(StrEnum):
    PYTHON = "PYTHON"
    DATABRICKS = "DATABRICKS"
    MCP = "MCP"
    API = "API"
    SUBGRAPH = "SUBGRAPH"


@dataclass(frozen=True)
class Capability:
    name: str
    kind: CapabilityKind
    description: str
    available: bool
    handler: Callable | None = None


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
    )
