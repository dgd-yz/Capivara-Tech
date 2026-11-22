"""Emite os certificados de conclusão do Projeto Kactuz.

A lista de alunos vem de fora do repositório (que é público): um arquivo ou a entrada
padrão, uma linha por aluno, "Nome;email" (aceita também vírgula ou tabulação).

    python manage.py emitir_certificados_kactuz alunos.csv
    cat alunos.csv | python manage.py emitir_certificados_kactuz -
    ... --enviar https://capivaratech.sistemasparainternet.com   (põe os e-mails na fila)

Rodar de novo não duplica: quem já tem certificado é só listado.
"""
import re
import sys

from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.db import transaction

from certification import kactuz
from certification.email import send_certificate_mail


def parse_line(line):
    parts = [part.strip() for part in re.split(r"[;\t,]", line) if part.strip()]
    if len(parts) < 2:
        raise ValueError("esperado 'Nome;email'")
    name, email = parts[0], parts[1]
    validate_email(email)
    return name, email


class Command(BaseCommand):
    help = "Emite (e opcionalmente envia por e-mail) os certificados de conclusão do Projeto Kactuz."

    def add_arguments(self, parser):
        parser.add_argument("arquivo", help="Arquivo com 'Nome;email' por linha, ou - para ler da entrada padrão.")
        parser.add_argument("--enviar", metavar="URL_DO_SITE", help="Coloca na fila o e-mail de cada certificado, com links para este site.")

    def handle(self, *args, arquivo, enviar=None, **options):
        stream = sys.stdin if arquivo == "-" else open(arquivo, encoding="utf-8-sig")
        with stream:
            lines = [line.strip() for line in stream if line.strip() and not line.lstrip().startswith("#")]
        if not lines:
            raise CommandError("Nenhum aluno na lista.")

        students = []
        for number, line in enumerate(lines, 1):
            try:
                students.append(parse_line(line))
            except (ValueError, ValidationError) as error:
                raise CommandError(f"Linha {number} inválida ({line!r}): {error}")

        with transaction.atomic():
            results = [kactuz.certificate_create(name, email) for name, email in students]

        for certificate, created in results:
            status = "criado" if created else "já existia"
            self.stdout.write(f"{status:10} {certificate.participant_name} <{certificate.participant_email}> {certificate.get_absolute_url()}")
        total_created = sum(created for _, created in results)
        self.stdout.write(self.style.SUCCESS(f"{len(results)} certificados ({total_created} novos)."))

        if enviar:
            for certificate, _ in results:
                send_certificate_mail.enqueue(certificate.pk, enviar)
            self.stdout.write(self.style.SUCCESS(f"{len(results)} e-mails colocados na fila de envio."))
