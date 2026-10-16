from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from django.urls import resolve, reverse

from export_service.forms.by_forms import BYSalesFileForm
from export_service.views.by_views import by_page
from tests.by_fixture import sales_xls


class BYPageTests(SimpleTestCase):
    def test_route_renders_page_and_menu_link(self):
        self.assertEqual(reverse("by_page"), "/export/by/")
        self.assertIs(resolve("/export/by/").func, by_page)

        response = self.client.get("/export/by/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Беларусь")
        self.assertContains(response, 'href="/export/by/"')
        self.assertContains(response, 'accept=".xls"')
        self.assertContains(response, "Выберите исходный файл .xls")

    def test_form_accepts_xls_and_rejects_other_extensions(self):
        xls = SimpleUploadedFile("sales.xls", b"placeholder")
        xlsx = SimpleUploadedFile("sales.xlsx", b"placeholder")
        self.assertTrue(BYSalesFileForm(files={"file": xls}).is_valid())
        self.assertFalse(BYSalesFileForm(files={"file": xlsx}).is_valid())

    def test_post_shows_reconciled_summary_without_loading_data(self):
        response = self.client.post(
            "/export/by/", {"file": SimpleUploadedFile("sales.xls", sales_xls())}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Файл обработан и проверен. Данные в SQL Server не загружены")
        self.assertContains(response, "<dd>12</dd>", html=True)
        self.assertContains(response, "<dd>2</dd>", count=2, html=True)
        self.assertContains(response, "март, апрель, май, июнь, июль, август")
        self.assertContains(response, "Итоги количества и суммы по всем месяцам совпали.")
        self.assertNotContains(response, "Покупатель Тест")

    def test_post_shows_mismatch_without_traceback_or_success(self):
        response = self.client.post(
            "/export/by/", {"file": SimpleUploadedFile("sales.xls", sales_xls(wrong_total=True))}
        )
        self.assertContains(response, "Итоги за месяц 3 не совпали.")
        self.assertNotContains(response, "Файл обработан и проверен")
        self.assertNotContains(response, "Traceback")

    def test_post_shows_invalid_xls_error(self):
        response = self.client.post(
            "/export/by/", {"file": SimpleUploadedFile("sales.xls", b"invalid")}
        )
        self.assertContains(response, "Не удалось прочитать файл .xls")
        self.assertNotContains(response, "Traceback")

    def test_invalid_file_shows_validation_error(self):
        response = self.client.post(
            "/export/by/", {"file": SimpleUploadedFile("sales.xlsx", b"placeholder")}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Выберите файл Excel с расширением .xls.")
        self.assertNotContains(response, "Файл обработан и проверен")

    def test_missing_file_shows_validation_error(self):
        response = self.client.post("/export/by/")
        self.assertContains(response, "Выберите файл .xls.")
        self.assertNotContains(response, "Файл обработан и проверен")
