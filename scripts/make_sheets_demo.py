"""Generate the synthetic demo spreadsheet used by SHEETS_BACKEND=memory (and its CSV twins).

    uv run python scripts/make_sheets_demo.py

Writes src/mcp_postgres_sheets/data/sheets_demo.json and sample_data/sheets/*.csv. The CSVs are
what you import into the template Google Sheet (see README → Google Sheets setup).
"""

from __future__ import annotations

import csv
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIRST = [
    "Ava",
    "Liam",
    "Noah",
    "Emma",
    "Mia",
    "Kenji",
    "Priya",
    "Mateo",
    "Zara",
    "Omar",
    "Hana",
    "Felix",
]
LAST = [
    "Smith",
    "Garcia",
    "Chen",
    "Patel",
    "Dubois",
    "Okafor",
    "Silva",
    "Kowalski",
    "Haddad",
    "Rossi",
]
COMPANIES = [
    "Northwind Traders", "Bluebird Logistics", "Copperleaf Studio", "Harbor & Pine", "Lumen Analytics",
    "Redwood Clinics", "Sparrow Foods", "Tidewater Energy", "Atlas Fitness", "Quill Publishing",
    "Orchid Hotels", "Granite Works",
]  # fmt: skip
STAGES = ["New", "Contacted", "Qualified", "Proposal", "Won", "Lost"]
OWNERS = ["Dana", "Luis", "Mei", "Sam"]
REGIONS = ["North America", "Europe", "APAC"]


def build() -> dict[str, object]:
    rng = random.Random(7)
    leads: list[list[object]] = [
        [
            "Lead ID",
            "Name",
            "Company",
            "Email",
            "Stage",
            "Value (USD)",
            "Owner",
            "Region",
            "Created",
        ]
    ]
    for i in range(1, 31):
        first, last = rng.choice(FIRST), rng.choice(LAST)
        company = rng.choice(COMPANIES)
        domain = company.lower().replace(" & ", "-").replace(" ", "") + ".example.com"
        leads.append(
            [
                f"L-{1000 + i}",
                f"{first} {last}",
                company,
                f"{first.lower()}.{last.lower()}@{domain}",
                rng.choices(STAGES, weights=[4, 4, 3, 2, 2, 1])[0],
                rng.randrange(20, 400) * 100,
                rng.choice(OWNERS),
                rng.choice(REGIONS),
                f"2026-{rng.randint(6, 11):02d}-{rng.randint(1, 28):02d}",
            ]
        )
    targets: list[list[object]] = [["Region", "Month", "Target (USD)", "Closed (USD)"]]
    for month in ("2026-08", "2026-09", "2026-10", "2026-11"):
        for region in REGIONS:
            target = rng.randrange(80, 200) * 1000
            targets.append([region, month, target, int(target * rng.uniform(0.55, 1.25))])
    return {
        "spreadsheets": {
            "demo-sales-pipeline": {
                "title": "Sales pipeline (demo)",
                "tabs": {"Leads": leads, "Targets": targets, "Notes": [["Date", "Note"]]},
            },
            "demo-hr-private": {
                "title": "HR - private (never in the allow-list)",
                "tabs": {"Salaries": [["Name", "Salary"], ["Synthetic Person A", 98000]]},
            },
        }
    }


def main() -> None:
    data = build()
    out = ROOT / "src" / "mcp_postgres_sheets" / "data" / "sheets_demo.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    csv_dir = ROOT / "sample_data" / "sheets"
    csv_dir.mkdir(parents=True, exist_ok=True)
    tabs = data["spreadsheets"]["demo-sales-pipeline"]["tabs"]  # type: ignore[index]
    for name, rows in tabs.items():
        with (csv_dir / f"{name.lower()}.csv").open("w", newline="", encoding="utf-8") as fh:
            csv.writer(fh).writerows(rows)
    print(f"wrote {out.relative_to(ROOT)} and {csv_dir.relative_to(ROOT)}/*.csv")


if __name__ == "__main__":
    main()
