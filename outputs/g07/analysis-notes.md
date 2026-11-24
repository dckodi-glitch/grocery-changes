# Monthly grocery price-level differences

This is a newly executed retrospective analysis for the July 26, 2023
coverage slot, not a claim that the work was performed then. The fixed ALFRED
vintage is June 13, 2023; it need not include all information available by
July 26. The original workbooks were created in November 2026.

The [monthly table](monthly-differences.csv) reports changes separately for
white bread, large eggs and whole milk, using each product's original unit.
The signed change is the current minus prior month's price; absolute change is
its magnitude, and percentage change divides the signed change by the prior
month's price. Among the 64 consecutive comparisons in each series, the
largest absolute movements within each series were:

| Series | Month | Signed change | Percentage change |
|---|---|---:|---:|
| Bread | September 2021 | +$0.113 per pound | +7.70% |
| Eggs | March 2023 | -$0.765 per dozen | -18.17% |
| Milk | May 2022 | +$0.192 per gallon | +4.79% |

These are within-series descriptions, not rankings across products. The first
month has no preceding observation, so its differences are blank. Each source
series contains 65 monthly observations from January 2018 to May 2023 and no
missing values or months. Missing data would not be bridged: the source audit
reports it and stops export; the calculation also marks unavailable
comparisons explicitly.

These national urban average price levels are not local store prices. They
are **not formal CPI inflation measures**; the BLS recommends CPI indexes
for measuring price change. No nutritional equivalence or causal
interpretation is implied. [Analysis metadata](analysis-metadata.json)
records the actual execution timestamp, input hashes, source revision,
source URLs and exact analysis-code hashes. The publication date is unknown.

Reproduce from the repository root with `python3 monthly_differences.py`;
run `python3 -m unittest discover -s tests -v` for the focused checks.
