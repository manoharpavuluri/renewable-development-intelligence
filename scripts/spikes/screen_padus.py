#!/usr/bin/env python3

import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
import requests


CANDIDATE_PATH = Path(
    "data/scenarios/western_ok_250mw/candidate_area.geojson"
)

RESULT_DIR = os.environ.get("RESULT_DIR")

if not RESULT_DIR:
    raise SystemExit("RESULT_DIR is not set")

OUT_DIR = Path(RESULT_DIR) / "gis" / "padus"
OUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

RAW_PATH = (
    OUT_DIR
    / "padus_intersections.geojson"
)

METADATA_PATH = (
    OUT_DIR
    / "padus_layer_metadata.json"
)

SUMMARY_PATH = (
    OUT_DIR
    / "padus_summary.json"
)


FEATURESERVER = (
    "https://services.arcgis.com/"
    "v01gqwM5QqNysAAi/arcgis/rest/services/"
    "PADUS_Protection_Status_by_GAP_Status_Code/"
    "FeatureServer"
)

LAYER_ID = 0

LAYER_URL = (
    f"{FEATURESERVER}/{LAYER_ID}"
)

QUERY_URL = (
    f"{LAYER_URL}/query"
)

SQM_PER_ACRE = 4046.8564224


def clean(value):
    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    if value.upper() in {
        "NONE",
        "NULL",
    }:
        return None

    return value


def union_area_acres(
    geometries,
    crs,
):
    geometries = [
        geometry
        for geometry in geometries
        if (
            geometry is not None
            and not geometry.is_empty
        )
    ]

    if not geometries:
        return 0.0

    series = gpd.GeoSeries(
        geometries,
        crs=crs,
    )

    return (
        series.union_all().area
        / SQM_PER_ACRE
    )


# ------------------------------------------------------------
# Candidate
# ------------------------------------------------------------

candidate = gpd.read_file(
    CANDIDATE_PATH
).to_crs(
    "EPSG:4326"
)

if candidate.empty:
    raise SystemExit(
        "Candidate polygon is empty."
    )

candidate_geom = (
    candidate.geometry.iloc[0]
)

if not candidate_geom.is_valid:
    raise SystemExit(
        "Candidate polygon is invalid."
    )

analysis_crs = (
    candidate.estimate_utm_crs()
)

if analysis_crs is None:
    raise SystemExit(
        "Could not determine local "
        "projected CRS."
    )

candidate_utm = (
    candidate.to_crs(
        analysis_crs
    )
)

candidate_geom_utm = (
    candidate_utm.geometry.iloc[0]
)

candidate_acres = (
    candidate_geom_utm.area
    / SQM_PER_ACRE
)


# ------------------------------------------------------------
# Session
# ------------------------------------------------------------

session = requests.Session()

session.headers.update(
    {
        "User-Agent": (
            "RenewableDevelopmentIntelligence/"
            "source-access-spike"
        )
    }
)


# ------------------------------------------------------------
# Read live layer metadata
# ------------------------------------------------------------

response = session.get(
    LAYER_URL,
    params={
        "f": "pjson",
    },
    timeout=60,
)

response.raise_for_status()

metadata = response.json()

if "error" in metadata:
    raise SystemExit(
        json.dumps(
            metadata["error"],
            indent=2,
        )
    )

METADATA_PATH.write_text(
    json.dumps(
        metadata,
        indent=2,
    ),
    encoding="utf-8",
)


field_names = {
    field.get("name")
    for field in metadata.get(
        "fields",
        []
    )
}


required_fields = {
    "OBJECTID",
    "Category",
    "Unit_Nm",
    "Pub_Access",
    "GAP_Sts",
    "MngTp_Desc",
    "MngNm_Desc",
    "DesTp_Desc",
    "ST_Name",
}

missing_fields = (
    required_fields
    - field_names
)

