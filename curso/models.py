from django.db import models
from solo.models import SingletonModel

DEFAULT_INTRO = (
    "Graduação tecnológica gratuita para quem quer criar sites, sistemas e aplicativos, "
    "do código à publicação, aqui no Território Serra da Capivara."
)

DEFAULT_ABOUT = (
    "O Curso Superior de Tecnologia em Sistemas para Internet forma profissionais para "
    "desenvolver, manter e operar aplicações e portais para a Internet, com uma base "
    "conceitual sólida e prática sempre atualizada.\n\n"
    "A matriz coloca o estudante em contato com as tecnologias usadas hoje no desenvolvimento "
    "web e mobile, com extensão curricularizada desde o segundo módulo: projetos que levam "
    "o que se aprende em sala para a comunidade da região."
)

DEFAULT_PROFILE = (
    "Ao concluir o curso, você estará preparado para projetar, desenvolver, testar, implantar "
    "e manter sites, sistemas de comércio eletrônico e aplicativos para plataformas móveis; "
    "escolher metodologias e ferramentas adequadas a cada projeto; criar interfaces pensadas "
    "para o público de cada aplicação; e emitir laudos e pareceres técnicos na sua área."
)

DEFAULT_CAREERS = "\n".join([
    "Empresas de tecnologia",
    "Desenvolvimento de projetos, assistência técnica e consultoria",
    "Indústria, comércio e serviços",
    "Órgãos públicos",
    "Organizações não governamentais",
    "Institutos e centros de pesquisa",
    "Instituições de ensino",
    "Seu próprio negócio digital",
])

DEFAULT_ADMISSION = (
    "O ingresso acontece por processo seletivo público do IFPI (vestibular), conforme o edital "
    "de cada ano. Metade das vagas é reservada pela Lei de Cotas, e o IFPI reserva ainda 5% "
    "para pessoas com deficiência.\n\n"
    "Quem já tem graduação ou estuda em outra instituição pode entrar por transferência ou "
    "como portador de diploma, nos editais de vagas remanescentes. Se sobrarem vagas, há "
    "chamada pública pela nota de redação do ENEM."
)

DEFAULT_ELECTIVES = "\n".join([
    "Desenvolvimento com IA",
    "Ciência de Dados",
    "Computação em Nuvem",
    "Desenvolvimento ServerLess",
    "Desenvolvimento de API",
    "CiberSegurança",
    "Segurança em Redes",
    "IoT - Internet das Coisas",
    "Realidade Aumentada e Virtual",
    "Dapps para Web3 com Blockchain",
    "Desenvolvimento NoCode",
    "Desenvolvimento Web III",
    "Desenvolvimento Front-End III",
    "Programação para Dispositivos Móveis III",
    "Banco de Dados III",
    "Engenharia de Software III",
    "TI Aplicada à Saúde",
    "TI Aplicada à Educação",
    "Compiladores",
    "Grafos",
])


def lines(text):
    return [line.strip() for line in (text or "").splitlines() if line.strip()]


