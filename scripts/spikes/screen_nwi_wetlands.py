#!/usr/bin/env python3

import json
import os
from collections import defaultdict
from pathlib import Path

import geopandas as gpd
import requests


PROJECT_AREA = Path(
    "data/scenarios/western_ok_250mw/candidate_area.geojson"
)

RESULT_DIR = os.environ.get("RESULT_DIR")

if not RESULT_DIR:
    raise SystemExit("RESULT_DIR is not set")

OUT_DIR = Path(RESULT_DIR) / "gis" / "nwi"
OUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

RAW_OUTPUT = OUT_DIR / "nwi_intersections.geojson"
SUMMARY_OUTPUT = OUT_DIR / "nwi_summary.json"


SERVICE_URL = (
    "https://fwspublicservices.wim.usgs.gov/"
    "wetlandsmapservice/rest/services/"
    "Wetlands/MapServer/0/query"
)


def normalize_property(row, suffix):
    """
    NWI REST responses may use qualified field names such as
    Wetlands.WETLAND_TYPE. This helper finds the field by suffix.
    """

    suffix = suffix.upper()

    for key, value in row.items():
        if str(key).upper().endswith(suffix):
            return value

    return None


# ------------------------------------------------------------
# Load candidate
# ------------------------------------------------------------

candidate = gpd.read_file(PROJECT_AREA)

if candidate.empty:
    raise SystemExit("Candidate polygon is empty.")

candidate = candidate.to_crs("EPSG:4326")

candidate_geom = candidate.geometry.iloc[0]

if not candidate_geom.is_valid:
    raise SystemExit("Candidate polygon is invalid.")


# ------------------------------------------------------------
# Build ArcGIS polygon
# ------------------------------------------------------------

rings = []

if candidate_geom.geom_type == "Polygon":
    rings.append(
        [
            [float(x), float(y)]
            for x, y in candidate_geom.exterior.coords
        ]
    )

elif candidate_geom.geom_type == "MultiPolygon":
    for polygon in candidate_geom.geoms:
        rings.append(
            [
                [float(x), float(y)]
                for x, y in polygon.exterior.coords
            ]
        )

else:
    raise SystemExit(
        f"Unsupported geometry: {candidate_geom.geom_type}"
    )


esri_geometry = json.dumps(
    {
        "rings": rings,
        "spatialReference": {
            "wkid": 4326
        },
    }
)


# ------------------------------------------------------------
# First get intersecting object IDs.
#
# This avoids relying on the service's 1,000-record
# maximum response size.
# ------------------------------------------------------------

id_params = {
    "where": "1=1",
    "geometry": esri_geometry,
    "geometryType": "esriGeometryPolygon",
    "inSR": "4326",
    "spatialRel": "esriSpatialRelIntersects",
    "returnIdsOnly": "true",
    "f": "json",
}

response = requests.get(
    SERVICE_URL,
    params=id_params,
    timeout=60,
)

response.raise_for_status()

id_payload = response.json()

if "error" in id_payload:
    raise SystemExit(
        json.dumps(
            id_payload["error"],
            indent=2,
        )
    )

object_ids = sorted(
    id_payload.get(
        "objectIds",
        [],
    )
)


print("=== NWI QUERY ===")
print(
    "Intersecting source features:",
    f"{len(object_ids):,}",
)


# ------------------------------------------------------------
# Fetch feature geometries in batches
# ------------------------------------------------------------

feature_collection = {
    "type": "FeatureCollection",
    "features": [],
}

BATCH_SIZE = 500

for start in range(
    0,
    len(object_ids),
    BATCH_SIZE,
):

    batch = object_ids[
        start:start + BATCH_SIZE
    ]

    params = {
        "objectIds": ",".join(
            str(x)
            for x in batch
        ),
        "outFields": "*",
        "returnGeometry": "true",
        "outSR": "4326",
        "f": "geojson",
    }

    response = requests.get(
        SERVICE_URL,
        params=params,
        timeout=60,
    )

    response.raise_for_status()

    payload = response.json()

    if "error" in payload:
        raise SystemExit(
            json.dumps(
                payload["error"],
                indent=2,
            )
        )

    feature_collection[
        "features"
    ].extend(
        payload.get(
            "features",
            [],
        )
    )


