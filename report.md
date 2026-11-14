# Grocery price history at the project's starting cutoff

**New retrospective analysis**, executed on November 13, 2026; no post has
been published. Editorial coverage starts June 14, 2023. The source vintage is
June 13, 2023, and the observations span January 2018 through May 2023.
These are separate dates, not evidence that a project was performed in 2023.
The workbook creation metadata is dated November 13, 2026; the workbook
metadata describes a current series, not necessarily its historical metadata.

## What information is represented?

The three workbooks contain monthly, not seasonally adjusted U.S. city average
prices from the Bureau of Labor Statistics, archived by ALFRED. For May 2023,
the vintage records:

| Item and source series | Price level | Unit |
|---|---:|---|
| [White pan bread, APU0000702111](https://alfred.stlouisfed.org/series?seid=APU0000702111) | $1.951 | per pound |
| [Large Grade A eggs, APU0000708111](https://alfred.stlouisfed.org/series?seid=APU0000708111) | $2.666 | per dozen |
| [Fresh whole milk, APU0000709112](https://alfred.stlouisfed.org/series?seid=APU0000709112) | $4.042 | per gallon |

These are price **levels**, not equivalent basket quantities. The
[price-history figure](outputs/price-history.svg) uses separate panels and
units; the [monthly price table](outputs/monthly-prices.csv) contains the
national aggregate observations underlying the panels.

## Data quality

The metadata and vintage worksheet headers agree on the identifiers and
June 13, 2023 vintage. The metadata gives U.S. dollars; the product titles
specify the different denominators. Each workbook contains 65 monthly rows,
from January 2018 to May 2023, with **zero** duplicate dates, missing months,
malformed dates, missing values, invalid prices, or out-of-range dates. The
workbook creation timestamps in the two metadata representations agree to the
minute. See the [complete quality table](outputs/data-quality.csv) and
[analysis metadata](outputs/analysis-metadata.json) for source URLs, input
hashes, revisions, execution timestamp and limitations. Original workbooks
remain unchanged.

The historical vintage does not establish an exact time of availability on
June 13 or personal activity on June 14. These national urban averages are not
local store prices and do not imply nutritional equivalence or causation. The
workbooks explicitly caution that average prices are best used for price
levels, not price change over time; use the relevant CPI indexes for formal
inflation measures. See [BLS average-price methodology](https://www.bls.gov/cpi/factsheets/average-prices.htm).

## Reproduce and excerpt

Install the pinned dependencies and run the commands in [README](README.md).
The following exact excerpt from `analyze.py` writes each separately labeled
series; no cross-item arithmetic is performed:

```python
for data in series:
    for month, price in data["rows"]:
        writer.writerow([data["item"], data["series_id"], month.isoformat(), f"{price:.3f}", data["unit"]])
```
