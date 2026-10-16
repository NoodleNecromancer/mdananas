from django.shortcuts import render

from ..forms.by_forms import BYSalesFileForm


def by_page(request):
    form = BYSalesFileForm(request.POST or None, request.FILES or None)
    notice = None

    if request.method == "POST" and form.is_valid():
        notice = "Файл выбран. Обработка файла и запись в базу будут подключены на следующем этапе. Данные пока не загружены."

    return render(request, "export_service/by_page.html", {"form": form, "notice": notice})
