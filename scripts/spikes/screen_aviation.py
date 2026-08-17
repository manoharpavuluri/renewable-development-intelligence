#!/usr/bin/env python3

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
import requests
from shapely.geometry import Point


CANDIDATE_PATH = Path(
    "data/scenarios/western_ok_250mw/candidate_area.geojson"
)

RESULT_DIR = os.environ.get("RESULT_DIR")

if not RESULT_DIR:
    raise SystemExit("RESULT_DIR is not set")

OUT_DIR = Path(RESULT_DIR) / "aviation"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SUMMARY_PATH = OUT_DIR / "aviation_summary.json"


AIRPORTS_SERVICE = (
    "https://services6.arcgis.com/ssFJjBXIUyZDrSYZ/"
    "arcgis/rest/services/US_Airport/FeatureServer/0"
)

SUA_SERVICE = (
    "https://coast.noaa.gov/arcgismc/rest/services/hosted/"
    "MilitarySpecialUseAirspace/FeatureServer/0"
)

# Oklahoma Wind Energy Development Act implementing rules
# currently apply a 1.5 nautical mile setback from public-use
# or municipally owned airports, public schools, and hospitals.
STATUTORY_AIRPORT_SETBACK_NM = 1.5

# Broader context radius for screening purposes only.
SCREENING_RADIUS_MILES = 30

METERS_PER_MILE = 1609.344
METERS_PER_NM = 1852.0


def dms_to_decimal(value: str) -> float:

    match = re.match(
        r"(\d+)-(\d+)-([\d.]+)([NSEW])", value.strip()
    )

    if not match:
        raise ValueError(f"Unrecognized DMS format: {value!r}")

    degrees, minutes, seconds, hemi = match.groups()

    decimal = (
        float(degrees)
        + float(minutes) / 60
        + float(seconds) / 3600
    )

    if hemi in {"S", "W"}:
        decimal *= -1

    return decimal


candidate = gpd.read_file(CANDIDATE_PATH).to_crs("EPSG:4326")

if candidate.empty:
    raise SystemExit("Candidate polygon is empty.")

candidate_geom = candidate.geometry.iloc[0]
analysis_crs = candidate.estimate_utm_crs()
candidate_utm = candidate.to_crs(analysis_crs)
candidate_geom_utm = candidate_utm.geometry.iloc[0]

minx, miny, maxx, maxy = candidate.total_bounds

# ~1 degree buffer covers well beyond the screening radius at
# this latitude.
buffer_deg = 1.0

bbox = (
    f"{minx - buffer_deg},{miny - buffer_deg},"
    f"{maxx + buffer_deg},{maxy + buffer_deg}"
)


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
# Airports
# ------------------------------------------------------------

response = session.get(
    f"{AIRPORTS_SERVICE}/query",
    params={
        "where": "STATE='OK'",
        "geometry": bbox,
        "geometryType": "esriGeometryEnvelope",
        "inSR": 4326,
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": (
            "IDENT,NAME,LATITUDE,LONGITUDE,PRIVATEUSE,"
            "TYPE_CODE,SERVCITY,OPERSTATUS"
        ),
        "returnGeometry": "false",
        "f": "json",
    },
    timeout=60,
)

response.raise_for_status()

payload = response.json()

if "error" in payload:
    raise SystemExit(json.dumps(payload["error"], indent=2))


airport_records = []

for feature in payload.get("features", []):

    attrs = feature["attributes"]

    try:
        lat = dms_to_decimal(attrs["LATITUDE"])
        lon = dms_to_decimal(attrs["LONGITUDE"])
    except (ValueError, KeyError, TypeError):
        continue

    point = gpd.GeoSeries(
        [Point(lon, lat)], crs="EPSG:4326"
    ).to_crs(analysis_crs)

    distance_miles = (
        point.iloc[0].distance(candidate_geom_utm)
        / METERS_PER_MILE
    )

    airport_records.append(
        {
            "ident": attrs.get("IDENT"),
            "name": attrs.get("NAME"),
            "service_city": attrs.get("SERVCITY"),
            "public_use": (
                attrs.get("PRIVATEUSE") == 0
            ),
            "type_code": attrs.get("TYPE_CODE"),
            "operational_status": attrs.get(
                "OPERSTATUS"
            ),
            "distance_to_candidate_miles": (
                round(distance_miles, 3)
            ),
            "distance_to_candidate_nm": (
                round(
                    distance_miles
                    * METERS_PER_MILE
                    / METERS_PER_NM,
                    3,
                )
            ),
        }
    )


airport_records.sort(
    key=lambda item: item["distance_to_candidate_miles"]
)

within_screening_radius = [
    item
    for item in airport_records
    if item["distance_to_candidate_miles"]
    <= SCREENING_RADIUS_MILES
]

public_use_within_radius = [
    item
    for item in within_screening_radius
    if item["public_use"]
]

nearest_public_use = (
    min(
        (
            item
            for item in airport_records
            if item["public_use"]
        ),
        key=lambda item: item[
            "distance_to_candidate_miles"
        ],
        default=None,
    )
)

