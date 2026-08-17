from __future__ import annotations

import json
import os
from pathlib import Path

from renewable_intelligence.interconnection.spp_additional_poi import (
    evaluate_additional_poi,
)


RESULT_DIR = Path(
    os.environ["RESULT_DIR"]
)


evidence = {
    "additional_pois": [
        "MATHWSN7",
    ],

    "model_cases": {
        "TC00": {
            "model": (
                "DIS231-TC00ALL-24SP3"
            ),

            "pois": {
                "TATONGA7": str(
                    RESULT_DIR
                    / "spp_hct"
                    / "tatonga_345_250mw"
                    / "grid-data.csv"
                ),

                "WWRDEHV7": str(
                    RESULT_DIR
                    / "spp_hct"
                    / "woodward_ehv_345_250mw"
                    / "grid-data.csv"
                ),

                "MATHWSN7": str(
                    RESULT_DIR
                    / "spp_hct"
                    / "additional_poi"
                    / "515497_MATHWSN7"
                    / "TC00"
                    / "grid-data.csv"
                ),
            },
        },

        "TC03": {
            "model": (
                "DIS231-TC03ALL-24SP3"
            ),

            "pois": {
                "TATONGA7": str(
                    RESULT_DIR
                    / "spp_hct"
                    / "model_cases"
                    / "DIS231-TC03ALL-24SP3"
                    / "tatonga_345_250mw"
                    / "grid-data.csv"
                ),

                "WWRDEHV7": str(
                    RESULT_DIR
                    / "spp_hct"
                    / "model_cases"
                    / "DIS231-TC03ALL-24SP3"
                    / "woodward_ehv_345_250mw"
                    / "grid-data.csv"
                ),

                "MATHWSN7": str(
                    RESULT_DIR
                    / "spp_hct"
                    / "additional_poi"
                    / "515497_MATHWSN7"
                    / "TC03"
                    / "grid-data.csv"
                ),
            },
        },
    },
}


# ------------------------------------------------------------
# Verify every governed artifact exists before executing.
# ------------------------------------------------------------

for case_id, case in evidence[
    "model_cases"
].items():

    for poi_name, artifact in (
        case["pois"].items()
    ):

        path = Path(
            artifact
        )

        if not path.exists():

            raise FileNotFoundError(
                f"{case_id} / {poi_name}: "
                f"{path}"
            )


# ------------------------------------------------------------
# Verify Mathewson provenance sidecars.
# ------------------------------------------------------------

expected_mathewson = {
    "TC00": {
        "model": (
            "DIS231-TC00ALL-24SP3"
        ),

        "sha256": (
            "05e22e01834f22cbce825723d5e7d06d83e5e8d61b3c4a020d6affa8280f538b"
        ),
    },

    "TC03": {
        "model": (
            "DIS231-TC03ALL-24SP3"
        ),

        "sha256": (
            "b1f5f8a530af4a925c0c0b5006eca5a7d21657f69275ae8c5b818d9476d290da"
        ),
    },
}


for case_id, expected in (
    expected_mathewson.items()
):

    query_path = (
        RESULT_DIR
        / "spp_hct"
        / "additional_poi"
        / "515497_MATHWSN7"
        / case_id
        / "query.json"
    )

    query = json.loads(
        query_path.read_text(
            encoding="utf-8"
        )
    )

    assert (
        query["model"]
        == expected["model"]
    )

    assert query["area"] == "OKGE"
    assert query["kv"] == 345
    assert query["bus_id"] == 515497

    assert (
        query["bus_name"]
        == "MATHWSN7"
    )

    assert (
        query["injection_mw"]
        == 250
    )

    assert (
        query["artifact_sha256"]
        == expected["sha256"]
    )


state = {
    "spp_additional_poi_evidence": (
        evidence
    ),
}


task = {
    "task_id": (
        "INT-FU-003"
    ),

    "action_id": (
        "INT-FU-003"
    ),

    "domain": (
        "interconnection"
    ),
}


result = evaluate_additional_poi(
    state=state,
    task=task,
)


print(
    "=== PRODUCTION ADDITIONAL-POI CAPABILITY ==="
)

print(
    json.dumps(
        result,
        indent=2,
    )
)


# ------------------------------------------------------------
# Contract assertions
# ------------------------------------------------------------

assert result[
    "executed"
] is True

assert (
    result["capability"]
    == "spp.evaluate_additional_poi"
)

assert (
    result["finding"][
        "tested_model_count"
    ]
    == 2
)

assert (
    result["finding"][
        "tested_poi_count"
    ]
    == 3
)

assert (
    result["finding"][
        "additional_pois_tested"
    ]
    == [
        "MATHWSN7",
    ]
)

assert (
    result["finding"][
        "preferred_poi_by_model_case"
    ][
        "TC00"
    ]
    == "TATONGA7"
)

assert (
    result["finding"][
        "preferred_poi_by_model_case"
    ][
        "TC03"
    ]
    == "TATONGA7"
)

assert (
    result["finding"][
        "screening_preferred_poi"
    ]
    == "TATONGA7"
)

assert (
    result["finding"][
        "additional_poi_displaced_existing_preference"
    ]
    is False
)


print()
print(
    "Production additional-POI "
    "capability validation: PASS"
)
