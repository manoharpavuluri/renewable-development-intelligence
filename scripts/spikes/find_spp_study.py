#!/usr/bin/env python3

import html
import os
import re
import sys
from pathlib import Path
from urllib.parse import urljoin


if len(sys.argv) != 2:
    raise SystemExit(
        "Usage: find_spp_study.py GEN-2026-PR2"
    )

study_number = sys.argv[1]

result_dir = os.environ.get("RESULT_DIR")

if not result_dir:
    raise SystemExit("RESULT_DIR is not set")

path = (
    Path(result_dir)
    / "spp_study_chain"
    / "2026_impact_studies.html"
)

text = path.read_text(
    encoding="utf-8",
    errors="replace",
)

# Find the complete HTML table row containing the study number.
rows = re.findall(
    r"<tr\b[^>]*>.*?</tr>",
    text,
    flags=re.IGNORECASE | re.DOTALL,
)

matching = [
    row for row in rows
    if study_number.lower() in row.lower()
]

if not matching:
    raise SystemExit(
        f"No study row found for {study_number}"
    )

print(f"Matches: {len(matching)}")

for i, row in enumerate(matching, start=1):

    print()
    print(f"=== MATCH {i} ===")

    # Produce readable cell text.
    cells = re.findall(
        r"<td\b[^>]*>(.*?)</td>",
        row,
        flags=re.IGNORECASE | re.DOTALL,
    )

    for n, cell in enumerate(cells, start=1):

        cleaned = re.sub(
            r"<[^>]+>",
            " ",
            cell,
        )

        cleaned = html.unescape(cleaned)

        cleaned = re.sub(
            r"\s+",
            " ",
            cleaned,
        ).strip()

        print(f"{n:02d}: {cleaned}")

    links = re.findall(
        r'href=["\']([^"\']+)["\']',
        row,
        flags=re.IGNORECASE,
    )

    print("\nLinks:")

    for link in links:
        absolute = urljoin(
            "https://opsportal.spp.org/",
            html.unescape(link),
        )

        print(absolute)
