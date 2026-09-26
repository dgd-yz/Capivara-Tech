from django.contrib import admin, messages
from django.db import transaction
from django.db.models import Q
from django.utils.html import mark_safe
from django.utils.translation import ngettext

from solo.admin import SingletonModelAdmin

from certification.domain import certificate_create
from core.models import EmailSettings, Image, Registration, Workshops
from core.tasks import send_registration_email


@admin.register(EmailSettings)
class EmailSettingsAdmin(SingletonModelAdmin):
    fieldsets = (
        ("Formulário de contato", {"fields": ("contact_recipient",)}),
        ("Ao realizar a inscrição", {"fields": ("received_subject", "received_body")}),
        ("Ao confirmar no admin", {"fields": ("confirmed_subject", "confirmed_body")}),
    )


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
        "resend_registration_email",
        "create_certificate",
        "create_certificate_workshop",
    ]

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
