import os
import tempfile
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageDraw
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .domain import certificate_create
from .models import Certificate, CertificationSettings
from .rendering import certificate_url_fetcher


def png_bytes(background=False):
    image = Image.new("RGB", (1485, 1050) if background else (320, 80), "#fcfaf3" if background else "#236b48")
    draw = ImageDraw.Draw(image)
    if background:
        draw.rectangle((20, 20, 1465, 1030), outline="#236b48", width=8)
        draw.rectangle((20, 20, 1465, 150), fill="#236b48")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


@override_settings(STORAGES={
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
})
class CertificateTests(TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.override = override_settings(MEDIA_ROOT=self.directory.name)
        self.override.enable()
        self.addCleanup(self.override.disable)

    def test_can_generate_without_preexisting_settings_or_background(self):
        certificate = certificate_create("Ana Silva", "ana@example.com", "Evento", 24)
        response = self.client.get(certificate.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content.startswith(b"%PDF"))
        self.assertEqual(CertificationSettings.objects.count(), 1)

    def test_background_and_uploaded_editor_image_render_without_http(self):
        configuration = CertificationSettings.get_solo()
        configuration.default_background_image.save("fundo.png", ContentFile(png_bytes(True)))
        storage = configuration.default_background_image.storage
        name = storage.save("signatures/assinatura.png", ContentFile(png_bytes()))
        configuration.default_text = '<h1 style="text-align:center">CERTIFICADO</h1><p>Certificamos que <strong>{{Nome_Participante}}</strong> participou de {{Atividade}}, com carga horária de {{Carga_Horaria}} horas.</p><figure class="image" style="width:40mm"><img src="' + storage.url(name) + '"></figure><p style="text-align:center">Organização do evento</p>'
        configuration.save()
        certificate = certificate_create("Ana Maria da Silva", "ana@example.com", "Capivara Tech II", 24)
        with self.assertNoLogs("weasyprint", level="ERROR"):
            response = self.client.get(certificate.get_absolute_url())
        self.assertTrue(response.content.startswith(b"%PDF"))
        self.assertEqual(certificate.background_image.name, configuration.default_background_image.name)
        if os.environ.get("CERTIFICATE_QA_DIR"):
            target = Path(os.environ["CERTIFICATE_QA_DIR"])
            target.mkdir(parents=True, exist_ok=True)
            (target / "certificate.pdf").write_bytes(response.content)

    def test_existing_certificate_keeps_background_after_settings_change(self):
        configuration = CertificationSettings.get_solo()
        configuration.default_background_image.save("old.png", ContentFile(png_bytes(True)))
        certificate = certificate_create("Ana", "ana@example.com", "Evento", 12)
        previous = certificate.background_image.name
        configuration.default_background_image.save("new.png", ContentFile(png_bytes(True)))
        certificate.refresh_from_db()
        self.assertEqual(certificate.background_image.name, previous)
        self.assertNotEqual(previous, configuration.default_background_image.name)

    def test_fetcher_blocks_external_and_file_urls(self):
        fetch = certificate_url_fetcher("https://evento.example/")
        for url in ["file:///etc/passwd", "http://127.0.0.1/", "https://external.example/image.png", "https://evento.example/uploads/%2e%2e/secret"]:
            with self.subTest(url=url), self.assertRaises(ValueError):
                fetch(url)

    def test_editor_upload_requires_staff_and_returns_readable_local_image(self):
        endpoint = reverse("ck_editor_5_upload_file")
        response = self.client.post(endpoint, {"upload": SimpleUploadedFile("image.png", png_bytes(), content_type="image/png")})
        self.assertIn(response.status_code, (302, 403))
        user = get_user_model().objects.create_user("editor", is_staff=True)
        self.client.force_login(user)
        response = self.client.post(endpoint, {"upload": SimpleUploadedFile("image.png", png_bytes(), content_type="image/png")})
        self.assertEqual(response.status_code, 200)
        fetch = certificate_url_fetcher("http://testserver/")
        result = fetch("http://testserver" + response.json()["url"])
        self.assertEqual(result["string"], png_bytes())


@override_settings(STORAGES={
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
})
class CertificateLayoutTests(TestCase):
    """Layout com a identidade do site (sem imagem de fundo configurada)."""

    def render_html(self, certificate):
        with patch("certification.views.HTML") as html:
            html.return_value.write_pdf.return_value = b"%PDF-fake"
            response = self.client.get(certificate.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        return html.call_args.kwargs["string"]

    def test_default_text_says_event_or_workshop(self):
        from core.event_config import get_event_config
        from core.models import Workshop

        event = get_event_config()
        workshop = Workshop.objects.get_or_create(code="1", defaults={"name": "Teste", "workload": 8})[0]
        cases = [
            (event["name"], "participou do evento"),
            (workshop.name, "participou do minicurso"),
            ("Organização Geral", "participou da atividade"),
        ]
        for activity, expected in cases:
            with self.subTest(activity=activity):
                certificate = certificate_create("Ana Maria da Silva", "ana@example.com", activity, 8)
                html = self.render_html(certificate)
                self.assertIn(expected, html)
                self.assertIn("Ana Maria da Silva", html)
                self.assertIn("carga horária de <strong>8&nbsp;horas</strong>", html)

    def test_layout_shows_signature_issue_date_and_brand_fonts(self):
        import datetime

        configuration = CertificationSettings.get_solo()
        configuration.default_certifier_name = "Paul Symon Ribeiro"
        configuration.default_certifier_position = "Coordenador do Curso de Sistemas para Internet"
        configuration.save()
        certificate = certificate_create("Ana", "ana@example.com", "Evento", 24)
        Certificate.objects.filter(pk=certificate.pk).update(date=datetime.date(2026, 11, 13))
        html = self.render_html(certificate)
        self.assertIn("Paul Symon Ribeiro", html)
        self.assertIn("Coordenador do Curso de Sistemas para Internet", html)
        self.assertIn("13 de novembro de 2026", html)
        self.assertIn("certification/fonts/Sora-ExtraBold.ttf", html)
        self.assertIn("images/capivara-logo.svg", html)

    def test_issue_date_is_the_day_the_certificate_was_generated(self):
        from django.utils.timezone import localdate

        certificate = certificate_create("Ana", "ana@example.com", "Evento", 24)
        self.assertEqual(certificate.date, localdate())
        self.assertFalse(hasattr(CertificationSettings.get_solo(), "default_date"))

    def test_migration_moves_existing_certificates_to_their_generation_day(self):
        import datetime
        from importlib import import_module

        from django.apps import apps
        from django.utils import timezone

        certificate = certificate_create("Ana", "ana@example.com", "Evento", 24)
        generated = timezone.make_aware(datetime.datetime(2026, 11, 13, 22, 30))  # noite, horário local
        Certificate.objects.filter(pk=certificate.pk).update(created_at=generated, date=datetime.date(2026, 7, 10))
        import_module("certification.migrations.0005_issue_date_from_generation").use_generation_date(apps, None)
        certificate.refresh_from_db()
        self.assertEqual(certificate.date, datetime.date(2026, 11, 13))

    def test_real_pdf_renders_with_brand_fonts_without_errors(self):
        certificate = certificate_create("Giovanna Milena de Sousa Carvalho Santos", "g@example.com", "Evento", 24)
        with self.assertNoLogs("weasyprint", level="ERROR"):
            response = self.client.get(certificate.get_absolute_url())
        self.assertTrue(response.content.startswith(b"%PDF"))

    def test_migration_recognizes_the_legacy_default_text(self):
        from importlib import import_module

        from .models import LegacyCertificateTemplate

        migration = import_module("certification.migrations.0004_certificate_layout_text")
        self.assertEqual(migration.normalized(LegacyCertificateTemplate), migration.LEGACY)
        edited_by_editor = LegacyCertificateTemplate.replace("\n    ", "").replace("\n", "")
        self.assertEqual(migration.normalized(edited_by_editor), migration.LEGACY)


class PersonNameTests(TestCase):
    def test_formats_names_with_portuguese_rules(self):
        from .names import format_person_name

        cases = {
            "ADRIANO DA LUZ PEREIRA": "Adriano da Luz Pereira",
            "lucas negreiros da silva": "Lucas Negreiros da Silva",
            "Kamel De Santana Silva": "Kamel de Santana Silva",
            "thayla negreiros da rocha mata": "Thayla Negreiros da Rocha Mata",
            "Nara Letícia Gomes E Silva": "Nara Letícia Gomes e Silva",
            "Ulisses g. Lima": "Ulisses G. Lima",
            "Vitor Emanuel Paes De C. Miranda": "Vitor Emanuel Paes de C. Miranda",
            "pedro ii de alcântara": "Pedro II de Alcântara",
            "ANA-MARIA SOUSA": "Ana-Maria Sousa",
            "Ronald McDonald": "Ronald McDonald",
            "  JOSÉ   FRANCISCO  DE ARAÚJO ": "José Francisco de Araújo",
            "De Souza Lima": "De Souza Lima",
            "Allex": "Allex",
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(format_person_name(raw), expected)

    def test_certificate_stores_formatted_name_and_reuses_it(self):
        first = certificate_create("ADRIANO DA LUZ PEREIRA", "a@example.com", "Evento", 24)
        again = certificate_create("adriano da luz pereira", "a@example.com", "Evento", 24)
        self.assertEqual(first.participant_name, "Adriano da Luz Pereira")
        self.assertEqual(first.pk, again.pk)
        self.assertEqual(Certificate.objects.count(), 1)

    def test_migration_formats_existing_certificates(self):
        from importlib import import_module

        from django.apps import apps

        certificate = certificate_create("Ana", "ana@example.com", "Evento", 24)
        Certificate.objects.filter(pk=certificate.pk).update(participant_name="MARIA DE LOURDES")
        import_module("certification.migrations.0006_format_participant_names").format_existing_names(apps, None)
        certificate.refresh_from_db()
        self.assertEqual(certificate.participant_name, "Maria de Lourdes")


@override_settings(STORAGES={
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}, EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class CertificateEmailTests(TestCase):
    site = "https://capivaratech.example"

    def test_event_certificate_email_has_summary_button_and_embedded_logo(self):
        from .email import build_certificate_mail

        certificate = certificate_create("ADRIANO DA LUZ PEREIRA", "adriano@example.com", "Capivara Tech II", 24)
        message = build_certificate_mail(certificate, self.site)
        html = message.alternatives[0][0]
        url = f"{self.site}/certificado/{certificate.uuid}"
        self.assertEqual(message.to, ["adriano@example.com"])
        self.assertEqual(message.subject, "Capivara Tech II: seu certificado está disponível")
        self.assertIn("Parabéns, Adriano!", html)
        self.assertIn("Seu certificado do evento <strong", html)
        self.assertIn("Adriano da Luz Pereira", html)
        self.assertIn("24 horas", html)
        self.assertIn(f'href="{url}"', html)
        self.assertIn("Baixar meu certificado (PDF)", html)
        self.assertIn('src="cid:certificate-logo"', html)
        self.assertIn(url, message.body)
        self.assertIn("Content-ID: <certificate-logo>", message.message().as_string())

    def test_workshop_certificate_email_names_the_workshop(self):
        from core.models import Workshop

        from .email import build_certificate_mail

        workshop = Workshop.objects.create(code="97", name="Django Girls", capacity=10, workload=8)
        certificate = certificate_create("Ana Clara", "ana@example.com", workshop.name, workshop.workload)
        message = build_certificate_mail(certificate, self.site)
        html = message.alternatives[0][0]
        self.assertIn("minicurso Django Girls", message.subject)
        self.assertIn("Seu certificado do minicurso <strong", html)
        self.assertIn("Minicurso Django Girls", html)
        self.assertIn("8 horas", html)
        self.assertNotIn("&lt;", message.body)

    def test_task_sends_and_records_delivery(self):
        from django.core import mail

        from core.models import EmailDelivery

        from .email import send_certificate_mail

        certificate = certificate_create("Ana D'Ávila", "ana@example.com", "Capivara Tech II", 24)
        send_certificate_mail.call(certificate.pk, self.site)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Ana D'Ávila", mail.outbox[0].body)
        self.assertEqual(EmailDelivery.objects.get().kind, "Certificado")
        self.assertIsNone(send_certificate_mail.call(999999, self.site))

    def test_admin_action_queues_one_email_per_certificate(self):
        from django_tasks.backends.database.models import DBTaskResult

        admin_user = get_user_model().objects.create_superuser("cert-admin", "a@example.com", None)
        self.client.force_login(admin_user)
        first = certificate_create("Ana", "ana@example.com", "Capivara Tech II", 24)
        second = certificate_create("Bia", "bia@example.com", "Capivara Tech II", 24)
        response = self.client.post(reverse("admin:certification_certificate_changelist"), {
            "action": "send_certificate_email", "_selected_action": [first.pk, second.pk],
        }, follow=True)
        self.assertContains(response, "2 e-mails de certificado colocados na fila de envio.")
        self.assertEqual(DBTaskResult.objects.count(), 2)
        args = sorted(row.args_kwargs["args"][0] for row in DBTaskResult.objects.all())
        self.assertEqual(args, sorted([first.pk, second.pk]))


@override_settings(DEFAULT_FROM_EMAIL="Capivara Tech <certificados@example.com>")
class KactuzCertificateTests(TestCase):
    site = "https://capivaratech.example"

    def render_html(self, certificate):
        with patch("certification.views.HTML") as html:
            html.return_value.write_pdf.return_value = b"%PDF-fake"
            response = self.client.get(certificate.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        return html.call_args.kwargs["string"]

    def test_creates_course_certificate_once(self):
        from . import kactuz

        certificate, created = kactuz.certificate_create("AYLA MONIZE DIAS DOS REIS", " Ayla@Example.com ")
        self.assertTrue(created)
        self.assertEqual(certificate.layout, Certificate.KACTUZ)
        self.assertEqual(certificate.participant_name, "Ayla Monize Dias dos Reis")
        self.assertEqual(certificate.participant_email, "ayla@example.com")
        self.assertEqual(certificate.workload, 60)
        self.assertEqual(certificate.certifier_name, "Dann Luciano de Menezes")
        self.assertEqual(certificate.activity, "Projeto Kactuz: Formação em Lógica de Programação")
        again, created = kactuz.certificate_create("Ayla Monize Dias dos Reis", "ayla@example.com")
        self.assertFalse(created)
        self.assertEqual(again.pk, certificate.pk)

    def test_event_certificates_keep_the_capivara_layout(self):
        certificate = certificate_create("Ana", "ana@example.com", "Evento", 24)
        self.assertEqual(certificate.layout, Certificate.CAPIVARA)
        self.assertIn("capivara-logo", self.render_html(certificate))

    def test_layout_has_course_text(self):
        from . import kactuz

        certificate, _ = kactuz.certificate_create("Kayo César Assis Pereira da Mata", "kayo@example.com")
        html = self.render_html(certificate)
        self.assertIn("Kayo César Assis Pereira da Mata", html)
        self.assertIn("Certificado de conclusão", html)
        self.assertIn("carga horária de <strong>60&nbsp;horas</strong>", html)
        self.assertIn("de 3 de maio a 22 de agosto de 2026", html)
        self.assertNotIn("Conteúdo programático", html)
        self.assertIn("Coordenador do Projeto Kactuz", html)
        self.assertNotIn("capivara-logo", html)
        self.assertNotRegex(html, r"left: \d+,\d+mm")  # decimais com vírgula quebram o CSS

    def test_real_pdf_has_a_single_page(self):
        from . import kactuz

        certificate, _ = kactuz.certificate_create("Apollo Neri Siqueira Rubem de Macedo", "apollo@example.com")
        with self.assertNoLogs("weasyprint", level="ERROR"):
            response = self.client.get(certificate.get_absolute_url())
        self.assertTrue(response.content.startswith(b"%PDF"))

        from weasyprint import HTML

        base_url = "http://testserver/"
        html = self.render_html(certificate)
        document = HTML(string=html, base_url=base_url, url_fetcher=certificate_url_fetcher(base_url)).render()
        self.assertEqual(len(document.pages), 1)

    def test_email_uses_course_identity(self):
        from . import kactuz
        from .email import build_certificate_mail

        certificate, _ = kactuz.certificate_create("Wemerson Ferreira Fernandes", "wemerson@example.com")
        message = build_certificate_mail(certificate, self.site)
        html = message.alternatives[0][0]
        url = f"{self.site}/certificado/{certificate.uuid}"
        self.assertEqual(message.subject, "Projeto Kactuz: seu certificado de conclusão está disponível")
        self.assertEqual(message.from_email, "Projeto Kactuz · IFPI <certificados@example.com>")
        self.assertEqual(message.to, ["wemerson@example.com"])
        self.assertIn("Parabéns, Wemerson!", html)
        self.assertIn("60 horas", html)
        self.assertIn(f'href="{url}"', html)
        self.assertNotIn("Capivara", html)
        self.assertIn(url, message.body)
        self.assertIn('filename="projeto-kactuz.png"', message.message().as_string())

    def test_command_issues_from_list_and_queues_emails(self):
        from django.core.management import CommandError, call_command
        from django_tasks.backends.database.models import DBTaskResult

        path = os.path.join(tempfile.mkdtemp(), "alunos.csv")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("# nome;email\nAna Vitória;ana@example.com\nPedro Vitor\tpedro@example.com\n")
        call_command("emitir_certificados_kactuz", path, stdout=open(os.devnull, "w"))
        call_command("emitir_certificados_kactuz", path, "--enviar", self.site, stdout=open(os.devnull, "w"))
        self.assertEqual(Certificate.objects.filter(layout=Certificate.KACTUZ).count(), 2)
        self.assertEqual(DBTaskResult.objects.count(), 2)

        with open(path, "w", encoding="utf-8") as handle:
            handle.write("Sem email\n")
        with self.assertRaises(CommandError):
            call_command("emitir_certificados_kactuz", path, stdout=open(os.devnull, "w"))

    def test_admin_keeps_kactuz_in_its_own_list(self):
        from . import kactuz

        admin_user = get_user_model().objects.create_superuser("kactuz-admin", "a@example.com", None)
        self.client.force_login(admin_user)
        kactuz.certificate_create("Luccas Wender dos Santos", "luccas@example.com")
        certificate_create("Ana do Evento", "ana@example.com", "Capivara Tech II", 24)

        event_list = self.client.get(reverse("admin:certification_certificate_changelist"))
        self.assertContains(event_list, "Ana do Evento")
        self.assertNotContains(event_list, "Luccas Wender dos Santos")

        kactuz_list = self.client.get(reverse("admin:certification_kactuzcertificate_changelist"))
        self.assertContains(kactuz_list, "Luccas Wender dos Santos")
        self.assertNotContains(kactuz_list, "Ana do Evento")

        response = self.client.post(reverse("admin:certification_kactuzcertificate_add"), {
            "participant_name": "PABLO HENRIQUE ARAÚJO NEGREIROS", "participant_email": "Pablo@Example.com", "_save": "Salvar",
        })
        self.assertEqual(response.status_code, 302)
        pablo = Certificate.objects.get(participant_email="pablo@example.com")
        self.assertEqual(pablo.participant_name, "Pablo Henrique Araújo Negreiros")
        self.assertEqual((pablo.layout, pablo.workload, pablo.certifier_name), (Certificate.KACTUZ, 60, "Dann Luciano de Menezes"))
        self.assertEqual(pablo.activity, kactuz.ACTIVITY)

    def test_email_history_tells_kactuz_apart(self):
        from core.models import EmailDelivery

        from . import kactuz
        from .email import send_certificate_mail

        certificate, _ = kactuz.certificate_create("Anna Vitória Miranda Coelho", "anna@example.com")
        send_certificate_mail.call(certificate.pk, self.site)
        self.assertEqual(EmailDelivery.objects.get().kind, "Certificado Projeto Kactuz")
