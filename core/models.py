import uuid

from django.core.exceptions import ValidationError
from django.db import models
from io import BytesIO

from django.core.files.base import ContentFile
from django.core.validators import RegexValidator
from django.utils.text import slugify
from PIL import Image as PILImage
from PIL import ImageOps
from pictures.models import PictureField


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
        "Comunidade / entusiasta de tecnologia",
    )
    ESTUDENT = "ESTUDENT", "Estudantes de nível médio e técnico"
    DEGREE = "DEGREE", "Estudantes de curso superior"
    POS = "POS", "Estudantes de pós graduação"
    TEACHER = "TEACHER", "Professores"
    OTHERS = "OTHERS", "Outros profissionais"


class Workshops(models.TextChoices):
    NONE = "0", "Não participarei de minicurso"


class Organization(models.TextChoices):
    NONE = ("NONE", "Não faz parte da Organização")
    PRESENTATION = ("PRESENTATION", "Apresentação de Trabalhos")
    MONITOR = ("MONITOR", "Monitores")
    COMMITTEE = ("COMMITTEE", "Membro de Comissões")


class Workshop(models.Model):
    code = models.CharField(
        "Código",
        max_length=10,
        unique=True,
        validators=[
            RegexValidator(
                r"^[1-9][0-9]*$",
                "Use só números, sem zero à esquerda (o 0 é reservado para "
                '"não participarei de minicurso").',
            )
        ],
        help_text=(
            "Identifica o minicurso em cada inscrição. "
            "Não pode ser alterado depois de criado."
        ),
    )
    name = models.CharField("Nome do minicurso", max_length=250)
    instructors = models.CharField(
        "Ministrante(s)",
        max_length=250,
        blank=True,
        help_text='Aparece no card do site. Ex.: "João Dias" ou "Django Girls".',
    )
    capacity = models.PositiveIntegerField(
        "Vagas",
        default=30,
        help_text=(
            "Ao atingir esse número de inscritos, o minicurso deixa de aparecer "
            "no formulário de inscrição."
        ),
    )
    order = models.PositiveIntegerField(
        "Ordem",
        default=0,
        help_text="Números menores aparecem primeiro.",
    )
    published = models.BooleanField(
        "Exibir no site e na inscrição",
        default=True,
        help_text=(
            "Desmarque para esconder. As inscrições já feitas continuam "
            "ligadas a este minicurso."
        ),
    )

    class Meta:
        ordering = ("order", "id")
        verbose_name = "Minicurso"
        verbose_name_plural = "Minicursos"

    def __str__(self):
        return self.choice_label

    @property
    def choice_label(self):
        return f"{self.code}. {self.name}"

    @property
    def title(self):
        return f"Minicurso {self.code} — {self.name}"

    @property
    def initials(self):
        words = (self.instructors or self.name).split()
        return "".join(word[0] for word in words[:2]).upper()

    @property
    def registered(self):
        return Registration.objects.filter(workshop=self.code).count()

    @property
    def is_full(self):
        return self.registered >= self.capacity


def get_workshops_choices():
    """Opções do formulário público: só minicursos publicados e com vaga."""
    choices = [(Workshops.NONE.value, Workshops.NONE.label)]
    for workshop in Workshop.objects.filter(published=True):
        if not workshop.is_full:
            choices.append((workshop.code, workshop.choice_label))
    return choices


