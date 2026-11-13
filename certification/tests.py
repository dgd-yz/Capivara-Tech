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
