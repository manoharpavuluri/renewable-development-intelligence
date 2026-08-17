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

OUT_DIR = Path(RESULT_DIR) / "gis" / "fema_nfhl"
OUT_DIR.mkdir(parents=True, exist_ok=True)

RAW_PATH = OUT_DIR / "flood_hazard_zones.geojson"
METADATA_PATH = OUT_DIR / "layer_metadata.json"
SUMMARY_PATH = OUT_DIR / "fema_nfhl_summary.json"

MAPSERVER_URL = (
    "https://hazards.fema.gov/arcgis/rest/services/"
    "public/NFHL/MapServer"
)

SQM_PER_ACRE = 4046.8564224


def clean(value):
    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    if value.upper() in {"NONE", "NULL"}:
        return None

    return value


def property_by_name(row, field_name):
    target = field_name.upper()

    for key, value in row.items():
        if str(key).upper() == target:
            return value

        if str(key).upper().endswith("." + target):
            return value

    return None


def is_true(value):
    value = clean(value)

    if value is None:
        return False

    return value.upper() in {
        "T",
        "TRUE",
        "Y",
        "YES",
        "1",
    }


def union_acres(geometries, crs):
    geometries = [
        g
        for g in geometries
        if g is not None and not g.is_empty
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
).to_crs("EPSG:4326")

if candidate.empty:
    raise SystemExit(
        "Candidate polygon is empty."
    )

candidate_geom = candidate.geometry.iloc[0]

if not candidate_geom.is_valid:
    raise SystemExit(
        "Candidate polygon is invalid."
    )

analysis_crs = candidate.estimate_utm_crs()

if analysis_crs is None:
    raise SystemExit(
        "Could not determine local projected CRS."
    )

candidate_utm = candidate.to_crs(
    analysis_crs
)

candidate_geom_utm = (
    candidate_utm.geometry.iloc[0]
)

candidate_acres = (
    candidate_geom_utm.area
    / SQM_PER_ACRE
)


# ------------------------------------------------------------
# Read live FEMA layer metadata first
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
# Discover Flood Hazard Zones layer dynamically.
#
# Do not hardcode an ArcGIS layer ID because service layer
# numbering can change independently of our application.
# ------------------------------------------------------------

service_response = session.get(
    MAPSERVER_URL,
    params={"f": "pjson"},
    timeout=60,
)

service_response.raise_for_status()

service_metadata = service_response.json()

if "error" in service_metadata:
    raise SystemExit(
        json.dumps(
            service_metadata["error"],
            indent=2,
        )
    )

matching_layers = [
    layer
    for layer in service_metadata.get("layers", [])
    if str(
        layer.get("name", "")
    ).strip().lower() == "flood hazard zones"
]

if len(matching_layers) != 1:
    available = [
        {
            "id": layer.get("id"),
            "name": layer.get("name"),
        }
        for layer in service_metadata.get("layers", [])
    ]

    raise SystemExit(
        "Unable to uniquely discover FEMA "
        "'Flood Hazard Zones' layer.\n"
        + json.dumps(
            available,
            indent=2,
        )
    )

layer_id = matching_layers[0]["id"]

LAYER_URL = (
    f"{MAPSERVER_URL}/{layer_id}"
)

QUERY_URL = (
    f"{LAYER_URL}/query"
)

print(
    "Discovered FEMA layer:",
    layer_id,
    matching_layers[0]["name"],
)

metadata_response = session.get(
    LAYER_URL,
    params={"f": "pjson"},
    timeout=60,
)

metadata_response.raise_for_status()

metadata = metadata_response.json()

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

field_names = [
    field.get("name")
    for field in metadata.get(
        "fields",
        []
    )
]

object_id_field = (
    metadata.get("objectIdField")
    or metadata.get("objectIdFieldName")
)

print(
    "=== FEMA NFHL LAYER ==="
)

print(
    "Layer:",
    metadata.get(
        "name",
        "<unknown>",
    ),
)

print(
    "Object ID field:",
    object_id_field,
)

for expected in [
    "FLD_ZONE",
    "ZONE_SUBTY",
    "SFHA_TF",
]:
    print(
        f"{expected}:",
        (
            "FOUND"
            if expected in field_names
            else "NOT FOUND"
        ),
    )


