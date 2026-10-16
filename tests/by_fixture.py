from io import BytesIO

import xlwt


def sales_xls(*, wrong_total=False, missing_store=False, missing_total=False):
    """Small artificial BIFF .xls report with buyer/store/SKU outline levels."""
    book = xlwt.Workbook()
    sheet = book.add_sheet("Sales")
    sheet.write(7, 2, "Покупатель Тест")
    sheet.row(7).level = 1
    sheet.write(8, 2, "Магазин Один")
    sheet.row(8).level = 2
    sheet.row(9).level = 3
    sheet.write(9, 5, 1001)
    sheet.write(10, 2, "Магазин Два")
    sheet.row(10).level = 1 if missing_store else 2
    sheet.row(11).level = 3
    sheet.write(11, 5, 1002)

    for month in range(3, 9):
        qty_col = 2 * month
        amount_col = qty_col + 1
        if not (missing_total and month == 3):
            sheet.write(6, qty_col, 4 if wrong_total and month == 3 else 3)
        sheet.write(6, amount_col, 30)
        sheet.write(9, qty_col, 1)
        sheet.write(9, amount_col, 10)
        sheet.write(11, qty_col, 2)
        sheet.write(11, amount_col, 20)

    output = BytesIO()
    book.save(output)
    return output.getvalue()
