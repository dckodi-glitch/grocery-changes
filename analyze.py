#!/usr/bin/env python3
"""Audit the three ALFRED workbooks and export retrospective price histories."""

import csv
import hashlib
import json
import math
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import date, datetime, time, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from openpyxl import load_workbook
from openpyxl.utils.datetime import from_excel

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "outputs"
VINTAGE = "2023-06-13"
START, END = date(2018, 1, 1), date(2023, 5, 1)
QUESTION = "What historical price information was available when beginning a simple grocery-budget project on June 14, 2023?"
SERIES = {
    "bread": ("APU0000702111", "U.S. dollars per pound", "Average Price: Bread, White, Pan (Cost per Pound/453.6 Grams) in U.S. City Average"),
    "eggs": ("APU0000708111", "U.S. dollars per dozen", "Average Price: Eggs, Grade A, Large (Cost per Dozen) in U.S. City Average"),
    "milk": ("APU0000709112", "U.S. dollars per gallon", "Average Price: Milk, Fresh, Whole, Fortified (Cost per Gallon/3.8 Liters) in U.S. City Average"),
}
LIMITATIONS = [
    "U.S. city average prices are not local store prices; products and units differ.",
    "Average price levels are not formal CPI inflation measures; BLS recommends CPI indexes for measuring price change.",
    "The vintage is dated 2023-06-13; no intraday availability or actual project activity on 2023-06-14 is established.",
    "Workbooks were created in 2026; this is a newly executed retrospective analysis, not a contemporaneous record.",
    "No nutritional equivalence or causal interpretation is implied.",
]


def parse_date(value, epoch):
    """Accept Excel date cells, ISO dates, or numeric Excel serials; reject non-month starts."""
    if isinstance(value, bool):
        raise ValueError(f"invalid date {value!r}")
    if isinstance(value, (int, float)):
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f"invalid Excel date {value!r}")
        value = from_excel(value, epoch)
    if isinstance(value, datetime):
        if value.time() != time.min:
            raise ValueError(f"date has a time component: {value!r}")
        value = value.date()
    elif isinstance(value, str):
        try:
            value = date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"invalid date {value!r}") from exc
    if not isinstance(value, date) or value.day != 1:
        raise ValueError(f"expected a first-of-month date, got {value!r}")
    return value


def expected_months():
    return {date(y, m, 1) for y in range(START.year, END.year + 1)
            for m in range(1, 13) if START <= date(y, m, 1) <= END}


def audit_rows(rows, epoch):
    """Return parsed rows, quality counts and explicit problems without filling or dropping data."""
    parsed, issues, dates = [], [], []
    missing_values = invalid_values = malformed_dates = 0
    for row_number, row in enumerate(rows, 2):
        raw_date, raw_value, *extra = row
        if any(value is not None for value in extra):
            issues.append(f"row {row_number}: unexpected extra data {extra!r}")
        try:
            month = parse_date(raw_date, epoch)
            dates.append(month)
        except (ValueError, OverflowError) as exc:
            malformed_dates += 1
            issues.append(f"row {row_number}: {exc}")
            month = None
        if raw_value is None or raw_value == ".":
            missing_values += 1
            issues.append(f"row {row_number}: missing value")
        elif (isinstance(raw_value, bool) or not isinstance(raw_value, (int, float))
              or not math.isfinite(raw_value) or raw_value <= 0):
            invalid_values += 1
            issues.append(f"row {row_number}: invalid price {raw_value!r}")
        elif month is not None:
            parsed.append((month, float(raw_value)))
    counts = Counter(dates)
    duplicates = sorted(month for month, count in counts.items() if count > 1)
    missing = sorted(expected_months() - set(dates))
    outside = sorted(set(dates) - expected_months())
    if duplicates:
        issues.append("duplicate dates: " + ", ".join(str(d) for d in duplicates))
    if missing:
        issues.append("missing months: " + ", ".join(str(d) for d in missing))
    if outside:
        issues.append("dates outside expected coverage: " + ", ".join(str(d) for d in outside))
    quality = {
        "rows": len(rows), "observed_months": len(set(dates)),
        "duplicate_dates": len(duplicates), "missing_months": len(missing),
        "malformed_dates": malformed_dates, "missing_values": missing_values,
        "invalid_values": invalid_values, "out_of_range_dates": len(outside),
    }
    return sorted(parsed), quality, issues


