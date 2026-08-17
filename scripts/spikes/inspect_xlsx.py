#!/usr/bin/env python3

import posixpath
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
OFFICE_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PACKAGE_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"

NS = {
    "x": MAIN_NS,
    "r": OFFICE_REL_NS,
    "pr": PACKAGE_REL_NS,
}


def qname(tag):
    return f"{{{MAIN_NS}}}{tag}"


def load_xml(zf, name):
    with zf.open(name) as f:
        return ET.parse(f).getroot()


def read_shared_strings(zf):
    path = "xl/sharedStrings.xml"

    if path not in zf.namelist():
        return []

    root = load_xml(zf, path)
    values = []

    for si in root.findall("x:si", NS):
        parts = []

        for text in si.iter(qname("t")):
            if text.text:
                parts.append(text.text)

        values.append("".join(parts))

    return values


def get_sheets(zf):
    workbook = load_xml(zf, "xl/workbook.xml")
    rels = load_xml(zf, "xl/_rels/workbook.xml.rels")

    relationships = {
        rel.attrib["Id"]: rel.attrib["Target"]
        for rel in rels.findall("pr:Relationship", NS)
    }

    sheets = []

    for sheet in workbook.findall("x:sheets/x:sheet", NS):
        name = sheet.attrib["name"]
        rel_id = sheet.attrib[f"{{{OFFICE_REL_NS}}}id"]
        state = sheet.attrib.get("state", "visible")

        target = relationships[rel_id]

        if target.startswith("/"):
            target = target.lstrip("/")
        else:
            target = posixpath.normpath(
                posixpath.join("xl", target)
            )

        sheets.append(
            {
                "name": name,
                "state": state,
                "target": target,
            }
        )

    return sheets


def get_cell_value(cell, shared_strings):
    cell_type = cell.attrib.get("t")
    value = cell.find("x:v", NS)
    formula = cell.find("x:f", NS)

    if cell_type == "inlineStr":
        parts = []
        inline = cell.find("x:is", NS)

        if inline is not None:
            for text in inline.iter(qname("t")):
                if text.text:
                    parts.append(text.text)

        rendered = "".join(parts)

    elif value is None:
        rendered = ""

    else:
        raw = value.text or ""

        if cell_type == "s":
            try:
                rendered = shared_strings[int(raw)]
            except (ValueError, IndexError):
                rendered = f"<invalid shared string: {raw}>"

        elif cell_type == "b":
            rendered = "TRUE" if raw == "1" else "FALSE"

        else:
            rendered = raw

    if formula is not None:
        return f"FORMULA[{formula.text or ''}] => {rendered}"

    return rendered


def inspect_sheet(zf, sheet, shared_strings, max_rows=12):
    root = load_xml(zf, sheet["target"])

    dimension = root.find("x:dimension", NS)

    if dimension is not None:
        print("Dimension:", dimension.attrib.get("ref", "<unknown>"))

    sheet_data = root.find("x:sheetData", NS)

    if sheet_data is None:
        print("<no sheet data>")
        return

    printed = 0

    for row in sheet_data.findall("x:row", NS):
        values = []

        for cell in row.findall("x:c", NS):
            rendered = get_cell_value(cell, shared_strings)

            if not rendered:
                continue

            rendered = rendered.replace("\n", " ")

            if len(rendered) > 160:
                rendered = rendered[:157] + "..."

            values.append(
                f"{cell.attrib.get('r', '?')}={rendered}"
            )

            if len(values) >= 20:
                values.append("...")
                break

        if not values:
            continue

        print(
            f"ROW {row.attrib.get('r', '?')}: "
            + " | ".join(values)
        )

        printed += 1

        if printed >= max_rows:
            break


def main():
    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: inspect_xlsx.py path/to/workbook.xlsx"
        )

    path = Path(sys.argv[1])

    if not path.exists():
        raise SystemExit(f"File not found: {path}")

    with zipfile.ZipFile(path) as zf:
        shared_strings = read_shared_strings(zf)
        sheets = get_sheets(zf)

        print("=== WORKBOOK ===")
        print("Path:", path)
        print("Sheets:", len(sheets))
        print("Shared strings:", len(shared_strings))

        print("\n=== SHEET INDEX ===")

        for i, sheet in enumerate(sheets, start=1):
            print(
                f"{i:02d}. {sheet['name']} "
                f"[{sheet['state']}] -> {sheet['target']}"
            )

        for i, sheet in enumerate(sheets, start=1):
            print()
            print("=" * 90)
            print(f"SHEET {i}: {sheet['name']}")
            print("=" * 90)

            inspect_sheet(
                zf,
                sheet,
                shared_strings,
            )


if __name__ == "__main__":
    main()
