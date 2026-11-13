import uuid

from django.db import models
from django.core.validators import MaxValueValidator
from django.urls import reverse
from django.utils.timezone import localdate
from django_ckeditor_5.fields import CKEditor5Field
from solo.models import SingletonModel

# Texto padrão antigo (que já trazia nome, data e assinatura). Mantido para a migração
# que o substitui pelo novo, já que agora o layout posiciona esses elementos.
LegacyCertificateTemplate = """
<p style="text-align:justify;">
    Declaro que <strong>{{Nome_Participante}}</strong> participou do <strong>{{Atividade}}</strong> com carga horaria de <strong>{{Carga_Horaria}}</strong> horas.
</p>
<p style="text-align:right;">
    <br>
    <strong>{{Local_de_Emissão}}, {{Data_de_Emissão}}</strong>
</p>
<p style="text-align:center;">
    <br>
    <strong>{{Nome_Certificador}}</strong><br>
    <strong>{{Cargo_Certificador}}</strong><br>
    &nbsp;
</p>
"""

# Só o corpo: o layout já mostra "Certificamos que", o nome, a data e a assinatura.
CerticateTemplate = """<p>participou {{Tipo_Atividade}} <strong>{{Atividade}}</strong>, com carga horária de <strong>{{Carga_Horaria}}&nbsp;horas</strong>.</p>"""

CertificateHelpText = f"""<p>O layout do certificado já mostra "Certificamos que", o nome do participante, o local e a data de emissão e a assinatura. Escreva aqui só o texto que vem depois do nome.</p>
<h3>Variáveis Disponíveis:</h3><br />
<b>{{{{Nome_Participante}}}}</b> Nome Completo do Participante.<br />
<b>{{{{Tipo_Atividade}}}}</b> "do evento", "do minicurso" ou "da atividade", conforme a atividade.<br />
<b>{{{{Atividade}}}}</b> Nome da Atividade.<br />
<b>{{{{Carga_Horaria}}}}</b> Carga Horária da Atividade.<br />
<b>{{{{Local_de_Emissão}}}}</b> Localização do Evento.<br />
<b>{{{{Data_de_Emissão}}}}</b> Data de Emissão do Certificado.<br />
<b>{{{{Nome_Certificador}}}}</b> Nome Completo do Certificador.<br />
<b>{{{{Cargo_Certificador}}}}</b> Cargo/Função do Certificador.<br />
<hr />
<b>Exemplo:</b><br />
{CerticateTemplate}
"""


class CertificationSettings(SingletonModel):
    default_location = models.CharField(
        "Local de Emissão",
        max_length=255,
        default="São Raimundo Nonato",
    )

    default_certifier_name = models.CharField(
        "Nome do Certificador",
        max_length=255,
        default="Nome do Certificador",
    )

    default_certifier_position = models.CharField(
        "Cargo do Certificador",
        max_length=255,
        default="Cargo do Certificador",
    )

    default_background_image = models.ImageField(
        "Imagem de Fundo",
        upload_to="settings",
        default="",
        blank=True,
        help_text="Fundo A4 horizontal (proporção 297 × 210). Opcional.",
    )

    margin_top = models.PositiveSmallIntegerField("Margem superior do texto (mm)", default=50, validators=[MaxValueValidator(100)])
    margin_bottom = models.PositiveSmallIntegerField("Margem inferior do texto (mm)", default=45, validators=[MaxValueValidator(100)])
    margin_left = models.PositiveSmallIntegerField("Margem esquerda do texto (mm)", default=25, validators=[MaxValueValidator(100)])
    margin_right = models.PositiveSmallIntegerField("Margem direita do texto (mm)", default=25, validators=[MaxValueValidator(100)])

    default_text = CKEditor5Field(
        "Texto do Certificado",
        help_text=CertificateHelpText,
        default=CerticateTemplate,
    )

    def __str__(self):
        return " Configurações de Certificados"

    class Meta:
        verbose_name = " Configurações de Certificados"


class Certificate(models.Model):
    background_image = models.ImageField(
        "Imagem de fundo", upload_to="certificates", blank=True,
        help_text="Copiada das configurações ao gerar. Se vazia, usa o fundo atual das configurações.",
    )
    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        editable=False,
        verbose_name="Criado em",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        editable=False,
    )

    participant_name = models.CharField(
        "Nome do Participante",
        max_length=250,
        help_text="Exemplo: Maria José de Jesus",
    )

    participant_email = models.EmailField(
        "E-mail do Participante",
        help_text="Exemplo: mariajosedejesus@mail.com",
    )

    activity = models.CharField(
        "Atividade",
        max_length=250,
        help_text="Exemplo: Organização Geral",
    )

    workload = models.PositiveIntegerField(
        "Carga Horaria",
        help_text="Exemplo: 4 (horas)",
    )

    location = models.CharField(
        "Local", max_length=250, help_text="Exemplo: São Raimundo Nonato"
    )

    date = models.DateField(
        "Data de Emissão",
        default=localdate,
        editable=False,
        help_text="Preenchida automaticamente com o dia em que o certificado foi gerado.",
    )

    certifier_name = models.CharField(
        "Nome do Certificador", max_length=250, help_text="Exemplo: Deus Todo Poderoso"
    )

    certifier_position = models.CharField(
        "Cargo do Certificador",
        max_length=250,
        help_text="Exemplo: Criador de Tudo e de Todos",
    )

    text = CKEditor5Field(
        "Texto",
        help_text=CertificateHelpText,
    )

    class Meta:
        verbose_name = "Certificado"
        verbose_name_plural = "Certificados"

    def __str__(self):
        return f"{self.participant_name} - {self.uuid}"

    def get_absolute_url(self):
        return reverse("certificate_detail", kwargs={"uuid": self.uuid})