def read_workbook(item):
    series_id, unit, expected_title = SERIES[item]
    path = ROOT / f"{item}.xlsx"
    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        issues = []
        expected_sheets = ["README", f"Vintages Starting {VINTAGE}"]
        if workbook.sheetnames != expected_sheets:
            raise ValueError(f"{path.name}: expected sheets {expected_sheets!r}, found {workbook.sheetnames!r}")
        meta = list(workbook["README"].iter_rows(values_only=True))
        checks = {
            "series ID": (meta[0][0], f"Series ID: {series_id}"),
            "source URL": (meta[2][0], f"Link: https://alfred.stlouisfed.org/series?seid={series_id}"),
            "title": (meta[9][0], expected_title),
            "source": (meta[12][0], "U.S. Bureau of Labor Statistics"),
            "units": (meta[18][0], "U.S. Dollars"),
            "frequency": (meta[21][0], "Monthly"),
            "seasonal adjustment": (meta[24][0], "Not Seasonally Adjusted"),
            "vintage": (meta[31][0], VINTAGE),
        }
        for label, (actual, expected) in checks.items():
            if actual != expected:
                issues.append(f"{label}: expected {expected!r}, found {actual!r}")
        data = workbook[expected_sheets[1]]
        rows = list(data.iter_rows(values_only=True))
        expected_header = ("observation_date", f"{series_id}_20230613")
        if rows[0][:2] != expected_header or any(x is not None for x in rows[0][2:]):
            issues.append(f"data header: expected {expected_header!r}, found {rows[0]!r}")
        parsed, quality, row_issues = audit_rows(rows[1:], workbook.epoch)
        issues.extend(row_issues)
        created = workbook.properties.created
        creation_text = meta[6][0]
        try:
            claimed = datetime.strptime(creation_text, "File Created: %Y-%m-%d %I:%M %p CST")
            claimed_utc = claimed.replace(tzinfo=timezone.utc).timestamp() + 6 * 3600
            if created is None or abs(created.replace(tzinfo=timezone.utc).timestamp() - claimed_utc) >= 60:
                issues.append(f"creation metadata disagree: {creation_text!r} vs {created!r} UTC")
        except (TypeError, ValueError):
            issues.append(f"unrecognized creation metadata: {creation_text!r}")
        return {
            "item": item, "series_id": series_id, "unit": unit,
            "url": f"https://alfred.stlouisfed.org/series?seid={series_id}",
            "workbook_created_utc": created.replace(tzinfo=timezone.utc).isoformat() if created else None,
            "rows": parsed, "quality": quality, "issues": issues,
        }
    finally:
        workbook.close()


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def input_revision(item):
    """Only identify a Git revision if its workbook bytes match the current input."""
    name = f"{item}.xlsx"
    result = subprocess.run(["git", "log", "-1", "--format=%H", "--", name],
                            cwd=ROOT, capture_output=True, text=True, check=False)
    revision = result.stdout.strip()
    if result.returncode or not revision:
        return None
    content = subprocess.run(["git", "show", f"{revision}:{name}"], cwd=ROOT,
                             capture_output=True, check=False)
    if content.returncode or hashlib.sha256(content.stdout).hexdigest() != sha256(ROOT / name):
        return None
    return revision


