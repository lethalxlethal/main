from django import forms
from django.core.exceptions import ValidationError
import re

from users.models import NAME_ERROR, validate_user_name


class CodeForm(forms.Form):
    code = forms.CharField(max_length=4, label="Код")


class PhoneLoginForm(forms.Form):
    """Форма для входа: имя и номер телефона, без пароля и почты."""

    name = forms.CharField(
        label="Имя",
        max_length=15,
        widget=forms.TextInput(
            attrs={
                "class": "form-control form-control-lg",
                "placeholder": "Как к вам обращаться",
                "id": "name",
            }
        ),
    )
    phone = forms.CharField(
        label="Номер телефона",
        max_length=12,
        widget=forms.TextInput(
            attrs={
                "type": "tel",
                "class": "form-control form-control-lg",
                "placeholder": "+7 (999) 999-99-99",
                "id": "phone",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["phone"].help_text = (
            '- Номер должен начинаться с символа "+"<br>'
            '- Длина номера не должна превышать 12 символов (включая "+")<br>'
            "- Исключите все специальные символы (скобки, тире, пробелы)"
        )

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        try:
            validate_user_name(name)
        except ValidationError:
            raise forms.ValidationError(NAME_ERROR)
        return name

    def clean_phone(self):
        phone = self.cleaned_data["phone"]
        # Удаляем все не цифровые символы, кроме +
        cleaned_phone = "".join(char for char in phone if char.isdigit() or char == "+")
        if not cleaned_phone.startswith("+"):
            raise forms.ValidationError("Номер телефона должен начинаться с '+'")
        if len(cleaned_phone) > 12:
            raise forms.ValidationError(
                "Номер телефона не должен превышать 12 символов"
            )
        if not re.match(r"^\+7\d{10}$", cleaned_phone):
            raise forms.ValidationError(
                "Номер телефона должен быть в формате +7XXXXXXXXXX"
            )
        return cleaned_phone