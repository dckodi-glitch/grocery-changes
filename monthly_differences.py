#!/usr/bin/env python3
"""Export within-series changes for the July 26 retrospective milestone."""

import csv
import json
import math
import sys
from datetime import datetime
from pathlib import Path

from analyze import END, ROOT, SERIES, START, VINTAGE, input_revision, read_workbook, sha256

OUTPUT = ROOT / "outputs" / "g07"
QUESTION = "How did monthly average price levels change within each grocery series?"


def monthly_differences(rows):
    """Compare only adjacent months; never bridge a missing value or month."""
    previous_month = previous_price = None
    results = []
    for month, price in rows:
        if previous_month is not None and month <= previous_month:
            raise ValueError(f"dates must be unique and increasing: {month}")
        if price is not None and (isinstance(price, bool) or not isinstance(price, (int, float))
                                  or not math.isfinite(price) or price <= 0):
            raise ValueError(f"invalid price at {month}: {price!r}")
        if previous_month is None:
            status = "first_month_missing_value" if price is None else "first_month"
        elif price is None:
            status = "missing_current_value"
        elif (month.year * 12 + month.month) - (previous_month.year * 12 + previous_month.month) != 1:
            status = "missing_previous_month"
        elif previous_price is None:
            status = "missing_previous_value"
        else:
            status = "ok"
        change = price - previous_price if status == "ok" else None
        percent = change / previous_price * 100 if status == "ok" else None
        results.append((month, price, change, abs(change) if change is not None else None, percent, status))
        previous_month, previous_price = month, price
    return results


def main():
    series = [read_workbook(item) for item in SERIES]
    errors = [f"{data['item']}: {issue}" for data in series for issue in data["issues"]]
    if errors:
        raise ValueError("Workbook audit failed; no exports written:\n" + "\n".join(errors))
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with (OUTPUT / "monthly-differences.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file, lineterminator="\n")
        writer.writerow(["item", "series_id", "observation_month", "price", "price_unit",
                         "change", "absolute_change", "percentage_change", "status"])
        for data in series:
            for month, price, change, magnitude, percent, status in monthly_differences(data["rows"]):
                writer.writerow([data["item"], data["series_id"], month.isoformat(),
                                 f"{price:.3f}" if price is not None else "", data["unit"],
                                 f"{change:.3f}" if change is not None else "",
                                 f"{magnitude:.3f}" if magnitude is not None else "",
                                 f"{percent:.6f}" if percent is not None else "", status])

    metadata = {
        "project": "grocery-changes",
        "question": QUESTION,
        "coverage_date": "2023-07-26",
        "observation_start": START.isoformat(),
        "observation_end": END.isoformat(),
        "source_vintage": VINTAGE,
        "historical_cutoff": "2023-07-26",
        "source_urls": {data["item"]: data["url"] for data in series},
        "input_revision": {data["item"]: input_revision(data["item"]) for data in series},
        "input_hashes": {f"{data['item']}.xlsx": sha256(ROOT / f"{data['item']}.xlsx") for data in series},
        "analysis_revision": {
            "monthly_differences.py": f"sha256:{sha256(Path(__file__))}",
            "analyze.py": f"sha256:{sha256(ROOT / 'analyze.py')}",
        },
        "execution_date": datetime.now().astimezone().isoformat(timespec="seconds"),
        "publication_date": None,
        "method": "Audit original workbooks, then subtract the preceding month's price and divide by that price for percentage change. Absolute change is the magnitude of the signed change. First months and missing values or months have no comparison; no gaps are bridged. The workbook audit fails explicitly on missing inputs.",
        "limitations": [
            "Retrospective analysis; the workbooks were created in November 2026.",
            "The 2023-06-13 vintage is a fixed snapshot and may not include all information available by the July coverage date.",
            "BLS average price levels are not formal CPI inflation measures; BLS recommends CPI indexes to measure price changes.",
            "National urban averages are not local store prices; products have different units and are not directly comparable.",
        ],
        "outputs": ["outputs/g07/monthly-differences.csv", "outputs/g07/analysis-metadata.json",
                    "outputs/g07/analysis-notes.md"],
    }
    (OUTPUT / "analysis-metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print("Exported within-series monthly differences.")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, IndexError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
