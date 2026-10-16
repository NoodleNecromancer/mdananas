import json

import pandas as pd

from by_sales_parser import to_by_tmp_sales


def build_by_sales_json(records: pd.DataFrame, *, year: int, chain: str | None = None) -> str:
    """Build one in-memory JSON batch for a future Belarus SQL procedure call."""
    staging_rows = to_by_tmp_sales(records, year=year, chain=chain)
    try:
        return json.dumps(staging_rows.to_dict(orient="records"), ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError("Пакет продаж содержит недопустимое значение JSON.") from exc
