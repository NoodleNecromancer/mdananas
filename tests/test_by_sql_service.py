import json
from unittest.mock import MagicMock, patch

from django.db import DatabaseError
from django.test import SimpleTestCase, override_settings

from by_sales_parser import parse_by_sales
from export_service.by_sql_service import BYDryRunError, BYDryRunSummary, preview_by_sales_import
from tests.by_fixture import sales_xls


class BYSQLServiceTests(SimpleTestCase):
    def setUp(self):
        self.records = parse_by_sales(sales_xls()).records

    def test_sql_call_is_disabled_by_default(self):
        with patch("export_service.by_sql_service.connections") as connections:
            with self.assertRaisesMessage(BYDryRunError, "через SQL отключена"):
                preview_by_sales_import(self.records, year=2027)
        connections.__getitem__.assert_not_called()

    @override_settings(BY_SQL_DRY_RUN_ENABLED=True)
    def test_schema_confirmation_is_required(self):
        with patch("export_service.by_sql_service.connections") as connections:
            with self.assertRaisesMessage(BYDryRunError, "ещё не подтверждена"):
                preview_by_sales_import(self.records, year=2027)
        connections.__getitem__.assert_not_called()

    @override_settings(BY_SQL_DRY_RUN_ENABLED=True, BY_SQL_SCHEMA_CONFIRMED=True)
    def test_parameterized_call_is_dry_run_only(self):
        cursor = MagicMock()
        cursor.fetchone.return_value = (24, 12)
        connection = MagicMock()
        connection.cursor.return_value.__enter__.return_value = cursor

        with patch("export_service.by_sql_service.connections", {"ideal": connection}):
            result = preview_by_sales_import(self.records, year=2027)

        self.assertEqual(result, BYDryRunSummary(24, 12))
        sql, params = cursor.execute.call_args.args
        self.assertEqual(sql, "EXEC [15_BY].[BY_Import_Sales_Json_Draft] "
                              "@RowsJson=%s, @DryRun=%s, @SchemaConfirmed=%s")
        self.assertEqual(params[1:], [1, 1])
        payload = json.loads(params[0])
        self.assertEqual(len(payload), 24)
        self.assertEqual({row["date_year"] for row in payload}, {2027})

    @override_settings(BY_SQL_DRY_RUN_ENABLED=True, BY_SQL_SCHEMA_CONFIRMED=True)
    def test_database_error_is_wrapped(self):
        connection = MagicMock()
        connection.cursor.return_value.__enter__.side_effect = DatabaseError("test-only failure")

        with patch("export_service.by_sql_service.connections", {"ideal": connection}):
            with self.assertRaisesMessage(BYDryRunError, "Не удалось выполнить предварительную проверку"):
                preview_by_sales_import(self.records, year=2027)

    @override_settings(BY_SQL_DRY_RUN_ENABLED=True, BY_SQL_SCHEMA_CONFIRMED=True)
    def test_missing_procedure_result_is_an_error(self):
        cursor = MagicMock()
        cursor.fetchone.return_value = None
        connection = MagicMock()
        connection.cursor.return_value.__enter__.return_value = cursor

        with patch("export_service.by_sql_service.connections", {"ideal": connection}):
            with self.assertRaisesMessage(BYDryRunError, "не вернула результат"):
                preview_by_sales_import(self.records, year=2027)
