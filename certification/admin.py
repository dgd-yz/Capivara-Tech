from gettext import ngettext
from typing import Any

from django.contrib import admin, messages
from django.contrib.sites.shortcuts import get_current_site
from django.forms.models import ModelForm
from django.http import HttpRequest
from django.utils.html import mark_safe
from solo.admin import SingletonModelAdmin

from certification.email import send_certificate_mail
from core.event_config import get_event_config

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

    readonly_fields = ("date",)

    @admin.display(description="Ver Certificado")
    def view_button(self, obj):
        url = obj.get_absolute_url()
        return mark_safe(f"<a href='{url}' class='button'>Certificado</a>")

    @admin.action(description="Enviar E-mail para acessar o Certificado")
    def send_certificate_email(self, request, queryset):
        site_url = f"{request.scheme}://{get_current_site(request).domain}"
        certificates = list(queryset)
        for certificate in certificates:
            send_certificate_mail.enqueue(certificate.pk, site_url)

        total = len(certificates)
        self.message_user(
            request,
            ngettext(
                "%d e-mail de certificado colocado na fila de envio.",
                "%d e-mails de certificado colocados na fila de envio.",
                total,
            )
            % total,
            messages.SUCCESS,
        )

    def get_form(
        self,
        request: HttpRequest,
        obj: Any | None = None,
        change: bool = False,
        **kwargs: Any,
    ) -> type[ModelForm]:
        form = super().get_form(request, obj, change, **kwargs)
        if obj is not None:
            return form
        certification_settings = CertificationSettings.get_solo()
        bf = form.base_fields
        bf["workload"].initial = get_event_config()["workload"]
        bf["location"].initial = certification_settings.default_location
        bf["certifier_name"].initial = certification_settings.default_certifier_name
        bf[
            "certifier_position"
        ].initial = certification_settings.default_certifier_position
        bf["text"].initial = certification_settings.default_text
        bf["background_image"].initial = certification_settings.default_background_image
        return form
