import re

from django.db import migrations

# Cópia das regras de certification/names.py, para a migração não mudar se o módulo mudar depois.
PARTICLES = {"de", "da", "do", "das", "dos", "e"}
ROMAN = re.compile(r"^(i{1,3}|iv|vi{0,3}|ix|x)$", re.IGNORECASE)


def _format_part(part):
    if not part:
        return part
    if ROMAN.match(part):
        return part.upper()
    if any(c.isupper() for c in part[1:]) and any(c.islower() for c in part):
        return part
    return part[0].upper() + part[1:].lower()


def _format_word(word, first):
    if not first and word.lower() in PARTICLES:
        return word.lower()
    if re.fullmatch(r"\w\.?", word):
        return word.upper()
    return "-".join(_format_part(part) for part in word.split("-"))


def format_person_name(name):
    words = (name or "").split()
    return " ".join(_format_word(word, index == 0) for index, word in enumerate(words))


def format_existing_names(apps, schema_editor):
    Certificate = apps.get_model("certification", "Certificate")
    for certificate in Certificate.objects.only("pk", "participant_name"):
        formatted = format_person_name(certificate.participant_name)
        if formatted != certificate.participant_name:
            Certificate.objects.filter(pk=certificate.pk).update(participant_name=formatted)


class Migration(migrations.Migration):

    dependencies = [
        ("certification", "0005_issue_date_from_generation"),
    ]

    operations = [
        migrations.RunPython(format_existing_names, migrations.RunPython.noop),
    ]
