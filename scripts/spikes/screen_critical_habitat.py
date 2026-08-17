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

OUT_DIR = Path(RESULT_DIR) / "gis" / "critical_habitat"
OUT_DIR.mkdir(parents=True, exist_ok=True)

RAW_PATH = OUT_DIR / "critical_habitat_intersections.geojson"
METADATA_PATH = OUT_DIR / "critical_habitat_layer_metadata.json"
SUMMARY_PATH = OUT_DIR / "critical_habitat_summary.json"


FEATURESERVER = (
    "https://services.arcgis.com/QVENGdaPbd4LUkLV/"
    "arcgis/rest/services/USFWS_Critical_Habitat/FeatureServer"
)

LAYERS = {
    0: "Final",
    2: "Proposed",
}

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


def union_area_acres(geometries, crs):
    geometries = [
        g for g in geometries if g is not None and not g.is_empty
    ]
    if not geometries:
        return 0.0
    series = gpd.GeoSeries(geometries, crs=crs)
    return series.union_all().area / SQM_PER_ACRE


# ------------------------------------------------------------
# Candidate
# ------------------------------------------------------------

candidate = gpd.read_file(CANDIDATE_PATH).to_crs("EPSG:4326")

if candidate.empty:
    raise SystemExit("Candidate polygon is empty.")

candidate_geom = candidate.geometry.iloc[0]

if not candidate_geom.is_valid:
    raise SystemExit("Candidate polygon is invalid.")

analysis_crs = candidate.estimate_utm_crs()

if analysis_crs is None:
    raise SystemExit("Could not determine local projected CRS.")

candidate_utm = candidate.to_crs(analysis_crs)
candidate_geom_utm = candidate_utm.geometry.iloc[0]
candidate_acres = candidate_geom_utm.area / SQM_PER_ACRE


session = requests.Session()
session.headers.update(
    {
        "User-Agent": (
            "RenewableDevelopmentIntelligence/"
            "source-access-spike"
        )
    }
)


rings = []

if candidate_geom.geom_type == "Polygon":
    rings.append(
        [[float(x), float(y)] for x, y in candidate_geom.exterior.coords]
    )
elif candidate_geom.geom_type == "MultiPolygon":
    for polygon in candidate_geom.geoms:
        rings.append(
            [[float(x), float(y)] for x, y in polygon.exterior.coords]
        )
else:
    raise SystemExit("Candidate geometry must be polygonal.")

esri_geometry = json.dumps(
    {"rings": rings, "spatialReference": {"wkid": 4326}}
)


all_features = []
layer_metadata = {}