def export_figure(series):
    plt.rcParams["svg.fonttype"] = "none"
    fig, axes = plt.subplots(3, 1, figsize=(10, 8), sharex=True, constrained_layout=True)
    fig.suptitle("U.S. city average grocery price levels", fontsize=16, fontweight="bold")
    colors = ("#245f84", "#a14d16", "#526d32")
    for ax, data, color in zip(axes, series, colors):
        months, prices = zip(*data["rows"])
        ax.plot(months, prices, color=color, linewidth=2)
        ax.set_title(data["item"].capitalize(), loc="left", fontweight="bold")
        ax.set_ylabel(data["unit"])
        ax.grid(axis="y", alpha=0.25)
        ax.set_ylim(bottom=0)
    axes[-1].xaxis.set_major_locator(mdates.YearLocator())
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    axes[-1].set_xlabel("Observation month")
    fig.text(0.01, 0.002, "Monthly, not seasonally adjusted | ALFRED vintage 2023-06-13 | Retrospective analysis", fontsize=9)
    fig.savefig(OUTPUT / "price-history.svg", format="svg")
    plt.close(fig)
    path = OUTPUT / "price-history.svg"
    tree = ET.parse(path)
    root = tree.getroot()
    ns = "{http://www.w3.org/2000/svg}"
    root.set("role", "img")
    root.set("aria-labelledby", "chart-title chart-description")
    title = ET.Element(ns + "title", {"id": "chart-title"})
    title.text = "U.S. city average grocery price levels, January 2018 to May 2023"
    description = ET.Element(ns + "desc", {"id": "chart-description"})
    description.text = ("Three separate monthly price panels show white bread in dollars per pound, "
                        "large eggs in dollars per dozen, and whole milk in dollars per gallon. "
                        "The source is the June 13, 2023 ALFRED vintage. Units differ; prices are not directly comparable.")
    root.insert(0, description)
    root.insert(0, title)
    ET.register_namespace("", "http://www.w3.org/2000/svg")
    tree.write(path, encoding="utf-8", xml_declaration=True)


def main():
    series = [read_workbook(item) for item in SERIES]
    errors = [f"{data['item']}: {issue}" for data in series for issue in data["issues"]]
    if errors:
        raise ValueError("Workbook audit failed; no exports written:\n" + "\n".join(errors))
    OUTPUT.mkdir(exist_ok=True)
    with (OUTPUT / "monthly-prices.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["item", "series_id", "observation_month", "price", "unit"])
        for data in series:
            for month, price in data["rows"]:
                writer.writerow([data["item"], data["series_id"], month.isoformat(), f"{price:.3f}", data["unit"]])
    with (OUTPUT / "data-quality.csv").open("w", encoding="utf-8", newline="") as file:
        fields = ["item", "series_id", "unit", "observation_start", "observation_end"] + list(series[0]["quality"])
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for data in series:
            writer.writerow({"item": data["item"], "series_id": data["series_id"], "unit": data["unit"],
                             "observation_start": data["rows"][0][0].isoformat(),
                             "observation_end": data["rows"][-1][0].isoformat(), **data["quality"]})
    export_figure(series)
    metadata = {
        "project": "grocery-changes", "question": QUESTION,
        "observation_start": START.isoformat(), "observation_end": END.isoformat(),
        "source_vintage": VINTAGE, "historical_cutoff": "2023-06-14",
        "source_urls": {data["item"]: data["url"] for data in series},
        "input_revision": {data["item"]: input_revision(data["item"]) for data in series},
        "input_hashes": {f"{data['item']}.xlsx": sha256(ROOT / f"{data['item']}.xlsx") for data in series},
        "analysis_revision": f"sha256:{sha256(Path(__file__))}",
        "execution_date": datetime.now().astimezone().isoformat(timespec="seconds"),
        "publication_date": None,
        "workbook_created_utc": {data["item"]: data["workbook_created_utc"] for data in series},
        "method": "Read both sheets without modifying the workbooks; validate metadata and complete monthly coverage, then export national average price levels separately by item and unit.",
        "limitations": LIMITATIONS,
        "outputs": ["outputs/price-history.svg", "outputs/monthly-prices.csv", "outputs/data-quality.csv", "outputs/analysis-metadata.json"],
    }
    (OUTPUT / "analysis-metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print("Exported audited price histories for", ", ".join(SERIES))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, IndexError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
