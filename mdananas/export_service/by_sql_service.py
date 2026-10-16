from dataclasses import dataclass

import pandas as pd
from django.conf import settings
from django.db import DatabaseError, connections

from .by_payload import build_by_sales_json


class BYDryRunError(RuntimeError):
    pass


@dataclass(frozen=True)
class BYDryRunSummary:
    input_measure_rows: int
    proposed_sales_rows: int


def preview_by_sales_import(
    records: pd.DataFrame, *, year: int, chain: str | None = None
) -> BYDryRunSummary:
    if not getattr(settings, "BY_SQL_DRY_RUN_ENABLED", False):
        raise BYDryRunError("Проверка продаж Беларуси через SQL отключена.")
    if not getattr(settings, "BY_SQL_SCHEMA_CONFIRMED", False):
        raise BYDryRunError("Схема SQL для продаж Беларуси ещё не подтверждена.")

    payload = build_by_sales_json(records, year=year, chain=chain)
    try:
        with connections["ideal"].cursor() as cursor:
            cursor.execute(
                "EXEC [15_BY].[BY_Import_Sales_Json_Draft] "
                "@RowsJson=%s, @DryRun=%s, @SchemaConfirmed=%s",
                [payload, 1, 1],
            )
            result = cursor.fetchone()
    except DatabaseError as exc:
        raise BYDryRunError("Не удалось выполнить предварительную проверку продаж Беларуси.") from exc

    if result is None:
        raise BYDryRunError("SQL-процедура не вернула результат предварительной проверки.")
    return BYDryRunSummary(input_measure_rows=int(result[0]), proposed_sales_rows=int(result[1]))
