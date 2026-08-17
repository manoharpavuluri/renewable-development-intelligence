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

OUT_DIR = Path(RESULT_DIR) / "gis" / "jurisdiction"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SUMMARY_PATH = OUT_DIR / "jurisdiction_summary.json"


COUNTY_LAYER_URL = (
    "https://tigerweb.geo.census.gov/arcgis/rest/services/"
    "TIGERweb/State_County/MapServer/1/query"
)


candidate = gpd.read_file(CANDIDATE_PATH).to_crs("EPSG:4326")

if candidate.empty:
    raise SystemExit("Candidate polygon is empty.")

candidate_geom = candidate.geometry.iloc[0]
centroid = candidate_geom.centroid


session = requests.Session()
session.headers.update(
    {
        "User-Agent": (
            "RenewableDevelopmentIntelligence/"
            "source-access-spike"
        )
    }
)


response = session.get(
    COUNTY_LAYER_URL,
    params={
        "geometry": f"{centroid.x},{centroid.y}",
        "geometryType": "esriGeometryPoint",
        "inSR": 4326,
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "*",
        "returnGeometry": "false",
        "f": "json",
    },
    timeout=30,
)

response.raise_for_status()

payload = response.json()

if "error" in payload:
    raise SystemExit(json.dumps(payload["error"], indent=2))

features = payload.get("features", [])

if len(features) != 1:
    raise RuntimeError(
        "Expected exactly one county at the candidate "
        f"centroid, got {len(features)}."
    )

attrs = features[0]["attributes"]


STATE_FIPS_NAMES = {
    "40": "Oklahoma",
}

state_fips = attrs.get("STATE")
state_name = STATE_FIPS_NAMES.get(
    state_fips, f"FIPS {state_fips}"
)


summary = {
    "source": {
        "authority": "U.S. Census Bureau",
        "dataset": "TIGERweb State_County",
        "layer_url": COUNTY_LAYER_URL,
        "retrieved_utc": datetime.now(timezone.utc).isoformat(),
    },
    "candidate_centroid": {
        "longitude": centroid.x,
        "latitude": centroid.y,
    },
    "county_name": attrs.get("NAME"),
    "county_geoid": attrs.get("GEOID"),
    "state_fips": state_fips,
    "state_name": state_name,
    "evidence_classification": "SOURCE_FACT",
    "interpretation": (
        "County/state jurisdiction identified at the candidate "
        "centroid via authoritative Census TIGERweb boundaries."
    ),
    "limitations": [
        (
            "This identifies the county containing the candidate "
            "centroid only; a large candidate polygon may span "
            "additional county boundaries not captured here."
        ),
    ],
}

SUMMARY_PATH.write_text(
    json.dumps(summary, indent=2), encoding="utf-8"
)

print("=== JURISDICTION ===")
print(f"County: {summary['county_name']}")
print(f"State: {summary['state_name']}")
print(f"GEOID: {summary['county_geoid']}")
print()
print("Summary:", SUMMARY_PATH)