for layer_id, layer_label in LAYERS.items():

    layer_url = f"{FEATURESERVER}/{layer_id}"
    query_url = f"{layer_url}/query"

    response = session.get(layer_url, params={"f": "pjson"}, timeout=60)
    response.raise_for_status()
    metadata = response.json()

    if "error" in metadata:
        raise SystemExit(json.dumps(metadata["error"], indent=2))

    layer_metadata[layer_label] = metadata

    response = session.get(
        query_url,
        params={
            "where": "1=1",
            "geometry": esri_geometry,
            "geometryType": "esriGeometryPolygon",
            "inSR": "4326",
            "spatialRel": "esriSpatialRelIntersects",
            "returnIdsOnly": "true",
            "f": "json",
        },
        timeout=120,
    )
    response.raise_for_status()
    id_payload = response.json()

    if "error" in id_payload:
        raise SystemExit(json.dumps(id_payload["error"], indent=2))

    object_ids = sorted(id_payload.get("objectIds") or [])

    print(f"{layer_label} intersecting source features:", len(object_ids))

    if not object_ids:
        continue

    response = session.get(
        query_url,
        params={
            "objectIds": ",".join(str(v) for v in object_ids),
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
        raise SystemExit(json.dumps(payload["error"], indent=2))

    for feature in payload.get("features", []):
        feature["properties"]["_layer_status"] = layer_label
        all_features.append(feature)


METADATA_PATH.write_text(
    json.dumps(layer_metadata, indent=2), encoding="utf-8"
)

feature_collection = {"type": "FeatureCollection", "features": all_features}

RAW_PATH.write_text(
    json.dumps(feature_collection, indent=2), encoding="utf-8"
)


if not all_features:

    summary = {
        "source": {
            "authority": "U.S. Fish and Wildlife Service",
            "dataset": "USFWS Critical Habitat (Final + Proposed)",
            "layer_url": FEATURESERVER,
            "retrieved_utc": datetime.now(timezone.utc).isoformat(),
        },
        "candidate_area_acres": candidate_acres,
        "critical_habitat_overlap_acres": 0.0,
        "critical_habitat_overlap_percent": 0.0,
        "species": [],
        "evidence_classification": "SOURCE_FACT + DERIVED_FACT",
        "interpretation": (
            "No designated Final or Proposed critical habitat "
            "polygons intersect the candidate area."
        ),
        "limitations": [
            (
                "Absence of designated critical habitat does not "
                "establish the absence of ESA-listed species "
                "presence, migratory-bird concerns, or the need "
                "for a full IPaC official species list review."
            )
        ],
    }

    SUMMARY_PATH.write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    print("No critical habitat intersects candidate area.")
    print("Summary:", SUMMARY_PATH)
    raise SystemExit(0)


ch = gpd.GeoDataFrame.from_features(all_features, crs="EPSG:4326").to_crs(
    analysis_crs
)

ch["clipped_geometry"] = ch.geometry.intersection(candidate_geom_utm)
ch = ch[~ch["clipped_geometry"].is_empty].copy()
ch = ch.set_geometry("clipped_geometry")
ch = ch.drop(columns=["geometry"]).rename_geometry("geometry")


total_overlap_acres = union_area_acres(ch.geometry.tolist(), analysis_crs)
total_overlap_pct = total_overlap_acres / candidate_acres * 100

if total_overlap_acres > candidate_acres + 0.01:
    raise RuntimeError("Critical-habitat overlap exceeds candidate area.")


species_groups = defaultdict(list)

for _, row in ch.iterrows():

    key = (
        clean(row.get("comname")) or "UNKNOWN",
        clean(row.get("sciname")) or "UNKNOWN",
        clean(row.get("listing_status")) or "UNKNOWN",
        clean(row.get("_layer_status")) or "UNKNOWN",
        clean(row.get("fedreg")) or "UNKNOWN",
        clean(row.get("pubdate")) or "UNKNOWN",
    )

    species_groups[key].append(row.geometry)


species = []

for (
    comname,
    sciname,
    listing_status,
    critical_habitat_status,
    fedreg,
    pubdate,
), geometries in species_groups.items():

    acres = union_area_acres(geometries, analysis_crs)

    species.append(
        {
            "common_name": comname,
            "scientific_name": sciname,
            "listing_status": listing_status,
            "critical_habitat_status": critical_habitat_status,
            "federal_register_citation": fedreg,
            "publication_date": pubdate,
            "candidate_overlap_acres": acres,
            "percent_of_candidate": acres / candidate_acres * 100,
        }
    )

species.sort(key=lambda item: item["candidate_overlap_acres"], reverse=True)


summary = {
    "source": {
        "authority": "U.S. Fish and Wildlife Service",
        "dataset": "USFWS Critical Habitat (Final + Proposed)",
        "layer_url": FEATURESERVER,
        "retrieved_utc": datetime.now(timezone.utc).isoformat(),
        "source_feature_count": len(all_features),
    },
    "candidate_area_acres": candidate_acres,
    "critical_habitat_overlap_acres": total_overlap_acres,
    "critical_habitat_overlap_percent": total_overlap_pct,
    "species": species,
    "evidence_classification": "SOURCE_FACT + DERIVED_FACT",
    "interpretation": (
        "Calculated intersection with USFWS Final and Proposed "
        "designated critical habitat."
    ),
    "limitations": [
        (
            "Critical habitat is only one part of ESA screening; "
            "it does not cover all ESA-listed species with range "
            "in the area, migratory-bird concerns, or bald/golden "
            "eagle considerations."
        ),
        (
            "This is not equivalent to a USFWS IPaC official "
            "species list or a completed Section 7 consultation."
        ),
        (
            "Federal Register publication does not by itself "
            "establish the current legal boundary; 'vacatedate' "
            "and amendments should be checked against the current "
            "Federal Register record."
        ),
    ],
}

SUMMARY_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")


print()
print("=== CRITICAL HABITAT OVERLAP ===")
print(f"{total_overlap_acres:,.2f} acres ({total_overlap_pct:.4f}% of candidate)")
print()
print("=== SPECIES ===")
for item in species:
    print(
        f"{item['candidate_overlap_acres']:>10,.2f} acres | "
        f"{item['listing_status']:<12} | "
        f"{item['critical_habitat_status']:<10} | "
        f"{item['common_name']} ({item['scientific_name']})"
    )

print()
print("Raw:", RAW_PATH)
print("Metadata:", METADATA_PATH)
print("Summary:", SUMMARY_PATH)
