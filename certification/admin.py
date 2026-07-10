from gettext import ngettext
from typing import Any

from django.contrib import admin, messages
from django.contrib.sites.shortcuts import get_current_site
from django.forms.models import ModelForm
from django.http import HttpRequest
from django.templatetags.static import static
from django.utils.html import mark_safe
from solo.admin import SingletonModelAdmin

from certification.email import send_template_mail

from .models import Certificate, CertificationSettings

admin.site.register(CertificationSettings, SingletonModelAdmin)


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = (
        "participant_name",
        "activity",
        "workload",
        "view_button",
    )

    list_filter = ("activity",)

    search_fields = (
        "participant_name",
        "activity",
    )

    actions = ("send_certificate_email",)

    @admin.display(description="Ver Certificado")
    def view_button(self, obj):
        url = obj.get_absolute_url()
        return mark_safe(f"<a href='{url}' class='button'>Certificado</a>")

    @admin.action(description="Enviar E-mail para acessar o Certificado")
    def send_certificate_email(self, request, queryset):
        proto = request.scheme
        current_site = get_current_site(request)
        logo_path = static("images/capivara-logo.svg")

        certificates_size = len(queryset)
        certificates = queryset.all()
        for certificate in certificates:
            send_template_mail.enqueue(
                "certification",
                subject="Capivara Tech II - Certificados Disponíveis",
                to=str(certificate.participant_email),
                from_email=None,
                context={
                    "participant_name": certificate.participant_name,
                    "uuid": str(certificate.uuid),
                    "logo_path": logo_path,
                    "domain": current_site.domain,
                    "proto": proto,
                },
            )

        self.message_user(
            request,
            ngettext(
                "%d Certificado Gerado com Sucesso",
                "%d Certificados Gerados com Sucesso",
                certificates_size,
            )
            % certificates_size,
            messages.SUCCESS,
        )

    def get_form(
        self,
        request: HttpRequest,
        obj: Any | None = ...,
        change: bool = ...,
        **kwargs: Any,
    ) -> type[ModelForm]:
        form = super().get_form(request, obj, change, **kwargs)
        certification_settings = CertificationSettings.objects.get()
        bf = form.base_fields
        bf["workload"].initial = 1
        bf["location"].initial = certification_settings.default_location
        bf["date"].initial = certification_settings.default_date
        bf["certifier_name"].initial = certification_settings.default_certifier_name
        bf[
            "certifier_position"
        ].initial = certification_settings.default_certifier_position
        bf["text"].initial = certification_settings.default_text
        return form
