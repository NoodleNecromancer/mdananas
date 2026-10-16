from django import forms
from django.core.validators import FileExtensionValidator


class BYSalesFileForm(forms.Form):
    file = forms.FileField(
        label="Исходный Excel (.xls)",
        error_messages={"required": "Выберите файл .xls."},
        validators=[FileExtensionValidator(["xls"], message="Выберите файл Excel с расширением .xls.")],
        widget=forms.ClearableFileInput(attrs={"accept": ".xls"}),
    )
    year = forms.IntegerField(
        label="Год отчёта для проверки в SQL",
        required=False,
        min_value=1,
        max_value=9999,
        widget=forms.NumberInput(attrs={"min": 1, "max": 9999}),
    )

    def clean(self):
        cleaned_data = super().clean()
        if self.data.get("action") == "sql_preview" and cleaned_data.get("year") is None:
            self.add_error("year", "Укажите год отчёта для предварительной проверки в SQL.")
        return cleaned_data