def get_all_workshops_choices():
    """Todas as opções (inclusive escondidas ou lotadas), para editar inscrições antigas."""
    choices = [(Workshops.NONE.value, Workshops.NONE.label)]
    choices += [(w.code, w.choice_label) for w in Workshop.objects.all()]
    return choices


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
        unique=False,
        help_text="Exemplo: mariajose@email.com",
    )

    workshop = models.CharField(
        "Minicurso",
        max_length=150,
        help_text="Escolha um dos minicursos disponíveis",
        default=Workshops.NONE,
    )

    confirmated = models.BooleanField("Inscrição Confirmada?", default=False)

    organization = models.CharField(
        "Organização",
        max_length=150,
        choices=Organization,
        help_text="Escolha uma das categorias de organização disponíveis",
        default=Organization.NONE,
    )

    def get_workshop_name(self):
        return Workshop.objects.get(code=self.workshop).name

    def clean(self):
        if self.workshop != Workshops.NONE:
            workshop = Workshop.objects.filter(code=self.workshop).first()
            if workshop is None:
                raise ValidationError(
                    {
                        "workshop": ValidationError(
                            "Minicurso inválido.", code="invalid"
                        )
                    }
                )
            taken = (
                Registration.objects.filter(workshop=self.workshop)
                .exclude(pk=self.pk)
                .count()
            )
            if taken >= workshop.capacity:
                raise ValidationError(
                    {
                        "workshop": ValidationError(
                            "Infelizmente não há mais vagas para este Minicurso",
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


class Image(models.Model):
    title = models.CharField(
        "Título",
        max_length=255,
    )

    picture = PictureField(
        upload_to="pictures",
        width_field="picture_width",
        height_field="picture_height",
    )

    picture_width = models.PositiveIntegerField(
        editable=False,
    )

    picture_height = models.PositiveIntegerField(
        editable=False,
    )

    def __str__(self):
        return f"{self.title}"

    class Meta:
        verbose_name = "Imagem"
        verbose_name_plural = "Imagens"


class Speaker(models.Model):
    name = models.CharField("Nome", max_length=250)
    session = models.CharField(
        "Sessão",
        max_length=150,
        blank=True,
        help_text='Ex.: "Palestra 3" ou "Minicurso 2".',
    )
    role = models.CharField(
        "Cargo ou minicurso",
        max_length=250,
        blank=True,
        help_text='Aparece ao lado da sessão. Ex.: "Analista de Redes" ou "Django Girls".',
    )
    talk = models.CharField(
        "Tema da palestra",
        max_length=250,
        blank=True,
        help_text="Aparece entre aspas no início da descrição.",
    )
    bio = models.TextField(
        "Descrição",
        blank=True,
        help_text="Deixe uma linha em branco para separar parágrafos.",
    )
    photo = models.ImageField(
        "Foto",
        upload_to="speakers",
        blank=True,
        help_text=(
            "JPG ou PNG, de preferência quadrada e com o rosto no centro. "
            "Sem foto, o site mostra uma imagem padrão."
        ),
    )
    order = models.PositiveIntegerField(
        "Ordem",
        default=0,
        help_text="Números menores aparecem primeiro.",
    )
    published = models.BooleanField("Exibir no site", default=True)

    class Meta:
        ordering = ("order", "id")
        verbose_name = "Palestrante ou instrutor"
        verbose_name_plural = "Palestrantes e instrutores"

    def __str__(self):
        return self.name

    @property
    def label(self):
        return " · ".join(part for part in (self.session, self.role) if part)

    def save(self, *args, **kwargs):
        if self.photo and not self.photo._committed:
            self.photo.save(
                f"{slugify(self.name) or 'palestrante'}.jpg",
                _normalized_photo(self.photo),
                save=False,
            )
        super().save(*args, **kwargs)


def _normalized_photo(uploaded, max_side=1000):
    """Corrige a rotação do celular, limita o tamanho e salva como JPG."""
    image = ImageOps.exif_transpose(PILImage.open(uploaded)).convert("RGB")
    image.thumbnail((max_side, max_side))
    buffer = BytesIO()
    image.save(buffer, "JPEG", quality=88, optimize=True)
    return ContentFile(buffer.getvalue())


class EventDay(models.Model):
    date = models.DateField("Data", unique=True)
    subtitle = models.CharField(
        "Subtítulo da aba",
        max_length=100,
        blank=True,
        help_text='Ex.: "Minicursos" ou "Palestras".',
    )
    published = models.BooleanField("Exibir no site", default=True)

    class Meta:
        ordering = ("date",)
        verbose_name = "Dia da programação"
        verbose_name_plural = "Programação"

    def __str__(self):
        suffix = f" · {self.subtitle}" if self.subtitle else ""
        return f"{self.date:%d/%m/%Y}{suffix}"


class ScheduleItem(models.Model):
    TAGS = {
        "minicurso": ("Minicurso", "minicurso"),
        "palestra": ("Palestra", "palestra"),
        "keynote": ("Keynote", "keynote"),
        "painel": ("Painel", "painel"),
        "pausa": ("Pausa", "pausa"),
        "abertura": ("Abertura", "pausa"),
        "social": ("Social", "pausa"),
        "parceiro": ("Parceiro", "cultura"),
        "cultura": ("Cultura", "cultura"),
    }

    day = models.ForeignKey(
        EventDay,
        verbose_name="Dia",
        related_name="items",
        on_delete=models.CASCADE,
    )
    start_time = models.TimeField("Início")
    end_time = models.TimeField("Término", null=True, blank=True)
    title = models.CharField("Título", max_length=250)
    subtitle = models.CharField(
        "Local e responsável",
        max_length=250,
        blank=True,
        help_text='Ex.: "Auditório · Nome do palestrante" ou "Lab 1".',
    )
    tag = models.CharField(
        "Etiqueta",
        max_length=20,
        choices=[(key, label) for key, (label, _) in TAGS.items()],
        default="palestra",
    )
    order = models.PositiveIntegerField(
        "Ordem no mesmo horário",
        default=0,
        help_text="Só serve para desempatar itens que começam na mesma hora.",
    )
    published = models.BooleanField("Exibir no site", default=True)

    class Meta:
        ordering = ("start_time", "order", "id")
        verbose_name = "Item da programação"
        verbose_name_plural = "Itens da programação"

    def __str__(self):
        return f"{self.time_label} {self.title}"

    @property
    def time_label(self):
        start = f"{self.start_time:%H:%M}"
        return f"{start}–{self.end_time:%H:%M}" if self.end_time else start

    @property
    def tag_text(self):
        return self.TAGS[self.tag][0]

    @property
    def tag_class(self):
        return self.TAGS[self.tag][1]
