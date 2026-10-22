from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0023_sponsor_amount_help_text"),
    ]

    operations = [
        migrations.AddField(
            model_name="registration",
            name="checked_in",
            field=models.BooleanField(
                default=False,
                help_text="Marque após realizar o credenciamento no evento. Necessário para gerar certificados pelas inscrições.",
                verbose_name="Credenciado?",
            ),
        ),
    ]