statutory_setback_violation = (
    nearest_public_use is not None
    and nearest_public_use["distance_to_candidate_nm"]
    < STATUTORY_AIRPORT_SETBACK_NM
)


# ------------------------------------------------------------
# Military Special Use Airspace
# ------------------------------------------------------------

rings = [
    [
        [float(x), float(y)]
        for x, y in candidate_geom.exterior.coords
    ]
]

esri_geometry = json.dumps(
    {"rings": rings, "spatialReference": {"wkid": 4326}}
)

sua_response = session.get(
    f"{SUA_SERVICE}/query",
    params={
        "where": "1=1",
        "geometry": esri_geometry,
        "geometryType": "esriGeometryPolygon",
        "inSR": 4326,
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": (
            "featurename,specialuseairspacetype,"
            "controllingagency,flooraltitude,"
            "ceilingaltitude,altitudeuom"
        ),
        "returnGeometry": "false",
        "f": "json",
    },
    timeout=60,
)

sua_response.raise_for_status()

sua_payload = sua_response.json()

if "error" in sua_payload:
    raise SystemExit(json.dumps(sua_payload["error"], indent=2))

sua_intersections = [
    feature["attributes"]
    for feature in sua_payload.get("features", [])
]


# ------------------------------------------------------------
# Summary
# ------------------------------------------------------------

summary = {
    "source": {
        "authority": "Federal Aviation Administration",
        "airports_dataset": (
            "FAA Aeronautical Information Services - "
            "US Airports"
        ),
        "airports_service_url": AIRPORTS_SERVICE,
        "sua_dataset": (
            "FAA Special Use Airspace "
            "(NOAA-hosted mirror)"
        ),
        "sua_service_url": SUA_SERVICE,
        "retrieved_utc": datetime.now(timezone.utc).isoformat(),
    },
    "screening_radius_miles": SCREENING_RADIUS_MILES,
    "statutory_airport_setback_nm": (
        STATUTORY_AIRPORT_SETBACK_NM
    ),
    "airports_within_screening_radius_count": (
        len(within_screening_radius)
    ),
    "public_use_airports_within_screening_radius_count": (
        len(public_use_within_radius)
    ),
    "nearest_public_use_airport": nearest_public_use,
    "statutory_setback_appears_violated": (
        statutory_setback_violation
    ),
    "airports_within_screening_radius": (
        within_screening_radius
    ),
    "military_special_use_airspace_intersections": (
        sua_intersections
    ),
    "military_special_use_airspace_intersection_count": (
        len(sua_intersections)
    ),
    "evidence_classification": "SOURCE_FACT + DERIVED_FACT",
    "interpretation": (
        "Nearest-airport distances and Special Use Airspace "
        "intersections computed against real FAA aeronautical "
        "data for the candidate polygon."
    ),
    "limitations": [
        (
            "This does not perform an FAA Part 77 obstruction "
            "evaluation or airspace determination; only the "
            "FAA's own Obstruction Evaluation / Airport Airspace "
            "Analysis (OE/AAA) process, via Form 7460-1, "
            "establishes that."
        ),
        (
            "Airport distances are computed to point locations "
            "in this dataset, not to runway centerlines or "
            "approach surfaces."
        ),
        (
            "Military Training Route (MTR) low-level corridors "
            "are not included in this screening; only Special "
            "Use Airspace polygons (MOAs, restricted/warning "
            "areas, etc.) intersecting the candidate boundary "
            "were checked."
        ),
        (
            "This does not establish radar/weather-surveillance "
            "compatibility or DoD mission-compatibility review "
            "outcomes."
        ),
    ],
}

SUMMARY_PATH.write_text(
    json.dumps(summary, indent=2), encoding="utf-8"
)


print("=== AIRPORTS WITHIN SCREENING RADIUS ===")
print(
    f"{len(within_screening_radius)} airports within "
    f"{SCREENING_RADIUS_MILES} miles "
    f"({len(public_use_within_radius)} public-use)"
)
print()

for item in within_screening_radius[:15]:
    print(
        f"{item['distance_to_candidate_miles']:>7.2f} mi | "
        f"{'PUBLIC' if item['public_use'] else 'PRIVATE':<7} | "
        f"{item['ident']:<6} {item['name']}"
    )

print()
print("=== NEAREST PUBLIC-USE AIRPORT ===")
if nearest_public_use:
    print(
        f"{nearest_public_use['name']} "
        f"({nearest_public_use['ident']}): "
        f"{nearest_public_use['distance_to_candidate_miles']:.2f} mi / "
        f"{nearest_public_use['distance_to_candidate_nm']:.2f} nm"
    )
    print(
        "Statutory 1.5 nm setback appears violated:",
        statutory_setback_violation,
    )
else:
    print("None found within screening extent.")

print()
print("=== MILITARY SPECIAL USE AIRSPACE ===")
print(
    "Intersections with candidate polygon:",
    len(sua_intersections),
)
for item in sua_intersections:
    print("-", item)

print()
print("Summary:", SUMMARY_PATH)