if missing_fields:
    raise RuntimeError(
        "PAD-US schema changed. "
        "Missing expected fields: "
        + ", ".join(
            sorted(
                missing_fields
            )
        )
    )


print(
    "=== PAD-US LAYER ==="
)

print(
    "Layer:",
    metadata.get("name"),
)

print(
    "Geometry:",
    metadata.get(
        "geometryType"
    ),
)

print(
    "Max record count:",
    metadata.get(
        "maxRecordCount"
    ),
)


# ------------------------------------------------------------
# Build ArcGIS geometry
# ------------------------------------------------------------

rings = []

if candidate_geom.geom_type == "Polygon":

    rings.append(
        [
            [float(x), float(y)]
            for x, y
            in candidate_geom.exterior.coords
        ]
    )

elif candidate_geom.geom_type == "MultiPolygon":

    for polygon in candidate_geom.geoms:

        rings.append(
            [
                [float(x), float(y)]
                for x, y
                in polygon.exterior.coords
            ]
        )

else:
    raise SystemExit(
        "Candidate geometry must "
        "be polygonal."
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
# Get intersecting object IDs
# ------------------------------------------------------------

response = session.get(
    QUERY_URL,
    params={
        "where": "1=1",

        "geometry": (
            esri_geometry
        ),

        "geometryType": (
            "esriGeometryPolygon"
        ),

        "inSR": "4326",

        "spatialRel": (
            "esriSpatialRelIntersects"
        ),

        "returnIdsOnly": "true",

        "f": "json",
    },
    timeout=120,
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
        "objectIds"
    )
    or []
)


print()
print(
    "Intersecting PAD-US source features:",
    f"{len(object_ids):,}",
)


# ------------------------------------------------------------
# Retrieve source features
# ------------------------------------------------------------

feature_collection = {
    "type": "FeatureCollection",
    "features": [],
}


max_records = int(
    metadata.get(
        "maxRecordCount",
        2000,
    )
)

batch_size = min(
    500,
    max_records,
)


