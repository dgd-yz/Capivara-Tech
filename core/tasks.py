import tempfile

from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django_tasks import task
from weasyprint import HTML

from core.email import build_text_mail, build_registration_mail
from core.email_tracking import send_tracked_email
from core.email_templates import render_registration_email
from core.models import DEFAULT_CONTACT_RECIPIENT, EmailSettings, Registration


@task()
def calculate_meaning_of_life() -> int:
    return 42


@task()
def calculate_complex_task() -> None:
    import time

    time.sleep(10)


@task()
def send_email(
    subject, message, sender_name, sender_email, to=None
):
    recipient = to or EmailSettings.get_solo().contact_recipient or DEFAULT_CONTACT_RECIPIENT
    email = build_text_mail(
        subject,
        f"Nome: {sender_name}\nEmail: {sender_email}\n\n{message}",
        [recipient],
        reply_to=[sender_email],
    )
    return send_tracked_email(email, "Contato / suporte")


@task()
def send_registration_email(registration_id, kind="received"):
    participant = Registration.objects.get(pk=registration_id)
    # Não anunciar uma confirmação que foi desfeita antes da execução da task.
    if kind == "confirmed" and not participant.confirmated:
        return {"status": "ignorado", "motivo": "Inscrição não está confirmada", "inscricao_id": registration_id}
    subject, body = render_registration_email(EmailSettings.get_solo(), participant, kind)
    message = build_registration_mail(subject, body, participant, kind)
    return send_tracked_email(message, "Inscrição confirmada" if kind == "confirmed" else "Inscrição recebida")


@task()
def generate_and_send_certification(context={}):
    import logging

    logger = logging.getLogger("weasyprint")
    logger.addHandler(logging.StreamHandler())

    email = context["participant"]["email"]
    html_string = render_to_string("core/certification.html", context)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as output:
        HTML(string=html_string).write_pdf(output.name)

        mail = EmailMessage(
            subject="Seu certificado de participação do V Seminário Piauiense de Agroecologia",
            body="Olá, segue em anexo o seu certificado de participação do V Seminário Piauiense de Agroecologia.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email],
        )
        mail.attach(f"certificado_{email}.pdf", output.read(), "application/pdf")
        mail.send(fail_silently=False)
