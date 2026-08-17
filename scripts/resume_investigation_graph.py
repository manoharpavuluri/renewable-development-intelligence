#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from langgraph.types import (
    Command,
)

from renewable_intelligence.graph.investigation_graph import (
    build_investigation_graph,
)
from renewable_intelligence.persistence.checkpointing import (
    checkpoint_backend_description,
    open_checkpointer,
)
from renewable_intelligence.tools.bootstrap import (
    register_implemented_capabilities,
)


THREAD_ID = os.environ.get(
    "RDI_THREAD_ID",
    "RDI-WOK-250-001:screening:v1",
)


RESULT_DIR_RAW = os.environ.get(
    "RESULT_DIR"
)

if not RESULT_DIR_RAW:

    raise SystemExit(
        "RESULT_DIR is not set."
    )


RESULT_DIR = Path(
    RESULT_DIR_RAW
)


EXPECTED_MATHWSN_HASHES = {
    "TC00": (
        "05e22e01834f22cbce825723d5e7d06d83e5e8d61b3c4a020d6affa8280f538b"
    ),

    "TC03": (
        "b1f5f8a530af4a925c0c0b5006eca5a7d21657f69275ae8c5b818d9476d290da"
    ),
}


EXPECTED_PADUS_SUMMARY_HASH = (
    "381146821c9a97b6dd829d91b075a5d60819356ed955e7ff9a543f3da82a4508"
)


EXPECTED_CRITICAL_HABITAT_SUMMARY_HASH = (
    "8113a55f2b97bedd1a7add9bbf3f5acd38ed42910ba4f412d5b42e13c7100ade"
)


EXPECTED_TERRAIN_SUMMARY_HASH = (
    "81ba8e033276cbbd51f00a4c719b740fc97fec014920b2d873c91bcdfd8e44c0"
)


EXPECTED_LAND_COVER_SUMMARY_HASH = (
    "d4a92088025aacab5d127b4cb806c08036e5e13eb8b446251f8216a40110bf93"
)


EXPECTED_FEMA_NFHL_SUMMARY_HASH = (
    "5ee1d395c4981fce68852e349205b10a392cb7dbeb5d98d07cc863726b27c663"
)


EXPECTED_JURISDICTION_SUMMARY_HASH = (
    "8dc3de0160b759de88d8191e6bc630d4b10ad337148ff2714ba7ee17c28e914d"
)


EXPECTED_AVIATION_SUMMARY_HASH = (
    "15b7eb63d23b22aa674957ffeedc4971419e464986fcaf7b03e4201f6650242d"
)


EXPECTED_WIND_RESOURCE_SUMMARY_HASH = (
    "54fc8c66f23031f7452d581521b0165a00dcd00a1d4e29ab82427d8f45dae22d"
)


EXPECTED_CULTURAL_RESOURCES_SUMMARY_HASH = (
    "f8a094f8670e23a038dffdc64217aa761d05b488c53775a52706ddbb4f7b87c0"
)


