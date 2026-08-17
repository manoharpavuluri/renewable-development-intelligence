#!/usr/bin/env python3

"""
Live-source smoke suite - NOT part of the offline regression
suite in tests/. This makes real network calls to every
authoritative external service this project depends on and
checks:

  1. reachability (the endpoint responds at all)
  2. schema stability (expected field/layer names this project's
     deterministic capabilities depend on are still present)

The 63-test offline suite in tests/ can never catch a live
endpoint going down or a service silently renaming a field this
project reads (e.g. PAD-US renaming "GAP_Sts", or NLCD changing
its class codes). This script exists to catch exactly that class
of drift. It is meant to be run manually or on a low-frequency
schedule, not on every commit - a flaky government GIS endpoint
should not block a PR.

Exit code is non-zero if anything is DOWN or SCHEMA_CHANGED.
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field
from enum import StrEnum

import requests


TIMEOUT_SECONDS = 20


class SourceStatus(StrEnum):
    UP = "UP"
    DOWN = "DOWN"
    SCHEMA_CHANGED = "SCHEMA_CHANGED"


@dataclass
class SourceCheck:
    name: str
    authority: str
    used_by_capability: str
    status: SourceStatus = SourceStatus.DOWN
    latency_ms: float | None = None
    detail: str = ""


def _check_arcgis_service(
    *,
    name: str,
    authority: str,
    used_by_capability: str,
    url: str,
    expected_fields: list[str] | None = None,
    expected_layer_names: list[str] | None = None,
) -> SourceCheck:

    check = SourceCheck(
        name=name,
        authority=authority,
        used_by_capability=used_by_capability,
    )

    start = time.monotonic()

    try:

        response = requests.get(
            url, params={"f": "pjson"}, timeout=TIMEOUT_SECONDS
        )

        check.latency_ms = round(
            (time.monotonic() - start) * 1000, 1
        )

        response.raise_for_status()

        payload = response.json()

        if "error" in payload:

            check.status = SourceStatus.DOWN
            check.detail = str(payload["error"])
            return check

        missing = []

        if expected_fields:

            field_names = {
                f.get("name")
                for f in payload.get("fields", [])
            }

            missing.extend(
                f"field:{name}"
                for name in expected_fields
                if name not in field_names
            )

        if expected_layer_names:

            layer_names = {
                layer.get("name")
                for layer in payload.get("layers", [])
            }

            missing.extend(
                f"layer:{name}"
                for name in expected_layer_names
                if name not in layer_names
            )

        if missing:

            check.status = SourceStatus.SCHEMA_CHANGED
            check.detail = (
                "missing expected: " + ", ".join(missing)
            )

        else:

            check.status = SourceStatus.UP
            check.detail = "reachable, expected schema present"

    except requests.RequestException as exc:

        check.latency_ms = round(
            (time.monotonic() - start) * 1000, 1
        )
        check.status = SourceStatus.DOWN
        check.detail = str(exc)

    return check


def _check_reachable(
    *,
    name: str,
    authority: str,
    used_by_capability: str,
    url: str,
) -> SourceCheck:

    check = SourceCheck(
        name=name,
        authority=authority,
        used_by_capability=used_by_capability,
    )

    start = time.monotonic()

    try:

        response = requests.get(url, timeout=TIMEOUT_SECONDS)

        check.latency_ms = round(
            (time.monotonic() - start) * 1000, 1
        )

        if response.status_code < 500:
            check.status = SourceStatus.UP
            check.detail = f"HTTP {response.status_code}"
        else:
            check.status = SourceStatus.DOWN
            check.detail = f"HTTP {response.status_code}"

    except requests.RequestException as exc:

        check.latency_ms = round(
            (time.monotonic() - start) * 1000, 1
        )
        check.status = SourceStatus.DOWN
        check.detail = str(exc)

    return check


def run_checks() -> list[SourceCheck]:

    return [
        _check_arcgis_service(
            name="USGS PAD-US",
            authority="U.S. Geological Survey",
            used_by_capability="land.resolve_status",
            url=(
                "https://services.arcgis.com/v01gqwM5QqNysAAi/"
                "arcgis/rest/services/"
                "PADUS_Protection_Status_by_GAP_Status_Code/"
                "FeatureServer/0"
            ),
            expected_fields=[
                "OBJECTID",
                "Category",
                "Unit_Nm",
                "GAP_Sts",
                "MngTp_Desc",
                "MngNm_Desc",
            ],
        ),
        _check_arcgis_service(
            name="USFWS Critical Habitat",
            authority="U.S. Fish and Wildlife Service",
            used_by_capability="environment.screen_species",
            url=(
                "https://services.arcgis.com/QVENGdaPbd4LUkLV/"
                "arcgis/rest/services/USFWS_Critical_Habitat/"
                "FeatureServer/0"
            ),
            expected_fields=[
                "comname",
                "sciname",
                "listing_status",
                "status",
                "fedreg",
            ],
        ),
        _check_arcgis_service(
            name="USGS 3DEP Elevation",
            authority="U.S. Geological Survey",
            used_by_capability="gis.analyze_terrain",
            url=(
                "https://elevation.nationalmap.gov/arcgis/"
                "rest/services/3DEPElevation/ImageServer"
            ),
        ),
        _check_arcgis_service(
            name="NLCD Annual Land Cover",
            authority="USGS / MRLC",
            used_by_capability="gis.analyze_land_cover",
            url=(
                "https://di-nlcd.img.arcgis.com/arcgis/rest/"
                "services/USA_NLCD_Annual_LandCover/ImageServer"
            ),
        ),
        _check_arcgis_service(
            name="Census TIGERweb Counties",
            authority="U.S. Census Bureau",
            used_by_capability="regulatory.build_permit_matrix",
            url=(
                "https://tigerweb.geo.census.gov/arcgis/rest/"
                "services/TIGERweb/State_County/MapServer/1"
            ),
            expected_fields=[
                "NAME",
                "GEOID",
                "STATE",
                "COUNTY",
            ],
        ),
        _check_arcgis_service(
            name="FAA US Airports",
            authority="Federal Aviation Administration",
            used_by_capability="aviation.screen_candidate",
            url=(
                "https://services6.arcgis.com/ssFJjBXIUyZDrSYZ/"
                "arcgis/rest/services/US_Airport/FeatureServer/0"
            ),
            expected_fields=[
                "IDENT",
                "NAME",
                "LATITUDE",
                "LONGITUDE",
                "PRIVATEUSE",
            ],
        ),
        _check_arcgis_service(
            name="Military Special Use Airspace",
            authority="FAA (NOAA-hosted mirror)",
            used_by_capability="aviation.screen_candidate",
            url=(
                "https://coast.noaa.gov/arcgismc/rest/services/"
                "hosted/MilitarySpecialUseAirspace/"
                "FeatureServer/0"
            ),
            expected_fields=[
                "featurename",
                "specialuseairspacetype",
                "controllingagency",
            ],
        ),
        _check_arcgis_service(
            name="FEMA NFHL",
            authority="Federal Emergency Management Agency",
            used_by_capability="gis.resolve_flood_evidence",
            url=(
                "https://hazards.fema.gov/arcgis/rest/services/"
                "public/NFHL/MapServer"
            ),
            expected_layer_names=[
                "NFHL Availability",
                "FIRM Panels",
            ],
        ),
        _check_arcgis_service(
            name="NPS NRHP",
            authority="National Park Service",
            used_by_capability=(
                "environment.screen_cultural_resources"
            ),
            url=(
                "https://mapservices.nps.gov/arcgis/rest/"
                "services/cultural_resources/nrhp_locations/"
                "MapServer/0"
            ),
            expected_fields=[
                "RESNAME",
                "ResType",
                "STATUS",
                "NRIS_Refnum",
            ],
        ),
        _check_reachable(
            name="SPP Operations Portal",
            authority="Southwest Power Pool",
            used_by_capability=(
                "spp.transmission_context (source portal; "
                "candidate evidence in this project was drawn "
                "from pre-fetched governed artifacts, not a "
                "live query against this URL)"
            ),
            url="https://opsportal.spp.org/",
        ),
    ]


def main() -> int:

    checks = run_checks()

    print("=== LIVE-SOURCE SMOKE CHECK ===")
    print()

    worst_exit = 0

    for check in checks:

        symbol = {
            SourceStatus.UP: "OK  ",
            SourceStatus.DOWN: "DOWN",
            SourceStatus.SCHEMA_CHANGED: "SCHM",
        }[check.status]

        print(
            f"[{symbol}] {check.name:<32} "
            f"{check.latency_ms or 0:>7.1f} ms  "
            f"{check.detail}"
        )

        print(f"       used by: {check.used_by_capability}")

        if check.status != SourceStatus.UP:
            worst_exit = 1

    print()

    up_count = sum(
        1 for c in checks if c.status == SourceStatus.UP
    )

    print(f"{up_count}/{len(checks)} sources UP")

    return worst_exit


if __name__ == "__main__":
    sys.exit(main())
