from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django_tasks import task


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
    msg.send()
