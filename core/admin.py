from django.contrib import admin, messages
from django.forms.models import model_to_dict
from django.utils.translation import ngettext

from core.email import send_template_mail
from core.models import Registration


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = ("full_name", "created_at")
    list_filter = ("confirmated", "activity", "workshop")

    actions = ["confirm_registration"]

    @admin.action(description="Confirmar Inscrição")
    def confirm_registration(self, request, queryset):
        updated = queryset.update(confirmated=True)

        participants = queryset.all()
        for participant in participants:
            send_template_mail.enqueue(
                "registration",
                subject="V SPA - Inscrição Confirmada",
                to=str(participant.email),
                from_email=None,
                context={"participant": model_to_dict(participant)},
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
