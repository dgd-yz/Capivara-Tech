import re

import django_ckeditor_5.fields
from django.db import migrations

import certification.models as cert_models


def normalized(html):
    """Texto sem tags, &nbsp; e espaços extras (o editor reformata o HTML ao salvar)."""
    text = re.sub(r"<[^>]+>", " ", html or "").replace("&nbsp;", " ").replace("\xa0", " ")
    return " ".join(text.split())


# Valores fixos aqui para a migração não mudar se os textos do models.py mudarem depois.
LEGACY = (
    "Declaro que {{Nome_Participante}} participou do {{Atividade}} com carga horaria de "
    "{{Carga_Horaria}} horas. {{Local_de_Emissão}}, {{Data_de_Emissão}} {{Nome_Certificador}} "
    "{{Cargo_Certificador}}"
)
NEW_TEXT = (
    "<p>participou {{Tipo_Atividade}} <strong>{{Atividade}}</strong>, com carga horária de "
    "<strong>{{Carga_Horaria}}&nbsp;horas</strong>.</p>"
)


def use_new_default_text(apps, schema_editor):
    """Troca o texto padrão antigo pelo novo, sem mexer em textos personalizados."""
    CertificationSettings = apps.get_model("certification", "CertificationSettings")
    Certificate = apps.get_model("certification", "Certificate")
    for model, field in ((CertificationSettings, "default_text"), (Certificate, "text")):
        for obj in model.objects.all():
            if normalized(getattr(obj, field)) == LEGACY:
                model.objects.filter(pk=obj.pk).update(**{field: NEW_TEXT})


class Migration(migrations.Migration):

    dependencies = [
        ("certification", "0003_alter_certificate_text_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="certificate",
            name="text",
            field=django_ckeditor_5.fields.CKEditor5Field(help_text=cert_models.CertificateHelpText, verbose_name="Texto"),
        ),
        migrations.AlterField(
            model_name="certificationsettings",
            name="default_text",
            field=django_ckeditor_5.fields.CKEditor5Field(
                default=cert_models.CerticateTemplate,
                help_text=cert_models.CertificateHelpText,
                verbose_name="Texto do Certificado",
            ),
        ),
        migrations.RunPython(use_new_default_text, migrations.RunPython.noop),
    ]
