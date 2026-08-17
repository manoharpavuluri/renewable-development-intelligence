#!/usr/bin/env python3

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import geopandas as gpd
import requests


RESULT_DIR = Path(
    os.environ["RESULT_DIR"]
)

CANDIDATE_PATH = Path(
    "data/scenarios/western_ok_250mw/"
    "candidate_area.geojson"
)

SERVICE_URL = (
    "https://services1.arcgis.com/"
    "CD5mKowwN6nIaqd8/"
    "arcgis/rest/services/"
    "project_renewable_us_transmission_lines_2024/"
    "FeatureServer/19/query"
)

OUTPUT_DIR = (
    RESULT_DIR
    / "transmission"
    / "gen_tie_context"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# Candidate geometry
# ============================================================

candidate = gpd.read_file(
    CANDIDATE_PATH
)

candidate = candidate.to_crs(
    4326
)

candidate_geom = (
    candidate.geometry.union_all()
)

minx, miny, maxx, maxy = (
    candidate_geom.bounds
)


# Search a broad regional envelope.
#
# This does NOT imply a viable gen-tie radius.
# It is only used to discover transmission context.
SEARCH_EXPANSION_DEGREES = 1.5

query_bbox = {
    "xmin": (
        minx
        - SEARCH_EXPANSION_DEGREES
    ),
    "ymin": (
        miny
        - SEARCH_EXPANSION_DEGREES
    ),
    "xmax": (
        maxx
        + SEARCH_EXPANSION_DEGREES
    ),
    "ymax": (
        maxy
        + SEARCH_EXPANSION_DEGREES
    ),
}


params = {
    "where": (
        "VOLTAGE >= 230"
    ),

    "geometry": (
        f"{query_bbox['xmin']},"
        f"{query_bbox['ymin']},"
        f"{query_bbox['xmax']},"
        f"{query_bbox['ymax']}"
    ),

    "geometryType": (
        "esriGeometryEnvelope"
    ),

    "inSR": 4326,

    "spatialRel": (
        "esriSpatialRelIntersects"
    ),

    "outFields": (
        "ID,TYPE,STATUS,OWNER,"
        "VOLTAGE,VOLT_CLASS,"
        "SUB_1,SUB_2,"
        "SOURCE,SOURCEDATE,"
        "VAL_METHOD,VAL_DATE,"
        "INFERRED"
    ),

    "returnGeometry": (
        "true"
    ),

    "outSR": 4326,

    "f": (
        "geojson"
    ),
}


response = requests.get(
    SERVICE_URL,
    params=params,
    timeout=120,
)

response.raise_for_status()

payload = response.json()


raw_path = (
    OUTPUT_DIR
    / "hifld_transmission_lines.geojson"
)

raw_path.write_text(
    json.dumps(
        payload,
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)


# ============================================================
# Convert returned features to GeoDataFrame
# ============================================================

features = payload.get(
    "features",
    []
)

if not features:

    raise RuntimeError(
        "No >=230-kV transmission lines "
        "were returned for the search area."
    )


lines = (
    gpd.GeoDataFrame.from_features(
        features,
        crs=4326,
    )
)


# ============================================================
# Project to UTM Zone 14N for distance calculations.
#
# Western Oklahoma candidate is near 99 W / 36 N.
# ============================================================

candidate_m = candidate.to_crs(
    32614
)

lines_m = lines.to_crs(
    32614
)

candidate_union_m = (
    candidate_m.geometry.union_all()
)


METERS_PER_MILE = 1609.344


lines_m[
    "distance_to_candidate_miles"
] = (
    lines_m.geometry.distance(
        candidate_union_m
    )
    / METERS_PER_MILE
)


# Bring the calculated values back onto
# the WGS84 frame for output.
lines[
    "distance_to_candidate_miles"
] = (
    lines_m[
        "distance_to_candidate_miles"
    ].values
)


lines[
    "intersects_candidate"
] = lines.geometry.intersects(
    candidate_geom
)


# ============================================================
# Search endpoint-name attributes for Tatonga.
#
# This identifies transmission LINE records carrying
# Tatonga text. It is NOT treated as authoritative
# Tatonga substation-point geometry.
# ============================================================

def contains_tatonga(
    value: Any,
) -> bool:

    if value is None:
        return False

    return (
        "TATONGA"
        in str(value).upper()
    )


tatonga_mask = (
    lines[
        "SUB_1"
    ].map(
        contains_tatonga
    )
    |
    lines[
        "SUB_2"
    ].map(
        contains_tatonga
    )
)


tatonga_lines = lines[
    tatonga_mask
].copy()


# ============================================================
# Summaries
# ============================================================

nearest = lines.sort_values(
    "distance_to_candidate_miles"
).head(
    20
)


nearest_345 = lines[
    lines[
        "VOLTAGE"
    ]
    == 345
].sort_values(
    "distance_to_candidate_miles"
).head(
    20
)


def record(
    row,
) -> dict[str, Any]:

    return {
        "id": row.get(
            "ID"
        ),

        "owner": row.get(
            "OWNER"
        ),

        "voltage_kv": row.get(
            "VOLTAGE"
        ),

        "voltage_class": row.get(
            "VOLT_CLASS"
        ),

        "status": row.get(
            "STATUS"
        ),

        "substation_name_1": row.get(
            "SUB_1"
        ),

        "substation_name_2": row.get(
            "SUB_2"
        ),

        "distance_to_candidate_miles": round(
            float(
                row[
                    "distance_to_candidate_miles"
                ]
            ),
            3,
        ),

        "intersects_candidate": bool(
            row[
                "intersects_candidate"
            ]
        ),

        "source": row.get(
            "SOURCE"
        ),

        "source_date": row.get(
            "SOURCEDATE"
        ),

        "validation_method": row.get(
            "VAL_METHOD"
        ),

        "voltage_inferred": row.get(
            "INFERRED"
        ),
    }


result = {
    "source": {
        "dataset": (
            "DOE/ORNL HIFLD-derived "
            "2024 transmission lines"
        ),

        "service": (
            SERVICE_URL
        ),
    },

    "candidate": {
        "project_id": (
            "RDI-WOK-250-001"
        ),

        "candidate_geometry": (
            str(
                CANDIDATE_PATH
            )
        ),
    },

    "query": {
        "minimum_voltage_kv": (
            230
        ),

        "search_envelope": (
            query_bbox
        ),
    },

    "summary": {
        "transmission_line_count": (
            len(
                lines
            )
        ),

        "line_345kv_count": int(
            (
                lines[
                    "VOLTAGE"
                ]
                == 345
            ).sum()
        ),

        "candidate_intersection_count": int(
            lines[
                "intersects_candidate"
            ].sum()
        ),

        "tatonga_named_line_count": (
            len(
                tatonga_lines
            )
        ),
    },

    "nearest_high_voltage_lines": [
        record(row)
        for _, row
        in nearest.iterrows()
    ],

    "nearest_345kv_lines": [
        record(row)
        for _, row
        in nearest_345.iterrows()
    ],

    "tatonga_named_lines": [
        record(row)
        for _, row
        in tatonga_lines.sort_values(
            "distance_to_candidate_miles"
        ).iterrows()
    ],

    "interpretation_limits": [
        (
            "Distances are from the candidate "
            "polygon to public transmission-line "
            "geometry, not to an authoritative "
            "SPP bus coordinate."
        ),

        (
            "SUB_1 and SUB_2 are used only as "
            "transmission-line endpoint-name context."
        ),

        (
            "A Tatonga-named line does not establish "
            "the exact location of SPP bus "
            "515407:TATONGA7."
        ),

        (
            "This screen does not establish a "
            "constructible gen-tie route."
        ),

        (
            "This screen does not establish land "
            "rights, routing feasibility, cost, "
            "or generator-interconnection feasibility."
        ),
    ],
}


output_path = (
    OUTPUT_DIR
    / "gen_tie_context_screen.json"
)

output_path.write_text(
    json.dumps(
        result,
        indent=2,
        default=str,
    )
    + "\n",
    encoding="utf-8",
)


print(
    "=== PUBLIC GEN-TIE CONTEXT SPIKE ==="
)

print(
    "High-voltage lines:",
    result[
        "summary"
    ][
        "transmission_line_count"
    ],
)

print(
    "345-kV lines:",
    result[
        "summary"
    ][
        "line_345kv_count"
    ],
)

print(
    "Lines intersecting candidate:",
    result[
        "summary"
    ][
        "candidate_intersection_count"
    ],
)

print(
    "Tatonga-named lines:",
    result[
        "summary"
    ][
        "tatonga_named_line_count"
    ],
)


print()
print(
    "=== NEAREST 345-kV LINES ==="
)

for item in (
    result[
        "nearest_345kv_lines"
    ][
        :10
    ]
):

    print(
        f"{item['distance_to_candidate_miles']:8.3f} mi | "
        f"{item['owner']} | "
        f"{item['substation_name_1']} -> "
        f"{item['substation_name_2']}"
    )


print()
print(
    "=== TATONGA-NAMED LINES ==="
)

if not result[
    "tatonga_named_lines"
]:

    print(
        "NONE FOUND IN PUBLIC LINE DATA"
    )

else:

    for item in result[
        "tatonga_named_lines"
    ]:

        print(
            f"{item['distance_to_candidate_miles']:8.3f} mi | "
            f"{item['voltage_kv']} kV | "
            f"{item['substation_name_1']} -> "
            f"{item['substation_name_2']}"
        )


print()
print(
    "Output:",
    output_path
)
