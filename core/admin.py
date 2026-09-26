from django.contrib import admin, messages
from django.contrib.admin.views.main import IncorrectLookupParameters
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.urls import path
from django.utils import timezone
from django.utils.html import format_html, mark_safe
from django.utils.translation import ngettext

from solo.admin import SingletonModelAdmin

from certification.domain import certificate_create
from core.attendance import build_attendance_pdf, workshop_activity
from core.forms import RegistrationAdminForm
from core.event_config import get_event_config
from core.models import (
    EmailSettings,
    EventDay,
    Image,
    Registration,
    ScheduleItem,
    Speaker,
    Workshop,
    Workshops,
    get_all_workshops_choices,
)
from core.tasks import send_registration_email


class WorkshopFilter(admin.SimpleListFilter):
    title = "Minicurso"
    parameter_name = "workshop__exact"

    def lookups(self, request, model_admin):
        return get_all_workshops_choices()

    def queryset(self, request, queryset):
        if self.value() is None:
            return queryset
        return queryset.filter(workshop=self.value())


@admin.register(EmailSettings)
class EmailSettingsAdmin(SingletonModelAdmin):
    fieldsets = (
        ("Formulário de contato", {"fields": ("contact_recipient",)}),
        ("Ao realizar a inscrição", {"fields": ("received_subject", "received_body")}),
        ("Ao confirmar no admin", {"fields": ("confirmed_subject", "confirmed_body")}),
    )


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    form = RegistrationAdminForm

    list_display = (
        "full_name",
        "created_at",
        "confirmated",
    )

    list_filter = (
        "confirmated",
        "activity",
        WorkshopFilter,
        "organization",
    )

    search_fields = (
        "full_name",
        "entity",
    )

    actions = [
        "confirm_registration",
        "resend_registration_email",
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

    def save_model(self, request, obj, form, change):
        with transaction.atomic():
            was_confirmed = change and Registration.objects.filter(
                pk=obj.pk, confirmated=True
            ).exists()
            super().save_model(request, obj, form, change)
            if obj.confirmated and not was_confirmed:
                send_registration_email.enqueue(obj.pk, "confirmed")

    @admin.action(description="Confirmar Inscrição")
    def confirm_registration(self, request, queryset):
        with transaction.atomic():
            participants = list(queryset.select_for_update().filter(confirmated=False))
            updated = len(participants)
            Registration.objects.filter(pk__in=[p.pk for p in participants]).update(confirmated=True)
            for participant in participants:
                send_registration_email.enqueue(participant.pk, "confirmed")

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

    @admin.action(description="Reenviar email de inscrição (conforme status atual)")
    def resend_registration_email(self, request, queryset):
        with transaction.atomic():
            count = 0
            for participant in queryset:
                kind = "confirmed" if participant.confirmated else "received"
                send_registration_email.enqueue(participant.pk, kind)
                count += 1
        self.message_user(request, f"{count} email(s) colocado(s) na fila de envio.", messages.SUCCESS)

    @admin.action(description="Gerar Certificado de Particicação do Evento (Geral)")
    def create_certificate(self, request, queryset):
        event = get_event_config()
        qs = queryset.filter(confirmated=True)
        participants_size = len(qs)
        participants = qs.all()
        for participant in participants:
            participant_name = participant.full_name
            participant_email = participant.email
            activity = event["name"]
            workload = event["workload"]
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
            workload = Workshop.objects.get(code=participant.workshop).workload
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


@admin.register(Speaker)
class SpeakerAdmin(admin.ModelAdmin):
    list_display = ("photo_thumb", "name", "session_role", "order", "published")
    list_display_links = ("photo_thumb", "name")
    list_editable = ("order", "published")
    list_filter = ("published",)
    search_fields = ("name", "role", "session", "talk")
    readonly_fields = ("photo_preview",)
    fieldsets = (
        ("Identificação", {"fields": ("name", "session", "role", "talk")}),
        ("Perfil", {"fields": ("bio", "photo", "photo_preview")}),
        ("Exibição no site", {"fields": ("order", "published")}),
    )

    @admin.display(description="Foto")
    def photo_thumb(self, obj):
        if not obj.photo:
            return "—"
        return format_html(
            '<img src="{}" alt="" style="width:44px;height:44px;object-fit:cover;'
            'object-position:center top;border-radius:50%">',
            obj.photo.url,
        )

    @admin.display(description="Sessão e cargo")
    def session_role(self, obj):
        return obj.label

    @admin.display(description="Pré-visualização")
    def photo_preview(self, obj):
        if not obj.photo:
            return "Nenhuma foto enviada."
        return format_html(
            '<img src="{}" alt="" style="width:180px;height:180px;object-fit:cover;'
            'object-position:center top;border-radius:12px">',
            obj.photo.url,
        )


@admin.register(Workshop)
class WorkshopAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "instructors",
        "registered_count",
        "capacity",
        "order",
        "published",
    )
    list_display_links = ("code", "name")
    list_editable = ("capacity", "order", "published")
    search_fields = ("code", "name", "instructors")
    filter_horizontal = ("speakers",)

    def get_readonly_fields(self, request, obj=None):
        return ("code",) if obj else ()

    def has_delete_permission(self, request, obj=None):
        # inscrições guardam só o código: com inscritos, apagar deixaria essas
        # pessoas sem minicurso (para tirar do ar, desmarque "Exibir no site")
        if obj is not None and obj.registered:
            return False
        return super().has_delete_permission(request, obj)

    @admin.display(description="Inscritos")
    def registered_count(self, obj):
        return obj.registered


class ScheduleItemInline(admin.TabularInline):
    model = ScheduleItem
    extra = 1
    fields = ("start_time", "end_time", "title", "subtitle", "tag", "order", "published")


@admin.register(EventDay)
class EventDayAdmin(admin.ModelAdmin):
    list_display = ("date", "subtitle", "item_count", "published")
    list_display_links = ("date", "subtitle")
    list_editable = ("published",)
    inlines = [ScheduleItemInline]

    @admin.display(description="Itens")
    def item_count(self, obj):
        return obj.items.count()
