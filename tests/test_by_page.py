from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from django.urls import resolve, reverse

from export_service.forms.by_forms import BYSalesFileForm
from export_service.views.by_views import by_page


class BYPageTests(SimpleTestCase):
    def test_route_renders_page_and_menu_link(self):
        self.assertEqual(reverse("by_page"), "/export/by/")
        self.assertIs(resolve("/export/by/").func, by_page)

        response = self.client.get("/export/by/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Беларусь")
        self.assertContains(response, 'href="/export/by/"')
        self.assertContains(response, 'accept=".xls"')
        self.assertContains(response, "Сейчас отправка файла не загружает данные.")

    def test_form_accepts_xls_and_rejects_other_extensions(self):
        xls = SimpleUploadedFile("sales.xls", b"placeholder")
        xlsx = SimpleUploadedFile("sales.xlsx", b"placeholder")
        self.assertTrue(BYSalesFileForm(files={"file": xls}).is_valid())
        self.assertFalse(BYSalesFileForm(files={"file": xlsx}).is_valid())

    def test_post_does_not_claim_data_was_loaded(self):
        response = self.client.post(
            "/export/by/", {"file": SimpleUploadedFile("sales.xls", b"placeholder")}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Данные пока не загружены.")
        self.assertNotContains(response, 'status": "success')

    def test_invalid_file_shows_validation_error(self):
        response = self.client.post(
            "/export/by/", {"file": SimpleUploadedFile("sales.xlsx", b"placeholder")}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Выберите файл Excel с расширением .xls.")
        self.assertNotContains(response, "Данные пока не загружены.")
