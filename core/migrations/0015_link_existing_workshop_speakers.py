from django.db import migrations

# código do minicurso -> nomes de quem ministra (como cadastrados na migration 0011)
LINKS = {
    "1": ["Brenda Mota", "Giovanna Oliveira", "Irma Assunção", "Fernanda Farias"],
    "2": ["João Dias"],
    "3": ["Wanderson Paes"],
}


def link_existing_speakers(apps, schema_editor):
    Workshop = apps.get_model("core", "Workshop")
    Speaker = apps.get_model("core", "Speaker")

    for code, names in LINKS.items():
        workshop = Workshop.objects.filter(code=code).first()
        if workshop is None or workshop.speakers.exists():
            continue
        for name in names:
            speaker = Speaker.objects.filter(name=name).first()
            if speaker is not None:
                workshop.speakers.add(speaker)


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0014_workshop_speakers"),
    ]

    operations = [
        migrations.RunPython(link_existing_speakers, migrations.RunPython.noop),
    ]
