#!/usr/bin/env python3

import json
from pathlib import Path

import geopandas as gpd
import requests


CANDIDATE_PATH = Path(
    "data/scenarios/western_ok_250mw/candidate_area.geojson"
)

MAPSERVER_URL = (
    "https://hazards.fema.gov/arcgis/rest/services/"
    "public/NFHL/MapServer"
)


candidate = gpd.read_file(
    CANDIDATE_PATH
).to_crs("EPSG:4326")

geom = candidate.geometry.iloc[0]

rings = [
    [
        [float(x), float(y)]
        for x, y in geom.exterior.coords
    ]
]

esri_geometry = json.dumps(
    {
        "rings": rings,
        "spatialReference": {
            "wkid": 4326
        },
    }
)


session = requests.Session()

service = session.get(
    MAPSERVER_URL,
    params={"f": "json"},
    timeout=60,
)

service.raise_for_status()

metadata = service.json()


def find_layer(name):
    matches = [
        layer
        for layer in metadata.get(
            "layers",
            []
        )
        if str(
            layer.get("name", "")
        ).strip().lower()
        == name.lower()
    ]

    if len(matches) != 1:
        raise RuntimeError(
            f"Could not uniquely find "
            f"layer {name!r}: {matches}"
        )

    return matches[0]


def count_intersections(layer):
    url = (
        f"{MAPSERVER_URL}/"
        f"{layer['id']}/query"
    )

    response = session.get(
        url,
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
            "returnCountOnly": "true",
            "f": "json",
        },
        timeout=120,
    )

    response.raise_for_status()

    payload = response.json()

    if "error" in payload:
        raise RuntimeError(
            json.dumps(
                payload["error"],
                indent=2,
            )
        )

    return payload.get("count")


flood_layer = find_layer(
    "Flood Hazard Zones"
)

firm_layer = find_layer(
    "FIRM Panels"
)


print("=== FEMA COVERAGE DIAGNOSTIC ===")

print(
    "Flood Hazard Zones:",
    f"layer {flood_layer['id']}",
)

print(
    "FIRM Panels:",
    f"layer {firm_layer['id']}",
)


flood_count = count_intersections(
    flood_layer
)

firm_count = count_intersections(
    firm_layer
)


print()
print(
    "Flood-zone features intersecting candidate:",
    flood_count,
)

print(
    "FIRM panels intersecting candidate:",
    firm_count,
)


print()
print("=== INTERPRETATION ===")

if (
    flood_count == 0
    and firm_count == 0
):
    print(
        "No digital Flood Hazard Zone polygons "
        "or FIRM panels intersect the candidate."
    )

    print(
        "Treat FEMA NFHL flood status as "
        "UNKNOWN due to source coverage."
    )

elif (
    flood_count == 0
    and firm_count > 0
):
    print(
        "FIRM panel coverage exists but no "
        "Flood Hazard Zone features were returned."
    )

    print(
        "Do NOT accept the previous zero as "
        "a no-hazard result; investigate the "
        "hazard-layer query/data further."
    )

elif flood_count > 0:

    print(
        "Flood Hazard Zone data exists for "
        "the candidate."
    )

    print(
        "The screening script should retrieve "
        "and calculate those features."
    )

else:
    print(
        "Unexpected FEMA response combination; "
        "keep status UNKNOWN."
    )
