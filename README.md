# grocery-changes

The [first retrospective grocery analysis](report.md) audits three preserved
ALFRED workbooks and plots their national average price histories. It is not a
record of work performed in 2023.

Run with Python 3, Git, and the versions in `requirements.txt`:

```sh
python3 -m pip install -r requirements.txt
python3 -m unittest discover -s tests -v
python3 analyze.py
```

The script reads the original workbooks without writing to them and regenerates
`outputs/`. It fails with explicit audit problems instead of filling missing
months or values. The metadata sidecar records the actual execution timestamp,
input hashes and source revisions, and the SHA-256 of the analysis script.

For the July 26 retrospective milestone, run `python3 monthly_differences.py`.
It writes a separate `outputs/g07/` table and provenance record; the signed
change and its absolute magnitude are in the series' own price unit, while
percentage change uses the preceding month's price. Missing months and values
are never bridged, and workbook audit failures stop the export.