RAW_OUTPUT.write_text(
    json.dumps(
        feature_collection,
        indent=2,
    ),
    encoding="utf-8",
)


# ------------------------------------------------------------
# No wetlands case
# ------------------------------------------------------------

if not feature_collection["features"]:

    summary = {
        "source": {
            "authority": (
                "U.S. Fish and Wildlife Service"
            ),
            "dataset": (
                "National Wetlands Inventory"
            ),
            "service": SERVICE_URL,
        },

        "project_id": (
            candidate.iloc[0].get(
                "project_id"
            )
        ),

        "source_feature_count": 0,

        "candidate_area_acres": None,

        "nwi_overlap_acres": 0.0,

        "nwi_overlap_percent": 0.0,

        "wetland_types": {},

        "interpretation": (
            "No NWI-mapped wetland polygons "
            "intersect the candidate polygon."
        ),

        "limitation": (
            "NWI is a screening dataset and "
            "does not establish jurisdictional "
            "wetland boundaries."
        ),
    }

    SUMMARY_OUTPUT.write_text(
        json.dumps(
            summary,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("No NWI polygons intersect candidate area.")
    print("Output:", SUMMARY_OUTPUT)

    raise SystemExit(0)


# ------------------------------------------------------------
# Convert returned features to GeoDataFrame
# ------------------------------------------------------------

wetlands = gpd.GeoDataFrame.from_features(
    feature_collection["features"],
    crs="EPSG:4326",
)


# ------------------------------------------------------------
# Use same local UTM logic as candidate profiling
# ------------------------------------------------------------

analysis_crs = (
    candidate.estimate_utm_crs()
)

if analysis_crs is None:
    raise SystemExit(
        "Could not estimate local projected CRS."
    )


candidate_utm = candidate.to_crs(
    analysis_crs
)

wetlands_utm = wetlands.to_crs(
    analysis_crs
)

candidate_geom_utm = (
    candidate_utm.geometry.iloc[0]
)


# ------------------------------------------------------------
# Clip returned wetland polygons to candidate boundary
# ------------------------------------------------------------

wetlands_utm["clipped_geometry"] = (
    wetlands_utm.geometry.intersection(
        candidate_geom_utm
    )
)

wetlands_utm = wetlands_utm[
    ~wetlands_utm["clipped_geometry"].is_empty
].copy()

wetlands_utm = wetlands_utm.set_geometry(
    "clipped_geometry"
)

# Remove the original un-clipped geometry so downstream
# calculations cannot accidentally use it.
wetlands_utm = wetlands_utm.drop(
    columns=["geometry"]
)

wetlands_utm = wetlands_utm.rename_geometry(
    "geometry"
)


# ------------------------------------------------------------
# Area calculations
# ------------------------------------------------------------

SQM_PER_ACRE = 4046.8564224

candidate_acres = (
    candidate_geom_utm.area
    / SQM_PER_ACRE
)


# Union prevents double-counting overlapping source polygons.
union_geometry = (
    wetlands_utm.geometry.union_all()
)

overlap_acres = (
    union_geometry.area
    / SQM_PER_ACRE
)

overlap_percent = (
    overlap_acres
    / candidate_acres
    * 100
)


# ------------------------------------------------------------
# Area by NWI wetland type
# ------------------------------------------------------------

type_geometries = defaultdict(
    list
)

for _, row in wetlands_utm.iterrows():

    wetland_type = normalize_property(
        row,
        "WETLAND_TYPE",
    )

    if not wetland_type:
        wetland_type = "UNKNOWN"

    type_geometries[
        str(wetland_type)
    ].append(
        row.geometry
    )


type_summary = {}

for wetland_type, geometries in (
    type_geometries.items()
):

    series = gpd.GeoSeries(
        geometries,
        crs=analysis_crs,
    )

    type_union = (
        series.union_all()
    )

    acres = (
        type_union.area
        / SQM_PER_ACRE
    )

    type_summary[
        wetland_type
    ] = {
        "acres": acres,
        "percent_of_candidate": (
            acres
            / candidate_acres
            * 100
        ),
    }


# ------------------------------------------------------------
# Sanity check
#
# No individual wetland class can have a union area larger
# than the union of all intersecting wetland geometries.
# ------------------------------------------------------------

for wetland_type, values in type_summary.items():

    if values["acres"] > overlap_acres + 0.01:

        raise RuntimeError(
            f"Invalid wetland-area result: "
            f"{wetland_type}={values['acres']:.2f} acres "
            f"exceeds total NWI overlap="
            f"{overlap_acres:.2f} acres"
        )


# ------------------------------------------------------------
# NWI codes
# ------------------------------------------------------------

attribute_counts = defaultdict(
    int
)

for _, row in wetlands_utm.iterrows():

    attribute = normalize_property(
        row,
        "ATTRIBUTE",
    )

    if attribute:
        attribute_counts[
            str(attribute)
        ] += 1


# ------------------------------------------------------------
# Summary
# ------------------------------------------------------------

summary = {
    "source": {
        "authority": (
            "U.S. Fish and Wildlife Service"
        ),

        "dataset": (
            "National Wetlands Inventory"
        ),

        "service": SERVICE_URL,

        "source_feature_count": (
            len(object_ids)
        ),

        "returned_feature_count": (
            len(feature_collection["features"])
        ),
    },

    "project_id": (
        candidate.iloc[0].get(
            "project_id"
        )
    ),

    "analysis_crs": (
        str(analysis_crs)
    ),

    "candidate_area_acres": (
        candidate_acres
    ),

    "nwi_overlap_acres": (
        overlap_acres
    ),

    "nwi_overlap_percent": (
        overlap_percent
    ),

    "wetland_types": (
        type_summary
    ),

    "nwi_attribute_counts": (
        dict(
            sorted(
                attribute_counts.items()
            )
        )
    ),

    "evidence_classification": (
        "SOURCE_FACT + DERIVED_FACT"
    ),

    "interpretation": (
        "Calculated overlap with mapped "
        "National Wetlands Inventory polygons."
    ),

    "limitations": [
        (
            "NWI is suitable for screening "
            "but does not establish federal, "
            "state, tribal, or local regulatory "
            "wetland jurisdiction."
        ),
        (
            "Mapped wetland boundaries may differ "
            "from actual site conditions."
        ),
        (
            "No wetland setbacks or buffers are "
            "applied in this calculation."
        ),
    ],
}


SUMMARY_OUTPUT.write_text(
    json.dumps(
        summary,
        indent=2,
    ),
    encoding="utf-8",
)


# ------------------------------------------------------------
# Report
# ------------------------------------------------------------

print()
print(
    "=== CANDIDATE AREA ==="
)

print(
    f"{candidate_acres:,.1f} acres"
)


print()
print(
    "=== NWI-MAPPED OVERLAP ==="
)

print(
    f"{overlap_acres:,.2f} acres"
)

print(
    f"{overlap_percent:.3f}% "
    "of candidate area"
)


print()
print(
    "=== BY WETLAND TYPE ==="
)

for wetland_type, values in sorted(
    type_summary.items(),
    key=lambda item: (
        item[1]["acres"]
    ),
    reverse=True,
):

    print(
        f"{wetland_type:<40} "
        f"{values['acres']:>10,.2f} acres "
        f"({values['percent_of_candidate']:>6.3f}%)"
    )


print()
print(
    "=== IMPORTANT ==="
)

print(
    "This is NWI screening overlap, "
    "not a jurisdictional wetland delineation."
)

print()
print(
    "Raw:"
)
print(
    RAW_OUTPUT
)

print(
    "Summary:"
)
print(
    SUMMARY_OUTPUT
)