def sha256_file(
    path: Path,
) -> str:

    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def build_additional_poi_evidence(
    snapshot_values,
):

    base_cases = (
        snapshot_values.get(
            "spp_hct_model_cases"
        )
        or {}
    )


    required_cases = {
        "TC00",
        "TC03",
    }


    if not required_cases.issubset(
        base_cases.keys()
    ):

        raise RuntimeError(
            "Checkpoint does not contain the "
            "required TC00 and TC03 base HCT cases."
        )


    expanded_cases = {}


    for case_id in [
        "TC00",
        "TC03",
    ]:

        base_case = (
            base_cases[
                case_id
            ]
        )

        model_name = base_case.get(
            "model"
        )

        existing_pois = dict(
            base_case.get(
                "pois"
            )
            or {}
        )


        case_dir = (
            RESULT_DIR
            / "spp_hct"
            / "additional_poi"
            / "515497_MATHWSN7"
            / case_id
        )

        artifact = (
            case_dir
            / "grid-data.csv"
        )

        query_path = (
            case_dir
            / "query.json"
        )


        if not artifact.exists():

            raise FileNotFoundError(
                artifact
            )


        if not query_path.exists():

            raise FileNotFoundError(
                query_path
            )


        query = json.loads(
            query_path.read_text(
                encoding="utf-8"
            )
        )


        actual_hash = sha256_file(
            artifact
        )

        expected_hash = (
            EXPECTED_MATHWSN_HASHES[
                case_id
            ]
        )


        if (
            actual_hash
            != expected_hash
        ):

            raise RuntimeError(
                f"{case_id} MATHWSN7 artifact "
                "hash does not match the governed "
                "expected hash."
            )


        if (
            query.get(
                "artifact_sha256"
            )
            != actual_hash
        ):

            raise RuntimeError(
                f"{case_id} query sidecar hash "
                "does not match grid-data.csv."
            )


        expected_query_values = {
            "source": (
                "SPP Pre-Screening Tool"
            ),
            "model": (
                model_name
            ),
            "area": "OKGE",
            "kv": 345,
            "bus_id": 515497,
            "bus_name": (
                "MATHWSN7"
            ),
            "injection_mw": 250,
        }


        for key, expected in (
            expected_query_values.items()
        ):

            if (
                query.get(
                    key
                )
                != expected
            ):

                raise RuntimeError(
                    f"{case_id} query provenance "
                    f"mismatch for {key!r}: "
                    f"{query.get(key)!r} "
                    f"!= {expected!r}"
                )


        existing_pois[
            "MATHWSN7"
        ] = str(
            artifact
        )


        expanded_cases[
            case_id
        ] = {
            "model": (
                model_name
            ),

            "pois": (
                existing_pois
            ),
        }


    return {
        "additional_pois": [
            "MATHWSN7",
        ],

        "model_cases": (
            expanded_cases
        ),
    }


PADUS_SUMMARY_PATH = (
    Path(
        "data/spikes/public_sources_20260815T173207Z"
        "/gis/padus/padus_summary.json"
    )
)


def build_land_status_evidence():

    if not PADUS_SUMMARY_PATH.exists():

        raise FileNotFoundError(
            PADUS_SUMMARY_PATH
        )

    actual_hash = sha256_file(
        PADUS_SUMMARY_PATH
    )

    if (
        actual_hash
        != EXPECTED_PADUS_SUMMARY_HASH
    ):

        raise RuntimeError(
            "PAD-US summary artifact hash does "
            "not match the governed expected hash."
        )

    return {
        "padus_summary_artifact": str(
            PADUS_SUMMARY_PATH
        ),
    }


CRITICAL_HABITAT_SUMMARY_PATH = (
    Path(
        "data/spikes/public_sources_20260815T173207Z"
        "/gis/critical_habitat/critical_habitat_summary.json"
    )
)


def build_species_evidence():

    if not CRITICAL_HABITAT_SUMMARY_PATH.exists():

        raise FileNotFoundError(
            CRITICAL_HABITAT_SUMMARY_PATH
        )

    actual_hash = sha256_file(
        CRITICAL_HABITAT_SUMMARY_PATH
    )

    if (
        actual_hash
        != EXPECTED_CRITICAL_HABITAT_SUMMARY_HASH
    ):

        raise RuntimeError(
            "Critical-habitat summary artifact hash does "
            "not match the governed expected hash."
        )

    return {
        "critical_habitat_summary_artifact": str(
            CRITICAL_HABITAT_SUMMARY_PATH
        ),
    }


TERRAIN_SUMMARY_PATH = (
    Path(
        "data/spikes/public_sources_20260815T173207Z"
        "/gis/terrain/terrain_summary.json"
    )
)


def build_terrain_evidence():

    if not TERRAIN_SUMMARY_PATH.exists():

        raise FileNotFoundError(
            TERRAIN_SUMMARY_PATH
        )

    actual_hash = sha256_file(
        TERRAIN_SUMMARY_PATH
    )

    if (
        actual_hash
        != EXPECTED_TERRAIN_SUMMARY_HASH
    ):

        raise RuntimeError(
            "Terrain summary artifact hash does "
            "not match the governed expected hash."
        )

    return {
        "terrain_summary_artifact": str(
            TERRAIN_SUMMARY_PATH
        ),
    }