# ------------------------------------------------------------
# Candidate geometry for ArcGIS REST
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
        "Candidate geometry must be polygonal."
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
# Retrieve intersecting FEMA features with pagination.
#
# FEMA's current NFHL layer does not expose an Object ID field
# through this service, so returnIdsOnly cannot be relied upon.
# ------------------------------------------------------------

advanced = metadata.get(
    "advancedQueryCapabilities",
    {},
)

supports_pagination = advanced.get(
    "supportsPagination",
    False,
)

max_record_count = int(
    metadata.get(
        "maxRecordCount",
        1000,
    )
)

print()
print(
    "Supports pagination:",
    supports_pagination,
)

print(
    "Max record count:",
    max_record_count,
)

if not supports_pagination:
    raise SystemExit(
        "FEMA Flood Hazard Zones layer does not "
        "report pagination support. "
        "A different retrieval strategy is required."
    )


feature_collection = {
    "type": "FeatureCollection",
    "features": [],
}

BATCH_SIZE = min(
    500,
    max_record_count,
)

offset = 0
previous_signature = None


while True:

    response = session.get(
        QUERY_URL,
        params={
            "where": "1=1",
            "geometry": esri_geometry,
            "geometryType": (
                "esriGeometryPolygon"
            ),
            "inSR": "4326",
            "spatialRel": (
                "esriSpatialRelIntersects"
            ),
            "outFields": "*",
            "returnGeometry": "true",
            "outSR": "4326",
            "resultOffset": offset,
            "resultRecordCount": (
                BATCH_SIZE
            ),
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

    features = payload.get(
        "features",
        [],
    )

    if not features:
        break


    # Defensive protection against a service that
    # ignores resultOffset and repeatedly returns
    # the same page.
    first_properties = (
        features[0].get(
            "properties",
            {},
        )
    )

    signature = json.dumps(
        first_properties,
        sort_keys=True,
        default=str,
    )

    if (
        previous_signature is not None
        and signature == previous_signature
    ):
        raise RuntimeError(
            "FEMA query appears to be repeating "
            "the same page; resultOffset may not "
            "be honored."
        )

    previous_signature = signature


    feature_collection[
        "features"
    ].extend(
        features
    )

    print(
        f"Fetched offset={offset:,}: "
        f"{len(features):,} features"
    )


    if len(features) < BATCH_SIZE:
        break

    offset += len(features)


print()
print(
    "Intersecting source features:",
    f"{len(feature_collection['features']):,}",
)


RAW_PATH.write_text(
    json.dumps(
        feature_collection,
        indent=2,
    ),
    encoding="utf-8",
)

object_ids = []

# ------------------------------------------------------------
# Analyze geometries
# ------------------------------------------------------------

zone_summary = {}
sfha_acres = 0.0
mapped_acres = 0.0

if feature_collection["features"]:

    flood = (
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

    flood["clipped_geometry"] = (
        flood.geometry.intersection(
            candidate_geom_utm
        )
    )

    flood = flood[
        ~flood[
            "clipped_geometry"
        ].is_empty
    ].copy()

    flood = flood.set_geometry(
        "clipped_geometry"
    )

    flood = flood.drop(
        columns=["geometry"]
    )

    flood = flood.rename_geometry(
        "geometry"
    )

    mapped_acres = union_acres(
        flood.geometry.tolist(),
        analysis_crs,
    )

    sfha_geometries = []

    category_geometries = defaultdict(
        list
    )

    for _, row in flood.iterrows():

        zone = clean(
            property_by_name(
                row,
                "FLD_ZONE",
            )
        ) or "UNKNOWN"

        subtype = clean(
            property_by_name(
                row,
                "ZONE_SUBTY",
            )
        ) or "UNSPECIFIED"

        sfha = property_by_name(
            row,
            "SFHA_TF",
        )

        category = (
            zone,
            subtype,
            clean(sfha) or "UNKNOWN",
        )

        category_geometries[
            category
        ].append(
            row.geometry
        )

        if is_true(sfha):
            sfha_geometries.append(
                row.geometry
            )

    sfha_acres = union_acres(
        sfha_geometries,
        analysis_crs,
    )

    for (
        zone,
        subtype,
        sfha_flag,
    ), geometries in (
        category_geometries.items()
    ):

        acres = union_acres(
            geometries,
            analysis_crs,
        )

        if acres > candidate_acres + 0.01:
            raise RuntimeError(
                "FEMA zone area exceeds "
                "candidate area."
            )

        key = (
            f"{zone} | "
            f"{subtype} | "
            f"SFHA={sfha_flag}"
        )

        zone_summary[key] = {
            "flood_zone": zone,
            "zone_subtype": subtype,
            "sfha_tf": sfha_flag,
            "acres": acres,
            "percent_of_candidate": (
                acres
                / candidate_acres
                * 100
            ),
        }


# ------------------------------------------------------------
# Coverage / unknown
# ------------------------------------------------------------

if mapped_acres > candidate_acres + 0.01:
    raise RuntimeError(
        "NFHL mapped area exceeds "
        "candidate polygon area."
    )

if sfha_acres > mapped_acres + 0.01:
    raise RuntimeError(
        "SFHA area exceeds total "
        "NFHL mapped area."
    )

unmapped_acres = max(
    0.0,
    candidate_acres - mapped_acres,
)

mapped_pct = (
    mapped_acres
    / candidate_acres
    * 100
)

unmapped_pct = (
    unmapped_acres
    / candidate_acres
    * 100
)

sfha_pct = (
    sfha_acres
    / candidate_acres
    * 100
)


# ------------------------------------------------------------
# Summary artifact
# ------------------------------------------------------------

summary = {
    "source": {
        "authority": (
            "Federal Emergency "
            "Management Agency"
        ),

        "dataset": (
            "National Flood Hazard Layer"
        ),

        "layer": (
            metadata.get("name")
        ),

        "layer_url": LAYER_URL,

        "retrieved_utc": (
            datetime.now(
                timezone.utc
            ).isoformat()
        ),

        "source_feature_count": (
            len(
                feature_collection[
                    "features"
                ]
            )
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
        str(analysis_crs)
    ),

    "candidate_area_acres": (
        candidate_acres
    ),

    "nfhl_mapped_coverage": {
        "acres": mapped_acres,
        "percent": mapped_pct,
    },

    "nfhl_unmapped_or_unknown": {
        "acres": unmapped_acres,
        "percent": unmapped_pct,
    },

    "special_flood_hazard_area": {
        "acres": sfha_acres,
        "percent_of_candidate": (
            sfha_pct
        ),
    },

    "zones": dict(
        sorted(
            zone_summary.items(),
            key=lambda item: (
                item[1]["acres"]
            ),
            reverse=True,
        )
    ),

    "evidence_classification": (
        "SOURCE_FACT + DERIVED_FACT"
    ),

    "limitations": [
        (
            "NFHL represents FEMA's "
            "effective mapped flood "
            "hazard information."
        ),
        (
            "Unmapped acreage is treated "
            "as unknown, not as evidence "
            "of no flood hazard."
        ),
        (
            "No project setback or "
            "development exclusion is "
            "applied by this screening."
        ),
        (
            "Flood-hazard screening does "
            "not replace site-specific "
            "engineering or permitting "
            "review."
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
    "=== NFHL MAPPED COVERAGE ==="
)

print(
    f"{mapped_acres:,.2f} acres "
    f"({mapped_pct:.3f}%)"
)

print(
    "Unmapped / unknown:",
    f"{unmapped_acres:,.2f} acres "
    f"({unmapped_pct:.3f}%)"
)

print()
print(
    "=== SPECIAL FLOOD HAZARD AREA ==="
)

print(
    f"{sfha_acres:,.2f} acres "
    f"({sfha_pct:.3f}% of candidate)"
)

print()
print(
    "=== FEMA FLOOD ZONES ==="
)

for _, values in sorted(
    zone_summary.items(),
    key=lambda item: (
        item[1]["acres"]
    ),
    reverse=True,
):

    print(
        f"{values['flood_zone']:<8} "
        f"{values['acres']:>10,.2f} acres "
        f"({values['percent_of_candidate']:>6.3f}%) "
        f"SFHA={values['sfha_tf']} "
        f"{values['zone_subtype']}"
    )

print()
print(
    "=== IMPORTANT ==="
)

if unmapped_pct > 1.0:
    print(
        "Candidate contains meaningful "
        "NFHL coverage gaps; those areas "
        "must remain UNKNOWN."
    )
else:
    print(
        "Candidate has near-complete "
        "NFHL mapped coverage."
    )

print(
    "SFHA overlap is a screening fact, "
    "not an automatic project exclusion."
)

print()
print("Raw:", RAW_PATH)
print("Metadata:", METADATA_PATH)
print("Summary:", SUMMARY_PATH)
