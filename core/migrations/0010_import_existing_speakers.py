from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.files.storage import default_storage
from django.db import migrations

# Bianca (photo=None) fica sem foto: a dela deve ser enviada pelo admin.
SPEAKERS = [{'name': 'Brenda Mota',
  'session': 'Minicurso 1',
  'role': 'Django Girls',
  'talk': '',
  'bio': 'Professora de História, 31 anos, em momento de transição de carreira para a área da '
         'tecnologia. Cursando ADS no IFPI e se enveredando pela área de Cibersegurança. Acredita '
         'que a tecnologia é um lugar que não se limita apenas a códigos, mas também um espaço '
         'onde a criatividade e arte podem crescer. Faz parte do grupo Pyladies Parnaíba, onde os '
         'primeiros passos para a tecnologia começaram, rodeada de mulheres incríveis e empenhada '
         'a chamar mais mulheres para a área.',
  'photo': 'palestrante-brenda.jpg',
  'order': 10},
 {'name': 'Giovanna Oliveira',
  'session': 'Minicurso 1',
  'role': 'Django Girls',
  'talk': '',
  'bio': 'Graduanda em Análise e Desenvolvimento de Sistemas e em Gestão Pública, desenvolvedora '
         'Back-end e monitora do NAPNE no IFPI Parnaíba. Tem experiência com JavaScript e Python, '
         'com foco de interesse em proteção de dados e análise de negócios em TI. Integra a '
         'PyLadies Parnaíba e participa de iniciativas voltadas ao fortalecimento da presença '
         'feminina na tecnologia, incentivando o aprendizado, a colaboração e a inclusão na '
         'comunidade.',
  'photo': 'palestrante-giovanna.jpg',
  'order': 20},
 {'name': 'Irma Assunção',
  'session': 'Minicurso 1',
  'role': 'Django Girls',
  'talk': '',
  'bio': 'Designer gráfica em transição para o desenvolvimento back-end e amante de Java. '
         'Estudante de Análise e Desenvolvimento de Sistemas no IFPI Parnaíba e uma das '
         'coordenadoras da PyLadies Parnaíba, onde também é a responsável pela identidade visual '
         'da comunidade.',
  'photo': 'palestrante-irma.jpg',
  'order': 30},
 {'name': 'Fernanda Farias',
  'session': 'Minicurso 1',
  'role': 'Django Girls',
  'talk': '',
  'bio': 'Engenheira de Dados e Analytics, graduanda em Análise e Desenvolvimento de Sistemas pelo '
         'IFPI - Campus Parnaíba, coordenadora da PyLadies Parnaíba e Embaixadora Estudantil '
         'Google. Acredita que os dados não são apenas números, mas têm a capacidade de contar '
         'histórias e criar soluções.',
  'photo': 'palestrante-fernanda.jpg',
  'order': 40},
 {'name': 'João Dias',
  'session': 'Minicurso 2',
  'role': 'Teste de Software',
  'talk': '',
  'bio': 'Reingressante do IFPI – Campus São Raimundo Nonato, com experiência em Quality Assurance '
         '(QA) e testes de software. Entusiasta da área de qualidade, com interesse em aprimorar '
         'continuamente conhecimentos em testes, análise de qualidade, identificação de falhas e '
         'boas práticas de desenvolvimento de software.',
  'photo': 'palestrante-joao.jpg',
  'order': 50},
 {'name': 'Wanderson Paes',
  'session': 'Minicurso 3',
  'role': 'Desenvolvimento de Games',
  'talk': '',
  'bio': 'Técnico em Tecnologia da Informação e professor de Desenvolvimento de Sistemas.\n'
         '\n'
         'Iniciou sua formação com o curso Técnico em Informática pelo Instituto Federal do Piauí '
         '(IFPI), em São Raimundo Nonato. Posteriormente, graduou-se em Matemática pelo IFPI e em '
         'Análise e Desenvolvimento de Sistemas pela UNINTER.\n'
         '\n'
         'Possui especialização em Segurança da Informação e mestrado em Administração Pública, '
         'com ênfase em Governo Digital.\n'
         '\n'
         'Hoje, trabalha como técnico em Tecnologia da Informação na Universidade Federal do Vale '
         'do São Francisco (UNIVASF) e também como professor do curso Técnico em Desenvolvimento '
         'de Sistemas do Senac.',
  'photo': 'palestrante-wanderson.jpg',
  'order': 60},
 {'name': 'Eduardo Neri Martins',
  'session': 'Palestra 1',
  'role': 'Desenvolvedor Fullstack',
  'talk': 'Introdução a AWS',
  'bio': 'Técnico em Desenvolvimento Web pelo Senac Piauí e estudante de Tecnologia em Sistemas '
         'para Internet no IFPI — Campus São Raimundo Nonato. Iniciou sua trajetória profissional '
         'no suporte técnico, onde também teve contato com o desenvolvimento front-end. '
         'Posteriormente, atuou com cloud e infraestrutura, ampliando sua visão sobre o '
         'desenvolvimento e a sustentação de aplicações. Atualmente, trabalha como Desenvolvedor '
         'Full Stack freelancer.',
  'photo': 'palestrante-eduardo.jpg',
  'order': 70},
 {'name': 'Aldo Victor D. Oliveira',
  'session': 'Palestra 2',
  'role': 'Advogado',
  'talk': 'Propriedade Intelectual',
  'bio': 'Advogado. Atua com direito previdenciário e do consumidor, é Agente da Propriedade '
         'Industrial junto ao INPI e trabalha com registro de marcas e de software. Preside a '
         'Comissão Subseccional da Jovem Advocacia. @advogaldo',
  'photo': 'palestrante-aldo.jpg',
  'order': 80},
 {'name': 'Bianca Freire Marques',
  'session': 'Palestra 3',
  'role': 'Analista de Redes',
  'talk': '',
  'bio': 'Egressa do IFPI – Campus São Raimundo Nonato, onde concluiu o curso Técnico em '
         'Informática. Posteriormente, graduou-se como Tecnóloga em Análise e Desenvolvimento de '
         'Sistemas pelo IFPI – Campus Floriano.\n'
         '\n'
         'Atualmente, atua profissionalmente na área de redes de telecomunicações. Ao longo da '
         'trajetória acadêmica, também teve experiências com programação, participação em '
         'competições acadêmicas, monitoria e atividades relacionadas ao ensino de tecnologia.',
  'photo': None,
  'order': 90},
 {'name': 'Prof. Justino Duarte',
  'session': 'Palestra 4',
  'role': 'Professor do IFPI',
  'talk': 'Introdução a Visão Computacional',
  'bio': 'Formado em Análise e Desenvolvimento de Sistemas (IFPI), possui Mestrado e Doutorado em '
         'Ciência da Computação (UFPI/UFMA), onde pesquisou sobre aplicação de IA em imagens '
         'médicas para o diagnóstico de doenças. No campo profissional, atuou como técnico de TI '
         'no IFMA e é professor do IFPI desde 2014.',
  'photo': 'palestrante-justino.jpg',
  'order': 100},
 {'name': 'Aislan Rafael Rodrigues de Sousa',
  'session': '',
  'role': 'Professor do IFPI – Campus Teresina Central',
  'talk': '',
  'bio': 'Mestre em Engenharia de Software, professor do IFPI – Campus Teresina Central, '
         'Assistente em Ciência de Dados Pleno no IPEA, instrutor da Residência Tecnológica '
         'INOVATEC e cofundador das startups Bee Cerrado e Tiktests, com atuação em inteligência '
         'artificial, ciência de dados, inovação e desenvolvimento de software.',
  'photo': 'palestrante-aislan.jpg',
  'order': 110},
 {'name': 'Antônio Júnior',
  'session': '',
  'role': 'OxenteNet',
  'talk': '',
  'bio': '',
  'photo': 'palestrante-antonio.jpg',
  'order': 120},
 {'name': 'Mikael Costa Silva',
  'session': '',
  'role': 'Desenvolvedor · OxenteNet',
  'talk': '',
  'bio': 'Desenvolvimento e manutenção de sistemas.',
  'photo': 'palestrante-mikael.jpg',
  'order': 130},
 {'name': 'Patrícia de França Silva',
  'session': '',
  'role': 'Gestora de Processos',
  'talk': '',
  'bio': 'Responsável por coordenar e executar iniciativas de mapeamento, análise, desenho, '
         'implantação e melhoria contínua dos processos.',
  'photo': 'palestrante-patricia.jpg',
  'order': 140}]


def import_existing_speakers(apps, schema_editor):
    Speaker = apps.get_model("core", "Speaker")
    if Speaker.objects.exists():
        return
    images = Path(settings.BASE_DIR) / "core" / "static" / "images"
    for data in SPEAKERS:
        data = dict(data)
        photo = data.pop("photo")
        speaker = Speaker(**data)
        if photo:
            name = f"speakers/{photo}"
            if not default_storage.exists(name):
                with open(images / photo, "rb") as f:
                    name = default_storage.save(name, File(f))
            speaker.photo = name
        speaker.save()


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0009_speaker"),
    ]

    operations = [
        migrations.RunPython(import_existing_speakers, migrations.RunPython.noop),
    ]