LAND_COVER_SUMMARY_PATH = (
    Path(
        "data/spikes/public_sources_20260815T173207Z"
        "/gis/land_cover/land_cover_summary.json"
    )
)


def build_land_cover_evidence():

    if not LAND_COVER_SUMMARY_PATH.exists():

        raise FileNotFoundError(
            LAND_COVER_SUMMARY_PATH
        )

    actual_hash = sha256_file(
        LAND_COVER_SUMMARY_PATH
    )

    if (
        actual_hash
        != EXPECTED_LAND_COVER_SUMMARY_HASH
    ):

        raise RuntimeError(
            "Land-cover summary artifact hash does "
            "not match the governed expected hash."
        )

    return {
        "land_cover_summary_artifact": str(
            LAND_COVER_SUMMARY_PATH
        ),
    }


FEMA_NFHL_SUMMARY_PATH = (
    Path(
        "data/spikes/public_sources_20260815T173207Z"
        "/gis/fema_nfhl/fema_nfhl_summary.json"
    )
)


def build_flood_evidence():

    if not FEMA_NFHL_SUMMARY_PATH.exists():

        raise FileNotFoundError(
            FEMA_NFHL_SUMMARY_PATH
        )

    actual_hash = sha256_file(
        FEMA_NFHL_SUMMARY_PATH
    )

    if (
        actual_hash
        != EXPECTED_FEMA_NFHL_SUMMARY_HASH
    ):

        raise RuntimeError(
            "FEMA NFHL summary artifact hash does "
            "not match the governed expected hash."
        )

    return {
        "fema_nfhl_summary_artifact": str(
            FEMA_NFHL_SUMMARY_PATH
        ),
    }


JURISDICTION_SUMMARY_PATH = (
    Path(
        "data/spikes/public_sources_20260815T173207Z"
        "/gis/jurisdiction/jurisdiction_summary.json"
    )
)


def build_regulatory_evidence():

    if not JURISDICTION_SUMMARY_PATH.exists():

        raise FileNotFoundError(
            JURISDICTION_SUMMARY_PATH
        )

    actual_hash = sha256_file(
        JURISDICTION_SUMMARY_PATH
    )

    if (
        actual_hash
        != EXPECTED_JURISDICTION_SUMMARY_HASH
    ):

        raise RuntimeError(
            "Jurisdiction summary artifact hash does "
            "not match the governed expected hash."
        )

    return {
        "jurisdiction_summary_artifact": str(
            JURISDICTION_SUMMARY_PATH
        ),
    }


AVIATION_SUMMARY_PATH = (
    Path(
        "data/spikes/public_sources_20260815T173207Z"
        "/aviation/aviation_summary.json"
    )
)


def build_aviation_evidence():

    if not AVIATION_SUMMARY_PATH.exists():

        raise FileNotFoundError(
            AVIATION_SUMMARY_PATH
        )

    actual_hash = sha256_file(
        AVIATION_SUMMARY_PATH
    )

    if (
        actual_hash
        != EXPECTED_AVIATION_SUMMARY_HASH
    ):

        raise RuntimeError(
            "Aviation summary artifact hash does "
            "not match the governed expected hash."
        )

    return {
        "aviation_summary_artifact": str(
            AVIATION_SUMMARY_PATH
        ),
    }


WIND_RESOURCE_SUMMARY_PATH = (
    Path(
        "data/spikes/public_sources_20260815T173207Z"
        "/wind_resource/hrrr_met_2025_test_point_summary.json"
    )
)


def build_wind_resource_evidence():

    if not WIND_RESOURCE_SUMMARY_PATH.exists():

        raise FileNotFoundError(
            WIND_RESOURCE_SUMMARY_PATH
        )

    actual_hash = sha256_file(
        WIND_RESOURCE_SUMMARY_PATH
    )

    if (
        actual_hash
        != EXPECTED_WIND_RESOURCE_SUMMARY_HASH
    ):

        raise RuntimeError(
            "Wind-resource summary artifact hash does "
            "not match the governed expected hash."
        )

    return {
        "hrrr_met_summary_artifact": str(
            WIND_RESOURCE_SUMMARY_PATH
        ),
    }


