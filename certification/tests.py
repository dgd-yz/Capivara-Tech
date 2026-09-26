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
