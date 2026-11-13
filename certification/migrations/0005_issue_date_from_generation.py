import django.utils.timezone
from django.db import migrations, models
from django.utils.timezone import localtime


def use_generation_date(apps, schema_editor):
    """A data de emissão passa a ser o dia em que o certificado foi gerado (não mais um valor fixo)."""
    Certificate = apps.get_model("certification", "Certificate")
    for certificate in Certificate.objects.only("pk", "created_at", "date"):
        generated_on = localtime(certificate.created_at).date()
        if certificate.date != generated_on:
            Certificate.objects.filter(pk=certificate.pk).update(date=generated_on)


class Migration(migrations.Migration):

    dependencies = [
        ("certification", "0004_certificate_layout_text"),
    ]

    operations = [
        migrations.RunPython(use_generation_date, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="certificate",
            name="date",
            field=models.DateField(
                default=django.utils.timezone.localdate,
                editable=False,
                help_text="Preenchida automaticamente com o dia em que o certificado foi gerado.",
                verbose_name="Data de Emissão",
            ),
        ),
        migrations.RemoveField(
            model_name="certificationsettings",
            name="default_date",
        ),
    ]
