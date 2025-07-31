import tempfile
import uuid

from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django_tasks import task
from weasyprint import HTML


@task()
def calculate_meaning_of_life() -> int:
    return 42


@task()
def calculate_complex_task() -> None:
    import time

    time.sleep(10)


@task()
def send_email(
    subject, message, sender_name, sender_email, to=settings.DEFAULT_FROM_EMAIL
):
    email = EmailMessage(
        subject,
        message,
        f"{sender_name}<{sender_email}>",
        [to],
        reply_to=[sender_email],
        headers={"Message-ID": f"{uuid.uuid4()}"},
    )
    email.send(fail_silently=False)


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
