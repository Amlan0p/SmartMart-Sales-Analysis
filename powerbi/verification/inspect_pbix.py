#!/usr/bin/env python3
"""Read-only inspection of the delivered .pbix file (never modifies it).

A .pbix is a ZIP archive. This one stores the report in the PBIR layout
(Report/definition/pages/*/visuals/*/visual.json), which is plain JSON, so pages,
visuals, field bindings, sort orders, filters, slicers and sync groups can be read
directly. The semantic model (DataModel) is compressed with Microsoft's XPress9
algorithm and CANNOT be read without Power BI / Analysis Services libraries, so this
script cannot see measure formulas, relationships or Power Query steps.

Usage:
    python powerbi/verification/inspect_pbix.py [path/to/file.pbix] [--md out.md]
"""
from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PBIX = ROOT / "powerbi" / "SmartMart_Sales_Dashboard_Final.pbix"
EXPECTED_PAGES = ["Executive Overview", "Product Performance", "Regional Performance", "Customer & Payment"]
EXPECTED_SYNC = {"Date", "Region", "Category", "Product", "Payment_Mode"}


def field_name(f: dict) -> str:
    for kind in ("Measure", "Column"):
        if kind in f:
            v = f[kind]
            ref = v["Expression"]["SourceRef"]
            star = " (measure)" if kind == "Measure" else ""
            return f'{ref.get("Entity", ref.get("Source"))}[{v["Property"]}]{star}'
    if "HierarchyLevel" in f:
        v = f["HierarchyLevel"]
        return f'{v["Expression"]["Hierarchy"]["Hierarchy"]}.{v["Level"]}'
    if "Aggregation" in f:
        return "AGG " + field_name(f["Aggregation"]["Expression"])
    return str(f)[:50]


def inspect(pbix: Path) -> dict:
    out: dict = {"file": pbix.name, "parts": [], "pages": [], "errors": []}
    with zipfile.ZipFile(pbix) as z:
        names = z.namelist()
        out["parts"] = sorted({n.split("/")[0] for n in names})
        out["data_model_bytes"] = z.getinfo("DataModel").file_size if "DataModel" in names else None
        pages_json = json.loads(z.read("Report/definition/pages/pages.json"))
        for pid in pages_json["pageOrder"]:
            page = json.loads(z.read(f"Report/definition/pages/{pid}/page.json"))
            visuals = []
            for n in names:
                if n.startswith(f"Report/definition/pages/{pid}/visuals/") and n.endswith("visual.json"):
                    d = json.loads(z.read(n))
                    v = d["visual"]
                    qs = v.get("query", {}).get("queryState", {})
                    roles = {r: [field_name(p["field"]) for p in s["projections"]] for r, s in qs.items()}
                    sd = v.get("query", {}).get("sortDefinition")
                    sort = [(field_name(s["field"]), s["direction"]) for s in sd["sort"]] if sd else []
                    fc = d.get("filterConfig", {}).get("filters", [])
                    vco = v.get("visualContainerObjects", {})
                    visuals.append({
                        "type": v["visualType"], "x": d["position"]["x"], "y": d["position"]["y"],
                        "w": d["position"]["width"], "h": d["position"]["height"],
                        "roles": roles, "sort": sort, "hidden": bool(d.get("isHidden")),
                        "sync": (v.get("syncGroup") or {}).get("groupName"),
                        "filter_types": sorted({f.get("type", "?") for f in fc}),
                        "has_filter_body": any(f.get("filter") for f in fc),
                        "custom_title": "title" in vco, "alt_text": "general" in vco,
                    })
            out["pages"].append({"name": page["displayName"], "width": page["width"], "height": page["height"],
                                 "visuals": visuals})
    return out


def checks(info: dict) -> list[tuple[str, bool, str]]:
    res = []
    names = [p["name"] for p in info["pages"]]
    res.append(("Four expected pages in the expected order", names == EXPECTED_PAGES, ", ".join(names)))
    for p in info["pages"]:
        sync = {v["sync"] for v in p["visuals"] if v["type"] == "slicer"}
        res.append((f"{p['name']}: all five slicers present and synced", sync == EXPECTED_SYNC, ", ".join(sorted(sync))))
    all_v = [v for p in info["pages"] for v in p["visuals"]]
    res.append(("Top N / Bottom N filter on any visual (specification asks for 5)",
                any("TopN" in v["filter_types"] for v in all_v), "none found"))
    res.append(("Every non-slicer visual has a custom title",
                all(v["custom_title"] for v in all_v if v["type"] != "slicer"), "titles are Power BI automatic titles"))
    res.append(("Every visual has alt text", all(v["alt_text"] for v in all_v), "no alt text set"))
    for p in info["pages"]:
        for v in p["visuals"]:
            if v["type"] == "lineChart" and v["sort"] and v["sort"][0][1] == "Descending" and "(measure)" in v["sort"][0][0]:
                res.append((f"{p['name']}: line chart on {list(v['roles'].values())[0][0]} sorted by a measure (axis not chronological)",
                            False, f"sorted by {v['sort'][0][0]} {v['sort'][0][1]}"))
    return res


def to_markdown(info: dict) -> str:
    L = [f"# PBIX inspection - {info['file']}", "",
         "Read-only inspection by `inspect_pbix.py`. The compressed `DataModel` "
         f"({info['data_model_bytes']:,} bytes) could **not** be read, so measure formulas, relationships and Power Query steps are not covered.", ""]
    L += ["| Page | Canvas | Visuals | Of which slicers (hidden) |", "|---|---|---:|---:|"]
    for p in info["pages"]:
        sl = [v for v in p["visuals"] if v["type"] == "slicer"]
        L.append(f"| {p['name']} | {p['width']:.0f} x {p['height']:.0f} | {len(p['visuals'])} | {len(sl)} ({sum(v['hidden'] for v in sl)}) |")
    for p in info["pages"]:
        L += ["", f"## {p['name']}", "", "| Visual | Fields by role | Sort |", "|---|---|---|"]
        for v in sorted(p["visuals"], key=lambda v: (v["y"], v["x"])):
            if v["type"] == "slicer":
                continue
            roles = "; ".join(f"{r}: {', '.join(f)}" for r, f in v["roles"].items())
            sort = ", ".join(f"{f} {d}" for f, d in v["sort"]) or "-"
            L.append(f"| {v['type']} | {roles} | {sort} |")
    L += ["", "## Checks", "", "| Check | Result | Detail |", "|---|---|---|"]
    for name, ok, detail in checks(info):
        L.append(f"| {name} | {'PASS' if ok else 'FAIL'} | {detail} |")
    return "\n".join(L) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pbix", nargs="?", default=str(DEFAULT_PBIX))
    ap.add_argument("--md", help="write a Markdown report to this path")
    args = ap.parse_args()
    info = inspect(Path(args.pbix))
    md = to_markdown(info)
    if args.md:
        Path(args.md).write_text(md, encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
