"""Texto de abertura pedido pela coordenação e PPC versão 03 no site.

O texto só é trocado se ninguém tiver editado o antigo no admin.
"""
from django.db import migrations, models

ANTIGO = (
    "Graduação tecnológica gratuita para quem quer criar sites, sistemas e aplicativos, "
    "do código à publicação, aqui no Território Serra da Capivara."
)

NOVO = (
    "Aprenda a desenvolver sistemas, aplicações web e aplicativos móveis em uma graduação "
    "pública e gratuita do IFPI. Desenvolva competências em programação, inteligência "
    "artificial e outras áreas da tecnologia, preparando-se para criar soluções inovadoras "
    "e acompanhar as transformações do mundo digital.\n\n"
    "Com uma formação em Tecnologia em Sistemas para Internet, você poderá construir uma "
    "carreira e atuar em empresas de tecnologia em qualquer lugar do mundo."
)


def trocar(apps, schema_editor):
    apps.get_model("curso", "CourseSettings").objects.filter(intro=ANTIGO).update(intro=NOVO)


def voltar(apps, schema_editor):
    apps.get_model("curso", "CourseSettings").objects.filter(intro=NOVO).update(intro=ANTIGO)


class Migration(migrations.Migration):
    dependencies = [("curso", "0002_dados_do_ppc")]

    operations = [
        migrations.AlterField(
            model_name="coursesettings",
            name="intro",
            field=models.TextField(
                default=NOVO,
                help_text="Deixe uma linha em branco para separar parágrafos.",
                verbose_name="Texto de abertura",
            ),
        ),
        migrations.RunPython(trocar, voltar),
        migrations.AlterField(
            model_name="coursesettings",
            name="ppc",
            field=models.FileField(
                blank=True,
                help_text="Vazio usa o PPC que já vem com o site (versão 03, revisada em 31/03/2025). "
                "Ao trocar o arquivo, atualize a versão abaixo.",
                upload_to="curso",
                verbose_name="PPC (PDF)",
            ),
        ),
        migrations.AddField(
            model_name="coursesettings",
            name="ppc_version",
            field=models.CharField(blank=True, default="Versão 03 · revisada em 31/03/2025", max_length=120, verbose_name="Versão do PPC"),
        ),
    ]
