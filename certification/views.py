from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template import Context, Template
from django.template.loader import render_to_string
from django.utils.formats import date_format
from weasyprint import HTML

from .models import Certificate, CertificationSettings
from .rendering import certificate_url_fetcher, image_data_uri


def certificate_detail(request, uuid):
    certificate = get_object_or_404(Certificate, uuid=uuid)

    template = Template(certificate.text)

    text_rendered = template.render(
        context=Context(
            {
                "Nome_Participante": str(certificate.participant_name),
                "Atividade": str(certificate.activity),
                "Carga_Horaria": str(certificate.workload),
                "Local_de_Emissão": str(certificate.location),
                "Data_de_Emissão": date_format(certificate.date, "DATE_FORMAT"),
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
            "participant_name": certificate.participant_name,
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
