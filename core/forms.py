from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from core.models import (
    Registration,
    Workshops,
    get_all_workshops_choices,
    get_workshops_choices,
)


class RegistrationForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["workshop"] = forms.ChoiceField(
            label=self.fields["workshop"].label,
            choices=get_workshops_choices(),
            initial=Workshops.NONE,
            widget=forms.RadioSelect,
            help_text=(
                "Escolha um dos minicursos disponíveis. "
                "Atenção: o Django Girls é exclusivo para mulheres."
            ),
        )

    class Meta:
        model = Registration
        fields = "__all__"
        exclude = ("confirmated", "organization")


class RegistrationAdminForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["workshop"] = forms.ChoiceField(
            label=self.fields["workshop"].label,
            choices=get_all_workshops_choices(),
            initial=Workshops.NONE,
        )

    class Meta:
        model = Registration
        fields = "__all__"


class UserCreationForm(UserCreationForm):
    class Meta:
        model = get_user_model()
        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
            "password1",
            "password2",
        )


class ContactForm(forms.Form):
    sender_name = forms.CharField(max_length=255, label="Nome")

    sender_email = forms.EmailField(max_length=1024, label="E-mail")

    subject = forms.CharField(max_length=255, label="Assunto")

    message = forms.CharField(
        max_length=1024 * 10, label="Mensagem", widget=forms.Textarea
    )


class CertificatesForm(forms.Form):
    email = forms.EmailField(max_length=1024, label="E-mail")
