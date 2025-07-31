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

    search_fields = (
        "full_name",
        "entity",
    )

    actions = [
        "confirm_registration",
        "send_certification_email",
        # "generate_certification",
        # "generate_and_send_certification",
    ]

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

    @admin.action(description="Enviar E-mail de Certificado")
    def send_certification_email(self, request, queryset):
        updated = queryset.update(confirmated=True)

        proto = request.scheme

        current_site = get_current_site(request)
        logo_path = static("images/logo_horizontal_seminario_agroecologia_small.jpg")

        participants = queryset.all()
        for participant in participants:
            send_template_mail.enqueue(
                "certification",
                subject="V SPA - Certificados Disponíveis",
                to=str(participant.email),
                from_email=None,
                context={
                    "participant": model_to_dict(participant),
                    "uuid": str(participant.uuid),
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

    # @admin.action(description="Visualizar Certificado")
    # def generate_certification(self, request, queryset):
    #     confirmed = queryset.filter(confirmated=True)

    #     proto = request.scheme
    #     current_site = get_current_site(request)
    #     logo_path = static("images/logo_horizontal_seminario_agroecologia_small.jpg")

    #     if confirmed:
    #         return render(
    #             request,
    #             "core/certification.html",
    #             {
    #                 "participant": confirmed[0],
    #                 "logo_path": f"{proto}://{current_site}{logo_path}",
    #             },
    #         )
    #     return redirect(reverse("admin:core_registration_changelist"))

    # @admin.action(description="Gerar e Enviar Certificado pela Fila")
    # def generate_and_send_certification(self, request, queryset):
    #     proto = request.scheme
    #     # current_site = get_current_site(request)
    #     current_site = "host.docker.internal:8000"
    #     logo_path = static("images/logo_horizontal_seminario_agroecologia_small.jpg")

    #     confirmed = queryset.filter(confirmated=True)

    #     number_of_participants = 0
    #     participants = confirmed.all()
    #     for participant in participants:
    #         generate_and_send_certification.enqueue(
    #             context={
    #                 "participant": model_to_dict(participant),
    #                 "logo_path": f"{proto}://{current_site}{logo_path}",
    #             },
    #         )
    #         number_of_participants += 1

    #     self.message_user(
    #         request,
    #         ngettext(
    #             "%d Certificado foi para fila de geração e envio.",
    #             "%d Certificados foram para fila de geração e envio.",
    #             number_of_participants,
    #         )
    #         % number_of_participants,
    #         messages.SUCCESS,
    #     )
