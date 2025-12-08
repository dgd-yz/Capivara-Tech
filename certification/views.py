from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template import Context, Template
from django.template.defaultfilters import date
from django.template.loader import render_to_string
from weasyprint import HTML

from .models import Certificate, CertificationSettings


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
                "Data_de_Emissão": str(date(certificate.date, "d \d\e F \d\e Y")),
                "Nome_Certificador": str(certificate.certifier_name),
                "Cargo_Certificador": str(certificate.certifier_position),
            }
        )
    )

    certification_settings = CertificationSettings.objects.get()

    html_string = render_to_string(
        "certification/certification.html",
        {
            "background": certification_settings.default_background_image,
            "text": text_rendered,
            "uri": request.build_absolute_uri(),
        },
    )

    html = HTML(string=html_string, base_url=request.build_absolute_uri())

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = "inline; filename=certificado.pdf"

    result = html.write_pdf()
    response.write(result)
    return response
