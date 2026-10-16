from dataclasses import dataclass
from io import BytesIO
from math import isfinite
from typing import Protocol

import pandas as pd
import xlrd


class BYSalesParseError(ValueError):
    """The uploaded file is not a valid Belarus sales report."""


class BinaryReader(Protocol):
    def read(self) -> bytes: ...


@dataclass
class BYSalesParseResult:
    records: pd.DataFrame
    checked_months: tuple[int, ...]


def address_key(value):
    return " ".join(str(value).replace('"', "").split()).casefold()


def sku_key(value):
    return str(value).strip().strip('"').strip()


def read_stores_csv(path):
    rows = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        parts = line.split(";", 1)
        if len(parts) != 2:
            raise ValueError("В CSV магазинов не найден разделитель ';'")
        raw_id, raw_address = parts
        raw_id = raw_id.strip(' "')
        if raw_id.casefold() == "id":
            continue
        if not raw_id.isdecimal():
            raise ValueError("Некорректный ID магазина в CSV")
        rows.append((int(raw_id), raw_address.strip()))

    stores = pd.DataFrame(rows, columns=["id", "store_by"])
    if stores.empty:
        raise ValueError("Справочник магазинов пуст")

    stores["key"] = stores["store_by"].map(address_key)
    if not stores["key"].is_unique:
        raise ValueError("У разных магазинов одинаковый ключ адреса")
    if not stores["id"].is_unique:
        raise ValueError("В справочнике магазинов повторяются ID")
    return stores


def read_sku_csv(path):
    skus = pd.read_csv(
        path,
        sep=";",
        header=None,
        names=["id", "material", "root_cu_id"],
        dtype=str,
        encoding="utf-8-sig",
    )
    skus["id"] = pd.to_numeric(skus["id"].str.strip(' "'), errors="coerce")
    skus = skus.dropna(subset=["id", "material"]).copy()
    if skus.empty:
        raise ValueError("Справочник SKU пуст")

    skus["material"] = skus["material"].map(sku_key)
    if not skus["material"].is_unique:
        raise ValueError("В справочнике повторяются коды material")
    if not skus["id"].is_unique:
        raise ValueError("В справочнике товаров повторяются ID")
    return skus


def parse_by_sales(source: bytes | BinaryReader) -> BYSalesParseResult:
    """Parse and reconcile an uploaded .xls report without reference lookups or writes."""
    data = source if isinstance(source, bytes) else source.read()
    if not data:
        raise BYSalesParseError("Файл пуст. Выберите исходный отчёт .xls.")
    try:
        book = xlrd.open_workbook(file_contents=data, formatting_info=True)
        df = pd.read_excel(BytesIO(data), header=None, engine="xlrd")
        sheet = book.sheet_by_index(0)
    except (xlrd.XLRDError, ValueError, OSError, IndexError) as exc:
        raise BYSalesParseError("Не удалось прочитать файл .xls. Проверьте формат отчёта.") from exc

    if df.shape[0] <= 8 or df.shape[1] < 18:
        raise BYSalesParseError("Файл не похож на ожидаемый отчёт.")

    sku_mask = pd.to_numeric(df.iloc[:, 5], errors="coerce").notna()
    sku_indices = set(df.index[sku_mask & (df.index >= 8)].tolist())
    if not sku_indices:
        raise BYSalesParseError("Не удалось найти товарные строки в Excel.")

    parents = {}
    locations = {}
    for i in range(6, len(df)):
        info = sheet.rowinfo_map.get(i)
        if info is None:
            continue
        level = info.outline_level
        parents = {k: v for k, v in parents.items() if k < level}
        if i in sku_indices:
            locations[i] = (parents.get(level - 2), parents.get(level - 1))
        parents[level] = i

    if len(locations) != len(sku_indices) or any(
        buyer is None or store is None for buyer, store in locations.values()
    ):
        raise BYSalesParseError("Не для всех товаров удалось найти покупателя и магазин.")

    rows = []
    for i in sorted(sku_indices):
        buyer_row, store_row = locations[i]
        buyer = df.iat[buyer_row, 2]
        store = df.iat[store_row, 2]
        if pd.isna(buyer) or pd.isna(store):
            raise BYSalesParseError("Есть товар без названия покупателя или магазина.")
        for month in range(3, 9):
            qty = df.iat[i, 2 * month]
            amount = df.iat[i, 2 * month + 1]
            if pd.notna(qty) or pd.notna(amount):
                rows.append((buyer, store, sku_key(df.iat[i, 5]), month, qty, amount))

    out = pd.DataFrame(
        rows,
        columns=["buyer", "store", "sku", "month", "qty", "amount"],
    )
    for field in ("qty", "amount"):
        converted = pd.to_numeric(out[field], errors="coerce")
        lost = int((out[field].notna() & converted.isna()).sum())
        if lost:
            raise BYSalesParseError(f"Не удалось превратить в числа значения {field}: {lost}")
        out[field] = converted

    for month in range(3, 9):
        part = out[out["month"] == month]
        try:
            qty_diff = part["qty"].sum() - float(df.iat[6, 2 * month])
            amount_diff = part["amount"].sum() - float(df.iat[6, 2 * month + 1])
        except (TypeError, ValueError) as exc:
            raise BYSalesParseError(f"Некорректные итоги за месяц {month}.") from exc
        if not isfinite(qty_diff) or not isfinite(amount_diff):
            raise BYSalesParseError(f"Некорректные итоги за месяц {month}.")
        if abs(qty_diff) > 0.01 or abs(amount_diff) > 0.01:
            raise BYSalesParseError(f"Итоги за месяц {month} не совпали.")

    return BYSalesParseResult(records=out, checked_months=tuple(range(3, 9)))


def match_sales_references(records: pd.DataFrame, stores: pd.DataFrame, sku_ref: pd.DataFrame) -> pd.DataFrame:
    """Optional reference matching, kept separate from Excel parsing."""
    out = records.copy()
    store_to_id = dict(zip(stores["key"], stores["id"]))
    sku_to_id = dict(zip(sku_ref["material"], sku_ref["id"].astype(int)))
    out["by_store_id"] = out["store"].map(
        lambda value: store_to_id.get(address_key(value))
    )
    out["by_pivot_sku_id"] = out["sku"].map(sku_to_id)

    if out["by_store_id"].isna().any() or out["by_pivot_sku_id"].isna().any():
        raise ValueError("У некоторых продаж не найден ID магазина или товара")
    return out
