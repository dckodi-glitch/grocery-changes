import unittest
from datetime import date, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from openpyxl import load_workbook
from openpyxl.utils.datetime import WINDOWS_EPOCH, to_excel

from analyze import ROOT, audit_rows, parse_date, read_workbook


class AnalysisTests(unittest.TestCase):
    def test_excel_dates_and_invalid_dates(self):
        self.assertEqual(parse_date(datetime(2023, 5, 1), WINDOWS_EPOCH), date(2023, 5, 1))
        self.assertEqual(parse_date(to_excel(datetime(2023, 5, 1)), WINDOWS_EPOCH), date(2023, 5, 1))
        for value in ("not-a-date", "2023-05-02", datetime(2023, 5, 1, 12), True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_date(value, WINDOWS_EPOCH)

    def test_quality_reports_defects_without_filling(self):
        rows = [
            (datetime(2018, 1, 1), 1.0),
            (datetime(2018, 1, 1), None),
            ("bad", 2.0),
            (datetime(2018, 2, 1), -1),
            (datetime(2018, 3, 1), "."),
        ]
        parsed, quality, issues = audit_rows(rows, WINDOWS_EPOCH)
        self.assertEqual(parsed, [(date(2018, 1, 1), 1.0)])
        self.assertEqual(quality["duplicate_dates"], 1)
        self.assertEqual(quality["missing_months"], 62)
        self.assertEqual(quality["malformed_dates"], 1)
        self.assertEqual(quality["missing_values"], 2)
        self.assertEqual(quality["invalid_values"], 1)
        self.assertTrue(any("duplicate dates" in issue for issue in issues))
        self.assertTrue(any("missing months" in issue for issue in issues))

    def test_actual_workbook_metadata_and_coverage(self):
        for item in ("bread", "eggs", "milk"):
            with self.subTest(item=item):
                data = read_workbook(item)
                self.assertEqual(data["issues"], [])
                self.assertEqual(data["quality"]["rows"], 65)
                self.assertEqual(data["rows"][0][0], date(2018, 1, 1))
                self.assertEqual(data["rows"][-1][0], date(2023, 5, 1))

    def test_inconsistent_metadata_is_reported(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "bread.xlsx"
            path.write_bytes((ROOT / "bread.xlsx").read_bytes())
            workbook = load_workbook(path)
            workbook["README"]["A32"] = "2023-06-12"
            workbook["README"]["A19"] = "Euros"
            workbook.save(path)
            workbook.close()
            with patch("analyze.ROOT", Path(directory)):
                issues = read_workbook("bread")["issues"]
            self.assertTrue(any("vintage:" in issue for issue in issues))
            self.assertTrue(any("units:" in issue for issue in issues))


if __name__ == "__main__":
    unittest.main()
