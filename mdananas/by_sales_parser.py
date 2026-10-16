from pathlib import Path
from tkinter import Tk, filedialog

import pandas as pd
import xlrd


def address_key(value):
    return " ".join(str(value).replace('"', "").split()).casefold()


def sku_key(value):
    return str(value).strip().strip('"').strip()


def choose_file(title, filetypes):
    path = filedialog.askopenfilename(title=title, filetypes=filetypes)
    if not path:
        raise SystemExit(f"Файл не выбран: {title}")
    return Path(path)


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


def main():
    root = Tk()
    root.withdraw()
    try:
        excel_path = choose_file("1/3: выбери сэмпер_август.xls", [("Excel XLS", "*.xls")])
        stores_path = choose_file("2/3: выбери by_stores_reference.csv", [("CSV", "*.csv")])
        sku_path = choose_file("3/3: выбери by_sku_cu.csv", [("CSV", "*.csv")])
    finally:
        root.destroy()

    df = pd.read_excel(excel_path, header=None, engine="xlrd")
    book = xlrd.open_workbook(str(excel_path), formatting_info=True)
    sheet = book.sheet_by_index(0)
    print("Размер Excel:", df.shape)

    if df.shape[0] <= 8 or df.shape[1] < 18:
        raise ValueError("Файл не похож на ожидаемый отчёт")

    sku_mask = pd.to_numeric(df.iloc[:, 5], errors="coerce").notna()
    sku_indices = set(df.index[sku_mask & (df.index >= 8)].tolist())
    print("Товарных строк:", len(sku_indices))
    if not sku_indices:
        raise ValueError("Не удалось найти товарные строки в Excel")

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
        raise ValueError("Не для всех товаров удалось найти покупателя и магазин")

    rows = []
    for i in sorted(sku_indices):
        buyer_row, store_row = locations[i]
        buyer = df.iat[buyer_row, 2]
        store = df.iat[store_row, 2]
        if pd.isna(buyer) or pd.isna(store):
            raise ValueError("Есть товар без названия покупателя или магазина")
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
            raise ValueError(f"Не удалось превратить в числа значения {field}: {lost}")
        out[field] = converted

    for month in range(3, 9):
        part = out[out["month"] == month]
        qty_diff = part["qty"].sum() - float(df.iat[6, 2 * month])
        amount_diff = part["amount"].sum() - float(df.iat[6, 2 * month + 1])
        print(f"Месяц {month}: разница кол-ва={qty_diff:.2f}, суммы={amount_diff:.2f}")
        if abs(qty_diff) > 0.01 or abs(amount_diff) > 0.01:
            raise ValueError(f"Итоги за месяц {month} не совпали")

    stores = read_stores_csv(stores_path)
    sku_ref = read_sku_csv(sku_path)
    store_to_id = dict(zip(stores["key"], stores["id"]))
    sku_to_id = dict(zip(sku_ref["material"], sku_ref["id"].astype(int)))
    out["by_store_id"] = out["store"].map(
        lambda value: store_to_id.get(address_key(value))
    )
    out["by_pivot_sku_id"] = out["sku"].map(sku_to_id)

    if out["by_store_id"].isna().any() or out["by_pivot_sku_id"].isna().any():
        raise ValueError("У некоторых продаж не найден ID магазина или товара")

    used_skus = sku_ref[sku_ref["material"].isin(out["sku"].unique())]
    linked = pd.to_numeric(
        used_skus["root_cu_id"].str.strip(' "'), errors="coerce"
    ).notna()

    print("Итоговых помесячных записей:", len(out))
    print("Уникальных SKU:", out["sku"].nunique())
    print("Уникальных магазинов:", out["by_store_id"].nunique())
    print("SKU со связью CU:", int(linked.sum()))
    print("SKU без связи CU:", int((~linked).sum()))

    output_path = excel_path.with_name(excel_path.stem + "_processed.xlsx")
    out.to_excel(output_path, index=False)
    print("Готовая таблица сохранена:", output_path)
    print("Готово: в SQL Server ничего не записывалось.")


if __name__ == "__main__":
    main()
