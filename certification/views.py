from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template import Context, Template
from django.template.loader import render_to_string
from django.utils.formats import date_format
from weasyprint import HTML

from core.event_config import get_event_config

from .models import Certificate, CertificationSettings
from .rendering import certificate_url_fetcher, image_data_uri


def issue_date(value):
    """Ex.: 13 de novembro de 2026 (mês em minúsculas, como pede a norma culta)."""
    return f"{value.day} de {date_format(value, 'F').lower()} de {value.year}"


def activity_kind(activity, event_name):
    """Complemento usado em "participou ___ <atividade>"."""
    from core.models import Workshop

    if activity == event_name:
        return "do evento"
    if Workshop.objects.filter(name=activity).exists():
        return "do minicurso"
    return "da atividade"


def name_size(name):
    """Tamanho do nome (pt) para que nomes longos caibam em até duas linhas."""
    length = len(name)
    if length <= 26:
        return 36
    if length <= 36:
        return 31
    if length <= 46:
        return 26
    return 22


def certificate_detail(request, uuid):
    certificate = get_object_or_404(Certificate, uuid=uuid)
    event = get_event_config()
    issued_on = issue_date(certificate.date)

    template = Template(certificate.text)

    text_rendered = template.render(
        context=Context(
            {
                "Nome_Participante": str(certificate.participant_name),
                "Tipo_Atividade": activity_kind(certificate.activity, event["name"]),
                "Atividade": str(certificate.activity),
                "Carga_Horaria": str(certificate.workload),
                "Local_de_Emissão": str(certificate.location),
                "Data_de_Emissão": issued_on,
                "Nome_Certificador": str(certificate.certifier_name),
                "Cargo_Certificador": str(certificate.certifier_position),
            }
        )
    )

    certification_settings = CertificationSettings.get_solo()

    html_string = render_to_string(
        "certification/certification.html",
        {
            "background_url": image_data_uri(certificate.background_image or certification_settings.default_background_image),
            "layout": certification_settings,
            "certificate": certificate,
            "event": event,
            "issued_on": issued_on,
            "participant_name": certificate.participant_name,
            "name_size": name_size(certificate.participant_name),
            "text": text_rendered,
            "uri": request.build_absolute_uri(),
        },
    )

    base_url = request.build_absolute_uri("/")
    html = HTML(string=html_string, base_url=base_url, url_fetcher=certificate_url_fetcher(base_url))

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = "inline; filename=certificado.pdf"

    result = html.write_pdf()
    response.write(result)
    return response