CULTURAL_RESOURCES_SUMMARY_PATH = (
    Path(
        "data/spikes/public_sources_20260815T173207Z"
        "/gis/cultural_resources/cultural_resources_summary.json"
    )
)


def build_cultural_resources_evidence():

    if not CULTURAL_RESOURCES_SUMMARY_PATH.exists():

        raise FileNotFoundError(
            CULTURAL_RESOURCES_SUMMARY_PATH
        )

    actual_hash = sha256_file(
        CULTURAL_RESOURCES_SUMMARY_PATH
    )

    if (
        actual_hash
        != EXPECTED_CULTURAL_RESOURCES_SUMMARY_HASH
    ):

        raise RuntimeError(
            "Cultural-resources summary artifact hash does "
            "not match the governed expected hash."
        )

    return {
        "nrhp_summary_artifact": str(
            CULTURAL_RESOURCES_SUMMARY_PATH
        ),
    }


register_implemented_capabilities()


checkpoint_backend = (
    checkpoint_backend_description()
)


config = {
    "configurable": {
        "thread_id": (
            THREAD_ID
        )
    }
}


with open_checkpointer() as checkpointer:

    graph = build_investigation_graph(
        checkpointer=checkpointer
    )


    snapshot = graph.get_state(
        config
    )


    if not snapshot.values:

        raise SystemExit(
            f"No saved state exists for "
            f"thread {THREAD_ID!r} "
            f"using {checkpoint_backend}."
        )


    print(
        "=== RESUMING INVESTIGATION THREAD ==="
    )

    print(
        "Backend:",
        checkpoint_backend,
    )

    print(
        "Thread:",
        THREAD_ID,
    )

    print(
        "Project:",
        snapshot.values.get(
            "project_id"
        ),
    )

    print(
        "Task:",
        snapshot.values.get(
            "selected_task_id"
        ),
    )

    print(
        "Capability:",
        snapshot.values.get(
            "selected_capability"
        ),
    )


    resume_payload = {
        "action": (
            "RETRY_CAPABILITY"
        )
    }


    if (
        snapshot.values.get(
            "selected_capability"
        )
        ==
        "spp.evaluate_additional_poi"
    ):

        additional_poi_evidence = (
            build_additional_poi_evidence(
                snapshot.values
            )
        )

        resume_payload[
            "spp_additional_poi_evidence"
        ] = additional_poi_evidence


        print(
            "Resume evidence:",
            "MATHWSN7 across",
            len(
                additional_poi_evidence[
                    "model_cases"
                ]
            ),
            "model cases",
        )


    if (
        snapshot.values.get(
            "selected_capability"
        )
        ==
        "land.resolve_status"
    ):

        land_status_evidence = (
            build_land_status_evidence()
        )

        resume_payload[
            "land_status_evidence"
        ] = land_status_evidence

        print(
            "Resume evidence:",
            "PAD-US summary artifact",
            land_status_evidence[
                "padus_summary_artifact"
            ],
        )


    if (
        snapshot.values.get(
            "selected_capability"
        )
        ==
        "environment.screen_species"
    ):

        species_evidence = (
            build_species_evidence()
        )

        resume_payload[
            "species_evidence"
        ] = species_evidence

        print(
            "Resume evidence:",
            "Critical-habitat summary artifact",
            species_evidence[
                "critical_habitat_summary_artifact"
            ],
        )


    if (
        snapshot.values.get(
            "selected_capability"
        )
        ==
        "gis.analyze_terrain"
    ):

        terrain_evidence = (
            build_terrain_evidence()
        )

        resume_payload[
            "terrain_evidence"
        ] = terrain_evidence

        print(
            "Resume evidence:",
            "Terrain summary artifact",
            terrain_evidence[
                "terrain_summary_artifact"
            ],
        )


    if (
        snapshot.values.get(
            "selected_capability"
        )
        ==
        "gis.analyze_land_cover"
    ):

        land_cover_evidence = (
            build_land_cover_evidence()
        )

        resume_payload[
            "land_cover_evidence"
        ] = land_cover_evidence

        print(
            "Resume evidence:",
            "Land-cover summary artifact",
            land_cover_evidence[
                "land_cover_summary_artifact"
            ],
        )


    if (
        snapshot.values.get(
            "selected_capability"
        )
        ==
        "gis.resolve_flood_evidence"
    ):

        flood_evidence = (
            build_flood_evidence()
        )

        resume_payload[
            "flood_evidence"
        ] = flood_evidence

        print(
            "Resume evidence:",
            "FEMA NFHL summary artifact",
            flood_evidence[
                "fema_nfhl_summary_artifact"
            ],
        )


    if (
        snapshot.values.get(
            "selected_capability"
        )
        ==
        "regulatory.build_permit_matrix"
    ):

        regulatory_evidence = (
            build_regulatory_evidence()
        )

        resume_payload[
            "regulatory_evidence"
        ] = regulatory_evidence

        print(
            "Resume evidence:",
            "Jurisdiction summary artifact",
            regulatory_evidence[
                "jurisdiction_summary_artifact"
            ],
        )


    if (
        snapshot.values.get(
            "selected_capability"
        )
        ==
        "aviation.screen_candidate"
    ):

        aviation_evidence = (
            build_aviation_evidence()
        )

        resume_payload[
            "aviation_evidence"
        ] = aviation_evidence

        print(
            "Resume evidence:",
            "Aviation summary artifact",
            aviation_evidence[
                "aviation_summary_artifact"
            ],
        )


    if (
        snapshot.values.get(
            "selected_capability"
        )
        ==
        "wind.analyze_candidate_resource"
    ):

        wind_resource_evidence = (
            build_wind_resource_evidence()
        )

        resume_payload[
            "wind_resource_evidence"
        ] = wind_resource_evidence

        print(
            "Resume evidence:",
            "HRRR MET summary artifact",
            wind_resource_evidence[
                "hrrr_met_summary_artifact"
            ],
        )


    if (
        snapshot.values.get(
            "selected_capability"
        )
        ==
        "environment.screen_cultural_resources"
    ):

        cultural_resources_evidence = (
            build_cultural_resources_evidence()
        )

        resume_payload[
            "cultural_resources_evidence"
        ] = cultural_resources_evidence

        print(
            "Resume evidence:",
            "NRHP summary artifact",
            cultural_resources_evidence[
                "nrhp_summary_artifact"
            ],
        )


    print()


    result = graph.invoke(
        Command(
            resume=resume_payload
        ),
        config=config,
    )