for start in range(
    0,
    len(object_ids),
    batch_size,
):

    batch = object_ids[
        start:start + batch_size
    ]

    response = session.get(
        QUERY_URL,
        params={
            "objectIds": ",".join(
                str(value)
                for value in batch
            ),

            "outFields": "*",

            "returnGeometry": "true",

            "outSR": "4326",

            "f": "geojson",
        },
        timeout=120,
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


RAW_PATH.write_text(
    json.dumps(
        feature_collection,
        indent=2,
    ),
    encoding="utf-8",
)


# ------------------------------------------------------------
# Empty result
# ------------------------------------------------------------

if not feature_collection[
    "features"
]:

    summary = {
        "source": {
            "authority": (
                "U.S. Geological Survey"
            ),

            "dataset": (
                "Protected Areas Database "
                "of the United States"
            ),

            "layer": (
                metadata.get("name")
            ),

            "layer_url": (
                LAYER_URL
            ),

            "retrieved_utc": (
                datetime.now(
                    timezone.utc
                ).isoformat()
            ),
        },

        "project_id": (
            candidate.iloc[0].get(
                "project_id"
            )
        ),

        "candidate_area_acres": (
            candidate_acres
        ),

        "padus_overlap_acres": 0.0,

        "padus_overlap_percent": 0.0,

        "gap_status": {},

        "units": [],

        "evidence_classification": (
            "SOURCE_FACT + DERIVED_FACT"
        ),

        "interpretation": (
            "No PAD-US polygons intersect "
            "the candidate area."
        ),

        "limitations": [
            (
                "Absence of a PAD-US polygon "
                "does not establish absence "
                "of all land-use restrictions."
            )
        ],
    }

    SUMMARY_PATH.write_text(
        json.dumps(
            summary,
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print(
        "No PAD-US polygons intersect "
        "candidate area."
    )

    print(
        "Summary:",
        SUMMARY_PATH,
    )

    raise SystemExit(0)


# ------------------------------------------------------------
# Convert and clip
# ------------------------------------------------------------

padus = (
    gpd.GeoDataFrame.from_features(
        feature_collection[
            "features"
        ],
        crs="EPSG:4326",
    )
    .to_crs(
        analysis_crs
    )
)


padus["clipped_geometry"] = (
    padus.geometry.intersection(
        candidate_geom_utm
    )
)


padus = padus[
    ~padus[
        "clipped_geometry"
    ].is_empty
].copy()


padus = padus.set_geometry(
    "clipped_geometry"
)


# Avoid the NWI bug:
# remove original un-clipped geometry.
padus = padus.drop(
    columns=[
        "geometry"
    ]
)

padus = (
    padus.rename_geometry(
        "geometry"
    )
)


# ------------------------------------------------------------
# Total unique overlap
# ------------------------------------------------------------

total_overlap_acres = (
    union_area_acres(
        padus.geometry.tolist(),
        analysis_crs,
    )
)


total_overlap_pct = (
    total_overlap_acres
    / candidate_acres
    * 100
)


if (
    total_overlap_acres
    > candidate_acres + 0.01
):
    raise RuntimeError(
        "PAD-US overlap exceeds "
        "candidate area."
    )


# ------------------------------------------------------------
# GAP-status summary
# ------------------------------------------------------------

gap_geometries = defaultdict(
    list
)

for _, row in padus.iterrows():

    gap_status = (
        clean(
            row.get(
                "GAP_Sts"
            )
        )
        or "UNKNOWN"
    )

    gap_geometries[
        gap_status
    ].append(
        row.geometry
    )


gap_summary = {}

for gap_status, geometries in (
    gap_geometries.items()
):

    acres = union_area_acres(
        geometries,
        analysis_crs,
    )

    if acres > (
        total_overlap_acres
        + 0.01
    ):
        raise RuntimeError(
            f"GAP status {gap_status} "
            f"area exceeds total PAD-US "
            f"overlap."
        )

    gap_summary[
        gap_status
    ] = {
        "acres": acres,

        "percent_of_candidate": (
            acres
            / candidate_acres
            * 100
        ),

        "percent_of_padus_overlap": (
            acres
            / total_overlap_acres
            * 100
            if total_overlap_acres
            else 0.0
        ),
    }


# ------------------------------------------------------------
# Semantic protection views
#
# GAP 1/2:
#   Primarily biodiversity-protection signal.
#
# GAP 3:
#   Multiple-use conservation lands; extractive or other
#   uses may occur depending on the managing authority.
#
# GAP 4:
#   No known biodiversity-protection mandate.
#   Still important for ownership, jurisdiction, management,
#   tribal, state-land, and permitting context.
#
# These are screening classifications, not legal conclusions.
# ------------------------------------------------------------

semantic_geometries = {
    "BIODIVERSITY_PROTECTED_GAP_1_2": [],
    "MULTIPLE_USE_GAP_3": [],
    "NO_KNOWN_BIODIVERSITY_PROTECTION_MANDATE_GAP_4": [],
    "UNKNOWN_GAP_STATUS": [],
}


for _, row in padus.iterrows():

    gap_value = clean(
        row.get("GAP_Sts")
    )

    gap_value = (
        str(gap_value).strip()
        if gap_value is not None
        else None
    )

    if gap_value in {"1", "2"}:

        semantic_geometries[
            "BIODIVERSITY_PROTECTED_GAP_1_2"
        ].append(
            row.geometry
        )

    elif gap_value == "3":

        semantic_geometries[
            "MULTIPLE_USE_GAP_3"
        ].append(
            row.geometry
        )

    elif gap_value == "4":

        semantic_geometries[
            "NO_KNOWN_BIODIVERSITY_PROTECTION_MANDATE_GAP_4"
        ].append(
            row.geometry
        )

    else:

        semantic_geometries[
            "UNKNOWN_GAP_STATUS"
        ].append(
            row.geometry
        )


protection_views = {}

for classification, geometries in (
    semantic_geometries.items()
):

    acres = union_area_acres(
        geometries,
        analysis_crs,
    )

    protection_views[
        classification
    ] = {
        "acres": acres,
        "percent_of_candidate": (
            acres
            / candidate_acres
            * 100
        ),
    }


# ------------------------------------------------------------
# Detect cross-GAP overlap
#
# Sum of class unions can exceed total unique PAD-US
# union if categories overlap spatially.
# ------------------------------------------------------------

sum_gap_acres = sum(
    item["acres"]
    for item in gap_summary.values()
)

cross_gap_overlap_acres = max(
    0.0,
    sum_gap_acres
    - total_overlap_acres,
)


# ------------------------------------------------------------
# Unit-level details
# ------------------------------------------------------------

unit_groups = defaultdict(
    list
)


for _, row in padus.iterrows():

    key = (
        clean(
            row.get("Unit_Nm")
        )
        or "UNKNOWN",
        clean(
            row.get("GAP_Sts")
        )
        or "UNKNOWN",
        clean(
            row.get("MngNm_Desc")
        )
        or "UNKNOWN",
        clean(
            row.get("MngTp_Desc")
        )
        or "UNKNOWN",
        clean(
            row.get("DesTp_Desc")
        )
        or "UNKNOWN",
        clean(
            row.get("Pub_Access")
        )
        or "UNKNOWN",
        clean(
            row.get("Category")
        )
        or "UNKNOWN",
    )

    unit_groups[
        key
    ].append(
        row.geometry
    )


units = []

for (
    unit_name,
    gap_status,
    manager_name,
    manager_type,
    designation,
    public_access,
    category,
), geometries in unit_groups.items():

    acres = union_area_acres(
        geometries,
        analysis_crs,
    )

    units.append(
        {
            "unit_name": (
                unit_name
            ),

            "gap_status": (
                gap_status
            ),

            "manager_name": (
                manager_name
            ),

            "manager_type": (
                manager_type
            ),

            "designation": (
                designation
            ),

            "public_access": (
                public_access
            ),

            "category": (
                category
            ),

            "candidate_overlap_acres": (
                acres
            ),

            "percent_of_candidate": (
                acres
                / candidate_acres
                * 100
            ),
        }
    )


units.sort(
    key=lambda item: (
        item[
            "candidate_overlap_acres"
        ]
    ),
    reverse=True,
)


# ------------------------------------------------------------
# Manager summary
# ------------------------------------------------------------

manager_geometries = defaultdict(
    list
)

for _, row in padus.iterrows():

    manager = (
        clean(
            row.get(
                "MngNm_Desc"
            )
        )
        or "UNKNOWN"
    )

    manager_geometries[
        manager
    ].append(
        row.geometry
    )


manager_summary = {}

for manager, geometries in (
    manager_geometries.items()
):

    acres = union_area_acres(
        geometries,
        analysis_crs,
    )

    manager_summary[
        manager
    ] = {
        "acres": acres,

        "percent_of_candidate": (
            acres
            / candidate_acres
            * 100
        ),
    }


# ------------------------------------------------------------
# Summary
# ------------------------------------------------------------

summary = {
    "source": {
        "authority": (
            "U.S. Geological Survey"
        ),

        "dataset": (
            "Protected Areas Database "
            "of the United States"
        ),

        "layer": (
            metadata.get("name")
        ),

        "layer_url": (
            LAYER_URL
        ),

        "retrieved_utc": (
            datetime.now(
                timezone.utc
            ).isoformat()
        ),

        "source_feature_count": (
            len(object_ids)
        ),

        "returned_feature_count": (
            len(
                feature_collection[
                    "features"
                ]
            )
        ),
    },

    "project_id": (
        candidate.iloc[0].get(
            "project_id"
        )
    ),

    "analysis_crs": (
        str(
            analysis_crs
        )
    ),

    "candidate_area_acres": (
        candidate_acres
    ),

    "padus_unique_overlap": {
        "acres": (
            total_overlap_acres
        ),

        "percent_of_candidate": (
            total_overlap_pct
        ),
    },

    "gap_status": dict(
        sorted(
            gap_summary.items(),
            key=lambda item: (
                item[1]["acres"]
            ),
            reverse=True,
        )
    ),

    "cross_gap_overlap_acres": (
        cross_gap_overlap_acres
    ),

    "protection_views": (
        protection_views
    ),

    "managers": dict(
        sorted(
            manager_summary.items(),
            key=lambda item: (
                item[1]["acres"]
            ),
            reverse=True,
        )
    ),

    "units": units,

    "evidence_classification": (
        "SOURCE_FACT + DERIVED_FACT"
    ),

    "interpretation": (
        "Calculated intersection with "
        "PAD-US mapped protected areas."
    ),

    "limitations": [
        (
            "PAD-US mapped status does not "
            "by itself establish whether "
            "wind development is legally "
            "prohibited."
        ),

        (
            "GAP status is retained as "
            "source evidence and is not "
            "converted into a development "
            "exclusion in this spike."
        ),

        (
            "Individual protected-area "
            "records or categories may "
            "overlap spatially."
        ),

        (
            "Land ownership, leases, local "
            "zoning, easements, and other "
            "development restrictions are "
            "outside this calculation."
        ),
    ],
}


SUMMARY_PATH.write_text(
    json.dumps(
        summary,
        indent=2,
    ),
    encoding="utf-8",
)


# ------------------------------------------------------------
# Terminal report
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
    "=== PAD-US UNIQUE OVERLAP ==="
)

print(
    f"{total_overlap_acres:,.2f} acres "
    f"({total_overlap_pct:.3f}% "
    f"of candidate)"
)


print()
print(
    "=== BY GAP STATUS ==="
)

for status, values in sorted(
    gap_summary.items(),
    key=lambda item: (
        item[1]["acres"]
    ),
    reverse=True,
):

    print(
        f"GAP {status:<10} "
        f"{values['acres']:>10,.2f} acres "
        f"({values['percent_of_candidate']:>6.3f}%)"
    )


print()
print(
    "Cross-GAP overlap:",
    f"{cross_gap_overlap_acres:,.2f} acres",
)


print()
print(
    "=== PROTECTION / MANAGEMENT VIEWS ==="
)

for classification, values in (
    protection_views.items()
):

    print(
        f"{classification:<55} "
        f"{values['acres']:>10,.2f} acres "
        f"({values['percent_of_candidate']:>6.3f}%)"
    )


print()
print(
    "=== TOP PAD-US UNITS ==="
)

for unit in units[:15]:

    print(
        f"{unit['candidate_overlap_acres']:>10,.2f} acres | "
        f"GAP {unit['gap_status']} | "
        f"{unit['unit_name']} | "
        f"{unit['designation']} | "
        f"{unit['manager_name']}"
    )


print()
print(
    "=== MANAGERS ==="
)

for manager, values in sorted(
    manager_summary.items(),
    key=lambda item: (
        item[1]["acres"]
    ),
    reverse=True,
):

    print(
        f"{manager:<40} "
        f"{values['acres']:>10,.2f} acres"
    )


print()
print(
    "=== IMPORTANT ==="
)

print(
    "PAD-US overlap is protected-land "
    "screening evidence, not an automatic "
    "wind-development exclusion."
)

if cross_gap_overlap_acres > 0.01:

    print(
        "Multiple GAP categories overlap "
        "spatially; category acreages must "
        "not be summed as unique acreage."
    )


print()
print(
    "Raw:",
    RAW_PATH,
)

print(
    "Metadata:",
    METADATA_PATH,
)

print(
    "Summary:",
    SUMMARY_PATH,
)
