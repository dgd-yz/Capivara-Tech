"""Dados institucionais editáveis no admin do django-extra-settings."""
from datetime import date

from django.utils.formats import date_format


EVENT_DEFAULTS = [
    {"name": "EVENT_NAME", "type": "string", "value": "Capivara Tech II", "description": "Nome exibido no site e nos novos certificados."},
    {"name": "EVENT_EDITION", "type": "string", "value": "2ª Edição"},
    {"name": "EVENT_START_DATE", "type": "date", "value": date(2026, 10, 21), "description": "Início do evento. Atualize também os dias da programação ao mudar de edição."},
    {"name": "EVENT_END_DATE", "type": "date", "value": date(2026, 10, 23)},
    {"name": "EVENT_VENUE", "type": "string", "value": "IFPI Campus São Raimundo Nonato"},
    {"name": "EVENT_CITY", "type": "string", "value": "São Raimundo Nonato — PI"},
    {"name": "EVENT_ADDRESS", "type": "string", "value": "BR 020, São Raimundo Nonato — Piauí"},
    {"name": "EVENT_CONTACT_EMAIL", "type": "email", "value": "contato@sistemasparainternet.com", "description": "Contato público. O destino do formulário é definido em Configurações de email."},
    {"name": "EVENT_INSTAGRAM_URL", "type": "url", "value": "https://instagram.com/sistemasparainternetifpi"},
    {"name": "EVENT_WORKLOAD", "type": "int", "value": 24, "validator": "core.event_config.positive_integer", "description": "Carga horária do certificado geral, em horas."},
    {"name": "EVENT_EXPECTED_PARTICIPANTS", "type": "int", "value": 200, "validator": "core.event_config.positive_integer"},
    {"name": "EVENT_HERO_DESCRIPTION", "type": "text", "value": "Uma imersão em inovação, empreendedorismo e transformação digital — palestras, minicursos e muito networking no coração da Serra da Capivara."},
    {"name": "EVENT_MAP_URL", "type": "url", "value": "https://maps.google.com/maps?q=IFPI+Campus+Sao+Raimundo+Nonato&output=embed"},
]


def positive_integer(value):
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def get_event_config():
    from extra_settings.models import Setting

    values = {item["name"]: item["value"] for item in EVENT_DEFAULTS}
    # Uma consulta por leitura, sem cache local que fique obsoleto entre web e worker.
    values.update({row.name: row.value for row in Setting.objects.filter(name__in=values)})
    event = {name.removeprefix("EVENT_").lower(): value for name, value in values.items()}
    start, end = event["start_date"], event["end_date"]
    if start == end:
        label = date_format(start, "j \\d\\e F \\d\\e Y")
    elif (start.year, start.month) == (end.year, end.month):
        label = f"{start.day} a {date_format(end, 'j')} de {date_format(end, 'F')} de {end.year}"
    else:
        label = f"{date_format(start, 'DATE_FORMAT')} a {date_format(end, 'DATE_FORMAT')}"
    event.update(date_label=label.lower(), duration_days=max(0, (end - start).days + 1))
    return event


def event_context(request):
    return {"event": get_event_config()}
