from django import forms
from django.core.validators import FileExtensionValidator


class BYSalesFileForm(forms.Form):
    file = forms.FileField(
        label="Исходный Excel (.xls)",
        error_messages={"required": "Выберите файл .xls."},
        validators=[FileExtensionValidator(["xls"], message="Выберите файл Excel с расширением .xls.")],
        widget=forms.ClearableFileInput(attrs={"accept": ".xls"}),
    )
