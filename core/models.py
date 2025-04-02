import uuid

from django.core.exceptions import ValidationError
from django.db import models


class BaseModel(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(
        auto_now_add=True, editable=False, verbose_name="Criado em"
    )
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        abstract = True


class Activities(models.TextChoices):
    ORIGIN = (
        "ORIGIN",
        "Povos dos campos, das águas, das florestas: agricultores(as), produtores(as), pescadores(as), indígenas, quilombolas",
    )
    ESTUDENT = "ESTUDENT", "Estudantes de nível médio e técnico"
    DEGREE = "DEGREE", "Estudantes de curso superior"
    POS = "POS", "Estudantes de pós graduação"
    TEACHER = "TEACHER", "Professores"
    OTHERS = "OTHERS", "Outros profissionais"


class Workshops(models.TextChoices):
    NONE = "0", "Não participarei de Oficina"
    ONE = (
        "1",
        "1. Oficina Sementes da Fartura: Pureza, germinação, manejo, armazenagem e implantação de casas/bancos comunitários de sementes",
    )
    TWO = "2", "2. Práticas Agroecológicas (água de vidro, biofertilizantes)"
    TREE = (
        "3",
        "3. Redesenho dos agroecossistemas familiares para a transição agroecológica e o fortalecimento dos sistemas agroalimentares",
    )
    FOUR = "4", "4. Introdução à meliponicultura"
    FIVE = (
        "5",
        "5. Introdução aos Sistemas Agroflorestais (SAF) e o uso do SAF na mitigação das mudanças climáticas",
    )
    SIX = (
        "6",
        "6. Bases gerais da pecuária orgânica e alimentação de aves, bovinos, suínos, caprinos e ovinos no sistema orgânico",
    )
    SEVEN = "7", "7. Fontes alternativas para alimentação de aves caipiras"
    EIGHT = "8", "8. Preparações sustentáveis"
    NINE = (
        "9",
        "9. Agroecologica, cuidado e feminismo",
    )
    TEN = (
        "10",
        "10. Acesso dos jovens rurais aos espaços decisórios e de diálogo agroecologia",
    )
    ELEVEN = "11", "11. Manipulação de plantas medicinais"
    TWELVE = (
        "12",
        "12. Formação de preços de venda de produtos da agricultura familiar",
    )


class Registration(BaseModel):
    activity = models.CharField(
        "Atividade",
        max_length=250,
        choices=Activities,
        default=Activities.ORIGIN,
        help_text="Escolha uma das opções disponíveis",
    )

    full_name = models.CharField(
        "Nome", max_length=250, help_text="Exemplo: Maria José de Jesus"
    )

    entity = models.CharField(
        "Entidade", max_length=250, blank=True, help_text="Exemplo: IFPI"
    )

    telephone = models.CharField(
        "Telefone", max_length=15, blank=True, help_text="Exemplo: (89) 98123-4567"
    )

    email = models.EmailField(
        "E-mail",
        max_length=254,
        unique=True,
        help_text="Exemplo: mariajose@email.com",
    )

    workshop = models.CharField(
        "Oficina",
        max_length=150,
        choices=Workshops,
        help_text="Escolha uma das oficinas disponíveis",
        default=Workshops.NONE,
    )

    confirmated = models.BooleanField("Inscrição Confirmada?", default=False)

    def clean(self):
        if self.workshop != Workshops.NONE:
            if Registration.objects.filter(workshop=self.workshop).count() >= 30:
                raise ValidationError(
                    {
                        "workshop": ValidationError(
                            "Infelizmente não há mais vagas para esta Oficina",
                            code="invalid",
                        )
                    }
                )

        return super().clean()

    def __str__(self):
        return f"{self.full_name}"

    class Meta:
        verbose_name = "Inscrição"
        verbose_name_plural = "Inscrições"
