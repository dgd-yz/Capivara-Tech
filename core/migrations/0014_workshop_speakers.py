from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0013_import_existing_workshops_and_schedule"),
    ]

    operations = [
        migrations.AddField(
            model_name="workshop",
            name="speakers",
            field=models.ManyToManyField(
                blank=True,
                help_text="Escolha quem ministra para mostrar as fotos no card do site. Cadastre a pessoa antes em Palestrantes e instrutores.",
                related_name="workshops",
                to="core.speaker",
                verbose_name="Quem ministra (fotos no card)",
            ),
        ),
    ]
