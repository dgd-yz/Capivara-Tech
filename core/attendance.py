import base64
import mimetypes
import unicodedata

from django.contrib.staticfiles import finders
from django.template.loader import render_to_string
from django.utils import timezone
from weasyprint import HTML

from core.models import Workshop, Workshops


def _sort_key(name):
    """Ordem alfabética ignorando acentos e maiúsculas (Ícaro fica junto do I)."""
    base = unicodedata.normalize("NFKD", name.strip().casefold())
    return base.encode("ascii", "ignore").decode()


def _static_data_uri(path):
    """Embute a imagem no HTML para o WeasyPrint não precisar buscar nada pela rede."""
    found = finders.find(path)
    if not found:
        return ""
    mime = mimetypes.guess_type(found)[0] or "application/octet-stream"
    with open(found, "rb") as f:
        return f"data:{mime};base64,{base64.b64encode(f.read()).decode()}"


def workshop_activity(value):
    """Nome de exibição do minicurso a partir do valor do filtro (ex.: '2' -> 'Teste de Software')."""
    if value == Workshops.NONE:
        return "Evento geral (sem minicurso)"
    return Workshop.objects.filter(code=value).values_list("name", flat=True).first() or ""


def build_attendance_pdf(registrations, activity=""):
    rows = sorted(registrations, key=lambda r: _sort_key(r.full_name))
    html = render_to_string(
        "core/attendance_list.html",
        {
            "registrations": rows,
            "total": len(rows),
            "activity": activity,
            "generated_at": timezone.localtime(),
            "logo_ifpi": _static_data_uri("images/logo-ifpi-vertical.png"),
            "logo_capivara": _static_data_uri("images/capivara-logo.svg"),
        },
    )
    return HTML(string=html).write_pdf()
