import unittest
from datetime import date

from monthly_differences import monthly_differences


class DifferenceTests(unittest.TestCase):
    def test_signed_magnitude_and_percent(self):
        rows = [(date(2023, 1, 1), 2.0), (date(2023, 2, 1), 3.0),
                (date(2023, 3, 1), 1.5)]
        result = monthly_differences(rows)
        self.assertEqual(result[0][2:], (None, None, None, "first_month"))
        self.assertEqual(result[1][2:], (1.0, 1.0, 50.0, "ok"))
        self.assertEqual(result[2][2:], (-1.5, 1.5, -50.0, "ok"))

    def test_missing_values_and_months_do_not_bridge(self):
        rows = [(date(2022, 12, 1), 2.0), (date(2023, 1, 1), None),
                (date(2023, 2, 1), 4.0), (date(2023, 4, 1), 5.0),
                (date(2023, 5, 1), 5.5)]
        result = monthly_differences(rows)
        self.assertEqual([x[-1] for x in result],
                         ["first_month", "missing_current_value", "missing_previous_value",
                          "missing_previous_month", "ok"])
        self.assertTrue(all(x[2:5] == (None, None, None) for x in result[:4]))
        self.assertEqual(result[-1][2:5], (0.5, 0.5, 10.0))
        first_missing = monthly_differences([(date(2023, 1, 1), None), (date(2023, 2, 1), 2)])
        self.assertEqual([x[-1] for x in first_missing], ["first_month_missing_value", "missing_previous_value"])

    def test_rejects_bad_prices_and_duplicate_dates(self):
        for price in (0, -1, float("nan"), True):
            with self.subTest(price=price), self.assertRaises(ValueError):
                monthly_differences([(date(2023, 1, 1), price)])
        with self.assertRaises(ValueError):
            monthly_differences([(date(2023, 1, 1), 1), (date(2023, 1, 1), 2)])


if __name__ == "__main__":
    unittest.main()
