#!/usr/bin/env python3

import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
import requests


CANDIDATE_PATH = Path(
    "data/scenarios/western_ok_250mw/candidate_area.geojson"
)

RESULT_DIR = os.environ.get("RESULT_DIR")

if not RESULT_DIR:
    raise SystemExit("RESULT_DIR is not set")

OUT_DIR = Path(RESULT_DIR) / "gis" / "land_cover"
OUT_DIR.mkdir(parents=True, exist_ok=True)

RASTER_PATH = OUT_DIR / "candidate_nlcd_30m.tif"
SUMMARY_PATH = OUT_DIR / "land_cover_summary.json"


IMAGE_SERVER = (
    "https://di-nlcd.img.arcgis.com/arcgis/rest/services/"
    "USA_NLCD_Annual_LandCover/ImageServer"
)

EXPORT_URL = f"{IMAGE_SERVER}/exportImage"

TARGET_CRS = "EPSG:32614"
PIXEL_SIZE_M = 30.0
SQM_PER_ACRE = 4046.8564224


# Standard NLCD Anderson-level land-cover legend. This
# classification scheme is a fixed public-domain standard, not
# retrieved per request.
NLCD_CLASSES = {
    11: "Open Water",
    12: "Perennial Ice/Snow",
    21: "Developed, Open Space",
    22: "Developed, Low Intensity",
    23: "Developed, Medium Intensity",
    24: "Developed, High Intensity",
    31: "Barren Land",
    41: "Deciduous Forest",
    42: "Evergreen Forest",
    43: "Mixed Forest",
    51: "Dwarf Scrub",
    52: "Shrub/Scrub",
    71: "Grassland/Herbaceous",
    72: "Sedge/Herbaceous",
    73: "Lichens",
    74: "Moss",
    81: "Pasture/Hay",
    82: "Cultivated Crops",
    90: "Woody Wetlands",
    95: "Emergent Herbaceous Wetlands",
}


candidate = gpd.read_file(CANDIDATE_PATH).to_crs(TARGET_CRS)

if candidate.empty:
    raise SystemExit("Candidate polygon is empty.")

candidate_geom = candidate.geometry.iloc[0]
candidate_acres = candidate_geom.area / SQM_PER_ACRE

minx, miny, maxx, maxy = candidate.total_bounds

width_px = int(round((maxx - minx) / PIXEL_SIZE_M))
height_px = int(round((maxy - miny) / PIXEL_SIZE_M))


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
    EXPORT_URL,
    params={
        "bbox": f"{minx},{miny},{maxx},{maxy}",
        "bboxSR": 32614,
        "imageSR": 32614,
        "size": f"{width_px},{height_px}",
        "format": "tiff",
        "pixelType": "U8",
        "noDataInterpretation": "esriNoDataMatchAny",
        "interpolation": "RSP_NearestNeighbor",
        "f": "image",
    },
    timeout=120,
)

response.raise_for_status()

if response.headers.get("Content-Type", "").startswith(
    "application/json"
):
    raise SystemExit(
        "NLCD ImageServer returned an error: "
        + response.text[:2000]
    )


RASTER_PATH.write_bytes(response.content)


with rasterio.open(RASTER_PATH) as src:

    land_cover = src.read(1)
    transform = src.transform
    crs = src.crs


# Rasterize the candidate polygon at the same grid to mask
# pixels strictly to the candidate footprint (the exported
# image covers the bounding box, not just the polygon).
from rasterio.features import geometry_mask

candidate_pixel_mask = ~geometry_mask(
    [candidate_geom],
    out_shape=land_cover.shape,
    transform=transform,
    invert=False,
)


valid_mask = candidate_pixel_mask & np.isin(
    land_cover,
    list(NLCD_CLASSES.keys()),
)

if not valid_mask.any():
    raise RuntimeError(
        "No valid NLCD class pixels intersect the candidate polygon."
    )


pixel_area_acres = (PIXEL_SIZE_M * PIXEL_SIZE_M) / SQM_PER_ACRE

class_counts = defaultdict(int)

values, counts = np.unique(
    land_cover[valid_mask], return_counts=True
)

for value, count in zip(values, counts):
    class_counts[int(value)] = int(count)


total_valid_pixels = int(valid_mask.sum())
sampled_acres = total_valid_pixels * pixel_area_acres


