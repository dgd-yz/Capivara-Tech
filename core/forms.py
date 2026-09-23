from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from core.models import Registration, get_workshops_choices


class RegistrationForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["workshop"].choices = get_workshops_choices()
        self.fields["workshop"].help_text = (
            "Escolha um dos minicursos disponíveis. "
            "Atenção: o Django Girls é exclusivo para mulheres."
        )

    class Meta:
        model = Registration
        fields = "__all__"
        exclude = ("confirmated", "organization")
        widgets = {"workshop": forms.RadioSelect}


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
