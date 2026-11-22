"""Certificados de conclusão do Projeto Kactuz (Formação em Lógica de Programação, IFPI).

O Kactuz não é o evento: usa o mesmo sistema de certificados, mas com layout, texto e
e-mail próprios. Os dados fixos do curso ficam aqui; nome e e-mail de cada aluno entram
pelo comando `emitir_certificados_kactuz` (a lista de alunos não vai para o repositório).
"""
import random

from .models import Certificate, CertificationSettings
from .names import format_person_name

NAME = "Projeto Kactuz"
COURSE = "Formação em Lógica de Programação"
ACTIVITY = f"{NAME}: {COURSE}"
WORKLOAD = 60
CERTIFIER_NAME = "Dann Luciano de Menezes"
CERTIFIER_POSITION = "Coordenador do Projeto Kactuz"
INSTITUTION = "Instituto Federal do Piauí"
CAMPUS = "Campus São Raimundo Nonato"
PERIOD_LABEL = "3 de maio a 22 de agosto de 2026"
TAGLINE = "Aprenda. Pratique. Evolua."

TEXT = (
    "<p>concluiu a <strong>Formação em Lógica de Programação</strong> do <strong>Projeto Kactuz</strong>, "
    "promovida pelo Instituto Federal do Piauí, Campus São Raimundo Nonato, de 3 de maio a 22 de agosto "
    "de 2026, na modalidade híbrida, com carga horária de <strong>{{Carga_Horaria}}&nbsp;horas</strong>.</p>"
)


def certificate_create(participant_name, participant_email):
    """Cria (ou devolve, se já existir) o certificado de conclusão do aluno."""
    participant_name = format_person_name(participant_name)
    participant_email = participant_email.strip().lower()
    existing = Certificate.objects.filter(
        participant_name=participant_name,
        participant_email__iexact=participant_email,
        activity=ACTIVITY,
    ).first()
    if existing:
        return existing, False
    certificate = Certificate(participant_name=participant_name, participant_email=participant_email)
    apply_course_data(certificate)
    certificate.save()
    return certificate, True


def apply_course_data(certificate):
    """Preenche tudo o que é igual para todos os alunos (usado também pelo admin)."""
    certificate.layout = Certificate.KACTUZ
    certificate.activity = ACTIVITY
    certificate.workload = WORKLOAD
    certificate.location = CertificationSettings.get_solo().default_location
    certificate.certifier_name = CERTIFIER_NAME
    certificate.certifier_position = CERTIFIER_POSITION
    certificate.text = TEXT


def matrix_digits(seed=7, columns=34, rows=13):
    """Colunas de dígitos que somem para baixo, como no cartaz do curso (sempre iguais: semente fixa)."""
    generator = random.Random(seed)
    digits = []
    step = 297 / columns
    for column in range(columns):
        x = round(column * step + generator.uniform(1, step - 2), 1)
        length = generator.randint(4, rows)
        start = generator.uniform(-6, 10)
        for row in range(length):
            y = round(start + row * 5.2, 1)
            if y < 3:
                continue
            fade = 1 - row / rows
            digits.append({"x": x, "y": y, "d": generator.randint(0, 9), "o": round(0.025 + 0.075 * fade * generator.uniform(0.4, 1), 3)})
    return digits


def context():
    return {
        "name": NAME,
        "course": COURSE,
        "institution": INSTITUTION,
        "campus": CAMPUS,
        "period_label": PERIOD_LABEL,
        "tagline": TAGLINE,
        "digits": matrix_digits(),
    }
