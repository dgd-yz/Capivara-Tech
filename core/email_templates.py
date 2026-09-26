from string import Template

from django.core.exceptions import ValidationError


def validate_email_template(value):
    template = Template(value)
    if not template.is_valid():
        raise ValidationError("Variável inválida. Use ${nome} ou $$ para um cifrão.")
    unknown = set(template.get_identifiers()) - {"nome", "email", "minicurso", "protocolo"}
    if unknown:
        raise ValidationError("Variáveis desconhecidas: %(names)s", params={"names": ", ".join(sorted(unknown))})


def validate_email_subject(value):
    validate_email_template(value)
    if "\n" in value or "\r" in value:
        raise ValidationError("O assunto deve ter apenas uma linha.")


def render_registration_email(configuration, participant, kind):
    if kind not in {"received", "confirmed"}:
        raise ValueError("Tipo de email de inscrição inválido")
    context = {
        "nome": participant.full_name,
        "email": participant.email,
        "minicurso": participant.get_workshop_display(),
        "protocolo": str(participant.uuid),
    }
    subject = Template(getattr(configuration, f"{kind}_subject")).substitute(context)
    body = Template(getattr(configuration, f"{kind}_body")).substitute(context)
    return " ".join(subject.splitlines()), body
