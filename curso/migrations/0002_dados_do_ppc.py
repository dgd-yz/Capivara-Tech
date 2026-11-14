"""Conteúdo inicial tirado do PPC (versão 02, 30/01/2025). Tudo editável no admin depois."""
from django.db import migrations

MATRIZ = {
    1: [
        ("Algoritmos e Lógica de Programação", 100),
        ("Desenvolvimento Front-End I", 80),
        ("Inglês Técnico I", 40),
        ("Matemática Aplicada", 60),
        ("Design de Interfaces para Web e Móveis", 60),
        ("Engenharia de Software I", 60),
    ],
    2: [
        ("Estrutura de Dados", 80),
        ("Desenvolvimento Front-End II", 80),
        ("Banco de Dados I", 80),
        ("Estatística", 40),
        ("Comunicação Linguística e Redação Empresarial", 40),
        ("Engenharia de Software II", 40),
        ("Práticas de Extensão I", 40),
    ],
    3: [
        ("Programação Orientada a Objetos", 80),
        ("Desenvolvimento Web I", 80),
        ("Banco de Dados II", 60),
        ("Inglês Técnico II", 60),
        ("Redes de Computadores I", 40),
        ("Metodologia Científica", 40),
        ("Práticas de Extensão II", 40),
    ],
    4: [
        ("Programação para Dispositivos Móveis I", 80),
        ("Desenvolvimento Web II", 60),
        ("Tópicos Especiais I", 60),
        ("Arquitetura de Software e Entrega Contínua", 60),
        ("Redes de Computadores II", 60),
        ("Elaboração de Projeto", 40),
        ("Práticas de Extensão III", 40),
    ],
    5: [
        ("Programação para Dispositivos Móveis II", 80),
        ("Tópicos Especiais II", 60),
        ("Disciplina Optativa", 40),
        ("Inteligência Artificial e Machine Learning", 60),
        ("Empreendedorismo e Inovação", 40),
        ("Trabalho de Conclusão de Curso (TCC)", 40),
        ("Práticas de Extensão IV", 80),
    ],
}

TEMAS = [
    ("Programação", "Algoritmos, estruturas de dados e orientação a objetos: a base para qualquer linguagem."),
    ("Front-end e interfaces", "HTML, CSS, JavaScript e design de interfaces para web e celular, pensando em quem vai usar."),
    ("Back-end e web", "Aplicações web completas, APIs e arquitetura de software com entrega contínua."),
    ("Banco de dados", "Modelagem, SQL e como guardar e consultar dados com segurança."),
    ("Aplicativos móveis", "Dois módulos de programação para dispositivos móveis, do protótipo ao app publicado."),
    ("Inteligência artificial", "Machine learning e desenvolvimento com IA aplicados a problemas reais."),
    ("Redes e infraestrutura", "Como a internet funciona por baixo: protocolos, servidores e publicação de sistemas."),
    ("Extensão e empreendedorismo", "Projetos com a comunidade desde o 2º módulo e formação para criar o próprio negócio."),
]


def seed(apps, schema_editor):
    Subject = apps.get_model("curso", "Subject")
    Topic = apps.get_model("curso", "Topic")
    if not Subject.objects.exists():
        Subject.objects.bulk_create(
            Subject(module=module, name=name, workload=workload, order=index)
            for module, items in MATRIZ.items()
            for index, (name, workload) in enumerate(items, start=1)
        )
    if not Topic.objects.exists():
        Topic.objects.bulk_create(
            Topic(title=title, description=description, order=index)
            for index, (title, description) in enumerate(TEMAS, start=1)
        )


class Migration(migrations.Migration):
    dependencies = [("curso", "0001_initial")]

    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
