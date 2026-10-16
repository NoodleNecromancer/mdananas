from django.conf import settings
from django.shortcuts import render

from by_sales_parser import BYSalesParseError, parse_by_sales

from ..by_sql_service import BYDryRunError, preview_by_sales_import
from ..forms.by_forms import BYSalesFileForm


def by_page(request):
    form = BYSalesFileForm(request.POST, request.FILES) if request.method == "POST" else BYSalesFileForm()
    notice = None
    error = None
    summary = None
    sql_preview = None

    if request.method == "POST" and form.is_valid():
        action = request.POST.get("action", "parse")
        if action not in ("parse", "sql_preview"):
            error = "Неизвестное действие. Выберите проверку файла или предварительную проверку в SQL."
        elif action == "sql_preview" and not getattr(settings, "BY_SQL_DRY_RUN_ENABLED", False):
            error = "Предварительная проверка в SQL отключена."
        elif action == "sql_preview" and not getattr(settings, "BY_SQL_SCHEMA_CONFIRMED", False):
            error = "Схема SQL для предварительной проверки ещё не подтверждена."
        else:
            try:
                result = parse_by_sales(form.cleaned_data["file"])
                if action == "sql_preview":
                    sql_preview = preview_by_sales_import(result.records, year=form.cleaned_data["year"])
            except BYSalesParseError as exc:
                error = str(exc)
            except BYDryRunError:
                error = "Предварительная проверка в SQL не выполнена. Проверьте настройки и данные отчёта."
            except Exception:
                error = "Не удалось обработать отчёт или выполнить предварительную проверку. Проверьте файл и попробуйте снова."
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
        {"form": form, "notice": notice, "error": error, "summary": summary, "sql_preview": sql_preview},
    )
