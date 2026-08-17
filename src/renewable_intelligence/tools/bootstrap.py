from renewable_intelligence.interconnection.spp_precedent_study import (
    analyze_precedent_study,
)
from renewable_intelligence.interconnection.spp_model_case_comparison import (
    compare_model_cases,
)
from renewable_intelligence.interconnection.spp_additional_poi import (
    evaluate_additional_poi,
)
from renewable_intelligence.interconnection.spp_transmission_context import (
    run_transmission_context,
)
from renewable_intelligence.transmission.gen_tie_context import (
    assess_gen_tie_context,
)
from renewable_intelligence.land.land_status_screening import (
    resolve_land_status,
)
from renewable_intelligence.environmental.species_screening import (
    screen_species,
)
from renewable_intelligence.gis.terrain_screening import (
    analyze_terrain,
)
from renewable_intelligence.gis.land_cover_screening import (
    analyze_land_cover,
)
from renewable_intelligence.gis.flood_screening import (
    resolve_flood_evidence,
)
from renewable_intelligence.regulatory.permit_matrix import (
    build_permit_matrix,
)
from renewable_intelligence.aviation.aviation_screening import (
    screen_candidate,
)
from renewable_intelligence.resource.wind_resource_screening import (
    analyze_candidate_resource,
)
from renewable_intelligence.environmental.cultural_resources_screening import (
    screen_cultural_resources,
)
from renewable_intelligence.tools.registry import (
    enable_capability,
)


def register_implemented_capabilities():

    enable_capability(
        "spp.transmission_context",
        run_transmission_context,
    )

    enable_capability(
        "spp.analyze_precedent_study",
        analyze_precedent_study,
    )

    enable_capability(
        "spp.compare_model_cases",
        compare_model_cases,
    )

    enable_capability(
        "spp.evaluate_additional_poi",
        evaluate_additional_poi,
    )

    enable_capability(
        "transmission.assess_gen_tie_context",
        assess_gen_tie_context,
    )

    enable_capability(
        "land.resolve_status",
        resolve_land_status,
    )

    enable_capability(
        "environment.screen_species",
        screen_species,
    )

    enable_capability(
        "gis.analyze_terrain",
        analyze_terrain,
    )

    enable_capability(
        "gis.analyze_land_cover",
        analyze_land_cover,
    )

    enable_capability(
        "gis.resolve_flood_evidence",
        resolve_flood_evidence,
    )

    enable_capability(
        "regulatory.build_permit_matrix",
        build_permit_matrix,
    )

    enable_capability(
        "aviation.screen_candidate",
        screen_candidate,
    )

    enable_capability(
        "wind.analyze_candidate_resource",
        analyze_candidate_resource,
    )

    enable_capability(
        "environment.screen_cultural_resources",
        screen_cultural_resources,
    )