print(
    "=== RESUMED RESULT ==="
)

print(
    "Selected task:",
    result.get(
        "selected_task_id"
    ),
)

print(
    "Capability:",
    result.get(
        "selected_capability"
    ),
)

print(
    "Status:",
    result.get(
        "investigation_status"
    ),
)


interrupts = result.get(
    "__interrupt__",
    []
)


if interrupts:

    print()
    print(
        "=== GRAPH PAUSED AGAIN ==="
    )

    for item in interrupts:

        payload = getattr(
            item,
            "value",
            item,
        )

        print(
            json.dumps(
                payload,
                indent=2,
                default=str,
            )
        )


print()
print(
    "Completed investigations:",
    len(
        result.get(
            "investigation_history",
            []
        )
    ),
)


for item in result.get(
    "investigation_history",
    []
):

    print(
        "-",
        item.get(
            "task_id"
        ),
        "|",
        item.get(
            "capability"
        ),
    )


print()
print(
    "Evidence assessments:",
    len(
        result.get(
            "evidence_ledger",
            []
        )
    ),
)


for item in result.get(
    "evidence_ledger",
    []
):

    print(
        "-",
        item.get(
            "task_id"
        ),
        "|",
        item.get(
            "capability"
        ),
        "|",
        item.get(
            "status"
        ),
    )
