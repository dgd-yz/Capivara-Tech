from django.contrib import admin, messages
from django.contrib.sites.shortcuts import get_current_site
from django.forms.models import model_to_dict
from django.templatetags.static import static
from django.utils.translation import ngettext

from core.email import send_template_mail
from core.models import Registration


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
    )

    actions = ["confirm_registration"]

    @admin.action(description="Confirmar Inscrição")
    def confirm_registration(self, request, queryset):
        updated = queryset.update(confirmated=True)

        current_site = get_current_site(request)
        logo_url = f"https://{current_site.domain}{static('images/logo_horizontal_seminario_agroecologia_small.jpg')}"

        participants = queryset.all()
        for participant in participants:
            send_template_mail.enqueue(
                "registration",
                subject="V SPA - Inscrição Confirmada",
                to=str(participant.email),
                from_email=None,
                context={
                    "participant": model_to_dict(participant),
                    "logo_url": logo_url,
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
