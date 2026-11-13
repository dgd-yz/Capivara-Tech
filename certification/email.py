from email import policy

from django.conf import settings
from django.contrib.staticfiles import finders
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse
from django_tasks import task
from core.email_tracking import send_tracked_email

LOGO_CID = "certificate-logo"
LOGO_STATIC = "images/capivara-logo-email.png"


@task
def send_template_mail(template_name, subject="", to=[], from_email=None, context={}):
    text_content = render_to_string(
        f"emails/{template_name}.txt",
        context=context,
    )

    html_content = render_to_string(
        f"emails/{template_name}.html",
        context=context,
    )

    if not isinstance(to, (list, tuple)):
        to = (to,)

    msg = EmailMultiAlternatives(
        subject,
        text_content,
        from_email or settings.DEFAULT_FROM_EMAIL,
        to,
    )

    msg.attach_alternative(html_content, "text/html")
    return send_tracked_email(msg, "Certificado")


class CertificateEmail(EmailMultiAlternatives):
    """E-mail com o logo embutido (cid), que aparece mesmo quando o leitor bloqueia imagens externas."""

    logo_content = None

    def message(self, *, policy=policy.default):
        message = super().message(policy=policy)
        if self.logo_content:
            html_part = message.get_body(preferencelist=("html",))
            html_part.add_related(
                self.logo_content, maintype="image", subtype="png", cid=f"<{LOGO_CID}>",
                disposition="inline", filename="capivara-tech.png",
            )
        return message


def certificate_email_context(certificate, site_url):
    from core.event_config import get_event_config

    from .views import activity_kind, issue_date

    event = get_event_config()
    kind = activity_kind(certificate.activity, event["name"])
    activity_label = {
        "do evento": certificate.activity,
        "do minicurso": f"Minicurso {certificate.activity}",
    }.get(kind, certificate.activity)
    return {
        "event": event,
        "certificate": certificate,
        "first_name": certificate.participant_name.split()[0] if certificate.participant_name else "",
        "kind": kind,
        "activity_label": activity_label,
        "issued_on": issue_date(certificate.date),
        "certificate_url": site_url.rstrip("/") + reverse("certificate_detail", kwargs={"uuid": certificate.uuid}),
        "site_url": site_url.rstrip("/") + "/",
        "logo_cid": LOGO_CID,
    }


def build_certificate_mail(certificate, site_url):
    context = certificate_email_context(certificate, site_url)
    event = context["event"]
    subject = f"{event['name']}: seu certificado está disponível"
    if context["kind"] == "do minicurso":
        subject = f"{event['name']}: seu certificado do minicurso {certificate.activity} está disponível"
    message = CertificateEmail(
        subject,
        render_to_string("emails/certification.txt", context),
        settings.DEFAULT_FROM_EMAIL,
        [certificate.participant_email],
        reply_to=[event["contact_email"]] if event.get("contact_email") else None,
    )
    message.attach_alternative(render_to_string("emails/certification.html", context), "text/html")
    with open(finders.find(LOGO_STATIC), "rb") as logo:
        message.logo_content = logo.read()
    return message


@task
def send_certificate_mail(certificate_pk, site_url):
    from .models import Certificate

    certificate = Certificate.objects.filter(pk=certificate_pk).first()
    if certificate is None:  # apagado depois de entrar na fila
        return None
    return send_tracked_email(build_certificate_mail(certificate, site_url), "Certificado")
