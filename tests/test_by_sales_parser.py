from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase

from by_sales_parser import BYSalesParseError, parse_by_sales, to_by_tmp_sales
from tests.by_fixture import sales_xls


class BYSalesParserTests(SimpleTestCase):
    def test_parses_upload_and_reconciles_all_six_months(self):
        result = parse_by_sales(SimpleUploadedFile("sales.xls", sales_xls()))

        self.assertEqual(result.checked_months, (3, 4, 5, 6, 7, 8))
        self.assertEqual(len(result.records), 12)
        self.assertEqual(result.records["sku"].nunique(), 2)
        self.assertEqual(result.records["store"].nunique(), 2)
        self.assertEqual(set(result.records["buyer"]), {"Покупатель Тест"})
        self.assertEqual(set(result.records["store"]), {"Магазин Один", "Магазин Два"})
        self.assertEqual(set(result.records.columns), {"buyer", "store", "sku", "month", "qty", "amount", "material_desc"})
        self.assertEqual(set(result.records["material_desc"]), {"Товар Один", "Товар Два"})
        self.assertEqual(result.records.groupby("month")["qty"].sum().to_dict(), {month: 3 for month in range(3, 9)})
        self.assertEqual(result.records.groupby("month")["amount"].sum().to_dict(), {month: 30 for month in range(3, 9)})

    def test_rejects_mismatched_totals(self):
        with self.assertRaisesMessage(BYSalesParseError, "Итоги за месяц 3 не совпали"):
            parse_by_sales(sales_xls(wrong_total=True))

    def test_rejects_missing_total(self):
        with self.assertRaisesMessage(BYSalesParseError, "Некорректные итоги за месяц 3"):
            parse_by_sales(sales_xls(missing_total=True))

    def test_rejects_missing_store_outline(self):
        with self.assertRaisesMessage(BYSalesParseError, "Не для всех товаров удалось найти покупателя и магазин"):
            parse_by_sales(sales_xls(missing_store=True))

    def test_rejects_non_xls_content(self):
        with self.assertRaisesMessage(BYSalesParseError, "Не удалось прочитать файл .xls"):
            parse_by_sales(b"not an Excel file")

    def test_rejects_missing_product_description(self):
        with self.assertRaisesMessage(BYSalesParseError, "Есть товар без описания в колонке C"):
            parse_by_sales(sales_xls(missing_description=True))

    def test_shapes_measures_without_inventing_chain_or_purchase_price(self):
        parsed = parse_by_sales(sales_xls())
        shaped = to_by_tmp_sales(parsed.records, year=2026)

        self.assertEqual(list(shaped.columns), [
            "date_year", "date_month", "store_by", "chain", "material",
            "material_desc", "measure", "value",
        ])
        self.assertEqual(len(shaped), 24)
        self.assertEqual(set(shaped["date_year"]), {2026})
        self.assertTrue(shaped["chain"].isna().all())
        self.assertEqual(set(shaped["measure"]), {"volume", "fact_price_value"})
        self.assertEqual(set(shaped["material_desc"]), {"Товар Один", "Товар Два"})
        self.assertEqual(set(shaped["store_by"]), {"Магазин Один", "Магазин Два"})
        self.assertEqual(shaped.loc[shaped["measure"] == "volume", "value"].sum(), 18)
        self.assertEqual(shaped.loc[shaped["measure"] == "fact_price_value", "value"].sum(), 180)

    def test_omits_missing_measures(self):
        parsed = parse_by_sales(sales_xls(missing_qty=True, missing_amount=True))
        shaped = to_by_tmp_sales(parsed.records, year=2027, chain="Подтверждённая сеть")

        march = shaped[shaped["date_month"] == 3]
        self.assertEqual(len(march), 2)
        self.assertEqual(set(march["measure"]), {"volume", "fact_price_value"})
        self.assertEqual(set(march["value"]), {2, 10})
        self.assertEqual(set(shaped["date_year"]), {2027})
        self.assertEqual(set(shaped["chain"]), {"Подтверждённая сеть"})

    def test_preserves_explicit_zero(self):
        records = parse_by_sales(sales_xls()).records.copy()
        records.loc[0, "qty"] = 0

        shaped = to_by_tmp_sales(records, year=2026)
        first_volume = shaped[(shaped["date_month"] == 3) &
                              (shaped["store_by"] == "Магазин Один") &
                              (shaped["measure"] == "volume")]
        self.assertEqual(first_volume["value"].tolist(), [0])

    def test_requires_explicit_valid_year(self):
        parsed = parse_by_sales(sales_xls())
        with self.assertRaises(TypeError):
            to_by_tmp_sales(parsed.records)
        with self.assertRaisesMessage(ValueError, "Год отчёта должен быть передан явно"):
            to_by_tmp_sales(parsed.records, year=True)
