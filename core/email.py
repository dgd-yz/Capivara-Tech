from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django_tasks import task
from email import policy
from django.contrib.staticfiles import finders

from core.email_tracking import send_tracked_email


class RegistrationEmail(EmailMultiAlternatives):
    banner_content = None

    def message(self, *, policy=policy.default):
        message = super().message(policy=policy)
        if self.banner_content:
            html_part = message.get_body(preferencelist=("html",))
            html_part.add_related(self.banner_content, maintype="image", subtype="png", cid="<registration-banner>", disposition="inline", filename="banner-email.png")
        return message


def build_registration_mail(subject, body, participant, kind):
    from core.event_config import get_event_config

    event = get_event_config()
    context = {"event": event, "participant": participant, "body": body, "confirmed": kind == "confirmed"}
    text_body = render_to_string("emails/registration_card.txt", context)
    message = RegistrationEmail(subject, text_body, settings.DEFAULT_FROM_EMAIL, [participant.email], reply_to=[event["contact_email"]])
    message.attach_alternative(render_to_string("emails/registration_card.html", {
        "event": event, "participant": participant, "body": body,
        "confirmed": kind == "confirmed",
    }), "text/html")
    path = finders.find("images/banner-email.png")
    with open(path, "rb") as banner:
        message.banner_content = banner.read()
    return message


def build_text_mail(subject, body, to, reply_to=None):
    """Preserva o texto original e oferece HTML equivalente, sem imagens."""
    message = EmailMultiAlternatives(
        subject, body, settings.DEFAULT_FROM_EMAIL, to, reply_to=reply_to,
    )
    message.attach_alternative(
        render_to_string("emails/text_message.html", {"body": body}),
        "text/html",
    )
    return message


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
    return send_tracked_email(msg, f"Modelo: {template_name}")
