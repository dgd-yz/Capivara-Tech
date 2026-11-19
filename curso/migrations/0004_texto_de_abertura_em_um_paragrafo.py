"""Texto de abertura num parágrafo só, a pedido da coordenação.

Só troca se o texto salvo ainda for o de dois parágrafos da migração 0003.
"""
from django.db import migrations, models

PRIMEIRA = (
    "Aprenda a desenvolver sistemas, aplicações web e aplicativos móveis em uma graduação "
    "pública e gratuita do IFPI. Desenvolva competências em programação, inteligência "
    "artificial e outras áreas da tecnologia, preparando-se para criar soluções inovadoras "
    "e acompanhar as transformações do mundo digital."
)
SEGUNDA = (
    "Com uma formação em Tecnologia em Sistemas para Internet, você poderá construir uma "
    "carreira e atuar em empresas de tecnologia em qualquer lugar do mundo."
)
DOIS_PARAGRAFOS = PRIMEIRA + "\n\n" + SEGUNDA
UM_PARAGRAFO = PRIMEIRA + " " + SEGUNDA


def juntar(apps, schema_editor):
    apps.get_model("curso", "CourseSettings").objects.filter(intro=DOIS_PARAGRAFOS).update(intro=UM_PARAGRAFO)


def separar(apps, schema_editor):
    apps.get_model("curso", "CourseSettings").objects.filter(intro=UM_PARAGRAFO).update(intro=DOIS_PARAGRAFOS)


class Migration(migrations.Migration):
    dependencies = [("curso", "0003_texto_de_abertura_e_ppc")]

    operations = [
        migrations.AlterField(
            model_name="coursesettings",
            name="intro",
            field=models.TextField(
                default=UM_PARAGRAFO,
                help_text="Deixe uma linha em branco para separar parágrafos.",
                verbose_name="Texto de abertura",
            ),
        ),
        migrations.RunPython(juntar, separar),
    ]
