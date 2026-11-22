"""Projeto Kactuz: 15 aulas de 2 horas, 30 horas no total (os primeiros saíram com 60)."""
from django.db import migrations


def corrigir(apps, schema_editor):
    apps.get_model("certification", "Certificate").objects.filter(layout="kactuz", workload=60).update(workload=30)


def voltar(apps, schema_editor):
    apps.get_model("certification", "Certificate").objects.filter(layout="kactuz", workload=30).update(workload=60)


class Migration(migrations.Migration):
    dependencies = [("certification", "0007_certificados_do_projeto_kactuz")]

    operations = [migrations.RunPython(corrigir, voltar)]