class CourseSettings(SingletonModel):
    name = models.CharField("Nome do curso", max_length=150, default="Tecnologia em Sistemas para Internet")
    short_name = models.CharField("Nome curto", max_length=60, default="Sistemas para Internet")
    degree = models.CharField("Tipo de curso", max_length=120, default="Curso Superior de Tecnologia")
    diploma = models.CharField("Diploma", max_length=120, default="Tecnólogo em Sistemas para Internet")
    tagline = models.CharField("Chamada", max_length=120, default="Sua graduação começa aqui")
    institution = models.CharField("Instituição", max_length=150, default="IFPI Campus São Raimundo Nonato")
    address = models.CharField("Endereço", max_length=250, default="BR 020, S/N, Primavera, São Raimundo Nonato - PI, 64770-000")
    logo = models.ImageField(
        "Logo do curso", upload_to="curso", blank=True,
        help_text="PNG ou SVG com fundo transparente. Sem logo, o site mostra o selo \"SI\" desenhado.",
    )

    intro = models.TextField("Texto de abertura", default=DEFAULT_INTRO)
    about = models.TextField("Sobre o curso", default=DEFAULT_ABOUT, help_text="Deixe uma linha em branco para separar parágrafos.")
    graduate_profile = models.TextField("Perfil do egresso", blank=True, default=DEFAULT_PROFILE)
    careers = models.TextField("Onde atuar", blank=True, default=DEFAULT_CAREERS, help_text="Um item por linha.")

    duration = models.CharField("Duração", max_length=60, blank=True, default="5 semestres")
    shift = models.CharField("Turno", max_length=60, blank=True, help_text="Vazio esconde o item no site.")
    seats = models.CharField("Vagas", max_length=60, blank=True, default="30 por ano")
    workload = models.CharField("Carga horária", max_length=60, blank=True, default="2.100 horas")

    admission = models.TextField("Como ingressar", blank=True, default=DEFAULT_ADMISSION, help_text="Deixe uma linha em branco para separar parágrafos.")
    admission_url = models.URLField("Link do processo seletivo", blank=True, default="https://selecao.ifpi.edu.br/")
    electives = models.TextField(
        "Tópicos especiais e optativas", blank=True, default=DEFAULT_ELECTIVES,
        help_text="Um por linha. Aparecem como exemplos abaixo da matriz.",
    )
    ppc = models.FileField("PPC (PDF)", upload_to="curso", blank=True)

    coordinator = models.CharField(
        "Coordenação", max_length=150, blank=True, default="Paul Symon Ribeiro Rocha",
        help_text="Nome de quem coordena o curso. Aparece no contato.",
    )
    contact_email = models.EmailField("E-mail de contato", blank=True, default="contato@sistemasparainternet.com")
    instagram_url = models.URLField("Instagram", blank=True, default="https://instagram.com/sistemasparainternetifpi")
    map_url = models.URLField(
        "Mapa (embed)", blank=True,
        default="https://maps.google.com/maps?q=IFPI+Campus+Sao+Raimundo+Nonato&output=embed",
    )

    class Meta:
        verbose_name = "Configurações do curso"

    def __str__(self):
        return "Configurações do curso"

    @property
    def career_list(self):
        return lines(self.careers)

    @property
    def elective_list(self):
        return lines(self.electives)


class Topic(models.Model):
    title = models.CharField("Título", max_length=120)
    description = models.TextField("Descrição", max_length=400)
    order = models.PositiveSmallIntegerField("Ordem", default=0)
    published = models.BooleanField("Publicado", default=True)

    class Meta:
        ordering = ["order", "pk"]
        verbose_name = "O que você vai aprender"
        verbose_name_plural = "O que você vai aprender"

    def __str__(self):
        return self.title


class Subject(models.Model):
    module = models.PositiveSmallIntegerField("Módulo")
    name = models.CharField("Disciplina", max_length=150)
    workload = models.PositiveSmallIntegerField("Carga horária (h)", null=True, blank=True)
    order = models.PositiveSmallIntegerField("Ordem", default=0)

    class Meta:
        ordering = ["module", "order", "pk"]
        verbose_name = "Disciplina"
        verbose_name_plural = "Matriz curricular"

    def __str__(self):
        return f"{self.module}º módulo · {self.name}"



class Highlight(models.Model):
    title = models.CharField("Título", max_length=150)
    summary = models.TextField("Resumo", max_length=400, blank=True)
    image = models.ImageField("Imagem", upload_to="curso/destaques", blank=True)
    url = models.URLField("Link", blank=True, help_text="Post no Instagram, notícia ou página do evento.")
    date = models.DateField("Data")
    published = models.BooleanField("Publicado", default=True)

    class Meta:
        ordering = ["-date", "-pk"]
        verbose_name = "Destaque"
        verbose_name_plural = "Destaques e notícias"

    def __str__(self):
        return self.title
