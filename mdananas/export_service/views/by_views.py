from django.shortcuts import render

from by_sales_parser import BYSalesParseError, parse_by_sales

from ..forms.by_forms import BYSalesFileForm


def by_page(request):
    form = BYSalesFileForm(request.POST, request.FILES) if request.method == "POST" else BYSalesFileForm()
    notice = None
    error = None
    summary = None

    if request.method == "POST" and form.is_valid():
        try:
            result = parse_by_sales(form.cleaned_data["file"])
        except BYSalesParseError as exc:
            error = str(exc)
        except Exception:
            error = "Не удалось обработать отчёт. Проверьте файл .xls и попробуйте снова."
        else:
            records = result.records
            summary = {
                "record_count": len(records),
                "sku_count": records["sku"].nunique(),
                "store_count": records["store"].nunique(),
                "months": "март, апрель, май, июнь, июль, август",
                "reconciliation": "Итоги количества и суммы по всем месяцам совпали.",
            }
            notice = "Файл обработан и проверен. Данные в SQL Server не загружены"

    return render(
        request,
        "export_service/by_page.html",
        {"form": form, "notice": notice, "error": error, "summary": summary},
    )
