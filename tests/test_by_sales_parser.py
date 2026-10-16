from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase

from by_sales_parser import BYSalesParseError, parse_by_sales
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
        self.assertEqual(set(result.records.columns), {"buyer", "store", "sku", "month", "qty", "amount"})
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
