import json

from django.test import SimpleTestCase

from by_sales_parser import parse_by_sales
from export_service.by_payload import build_by_sales_json
from tests.by_fixture import sales_xls


EXPECTED_FIELDS = {
    "date_year", "date_month", "store_by", "chain", "material",
    "material_desc", "measure", "value",
}


class BYPayloadTests(SimpleTestCase):
    def test_json_has_exact_staging_fields_and_measure_rows(self):
        records = parse_by_sales(sales_xls()).records

        payload = json.loads(build_by_sales_json(records, year=2026))

        self.assertEqual(len(payload), 24)
        self.assertTrue(all(set(row) == EXPECTED_FIELDS for row in payload))
        self.assertEqual({row["measure"] for row in payload}, {"volume", "fact_price_value"})
        self.assertEqual({row["date_month"] for row in payload}, set(range(3, 9)))
        self.assertEqual({row["store_by"] for row in payload}, {"Магазин Один", "Магазин Два"})
        self.assertEqual({row["material_desc"] for row in payload}, {"Товар Один", "Товар Два"})
        self.assertTrue(all(row["chain"] is None for row in payload))

    def test_missing_measures_are_omitted_without_zero_fill(self):
        records = parse_by_sales(sales_xls(missing_qty=True, missing_amount=True)).records

        payload = json.loads(build_by_sales_json(records, year=2026))
        march = [row for row in payload if row["date_month"] == 3]

        self.assertEqual(len(payload), 22)
        self.assertEqual(len(march), 2)
        self.assertEqual({(row["store_by"], row["measure"], row["value"]) for row in march}, {
            ("Магазин Один", "fact_price_value", 10),
            ("Магазин Два", "volume", 2),
        })

    def test_year_2027_is_used_only_when_explicitly_passed(self):
        records = parse_by_sales(sales_xls()).records

        payload = json.loads(build_by_sales_json(records, year=2027))

        self.assertEqual({row["date_year"] for row in payload}, {2027})
        with self.assertRaises(TypeError):
            build_by_sales_json(records)

    def test_nonfinite_values_cannot_be_serialized(self):
        records = parse_by_sales(sales_xls()).records
        for nonfinite in (float("inf"), float("-inf")):
            with self.subTest(value=nonfinite):
                changed = records.copy()
                changed.loc[0, "qty"] = nonfinite
                with self.assertRaisesMessage(ValueError, "недопустимое значение JSON"):
                    build_by_sales_json(changed, year=2026)

    def test_nan_is_treated_as_missing_not_serialized(self):
        records = parse_by_sales(sales_xls()).records.copy()
        records.loc[0, "qty"] = float("nan")

        payload_text = build_by_sales_json(records, year=2026)
        payload = json.loads(payload_text)

        self.assertEqual(len(payload), 23)
        self.assertNotIn("NaN", payload_text)
        self.assertNotIn("Infinity", payload_text)
