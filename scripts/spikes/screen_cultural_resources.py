#!/usr/bin/env python3

import json
import os
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

OUT_DIR = Path(RESULT_DIR) / "gis" / "cultural_resources"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SUMMARY_PATH = OUT_DIR / "cultural_resources_summary.json"


MAPSERVER_URL = (
    "https://mapservices.nps.gov/arcgis/rest/services/"
    "cultural_resources/nrhp_locations/MapServer"
)

LAYERS = {
    0: "National Register Of Historic Places Points",
    1: "National Register of Historic Places Polygons",
}

SCREENING_RADIUS_MILES = 10
METERS_PER_MILE = 1609.344


candidate = gpd.read_file(CANDIDATE_PATH).to_crs("EPSG:4326")

if candidate.empty:
    raise SystemExit("Candidate polygon is empty.")

candidate_geom = candidate.geometry.iloc[0]
analysis_crs = candidate.estimate_utm_crs()
candidate_utm = candidate.to_crs(analysis_crs)
candidate_geom_utm = candidate_utm.geometry.iloc[0]

minx, miny, maxx, maxy = candidate.total_bounds
buffer_deg = 0.2

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


rings = [
    [
        [float(x), float(y)]
        for x, y in candidate_geom.exterior.coords
    ]
]

esri_geometry = json.dumps(
    {"rings": rings, "spatialReference": {"wkid": 4326}}
)


direct_intersections = []
nearby_sites = []


for layer_id, layer_label in LAYERS.items():

    layer_url = f"{MAPSERVER_URL}/{layer_id}"

    # Direct intersection with candidate polygon.
    response = session.get(
        f"{layer_url}/query",
        params={
            "where": "1=1",
            "geometry": esri_geometry,
            "geometryType": "esriGeometryPolygon",
            "inSR": 4326,
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": (
                "RESNAME,ResType,City,County,State,"
                "Is_NHL,STATUS,NRIS_Refnum"
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

    for feature in payload.get("features", []):
        attrs = feature["attributes"]
        attrs["_layer"] = layer_label
        direct_intersections.append(attrs)

    # Broader screening-radius context (points layer only;
    # polygons are large districts already captured above).
    if layer_id != 0:
        continue

    response = session.get(
        f"{layer_url}/query",
        params={
            "where": "1=1",
            "geometry": bbox,
            "geometryType": "esriGeometryEnvelope",
            "inSR": 4326,
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": (
                "RESNAME,ResType,City,County,State,"
                "Is_NHL,STATUS"
            ),
            "returnGeometry": "true",
            "outSR": 4326,
            "f": "geojson",
        },
        timeout=60,
    )
    response.raise_for_status()
    geo_payload = response.json()

    if "error" in geo_payload:
        raise SystemExit(json.dumps(geo_payload["error"], indent=2))

    if geo_payload.get("features"):

        points = gpd.GeoDataFrame.from_features(
            geo_payload["features"], crs="EPSG:4326"
        ).to_crs(analysis_crs)

        for _, row in points.iterrows():

            distance_miles = (
                row.geometry.distance(candidate_geom_utm)
                / METERS_PER_MILE
            )

            if distance_miles > SCREENING_RADIUS_MILES:
                continue

            nearby_sites.append(
                {
                    "name": row.get("RESNAME"),
                    "resource_type": row.get("ResType"),
                    "city": row.get("City"),
                    "county": row.get("County"),
                    "state": row.get("State"),
                    "is_national_historic_landmark": (
                        row.get("Is_NHL")
                    ),
                    "status": row.get("STATUS"),
                    "distance_to_candidate_miles": (
                        round(distance_miles, 3)
                    ),
                }
            )


nearby_sites.sort(
    key=lambda item: item["distance_to_candidate_miles"]
)


summary = {
    "source": {
        "authority": "National Park Service",
        "dataset": "National Register of Historic Places (NRHP)",
        "service_url": MAPSERVER_URL,
        "retrieved_utc": datetime.now(timezone.utc).isoformat(),
    },
    "screening_radius_miles": SCREENING_RADIUS_MILES,
    "direct_intersection_count": len(direct_intersections),
    "direct_intersections": direct_intersections,
    "nearby_site_count_within_radius": len(nearby_sites),
    "nearby_sites_within_radius": nearby_sites,
    "evidence_classification": "SOURCE_FACT + DERIVED_FACT",
    "interpretation": (
        "Direct NRHP intersections with the candidate polygon "
        "and nearby listed sites within a screening radius, "
        "queried against the authoritative NPS NRHP service."
    ),
    "limitations": [
        (
            "This is not equivalent to a Section 106 cultural-"
            "resources survey or a State Historic Preservation "
            "Office (SHPO) consultation."
        ),
        (
            "The NRHP dataset covers only listed properties; "
            "unlisted but eligible historic or archaeological "
            "resources are not captured here."
        ),
        (
            "Point locations are representative, not parcel-"
            "accurate; district polygon boundaries should be "
            "checked directly for boundary-adjacent siting."
        ),
    ],
}

SUMMARY_PATH.write_text(
    json.dumps(summary, indent=2), encoding="utf-8"
)


print("=== NRHP DIRECT INTERSECTIONS ===")
print(len(direct_intersections))
for item in direct_intersections:
    print("-", item)

print()
print(
    f"=== NRHP SITES WITHIN {SCREENING_RADIUS_MILES} MILES ==="
)
print(len(nearby_sites))
for item in nearby_sites[:15]:
    print(
        f"{item['distance_to_candidate_miles']:>7.2f} mi | "
        f"{item['name']} ({item['resource_type']}) | "
        f"NHL={item['is_national_historic_landmark']}"
    )

print()
print("Summary:", SUMMARY_PATH)