classes = []

for code, count in sorted(
    class_counts.items(), key=lambda item: item[1], reverse=True
):

    acres = count * pixel_area_acres

    classes.append(
        {
            "nlcd_code": code,
            "class_name": NLCD_CLASSES.get(
                code, f"Unknown class {code}"
            ),
            "pixel_count": count,
            "acres": acres,
            "percent_of_sampled_area": (
                acres / sampled_acres * 100
                if sampled_acres
                else 0.0
            ),
        }
    )


developed_acres = sum(
    item["acres"]
    for item in classes
    if item["nlcd_code"] in {21, 22, 23, 24}
)

open_water_acres = sum(
    item["acres"]
    for item in classes
    if item["nlcd_code"] == 11
)

wetland_acres = sum(
    item["acres"]
    for item in classes
    if item["nlcd_code"] in {90, 95}
)

cultivated_pasture_acres = sum(
    item["acres"]
    for item in classes
    if item["nlcd_code"] in {81, 82}
)

grass_shrub_acres = sum(
    item["acres"]
    for item in classes
    if item["nlcd_code"] in {52, 71, 72, 73, 74}
)


summary = {
    "source": {
        "authority": (
            "U.S. Geological Survey / Multi-Resolution Land "
            "Characteristics (MRLC) Consortium"
        ),
        "dataset": "National Land Cover Database (NLCD), Annual",
        "service_url": IMAGE_SERVER,
        "retrieved_utc": datetime.now(timezone.utc).isoformat(),
        "sample_resolution_m": PIXEL_SIZE_M,
        "sample_crs": str(crs),
        "raster_shape": list(land_cover.shape),
    },
    "candidate_area_acres": candidate_acres,
    "sampled_area_acres": sampled_acres,
    "sampled_pixel_count": total_valid_pixels,
    "classes": classes,
    "class_group_summary": {
        "developed_acres": developed_acres,
        "developed_percent_of_candidate": (
            developed_acres / candidate_acres * 100
        ),
        "open_water_acres": open_water_acres,
        "open_water_percent_of_candidate": (
            open_water_acres / candidate_acres * 100
        ),
        "wetland_acres": wetland_acres,
        "wetland_percent_of_candidate": (
            wetland_acres / candidate_acres * 100
        ),
        "cultivated_pasture_acres": cultivated_pasture_acres,
        "cultivated_pasture_percent_of_candidate": (
            cultivated_pasture_acres / candidate_acres * 100
        ),
        "grass_shrub_acres": grass_shrub_acres,
        "grass_shrub_percent_of_candidate": (
            grass_shrub_acres / candidate_acres * 100
        ),
    },
    "evidence_classification": "SOURCE_FACT + DERIVED_FACT",
    "interpretation": (
        "Calculated NLCD 30 m land-cover class composition "
        "clipped to the candidate polygon."
    ),
    "limitations": [
        (
            "NLCD is a 30 m nationally consistent land-cover "
            "product; it is screening-grade and does not "
            "substitute for a site-specific land-cover or "
            "wetland delineation survey."
        ),
        (
            "No land-cover class is treated here as a "
            "development exclusion; compatibility screening "
            "against turbine siting, access, and other "
            "development constraints must be performed "
            "separately."
        ),
        (
            "This does not establish jurisdictional wetland "
            "status; compare against the governed NWI wetlands "
            "evidence already collected for this candidate."
        ),
    ],
}


SUMMARY_PATH.write_text(
    json.dumps(summary, indent=2), encoding="utf-8"
)


print("=== NLCD LAND COVER (candidate-clipped) ===")
print(
    f"Sampled: {sampled_acres:,.1f} acres of "
    f"{candidate_acres:,.1f} candidate acres"
)
print()

for item in classes:
    print(
        f"{item['acres']:>10,.1f} acres "
        f"({item['percent_of_sampled_area']:>5.2f}%) | "
        f"{item['nlcd_code']:>3} {item['class_name']}"
    )

print()
print("=== CLASS GROUPS ===")
for key, value in summary["class_group_summary"].items():
    if key.endswith("_acres"):
        print(f"{key:<40} {value:>10,.1f} acres")

print()
print("Raster:", RASTER_PATH)
print("Summary:", SUMMARY_PATH)
