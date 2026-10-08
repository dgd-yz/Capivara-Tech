from decimal import Decimal
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import migrations

STATIC_IMAGES = Path(__file__).resolve().parents[1] / "static" / "images"

# (nome, complemento, arquivo do logo, valor, master)
SPONSORS = [
    ("Tek D&D Papelaria & Presentes", "", "logo-tek-dd.png", "50", False),
]


def stored_logo(filename):
    """Copia o logo dos estáticos para a mídia (sem duplicar se já estiver lá)."""
    name = f"sponsors/{filename}"
    if not default_storage.exists(name):
        source = STATIC_IMAGES / filename
        if not source.exists():
            return ""
        default_storage.save(name, ContentFile(source.read_bytes()))
    return name


def add_sponsors(apps, schema_editor):
    Sponsor = apps.get_model("core", "Sponsor")
    for name, subtitle, logo, amount, is_master in SPONSORS:
        if Sponsor.objects.filter(name=name).exists():
            continue
        Sponsor.objects.create(
            name=name,
            subtitle=subtitle,
            logo=stored_logo(logo),
            amount=Decimal(amount),
            is_master=is_master,
        )


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0020_add_ohmycode_sponsor"),
    ]

    operations = [
        migrations.RunPython(add_sponsors, migrations.RunPython.noop),
    ]
