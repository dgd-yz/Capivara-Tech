from django.contrib import admin, messages
from django.contrib.admin.views.main import IncorrectLookupParameters
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.forms.models import model_to_dict
from django.http import HttpResponse
from django.templatetags.static import static
from django.urls import path
from django.utils import timezone
from django.utils.html import mark_safe
from django.utils.translation import ngettext

from certification.domain import certificate_create
from core.attendance import build_attendance_pdf, workshop_activity
from core.email import send_template_mail
from core.models import Image, Registration, Workshops


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "created_at",
        "confirmated",
    )

    list_filter = (
        "confirmated",
        "activity",
        "workshop",
        "organization",
    )

    search_fields = (
        "full_name",
        "entity",
    )

    actions = [
        "confirm_registration",
        "create_certificate",
        "create_certificate_workshop",
    ]

    change_list_template = "admin/core/registration/change_list.html"

    def get_urls(self):
        custom_urls = [
            path(
                "lista-de-frequencia/",
                self.admin_site.admin_view(self.attendance_list_view),
                name="core_registration_attendance",
            ),
        ]
        return custom_urls + super().get_urls()

    def attendance_list_view(self, request):
        """PDF de lista de frequência com as inscrições confirmadas da listagem (respeita filtros e busca)."""
        if not self.has_view_permission(request):
            raise PermissionDenied

        try:
            registrations = self.get_changelist_instance(request).get_queryset(request)
        except IncorrectLookupParameters:
            registrations = self.get_queryset(request)
        registrations = registrations.filter(confirmated=True)

        activity = workshop_activity(request.GET.get("workshop__exact", ""))
        pdf = build_attendance_pdf(registrations, activity=activity)

        filename = f"lista-de-frequencia-{timezone.localdate():%Y-%m-%d}.pdf"
        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="{filename}"'
        return response

    @admin.action(description="Confirmar Inscrição")
    def confirm_registration(self, request, queryset):
        updated = queryset.update(confirmated=True)

        proto = request.scheme

        current_site = get_current_site(request)
        logo_path = static("images/logo_horizontal_seminario_agroecologia_small.jpg")

        participants = queryset.all()
        for participant in participants:
            send_template_mail.enqueue(
                "registration",
                subject="V SPA - Inscrição Confirmada",
                to=str(participant.email),
                from_email=None,
                context={
                    "participant": model_to_dict(participant),
                    "logo_path": logo_path,
                    "domain": current_site.domain,
                    "proto": proto,
                },
            )

        self.message_user(
            request,
            ngettext(
                "%d Inscrição Confirmada com Sucesso",
                "%d Inscrições Confirmadas com Sucesso",
                updated,
            )
            % updated,
            messages.SUCCESS,
        )

    @admin.action(description="Gerar Certificado de Particicação do Evento (Geral)")
    def create_certificate(self, request, queryset):
        qs = queryset.filter(confirmated=True, workshop=Workshops.NONE)
        participants_size = len(qs)
        participants = qs.all()
        for participant in participants:
            participant_name = participant.full_name
            participant_email = participant.email
            activity = "V Seminário Piauiense de Agroecologia"
            workload = 24
            certificate_create(participant_name, participant_email, activity, workload)

        self.message_user(
            request,
            ngettext(
                "%d Certificado Gerado com Sucesso",
                "%d Certificados Gerados com Sucesso",
                participants_size,
            )
            % participants_size,
            messages.SUCCESS,
        )

    @admin.action(
        description="Gerar Certificado de Particicação nos Minicursos do Evento"
    )
    def create_certificate_workshop(self, request, queryset):
        qs = queryset.filter(~Q(workshop=Workshops.NONE), confirmated=True)
        participants_size = len(qs)
        participants = qs.all()
        for participant in participants:
            participant_name = participant.full_name
            participant_email = participant.email
            activity = participant.get_workshop_name()
            workload = 8
            certificate_create(participant_name, participant_email, activity, workload)

        self.message_user(
            request,
            ngettext(
                "%d Certificado Gerado com Sucesso",
                "%d Certificados Gerados com Sucesso",
                participants_size,
            )
            % participants_size,
            messages.SUCCESS,
        )


@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ("title",)
    search_fields = ("title",)
    readonly_fields = ("image_tag",)

    def image_tag(self, obj):
        return mark_safe(f"<img src='{obj.picture.url}' width='100%' />")

    image_tag.short_description = "Pré Visualização"
    image_tag.allow_tags = True
